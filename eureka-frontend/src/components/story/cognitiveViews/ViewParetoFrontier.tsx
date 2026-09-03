import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { getAcfl } from '../../../domain/cognitiveView';
import { DataPendingState } from './primitives';

/**
 * S-1 · PARETO FRONTIER (structural visual for the Cognitive Story).
 *
 * WHY: the Story answers cognitive questions in text/tables, but (per L2 §16)
 * it should also REVEAL STRUCTURE. This view draws the REAL alternatives in the
 * satisfaction space (x = criterion A, y = criterion B) and highlights the
 * Pareto-optimal subset — the trade-off frontier — using ONLY
 * `acfl.normalized_scores` (+ declared `acfl.frontier` when the backend emits it).
 *
 * Hard rules:
 *  - Never invent a node/score. If `acfl.normalized_scores` is empty the view
 *    reports a truthful "DATA PENDING" state.
 *  - Alternatives are the REAL keys of `normalized_scores`; criteria are the REAL
 *    keys of each score row (mirrors the backend artifact_exporter derivation).
 *  - The frontier is DERIVED from the real satisfaction matrix (genuine Pareto
 *    dominance), the same mathematical rule the backend uses for rendering; if
 *    the backend declares `acfl.frontier`, it is reported alongside.
 *
 * The axes are the FIRST TWO real criteria. With only one criterion there is no
 * 2D Pareto space, so the view states that honestly instead of inventing one.
 */

const finite = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null;

/** Union of the per-alternative criterion keys (real), preserving first-seen order. */
function criteriaFromScores(scores: Record<string, Record<string, unknown>>): string[] {
  const out: string[] = [];
  for (const row of Object.values(scores)) {
    if (!row || typeof row !== 'object') continue;
    for (const k of Object.keys(row)) {
      if (!out.includes(k)) out.push(k);
    }
  }
  return out;
}

/** True if point `a` is strictly Pareto-dominated by `b` on the two projected axes. */
function isDominated(a: { x: number; y: number }, b: { x: number; y: number }): boolean {
  if (b.x < a.x || b.y < a.y) return false; // b is not >= a on both axes
  return b.x > a.x || b.y > a.y; // and strictly better on at least one
}

/** The non-dominated (Pareto-optimal) subset in the 2D satisfaction projection. */
function deriveFrontier2D(points: { alt: string; x: number; y: number }[]): string[] {
  return points
    .filter((a) => !points.some((b) => b !== a && isDominated(a, b)))
    .map((p) => p.alt);
}

/** Full multi-criteria Pareto-optimal set (mirrors backend artifact_exporter.pareto_frontier). */
function deriveFrontierMulti(alternatives: string[], scores: Record<string, Record<string, unknown>>): string[] {
  const dom = (y: string, x: string): boolean => {
    const ry = scores[y] || {};
    const rx = scores[x] || {};
    const keys = [...new Set([...Object.keys(ry), ...Object.keys(rx)])];
    if (!keys.length) return false;
    let strictly = false;
    for (const k of keys) {
      const vy = finite(ry[k]) ?? 0;
      const vx = finite(rx[k]) ?? 0;
      if (vy < vx) return false;
      if (vy > vx) strictly = true;
    }
    return strictly;
  };
  return alternatives.filter((a) => !alternatives.some((b) => b !== a && dom(b, a)));
}

