import React, { useMemo, useState } from 'react';
import type { HeroProps } from './types';
import { Kicker } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';
import { statusColor } from '../cognitiveColors';
import { scalePoint } from 'd3';

/**
 * 03 — DISCOVERY. The evidence/finding LANDSCAPE (a visual scene, not a card
 * grid). Findings are laid out by a force model, colored by their real status
 * (VALIDATED / UNSUPPORTED / NOT_EVALUATED) and linked to the evidence they were
 * derived from via real `derived_from` edges. The header filters by status.
 * Clicking a finding opens the contextual Inspector (and highlights its lineage).
 *
 * Data strictly from the single DTO. Nothing is scored or inferred here.
 */
type StatusFilter = 'ALL' | 'VALIDATED' | 'UNSUPPORTED' | 'NOT_EVALUATED';

const FILTERS: StatusFilter[] = ['ALL', 'VALIDATED', 'UNSUPPORTED', 'NOT_EVALUATED'];

interface FRect {
  id: string;
  kind: 'FINDING' | 'EVIDENCE';
  x: number;
  y: number;
  w: number;
  h: number;
}

const VIEW_W = 940;
const VIEW_H = 430;

/**
 * Deterministic landscape layout. Findings are laid across a gentle terrain band
 * (x spread, y wavers) so the surface is used rather than clustered in the middle;
 * evidence sits in a lower band. This is a "landscape", not a table or a card grid.
 */
function useLandscape(dto: HeroProps['dto'], filter: StatusFilter) {
  return useMemo(() => {
    const findings = dto.findings.filter((f) => filter === 'ALL' || f.status === filter);
    const evidenceIds = new Set(findings.flatMap((f) => f.evidenceRefs));
    const evidence = dto.evidence.filter((e) => evidenceIds.has(e.id) || findings.length === 0);

    // X scales spread the kinds across the whole width.
    const xF = scalePoint<string>().domain(findings.map((f) => f.id)).range([70, VIEW_W - 70]).padding(0.4);
    const xE = scalePoint<string>().domain(evidence.map((e) => e.id)).range([110, VIEW_W - 110]).padding(0.3);

    const FW = 196;
    const FH = 66;
    const EW = 150;
    const EH = 44;

    const rects: FRect[] = [];
    findings.forEach((f, i) => {
      const cx = xF(f.id) ?? VIEW_W / 2;
      const cy = 176 + 44 * Math.sin(i * 1.15) + (i % 2 === 0 ? -18 : 14);
      rects.push({ id: f.id, kind: 'FINDING', x: Math.max(12, cx - FW / 2), y: Math.max(24, Math.min(VIEW_H - 120, cy - FH / 2)), w: FW, h: FH });
    });
    evidence.forEach((e) => {
      const cx = xE(e.id) ?? VIEW_W / 2;
      const cy = VIEW_H - 46;
      rects.push({ id: e.id, kind: 'EVIDENCE', x: Math.max(12, cx - EW / 2), y: Math.max(24, Math.min(VIEW_H - 20, cy - EH / 2)), w: EW, h: EH });
    });

    // Real derived_from links (finding -> evidence).
    const links: Array<{ source: string; target: string }> = [];
    const byId = new Map(rects.map((r) => [r.id, r]));
    findings.forEach((f) =>
      f.evidenceRefs.forEach((ref) => {
        if (byId.has(ref) && byId.has(f.id)) links.push({ source: f.id, target: ref });
      }),
    );

    return { findings, evidence, rects, links };
  }, [dto, filter]);
}

