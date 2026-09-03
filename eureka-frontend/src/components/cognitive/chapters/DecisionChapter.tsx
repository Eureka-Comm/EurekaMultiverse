import React, { useMemo } from 'react';
import type { HeroProps } from './types';
import { Kicker, MomentCell, Panel } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';

/**
 * 06 — DECISION. The DECISION FIELD. Two unmistakably distinct surfaces:
 *   · SYSTEM CANDIDATES  (the alternatives; recommended_option = a CANDIDATE label,
 *     never "selected")
 *   · HUMAN DECISION     (human_decision.selectedAlternativeId, HUMAN_AUTHORIZED,
 *     violet, visually dominant) — never read from recommendedOption.
 * A D3 field makes the selection relationship (selected_by) explicit, so the human
 * decision never looks like the system's own choice.
 */
export function DecisionChapter({ dto, graph, onSelectArtifact }: HeroProps) {
  const recommended = dto.recommendedOption;
  const human = dto.humanDecision;
  const hasDecision = !!human.selectedAlternativeId;
  const alternatives = dto.prescription?.alternatives || [];

  const artifactById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const select = (id: string) => {
    const art = artifactById.get(id);
    if (art) onSelectArtifact(art);
  };

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="06" title="Decision" sub="Human decision field" />
        <span className="ci-field-label">EM Prescriptor → HITL</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* HUMAN DECISION — the unmistakable, visually dominant marker */}
        <div
          className="lg:col-span-2 p-5 flex flex-col"
          style={{ border: '1.5px solid var(--eureka-signal-authority)', background: 'color-mix(in srgb, var(--eureka-signal-authority) 6%, var(--eureka-surface))' }}
        >
          <div className="flex items-center justify-between gap-2 mb-3">
            <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-authority)] uppercase flex items-center gap-2">
              <span style={{ width: 26, height: 3, background: 'var(--eureka-signal-authority)' }} />
              Human decision
            </div>
            <AuthorityChip authority="HUMAN_AUTHORIZED" />
          </div>
          {hasDecision ? (
            <div className="flex-1 flex flex-col justify-center">
              <div className="text-[10px] font-mono uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
                Selected alternative (from human_decision)
              </div>
              <div className="font-mono font-bold text-[40px] leading-none text-[var(--eureka-signal-authority)]">
                {human.selectedAlternativeId}
              </div>
              <div className="mt-4 grid grid-cols-1 gap-2">
                <MomentCell label="Decision id">{human.decisionId || 'DATA NOT AVAILABLE'}</MomentCell>
                <MomentCell label="Status">{human.status || 'PENDING'}</MomentCell>
                <MomentCell label="Authority"><AuthorityChip authority={human.authority} size="sm" /></MomentCell>
              </div>
              {human.preserved && (
                <div className="mt-3 text-[9px] text-[var(--eureka-text-micro)]">
                  Preserved from <span className="font-mono">human_decision</span> — never from recommended_option.
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-xs text-[var(--eureka-text-micro)]">
              DECISION PENDING — no human selection recorded (authority PENDING).
            </div>
          )}
        </div>

        {/* SYSTEM CANDIDATES */}
        <div className="lg:col-span-3 border border-[var(--eureka-spatial-hairline)] p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-cognitive)] uppercase">
              System candidates
            </div>
            <span className="text-[9px] font-mono text-[var(--eureka-text-micro)]">recommended_option is a CANDIDATE</span>
          </div>
          {alternatives.length ? (
            <div className="space-y-2">
              {alternatives.map((a) => {
                const isRec = a.id === recommended;
                const isHum = a.id === human.selectedAlternativeId;
                return (
                  <button
                    key={a.id}
                    onClick={() => select(a.id)}
                    className={`w-full flex items-start gap-3 border px-3 py-2.5 text-left transition-colors ${
                      isHum
                        ? 'border-[var(--eureka-signal-authority)] bg-[var(--eureka-surface-selected)]'
                        : isRec
                          ? 'border-[var(--eureka-signal-cognitive)] bg-[var(--eureka-signal-cognitive)]/5'
                          : 'border-[var(--eureka-spatial-hairline)] hover:border-[var(--eureka-signal-cognitive)]'
                    }`}
                  >
                    <span className="font-mono text-[12px] font-bold text-[var(--eureka-text-display)] shrink-0">{a.id}</span>
                    <span className="text-[11px] text-[var(--eureka-text-section)] flex-1">{a.description}</span>
                    <span className="shrink-0 flex items-center gap-1.5">
                      {isRec && <span className="text-[9px] font-mono text-[var(--eureka-signal-cognitive)]">RECOMMENDED</span>}
                      {isHum && <AuthorityChip authority="HUMAN_AUTHORIZED" label="SELECTED (HUMAN)" size="sm" />}
                    </span>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="text-xs text-[var(--eureka-text-micro)]">No alternatives proposed.</div>
          )}
          <div className="mt-2 text-[9px] text-[var(--eureka-text-micro)]">
            RECOMMENDED = EUREKA candidate (recommended_option). SELECTED = human_decision. Distinct surfaces — never conflated.
          </div>
        </div>
      </div>

      {/* DECISION FIELD — selection relationship */}
      <DecisionFieldDiagram alternatives={alternatives} humanSelected={human.selectedAlternativeId} recommended={recommended} onSelect={select} />

      {dto.projectionConflict && (
        <div className="ci-honest" style={{ borderColor: 'var(--eureka-signal-blocked)', background: 'var(--eureka-signal-blocked)/5' }}>
          <div className="ci-honest-label" style={{ color: 'var(--eureka-signal-blocked)' }}>⚠ Projection conflict</div>
          <p className="text-[11px] text-[var(--eureka-text-section)]">
            The action plan selects a different alternative than the human decision. Not autocorrected.
          </p>
        </div>
      )}
    </div>
  );
}

const FW = 840;
const FH = 250;

/** Deterministic columnar decision field: prescription → alternatives → decision. */
function DecisionFieldDiagram({
  alternatives,
  humanSelected,
  recommended,
  onSelect,
}: {
  alternatives: { id: string; description: string }[];
  humanSelected: string | null;
  recommended: string | null;
  onSelect: (id: string) => void;
}) {
  const rendered = useMemo(() => {
    const altNodes = alternatives.map((a, i) => {
      const isHum = a.id === humanSelected;
      const isRec = a.id === recommended;
      const y = FH / 2 + (i - (alternatives.length - 1) / 2) * 62;
      return { id: a.id, kind: 'ALT' as const, status: isHum ? 'HUMAN_SELECTED' : isRec ? 'RECOMMENDED' : 'CANDIDATE', x: FW * 0.46, y };
    });
    const prescNode = alternatives.length ? { id: 'PRESC', kind: 'PRESC' as const, status: 'prescription', x: FW * 0.14, y: FH / 2 } : null;
    const decNode = humanSelected ? { id: 'DEC', kind: 'DEC' as const, status: 'decision', x: FW * 0.84, y: FH / 2 } : null;
    const nodes = [...altNodes, ...(prescNode ? [prescNode] : []), ...(decNode ? [decNode] : [])];
    return { nodes };
  }, [alternatives, humanSelected, recommended]);

  if (alternatives.length === 0 && !humanSelected) return null;

  const pos = (id: string) => rendered.nodes.find((n) => n.id === id);

  return (
    <div className="border border-[var(--eureka-spatial-hairline)]">
      <div className="px-3 py-1.5 flex items-center justify-between gap-2">
        <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--eureka-text-label)]">
          Decision field · selected_by relationship (real)
        </span>
        <span className="text-[9px] font-mono text-[var(--eureka-text-micro)]">EM Prescriptor → HITL</span>
      </div>
      <svg viewBox={`0 0 ${FW} ${FH}`} className="w-full h-[250px] block">
        <g>
          {alternatives.map((a) => {
            const alt = pos(a.id);
            const presc = pos('PRESC');
            if (!alt || !presc) return null;
            return (
              <path key={`ap-${a.id}`} d={`M ${alt.x - 58} ${alt.y} L ${presc.x + 58} ${presc.y}`} stroke="#0969da" strokeWidth={1} fill="none" opacity={0.45} />
            );
          })}
          {alternatives.map((a) => {
            if (a.id !== humanSelected) return null;
            const alt = pos(a.id);
            const dec = pos('DEC');
            if (!alt || !dec) return null;
            return (
              <path key="sel" d={`M ${alt.x + 58} ${alt.y} L ${dec.x - 58} ${dec.y}`} stroke="#8250df" strokeWidth={1.6} fill="none" opacity={0.9} strokeDasharray="3 3" />
            );
          })}
          {pos('PRESC') && pos('DEC') && (
            <path d={`M ${pos('PRESC')!.x + 58} ${pos('PRESC')!.y} L ${pos('DEC')!.x - 58} ${pos('DEC')!.y}`} stroke="#8c959f" strokeWidth={1} fill="none" opacity={0.5} />
          )}
        </g>
        {rendered.nodes.map((n) => {
          const col = n.kind === 'DEC' ? '#8250df' : n.kind === 'PRESC' ? '#0969da' : n.status === 'HUMAN_SELECTED' ? '#8250df' : n.status === 'RECOMMENDED' ? '#0969da' : '#8c959f';
          const label = n.kind === 'DEC' ? 'HUMAN DECISION' : n.kind === 'PRESC' ? 'PRESCRIPTION' : n.id;
          const clickable = n.kind === 'ALT';
          return (
            <g
              key={n.id}
              transform={`translate(${n.x},${n.y})`}
              style={{ cursor: clickable ? 'pointer' : 'default' }}
              onClick={() => clickable && onSelect(n.id)}
            >
              <rect x={-58} y={-24} width={116} height={48} rx={4} fill="#fff" stroke={col} strokeWidth={n.kind === 'DEC' ? 2 : 1.2} />
              <text x={0} y={-4} textAnchor="middle" fontSize={9.5} fontFamily="var(--font-mono)" fontWeight={700} fill={col}>
                {label}
              </text>
              <text x={0} y={14} textAnchor="middle" fontSize={8} fontFamily="var(--font-mono)" fill="var(--eureka-text-micro)">
                {n.kind === 'ALT' ? (n.status === 'HUMAN_SELECTED' ? 'selected_by human' : n.status === 'RECOMMENDED' ? 'recommended (candidate)' : 'candidate') : n.status}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export default DecisionChapter;
