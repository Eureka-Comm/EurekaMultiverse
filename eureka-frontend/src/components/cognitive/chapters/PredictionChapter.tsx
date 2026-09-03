import React, { useMemo } from 'react';
import type { HeroProps } from './types';
import { Kicker, Honest, Panel } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';
import { statusColor } from '../cognitiveColors';
import ReactECharts from 'echarts-for-react';

/**
 * 04 — PREDICTION. The MATHEMATICAL SURFACE. Honest by construction:
 *   · ALWAYS surfaces the engine identity (ACFL_DETERMINISTIC · MathEngine · GCLV
 *     Eq 4.17) — the real model engine, never a fabricated figure.
 *   · ECharts renders a real numeric surface ONLY when a predicted value exists in
 *     the DTO. With NO such value it renders the explicit
 *     "MATHEMATICAL EVALUATION · NOT_EVALUATED" visual state — never a fake
 *     forecast, R², slope or optimum.
 */
export function PredictionChapter({ dto, graph, onSelectArtifact, selectedId }: HeroProps) {
  const predictions = dto.predictions || [];
  const artifactById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const select = (id: string) => {
    const art = artifactById.get(id);
    if (art) onSelectArtifact(art);
  };
  const anyValue = predictions.some((p) => typeof p.value === 'number' && Number.isFinite(p.value));
  const allNotEval = predictions.length > 0 && predictions.every((p) => /NOT_EVALUATED/i.test(p.status) || p.value == null);

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="04" title="Prediction" sub="Mathematical surface" />
        <span className="ci-field-label">EM Predictor · ACFL_DETERMINISTIC</span>
      </div>

      {/* Engine identity band — the real producing engine, never invented */}
      <div className="border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] px-4 py-3 flex flex-wrap items-center gap-x-8 gap-y-2">
        <IdentityField label="Engine" value="ACFL_DETERMINISTIC" big />
        <IdentityField label="Model" value="MathEngine" />
        <IdentityField label="Reference" value="GCLV · Eq 4.17" />
        <IdentityField label="Evaluated" value={`${predictions.length}`} />
      </div>

      {/* Honest evaluation state */}
      {allNotEval && (
        <Honest label="MATHEMATICAL EVALUATION · NOT EVALUATED">
          The ACFL math engine emitted no numeric predicted value for this work. No forecast, goodness-of-fit, slope or
          optimum is shown — these are not available in the governed state and are never fabricated.
        </Honest>
      )}

      {anyValue ? (
        <Panel title={`Mathematical surface · ${predictions.filter((p) => typeof p.value === 'number').length} evaluated`} accent="var(--eureka-signal-cognitive)">
          <MathSurface predictions={predictions} />
        </Panel>
      ) : (
        <div className="ci-panel">
          <div className="ci-panel-title">Signal structure · predictor → evaluation (real)</div>
          <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-3 content-start">
            {predictions.length === 0 ? (
              <Honest label="DATA NOT AVAILABLE" tone="var(--eureka-text-technical)" >The predictor has not emitted a mathematical model for this work.</Honest>
            ) : (
              predictions.map((p) => (
                <button
                  key={p.id}
                  onClick={() => select(p.id)}
                  className={`border p-3 text-left transition-colors ${selectedId === p.id ? 'border-[var(--eureka-signal-cognitive)]' : 'border-[var(--eureka-spatial-hairline)] hover:border-[var(--eureka-signal-cognitive)]'}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[9px] font-mono uppercase text-[var(--eureka-text-micro)]">{p.id}</span>
                    {p.value == null ? (
                      <span className="inline-flex items-center gap-1 text-[9px] font-mono uppercase border rounded px-1.5 py-0.5" style={{ color: statusColor('NOT_EVALUATED'), borderColor: statusColor('NOT_EVALUATED') }}>
                        not evaluated
                      </span>
                    ) : (
                      <span className="text-[11px] font-mono text-[var(--eureka-text-metric)]">{p.value}</span>
                    )}
                  </div>
                  <div className="mt-1.5 text-[12px] font-semibold text-[var(--eureka-text-display)]">{p.predictorVariables.join(', ') || p.modelType}</div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1">
                    <span className="text-[9px] font-mono text-[var(--eureka-text-label)]">{p.modelType}</span>
                    <span className="text-[9px] font-mono text-[var(--eureka-text-label)]">GCLV Eq 4.17</span>
                  </div>
                  <div className="mt-1.5"><AuthorityChip authority={p.authority} size="sm" /></div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function IdentityField({ label, value, big }: { label: string; value: string; big?: boolean }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="ci-field-label">{label}</span>
      <span className={`${big ? 'font-[var(--font-display)] font-semibold text-[15px]' : 'font-mono text-[12px]'} text-[var(--eureka-text-display)]`}>
        {value}
      </span>
    </div>
  );
}

/** ECharts scatter/surface — rendered ONLY when a real numeric value exists. */
function MathSurface({ predictions }: { predictions: HeroProps['dto']['predictions'] }) {
  const withValue = predictions.filter((p) => typeof p.value === 'number' && Number.isFinite(p.value));

  const option = useMemo(() => {
    const names = withValue.map((p, i) => p.predictorVariables.join('/') || `P${i + 1}`);
    return {
      backgroundColor: 'transparent',
      grid: { left: 44, right: 20, top: 20, bottom: 36 },
      tooltip: { trigger: 'axis' },
      xAxis: { type: 'category', data: names, axisLine: { lineStyle: { color: 'var(--eureka-spatial-hairline)' } }, axisLabel: { color: 'var(--eureka-text-label)', fontFamily: 'var(--font-mono)' }, nameTextStyle: { color: 'var(--eureka-text-label)', fontFamily: 'var(--font-mono)' } },
      yAxis: { type: 'value', name: 'predicted value', axisLabel: { color: 'var(--eureka-text-label)' }, splitLine: { lineStyle: { type: 'dashed', color: 'var(--eureka-spatial-grid)' } } },
      series: [
        {
          type: 'line',
          smooth: true,
          data: withValue.map((p) => p.value),
          symbolSize: 8,
          lineStyle: { width: 2, color: '#0f6e6e' },
          itemStyle: { color: '#0f6e6e' },
        },
      ],
    };
  }, [withValue]);

  return <ReactECharts option={option} style={{ height: 270, width: '100%' }} notMerge />;
}

export default PredictionChapter;