export function DiscoveryChapter({ dto, graph, onSelectArtifact, selectedId }: HeroProps) {
  const [filter, setFilter] = useState<StatusFilter>('ALL');
  const { findings, rects, links } = useLandscape(dto, filter);

  const findingById = useMemo(() => new Map(dto.findings.map((f) => [f.id, f])), [dto.findings]);
  const artifactById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const select = (id: string) => {
    const art = artifactById.get(id);
    if (art) onSelectArtifact(art);
  };

  const hasUnsupported = dto.findings.some((f) => f.status === 'UNSUPPORTED');
  const hasNotEval = dto.findings.some((f) => f.status === 'NOT_EVALUATED');

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="03" title="Discovery" sub="Evidence → finding landscape" />
        <div className="flex items-center gap-1.5">
          {FILTERS.map((f) => {
            const active = filter === f;
            const visible = f === 'UNSUPPORTED' ? hasUnsupported : f === 'NOT_EVALUATED' ? hasNotEval : true;
            if (!visible) return null;
            return (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-2 py-1 text-[9px] font-mono uppercase tracking-wider rounded border transition-colors ${
                  active
                    ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-text-display)] bg-[var(--eureka-surface-selected)]'
                    : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)]'
                }`}
              >
                {f}
              </button>
            );
          })}
        </div>
      </div>

      {findings.length === 0 && filter !== 'ALL' ? (
        <div className="ci-empty">
          <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">
            No {filter} findings
          </div>
          <p className="text-xs">EU REKA does not fabricate findings for a status that is absent from the governed state.</p>
        </div>
      ) : findings.length === 0 ? (
        <div className="ci-empty">
          <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">No governed findings</div>
          <p className="text-xs">DATA NOT AVAILABLE — no findings emitted for this work yet.</p>
        </div>
      ) : (
        <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="w-full h-[430px] block" role="img" aria-label="Discovery landscape: findings linked to evidence">
          {/* links */}
          <g>
            {links.map((l, i) => {
              const s = rects.find((r) => r.id === l.source);
              const t = rects.find((r) => r.id === l.target);
              if (!s || !t) return null;
              const x1 = s.x + s.w / 2;
              const y1 = s.y + s.h;
              const x2 = t.x + t.w / 2;
              const y2 = t.y;
              const mx = (x1 + x2) / 2;
              const my = (y1 + y2) / 2;
              return (
                <path
                  key={i}
                  d={`M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`}
                  stroke="#8c959f"
                  strokeWidth={1}
                  fill="none"
                  strokeDasharray="2 3"
                  opacity={0.7}
                />
              );
            })}
          </g>

          {/* evidence pods */}
          {rects
            .filter((r) => r.kind === 'EVIDENCE')
            .map((r) => (
              <g key={`e-${r.id}`} transform={`translate(${r.x},${r.y})`}>
                <rect width={r.w} height={r.h} rx={3} fill="#fff" stroke="#8250df" strokeWidth={1} />
                <text x={10} y={17} fontSize={9} fontFamily="var(--font-mono)" fill="#8250df" fontWeight={600}>
                  {r.id}
                </text>
                <text x={10} y={31} fontSize={8} fontFamily="var(--font-mono)" fill="var(--eureka-text-micro)">
                  evidence
                </text>
              </g>
            ))}

          {/* finding cards */}
          {rects
            .filter((r) => r.kind === 'FINDING')
            .map((r) => {
              const f = findingById.get(r.id);
              const col = statusColor(f?.status);
              const isActive = selectedId === r.id;
              return (
                <g
                  key={`f-${r.id}`}
                  transform={`translate(${r.x},${r.y})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => select(r.id)}
                >
                  <rect
                    width={r.w}
                    height={r.h}
                    rx={3}
                    fill="#fff"
                    stroke={col}
                    strokeWidth={isActive ? 2 : 1.2}
                    filter={isActive ? 'url(#ci-active-glow)' : undefined}
                  />
                  <text x={10} y={16} fontSize={9} fontFamily="var(--font-mono)" fill={col} fontWeight={700}>
                    FINDING
                  </text>
                  <text x={r.w - 10} y={16} fontSize={8} fontFamily="var(--font-mono)" fill="var(--eureka-text-micro)" textAnchor="end">
                    {r.id}
                  </text>
                  <text x={10} y={33} fontSize={8.5} fill="var(--eureka-text-section)" style={{ fontFamily: 'var(--font-sans)' }}>
                    {truncate(f?.statement || 'DATA NOT AVAILABLE', 34)}
                  </text>
                  <text x={10} y={49} fontSize={8} fontFamily="var(--font-mono)" fill={col}>
                    {f?.status || 'UNSUPPORTED'}
                  </text>
                </g>
              );
            })}

          <defs>
            <filter id="ci-active-glow" x="-40%" y="-40%" width="180%" height="180%">
              <feGaussianBlur stdDeviation="2.2" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>
        </svg>
      )}

      <div className="flex items-center justify-between flex-wrap gap-2 mt-2">
        <div className="ci-legend">
          {(findings.length ? Array.from(new Set(findings.map((f) => f.status))) : []).map((s) => (
            <span key={s} className="ci-legend-item">
              <span className="ci-legend-dot" style={{ color: statusColor(s), background: `${statusColor(s)}14` }} />
              {s}
            </span>
          ))}
        </div>
        <div className="text-[9px] text-[var(--eureka-text-micro)]">
          Links are real <span className="font-mono">derived_from</span> edges only. Click a finding to inspect its lineage.
        </div>
      </div>
    </div>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

export default DiscoveryChapter;
