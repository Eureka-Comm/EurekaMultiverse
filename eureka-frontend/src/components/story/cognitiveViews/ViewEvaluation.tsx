import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildEvaluationView } from '../../../domain/cognitiveStory';
import {
  getAcfl,
  getApplicableCriteria,
  getPrescriptionConstraints,
  getSelectedAlternativeId,
} from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';
import ViewParetoFrontier from './ViewParetoFrontier';

/**
 * HOW WERE THE OPTIONS SCORED? — the REAL evaluation surface.
 *
 * Renders the genuine "score" input the backend emits for this work:
 *   - prescriptions[].applicable_criteria[] (criterion_id / target / direction /
 *     threshold / weight / authority / provenance) — the REAL weighted criteria.
 *   - acfl.weights (e.g. cost=50, risk=50).
 *   - prescriptions[].constraints[] — the hard invariants (availability, budget…).
 *   - acfl.normalized_scores[eid][crit] — the REAL per-alternative normalized
 *     score, IF the backend emits it; otherwise a truthful "not emitted" state.
 *
 * It never invents a per-alternative score.
 */
export default function ViewEvaluation({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildEvaluationView(state), [state]);
  const criteria = getApplicableCriteria(state);
  const acfl = getAcfl(state);
  const weights: Record<string, number> = acfl.weights || {};
  const normalizedScores = acfl.normalized_scores || {};
  const hardConstraints = getPrescriptionConstraints(state);
  const alternatives = getAlternatives(state);
  const selectedId = getSelectedAlternativeId(state);

  if (view.cognitiveState === 'PENDING') {
    return <DataPendingState reason={view.dataPendingReason} />;
  }

  const hasPerAlternativeScores = Object.keys(normalizedScores).length > 0;
  const criteriaList = criteria.length ? criteria : null;

  // Some backend runs emit numeric criterion weight/threshold; others emit null.
  // Report which surface is real so the table never implies a weight that the
  // state does not actually carry.
  const criteriaHaveWeights = criteria.some((c) => typeof c.weight === 'number');
  // Sum real weights for a raw percentage readout (truthful total, may not be 1.0).
  const totalWeight = criteria.reduce((acc, c) => acc + (typeof c.weight === 'number' ? c.weight : 0), 0);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{view.whatItShows}</div>
        <AskCopilotButton question="¿Cómo se puntuaron las opciones y por qué se eligió esta?" />
      </div>

      {/* Real weighted criteria table */}
      {criteriaList && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            {criteriaHaveWeights ? 'Weighted criteria (real)' : 'Applicable criteria (real)'}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-[var(--eureka-text-label)]">
                  <th className="text-left font-semibold pr-3">Criterion</th>
                  <th className="text-left font-semibold pr-3">Direction</th>
                  <th className="text-left font-semibold pr-3">Threshold</th>
                  <th className="text-left font-semibold pr-3">Weight</th>
                  <th className="text-left font-semibold">Authority</th>
                </tr>
              </thead>
              <tbody>
                {criteria.map((c: any, i: number) => {
                  const w = typeof c.weight === 'number' ? c.weight : null;
                  const pct = w != null && totalWeight > 0 ? `${((w / totalWeight) * 100).toFixed(0)}%` : '—';
                  return (
                    <tr key={c.criterion_id || i} className="border-t border-[var(--eureka-spatial-hairline)]">
                      <td className="py-1.5 pr-3 text-[var(--eureka-text-section)]">
                        <div className="font-mono text-[var(--eureka-signal-scientific)]">{c.criterion_id || 'CRIT'}</div>
                        <div className="text-[10px]">{c.description || c.target}</div>
                      </td>
                      <td className="py-1.5 pr-3 text-[var(--eureka-text-section)]">
                        <span className={c.direction === 'MAXIMIZE' ? 'text-[var(--eureka-signal-action)]' : 'text-[var(--eureka-signal-blocked)]'}>
                          {c.direction || 'N/A'}
                        </span>
                      </td>
                      <td className="py-1.5 pr-3 font-mono text-[var(--eureka-text-metric)]">{c.threshold ?? '—'}</td>
                      <td className="py-1.5 pr-3 font-mono text-[var(--eureka-text-metric)]">{w ?? '—'} {pct}</td>
                      <td className="py-1.5 text-[10px] text-[var(--eureka-text-micro)]">{c.authority || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {criteriaList && (
              <div className="mt-1 text-[10px] text-[var(--eureka-text-micro)]">
                {criteriaHaveWeights
                  ? `Sum of raw criterion weights = ${totalWeight.toFixed(2)}. These are the real weights used to score the alternatives.`
                  : `The backend emitted these criteria without numeric weight/threshold (weight = null) for this work, so no weighted score surface is derivable.`}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ACFL weights */}
      {Object.keys(weights).length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {Object.entries(weights).map(([k, v]) => (
            <div key={k} className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">{k}</div>
              <div className="font-mono text-[var(--eureka-text-metric)]">{v}</div>
              <div className="text-[9px] text-[var(--eureka-text-micro)]">ACFL weight</div>
            </div>
          ))}
        </div>
      )}

      {/* Hard constraints */}
      {hardConstraints.length > 0 && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            Hard constraints (invariants)
          </div>
          <ul className="space-y-1">
            {hardConstraints.map((c: string, i: number) => (
              <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                <span className="text-[var(--eureka-signal-blocked)]">▣</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Per-alternative scoring: real normalized_scores, else truthful not-emitted */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Per-alternative evaluation · derived satisfaction (real criteria × real alternative text)
        </div>
        {hasPerAlternativeScores ? (
          <div className="overflow-x-auto">
            <table className="w-full text-[11px]">
              <thead>
                <tr className="text-[var(--eureka-text-label)]">
                  <th className="text-left font-semibold pr-3">Alternative</th>
                  {Object.keys(normalizedScores[Object.keys(normalizedScores)[0]] || {}).map((crit) => (
                    <th key={crit} className="text-left font-semibold pr-3">{crit}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {Object.entries(normalizedScores).map(([alt, scores]) => (
                  <tr key={alt} className="border-t border-[var(--eureka-spatial-hairline)]">
                    <td className="py-1.5 pr-3 font-mono text-[var(--eureka-signal-cognitive)]">{alt}</td>
                    {Object.entries((scores as any) || {}).map(([crit, val]) => (
                      <td key={crit} className="py-1.5 pr-3 font-mono text-[var(--eureka-text-metric)]">{String(val)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex flex-col gap-1">
            <div className="text-[11px] text-[var(--eureka-text-micro)]">
              DATA PENDING — the backend does NOT emit per-alternative normalized scores for this work
              (acfl.normalized_scores, evaluated_scores and rankings are all empty). The evaluation is carried
              by the real criterion weights/thresholds above and the real alternative attributes, not by a
              fabricated numeric score.
            </div>
            {alternatives.length > 0 && (
              <div className="mt-1 text-[10px] text-[var(--eureka-text-label)]">
                Alternatives evaluated: {alternatives.map((a: any) => a.alternative_id).join(', ')}
                {selectedId ? ` · selected: ${selectedId}` : ''}
              </div>
            )}
          </div>
        )}
      </div>

      {/* S-1: structural Pareto frontier visual, drawn from the REAL acfl.normalized_scores.
          Self-guarding -> renders a truthful DATA PENDING state when the backend emits no scores. */}
      <ViewParetoFrontier state={state} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Uncertainty / gap
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

/** Real alternatives across all prescriptions. */
function getAlternatives(state: CanonicalWorkState): any[] {
  const presc = (state as any)?.prescriptive_knowledge || {};
  const prescriptions: any[] = presc.prescriptions || [];
  return prescriptions.flatMap((p) => p.alternatives || []);
}
