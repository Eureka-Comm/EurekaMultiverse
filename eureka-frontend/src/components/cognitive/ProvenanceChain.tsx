import React, { useMemo } from 'react';
import type { CognitiveProjectionDTO } from '../../domain/cognitiveProjection';
import { buildCognitiveProjectionGraph, type GraphArtifact, type NodeKind } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from './AuthorityChip';

/**
 * §11 — Provenance / Lineage.
 *
 * A navigable chain EVI→FND→PRED→PRESC→DEC→ACT→EXEC→RESULT→FROZEN using REAL
 * artifact ids. A step that was not emitted by the backend renders
 * "DATA NOT AVAILABLE" — never a fabricated id. Clicking a real step opens the
 * inspector.
 */

const ORDER: Array<{ kind: NodeKind; title: string }> = [
  { kind: 'EVIDENCE', title: 'Evidence' },
  { kind: 'FINDING', title: 'Finding' },
  { kind: 'PREDICTION', title: 'Prediction' },
  { kind: 'PRESCRIPTION', title: 'Prescription' },
  { kind: 'DECISION', title: 'Decision' },
  { kind: 'ACTION', title: 'Action' },
  { kind: 'EXECUTION', title: 'Execution' },
  { kind: 'RESULT', title: 'Result' },
  { kind: 'FROZEN', title: 'Frozen' },
];

export function ProvenanceChain({
  dto,
  onSelect,
}: {
  dto: CognitiveProjectionDTO;
  onSelect?: (artifact: GraphArtifact) => void;
}) {
  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);

  const steps = useMemo(() => {
    return ORDER.map((o) => {
      const art = graph.nodes.find((n) => n.kind === o.kind);
      return { kind: o.kind, title: o.title, artifact: art || null };
    });
  }, [graph]);

  const hasAny = steps.some((s) => s.artifact);

  if (!hasAny) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-6 text-center">
        <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">No lineage</div>
        <p className="text-xs text-[var(--eureka-text-label)] mt-1">
          DATA NOT AVAILABLE — no provenance chain has been emitted by the backend.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-3">
      <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-text-label)] uppercase mb-3">
        Provenance / Lineage
      </div>
      <div className="flex flex-wrap items-stretch gap-y-2">
        {steps.map((s, i) => (
          <React.Fragment key={s.kind}>
            {i > 0 && (
              <div className="flex items-center px-1.5 text-[10px] text-[var(--eureka-text-micro)] shrink-0">→</div>
            )}
            {s.artifact ? (
              <button
                onClick={() => onSelect?.(s.artifact!)}
                className="group min-w-[118px] max-w-[150px] flex flex-col items-start gap-1 rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] px-2.5 py-2 hover:ring-2 hover:ring-[var(--eureka-signal-cognitive)] transition-shadow text-left"
              >
                <span className="text-[8px] font-mono uppercase tracking-wider text-[var(--eureka-text-micro)]">
                  {s.title}
                </span>
                <span className="text-[11px] font-mono font-bold text-[var(--eureka-text-display)] break-all">
                  {s.artifact.id}
                </span>
                <AuthorityChip authority={s.artifact.authority} />
              </button>
            ) : (
              <div className="min-w-[118px] flex flex-col items-start gap-1 rounded-lg border border-dashed border-[var(--eureka-text-micro)]/40 px-2.5 py-2 opacity-60 flex-1">
                <span className="text-[8px] font-mono uppercase tracking-wider text-[var(--eureka-text-micro)]">
                  {s.title}
                </span>
                <span className="text-[10px] font-mono text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE</span>
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
      <div className="mt-2 text-[9px] text-[var(--eureka-text-micro)]">
        Real artifact ids only. Missing steps are shown as DATA NOT AVAILABLE — never invented.
      </div>
    </div>
  );
}

export default ProvenanceChain;
