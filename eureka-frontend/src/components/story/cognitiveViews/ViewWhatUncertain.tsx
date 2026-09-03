import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildUncertainView } from '../../../domain/cognitiveStory';
import { getPredictive, finiteNum, getAcfl } from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';

/**
 * WHAT IS UNCERTAIN? — quantifies uncertainty ONLY where the real data carries it.
 * If a prediction has no uncertainty range / confidence / error metric, that is
 * reported as "Not quantified" (never invented).
 */
export default function ViewWhatUncertain({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildUncertainView(state), [state]);
  const predictive = getPredictive(state);
  const predictions: any[] = predictive.predictions || [];
  const acfl = getAcfl(state);
  const normalizedScores = acfl.normalized_scores || {};

  if (view.cognitiveState === 'PENDING') {
    const normKeys = Object.keys(normalizedScores);
    const hasNorm = normKeys.length > 0;
    const firstCrits = hasNorm
      ? Array.from(new Set(normKeys.flatMap((alt) => Object.keys((normalizedScores as any)[alt] || {}))))
      : [];
    return (
      <div className="space-y-4">
        <DataPendingState reason={view.dataPendingReason} />
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            Why there is no quantified uncertainty here
          </div>
          <div className="text-[11px] text-[var(--eureka-text-section)] space-y-1">
            <div>• predictive_knowledge.status = <b>{predictive.status || 'n/a'}</b> and predictions list is empty.</div>
            <div>• No numeric historical time-series was provided to the Predictor, so it cannot compute a real predicted_value / MSE / uncertainty range.</div>
            <div className="text-[var(--eureka-text-micro)]">The Copilot cannot state a numeric confidence; it will answer truthfully that uncertainty is not quantified.</div>
          </div>
        </div>
        {hasNorm && (
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
              What the evaluation does tell us · derived satisfaction (real criteria × real alternative text)
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-[var(--eureka-text-label)]">
                    <th className="text-left font-semibold pr-3">Alternative</th>
                    {firstCrits.map((c) => (
                      <th key={c} className="text-left font-semibold pr-3">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {normKeys.map((alt) => (
                    <tr key={alt} className="border-t border-[var(--eureka-spatial-hairline)]">
                      <td className="py-1.5 pr-3 font-mono text-[var(--eureka-signal-cognitive)]">{alt}</td>
                      {firstCrits.map((c) => {
                        const v = (normalizedScores as any)[alt]?.[c];
                        return (
                          <td key={c} className="py-1.5 pr-3 font-mono text-[var(--eureka-text-metric)]">
                            {v != null ? String(v) : '—'}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    );
  }

  let hasUncertaintyDatum = false;

  const cards = predictions.map((p) => {
    const unc = p.uncertainty || {};
    const ci: any = unc.confidence_interval;
    const ciLow = ci?.low ?? ci?.lower ?? ci?.min;
    const ciHigh = ci?.high ?? ci?.upper ?? ci?.max;
    const predicted = finiteNum(p.predicted_value);
    const baseline = finiteNum(p.baseline);
    const variance = finiteNum(unc.variance);
    const mse = finiteNum(p.mse);
    const metrics: Array<{ label: string; value: string }> = [];
    const isUncertain = unc.status === 'QUANTIFIED' || predicted != null || ciLow != null || ciHigh != null;

    if (predicted != null) metrics.push({ label: 'Expected value', value: String(predicted) });
    if (baseline != null) metrics.push({ label: 'Baseline', value: String(baseline) });
    if (predicted != null && baseline != null) {
      const delta = predicted - baseline;
      metrics.push({ label: 'Δ vs baseline', value: `${delta >= 0 ? '+' : ''}${delta}` });
    }
    if (p.units) metrics.push({ label: 'Units', value: p.units });
    if (ciLow != null || ciHigh != null) {
      metrics.push({
        label: 'Uncertainty range',
        value: `${ciLow ?? '—'} … ${ciHigh ?? '—'}`,
      });
    }
    if (variance != null) metrics.push({ label: 'Variance', value: String(variance) });
    if (mse != null) metrics.push({ label: 'MSE', value: String(mse) });
    if (unc.status === 'QUANTIFIED') metrics.push({ label: 'Uncertainty status', value: 'QUANTIFIED' });
    if (p.validation_status && p.validation_status !== 'NOT_EVALUATED') {
      metrics.push({ label: 'Validation', value: p.validation_status });
    }

    hasUncertaintyDatum = hasUncertaintyDatum || isUncertain;

    return (
      <div key={p.prediction_id} className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="text-[11px] font-mono text-[var(--eureka-text-display)]">{p.prediction_id}</div>
          <span className="text-[9px] font-mono uppercase text-[var(--eureka-signal-cognitive)]">
            {p.target_variable || 'target'}
          </span>
        </div>
        <div className="text-[11px] text-[var(--eureka-text-section)] mb-2">
          {p.model_type || 'MODEL'} · {p.model_definition || p.formula || 'formula not captured'}
        </div>
        {metrics.length ? (
          <div className="grid grid-cols-2 gap-2">
            {metrics.map((m) => (
              <div key={m.label} className="text-xs">
                <div className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">{m.label}</div>
                <div className="font-mono text-[var(--eureka-text-metric)] break-all">{m.value}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">
            No quantified uncertainty/error metric is recorded for this prediction.
          </div>
        )}
        {(unc.limitations || []).length > 0 && (
          <div className="mt-2 text-[10px] text-[var(--eureka-text-micro)]">
            Limitations: {unc.limitations.join('; ')}
          </div>
        )}
      </div>
    );
  });

  if (!cards.length) {
    return <DataPendingState reason="No predictions are recorded in the backend state." />;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">
          {view.whatItShows}
          {!hasUncertaintyDatum && (
            <span className="text-[var(--eureka-signal-blocked)]"> Uncertainty is not quantified by the predictor.</span>
          )}
        </div>
        <AskCopilotButton question="¿Cuánta incertidumbre hay en las predicciones?" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">{cards}</div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Uncertainty
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">{view.uncertainty}</div>
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Provenance
            </div>
            <ProvenanceList items={view.provenance} />
          </div>
        </div>
      </div>
    </div>
  );
}