export default function ViewParetoFrontier({ state }: { state: CanonicalWorkState }) {
  const acfl = useMemo(() => getAcfl(state) || {}, [state]);
  const scores = useMemo<Record<string, Record<string, unknown>>>(() => acfl.normalized_scores || {}, [acfl]);
  const declaredFrontier: string[] = useMemo(() => acfl.frontier || [], [acfl]);
  const alternatives = useMemo(
    () => Object.keys(scores).filter((a) => scores[a] && typeof scores[a] === 'object'),
    [scores],
  );
  const criteria = useMemo(() => criteriaFromScores(scores), [scores]);
  const hasScores = alternatives.length > 0 && criteria.length > 0;

  const multiFrontier = useMemo(
    () => (hasScores ? deriveFrontierMulti(alternatives, scores) : []),
    [hasScores, alternatives, scores],
  );

  if (!hasScores) {
    return (
      <DataPendingState
        reason="This view needs real per-alternative satisfaction scores to draw a Pareto frontier, but the backend did NOT emit `acfl.normalized_scores` for this work — so no frontier can be derived (it is not invented here)."
      />
    );
  }

  // 2D projection on the first two real criteria.
  const xC = criteria[0];
  const yC = criteria[1];

  if (criteria.length < 2) {
    return (
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 text-xs text-[var(--eureka-text-section)]">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Pareto frontier · satisfaction space
        </div>
        <div className="text-[var(--eureka-text-micro)]">
          Only one criterion was scored per alternative (<span className="font-mono">{xC}</span>), so there is no 2D
          trade-off space to draw a Pareto frontier. The real per-alternative satisfaction is
          shown in the per-alternative evaluation table instead.
        </div>
      </div>
    );
  }

  const points = alternatives.map((alt) => {
    const row = scores[alt] || {};
    return { alt, x: finite(row[xC]) ?? 0, y: finite(row[yC]) ?? 0, row };
  });
  const frontier2D = deriveFrontier2D(points);
  const frontierSet = new Set(frontier2D);
  // Sort frontier points ascending by x for a step (north-east) line.
  const frontierSorted = frontier2D
    .map((alt) => points.find((p) => p.alt === alt)!)
    .sort((a, b) => a.x - b.x);

  // Detect alternatives that project to the SAME satisfaction coordinates: the
  // backend data genuinely puts them on top of each other, so the view says so
  // rather than implying a separation that the state does not provide.
  const coordKey = (p: { x: number; y: number }) => `${p.x.toFixed(3)}/${p.y.toFixed(3)}`;
  const overlapGroups = points.reduce<Record<string, string[]>>((acc, p) => {
    const k = coordKey(p);
    (acc[k] ||= []).push(p.alt);
    return acc;
  }, {});
  const overlaps = Object.values(overlapGroups).filter((g) => g.length > 1);
  const overlapNote =
    overlaps.length > 0
      ? `Note: ${overlaps.map((g) => g.join(' = ')).join('; ')} share the same projected scores on these two criteria, so they overlap as a single point (a genuine data artifact, not a closeness judgment).`
      : '';

  const W = 560;
  const H = 320;
  const padX = 64;
  const padY = 42;
  const xFor = (v: number) => padX + v * (W - padX - 24);
  const yFor = (v: number) => H - padY - v * (H - padY - 24);

  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 space-y-2">
      <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">
        Pareto frontier · satisfaction space (real normalized scores)
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 320 }}>
        {/* axes */}
        <line x1={padX} y1={H - padY} x2={W - 12} y2={H - padY} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
        <line x1={padX} y1={H - padY} x2={padX} y2={14} stroke="rgba(255,255,255,0.15)" strokeWidth={1} />
        <text x={W - 14} y={H - padY + 18} fontSize={9} fill="#a1a1aa" textAnchor="end">{xC} →</text>
        <text x={14} y={18} fontSize={9} fill="#a1a1aa">{yC} ↑</text>
        {/* grid */}
        {[0.25, 0.5, 0.75].map((t) => (
          <g key={t}>
            <line x1={xFor(t)} y1={14} x2={xFor(t)} y2={H - padY} stroke="rgba(255,255,255,0.04)" />
            <line x1={padX} y1={yFor(t)} x2={W - 12} y2={yFor(t)} stroke="rgba(255,255,255,0.04)" />
          </g>
        ))}
        {/* Pareto front step line (real derived envelope) */}
        {frontierSorted.length > 1 && (
          <polyline
            points={frontierSorted.map((p) => `${xFor(p.x)},${yFor(p.y)}`).join(' ')}
            fill="none"
            stroke="#059669"
            strokeWidth={1.5}
            strokeDasharray="4 3"
          />
        )}
        {/* points */}
        {points.map((p) => {
          const onFront = frontierSet.has(p.alt);
          return (
            <g key={p.alt}>
              <circle
                cx={xFor(p.x)}
                cy={yFor(p.y)}
                r={onFront ? 8 : 5}
                fill={onFront ? '#059669' : '#3f3f46'}
                stroke={onFront ? '#0a0a0d' : 'rgba(255,255,255,0.25)'}
                strokeWidth={2}
              />
              <text
                x={xFor(p.x) + (onFront ? 11 : 8)}
                y={yFor(p.y) + 4}
                fontSize={10}
                fontFamily="monospace"
                fill={onFront ? '#059669' : '#a1a1aa'}
              >
                {p.alt}
                {onFront ? ' ●' : ''}
              </text>
              <title>{`${p.alt}\n${xC} = ${p.x}\n${yC} = ${p.y}`}</title>
            </g>
          );
        })}
      </svg>
      <div className="flex items-center gap-4 text-[9px] text-[var(--eureka-text-micro)] flex-wrap">
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#059669]" /> Pareto-optimal</span>
        <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#3f3f46]" /> dominated</span>
        <span>Axes = real normalized satisfaction (0..1); frontier = Pareto dominance of the projected two criteria.</span>
      </div>
      {declaredFrontier.length > 0 && (
        <div className="text-[9px] text-[var(--eureka-text-micro)]">
          Backend-declared ACFL frontier: <span className="font-mono">{declaredFrontier.join(', ')}</span>
        </div>
      )}
      <div className="text-[9px] text-[var(--eureka-text-micro)]">
        Multi-criteria Pareto-optimal set (all {criteria.length} criteria):{' '}
        <span className="font-mono">{multiFrontier.join(', ') || '—'}</span>
      </div>
      {overlapNote && <div className="text-[9px] text-[var(--eureka-text-micro)]">{overlapNote}</div>}
    </div>
  );
}
