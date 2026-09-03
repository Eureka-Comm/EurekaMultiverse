import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildAlternativeLandscapeView } from '../../../domain/cognitiveStory';
import {
  getPrescriptive,
  getSelectedAlternativeId,
  getApplicableCriteria,
  getPrescriptionConstraints,
  getAcfl,
} from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';

/**
 * WHAT ARE THE ALTERNATIVES? — the decision landscape.
 *
 * Positions the REAL prescriptive alternatives on a scatter using two
 * truth-preserving proxies (both derived from real counts, never invented
 * scores): impact ← count of expected_effects[], feasibility ← count of
 * constraints[]. The selected alternative is marked, and a WHY-SELECTED card is
 * built from real rationale/decision-rule/effects fields.
 */
export default function ViewAlternativeLandscape({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildAlternativeLandscapeView(state), [state]);
  const presc = getPrescriptive(state);
  const prescriptions: any[] = presc.prescriptions || [];
  const alternatives: any[] = prescriptions.flatMap((p) => p.alternatives || []);
  const selectedId = getSelectedAlternativeId(state);
  const criteria = getApplicableCriteria(state);
  const hardConstraints = getPrescriptionConstraints(state);

  if (view.cognitiveState === 'PENDING') {
    return <DataPendingState reason={view.dataPendingReason} />;
  }

  // Real derived proxies.
  const cols = alternatives.map((a) => ({
    a,
    impact: (a.expected_effects || []).length,
    feasibility: (a.constraints || []).length,
    desc: a.description || a.alternative_id,
  }));
  const maxImpact = Math.max(1, ...cols.map((c) => c.impact));
  const maxFeas = Math.max(1, ...cols.map((c) => c.feasibility));
  // Truthful disclosure: if every alternative carries the SAME real attribute
  // counts, the real proxy axes cannot separate them — say so instead of
  // implying a spread that the backend does not provide.
  const uniformCounts =
    cols.length > 1 &&
    new Set(cols.map((c) => `${c.impact}/${c.feasibility}`)).size === 1;

  const W = 560;
  const H = 320;
  const padX = 66;
  const padY = 42;

  const xFor = (feas: number) => padX + (feas / maxFeas) * (W - padX - 24);
  const yFor = (impact: number) => H - padY - (impact / maxImpact) * (H - padY - 24);

  // Lower feasibility proxy (fewer constraints) => further right (more feasible).
  const px = (c: { feasibility: number }) => xFor(Math.max(0, maxFeas - c.feasibility));

  const selected = alternatives.find((a) => a.alternative_id === selectedId);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{view.whatItShows}</div>
        <AskCopilotButton
          question={selectedId ? `¿Por qué ${selectedId} y no las demás alternativas?` : '¿Cómo se comparan las alternativas?'}
        />
      </div>

      {/* Real criteria + hard constraints that gate the landscape */}
      {(criteria.length > 0 || hardConstraints.length > 0) && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          {criteria.length > 0 && (
            <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
                Scoring criteria (real)
              </div>
              <ul className="space-y-1.5">
                {criteria.map((c: any) => (
                  <li key={c.criterion_id || c.target} className="text-[11px] flex items-center gap-1.5 flex-wrap">
                    <span className="text-[var(--eureka-text-section)]">{c.target || c.description}</span>
                    {c.direction && (
                      <span className={`text-[9px] font-mono ${c.direction === 'MAXIMIZE' ? 'text-[var(--eureka-signal-action)]' : 'text-[var(--eureka-signal-blocked)]'}`}>
                        {c.direction}
                      </span>
                    )}
                    {c.weight != null && <span className="text-[9px] font-mono text-[var(--eureka-text-metric)]">w={c.weight}</span>}
                    {c.threshold != null && <span className="text-[9px] font-mono text-[var(--eureka-text-micro)]">thr={c.threshold}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
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
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Scatter */}
        <div className="lg:col-span-2 rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            Decision landscape (real proxies)
          </div>
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 320 }}>
            {/* axes */}
            <line x1={padX} y1={H - padY} x2={W - 12} y2={H - padY} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
            <line x1={padX} y1={H - padY} x2={padX} y2={14} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
            <text x={W - 14} y={H - padY + 16} fontSize={9} fill="#a1a1aa" textAnchor="end">Feasibility proxy →</text>
            <text x={14} y={18} fontSize={9} fill="#a1a1aa">Impact proxy ↑</text>
            {/* grid lines */}
            {[1, 2, 3].map((n) => (
              <line key={n} x1={padX + (n / 3) * (W - padX - 24)} y1={14} x2={padX + (n / 3) * (W - padX - 24)} y2={H - padY} stroke="rgba(255,255,255,0.04)" />
            ))}
            {[1, 2].map((n) => (
              <line key={n} x1={padX} y1={14 + (n / 2) * (H - padY - 24)} x2={W - 12} y2={14 + (n / 2) * (H - padY - 24)} stroke="rgba(255,255,255,0.04)" />
            ))}
            {/* points */}
            {cols.map((c) => {
              const isSel = c.a.alternative_id === selectedId;
              const cx = px(c);
              const cy = yFor(c.impact);
              return (
                <g key={c.a.alternative_id}>
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSel ? 9 : 6}
                    fill={isSel ? '#059669' : '#2e8fff'}
                    stroke={isSel ? '#0a0a0d' : 'rgba(255,255,255,0.3)'}
                    strokeWidth={2}
                  />
                  <text
                    x={cx + (isSel ? 12 : 9)}
                    y={cy + 4}
                    fontSize={10}
                    fontFamily="monospace"
                    fill={isSel ? '#059669' : '#e4e4e7'}
                  >
                    {c.a.alternative_id}
                    {isSel ? ' ●' : ''}
                  </text>
                  <title>{`${c.a.alternative_id}\nEffects: ${c.impact}\nConstraints: ${c.feasibility}\n${c.desc}`}</title>
                </g>
              );
            })}
          </svg>
          <div className="flex items-center gap-4 mt-2 text-[9px] text-[var(--eureka-text-micro)]">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#059669]" /> SELECTED</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#2e8fff]" /> candidate</span>
            <span>Axes are real count proxies (expected_effects / constraints), not invented scores.</span>
          </div>
          {uniformCounts && (
            <div className="mt-1 text-[9px] text-[var(--eureka-text-micro)]">
              Note: all alternatives carry the same real attribute counts ({cols[0]?.impact} expected_effect(s) /
              {cols[0]?.feasibility} constraint(s)), so these real proxy axes cannot separate them — the
              proximity above is the backend data, not a closeness judgment.
            </div>
          )}
        </div>

        {/* WHY-SELECTED card */}
        <div className="rounded-lg border border-[var(--eureka-signal-action)] bg-[var(--eureka-surface-elevated)] p-3 flex flex-col gap-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-signal-action)] font-bold">
            Why selected
          </div>
          {selected ? (
            <>
              <div className="text-sm font-mono text-[var(--eureka-text-display)]">{selected.alternative_id}</div>
              <div className="text-xs text-[var(--eureka-text-section)]">{selected.description}</div>
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mt-1">Expected effects</div>
              {selected.expected_effects?.length ? (
                <ul className="space-y-1">
                  {selected.expected_effects.map((e: string, i: number) => (
                    <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                      <span className="text-[var(--eureka-signal-action)]">+</span>
                      <span>{e}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-[11px] text-[var(--eureka-text-micro)]">None recorded.</div>
              )}
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mt-1">Constraints</div>
              {selected.constraints?.length ? (
                <ul className="space-y-1">
                  {selected.constraints.map((c: string, i: number) => (
                    <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                      <span className="text-[var(--eureka-signal-blocked)]">—</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-[11px] text-[var(--eureka-text-micro)]">None recorded.</div>
              )}
              {prescriptions[0]?.rationale && (
                <div className="text-[10px] text-[var(--eureka-text-micro)] mt-1 border-t border-[var(--eureka-spatial-hairline)] pt-2">
                  <span className="uppercase tracking-wider text-[var(--eureka-text-label)]">Rationale: </span>
                  {prescriptions[0].rationale}
                </div>
              )}
              {prescriptions[0]?.decision_rule && (
                <div className="text-[10px] text-[var(--eureka-text-micro)]">
                  <span className="uppercase tracking-wider text-[var(--eureka-text-label)]">Decision rule: </span>
                  {prescriptions[0].decision_rule.status}
                </div>
              )}
            </>
          ) : (
            <div className="text-[11px] text-[var(--eureka-text-micro)]">No alternative selected yet.</div>
          )}
        </div>
      </div>

      {/* S-1: ACFL Pareto frontier — real satisfaction matrix, non-dominated set; DATA PENDING if absent. */}
      {(() => {
        const acfl = getAcfl(state);
        const ns: Record<string, Record<string, number>> = acfl.normalized_scores || {};
        const alts: string[] = (Array.isArray(acfl.alternatives) && acfl.alternatives.length ? acfl.alternatives : Object.keys(ns)) || [];
        const first = Object.values(ns)[0] as Record<string, number> | undefined;
        const crits: string[] = (Array.isArray(acfl.criteria) && acfl.criteria.length ? acfl.criteria : (first ? Object.keys(first) : [])) || [];
        const hasScores = alts.length > 0 && crits.length > 0 && Object.keys(ns).length > 0;
        if (!hasScores) {
          return (
            <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">ACFL Pareto frontier</div>
              <div className="text-[11px] text-[var(--eureka-text-micro)]">
                ACFL FRONTIER DATA PENDING — el estado no emitió normalized_scores.
              </div>
            </div>
          );
        }
        const weights: Record<string, number> = acfl.weights || {};
        const scoreOf = (a: string) => {
          const row = ns[a] || {}; let num = 0, den = 0;
          for (const c of crits) { const w = typeof weights[c] === 'number' ? weights[c] : 0.5; num += w * (row[c] || 0); den += w; }
          return den ? num / den : 0;
        };
        const dominates = (x: string, y: string) => {
          const rx = ns[x] || {}, ry = ns[y] || {}; let strictly = false;
          for (const c of crits) { const vx = rx[c] || 0, vy = ry[c] || 0; if (vx < vy) return false; if (vx > vy) strictly = true; }
          return strictly;
        };
        const declaredFrontier: string[] = Array.isArray(acfl.frontier) ? acfl.frontier.filter(Boolean) : [];
        const frontier: string[] = declaredFrontier.length
          ? declaredFrontier
          : alts.filter((a) => !alts.some((b) => b !== a && dominates(b, a)));
        return (
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
              ACFL Pareto frontier (real satisfaction)
            </div>
            <div className="flex flex-wrap gap-2">
              {alts.map((a) => {
                const f = frontier.includes(a);
                return (
                  <div key={a}
                    className={`px-2 py-1 rounded text-[11px] font-mono border ${f ? 'border-[var(--eureka-signal-action)] bg-[var(--eureka-surface-selected)] text-[var(--eureka-signal-action)]' : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-section)]'}`}>
                    {a} · {scoreOf(a).toFixed(3)}{f ? ' ★' : ''}
                  </div>
                );
              })}
            </div>
            <div className="text-[9px] text-[var(--eureka-text-micro)] mt-2">
              {declaredFrontier.length ? 'frontier declarado por ACFL' : 'frontier derivado por dominancia (no dominadas)'}.
              {' '}Ponderado con los weights de ACFL.
            </div>
          </div>
        );
      })()}

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
