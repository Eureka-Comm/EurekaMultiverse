import React, { useMemo, useState } from 'react';
import type { HeroProps } from './chapters/types';
import { statusColor } from './cognitiveColors';

/**
 * LINEAGE THREAD — a single cognitive thread (not a row of cards):
 *   EVI — FND — PRED — PRESC — DEC — ACT — EXEC — RESULT — FROZEN
 *
 * It is one connected rail. Selecting an artifact illuminates ONLY its trajectory
 * (the selected node lights up in the story stage + inspector). A stage that the
 * backend did not emit renders "DATA NOT AVAILABLE" on the rail (never invented).
 * Multi-artifact stages cycle through their real artifacts on repeat clicks.
 */
const ORDER: Array<{ kind: string; title: string }> = [
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

export function LineageRibbon({
  graph,
  onSelectArtifact,
  selectedId,
}: {
  graph: HeroProps['graph'];
  onSelectArtifact: (a: any) => void;
  selectedId?: string | null;
}) {
  const [cursor, setCursor] = useState<Record<string, number>>({});

  const stages = useMemo(() => {
    return ORDER.map((o) => {
      const arts = graph.nodes.filter((n) => n.kind === o.kind);
      return { kind: o.kind, title: o.title, artifacts: arts };
    });
  }, [graph]);

  const hasAny = stages.some((s) => s.artifacts.length > 0);
  if (!hasAny) {
    return (
      <div className="ci-thread p-3">
        <span className="text-[11px] text-[var(--eureka-text-micro)]">
          DATA NOT AVAILABLE — no provenance chain emitted by the backend.
        </span>
      </div>
    );
  }

  return (
    <div className="ci-thread" role="navigation" aria-label="Cognitive lineage thread">
      <div className="ci-thread-rail">
        <div className="ci-thread-line" />
        <div className="ci-thread-stage">
          {stages.map((s, i) => {
            const isGap = s.artifacts.length === 0;
            const active = s.artifacts.some((a) => a.id === selectedId);
            const idx = cursor[s.kind] ?? 0;
            const art = isGap ? null : s.artifacts[idx % s.artifacts.length];
            const col = art ? statusColor(art.authority === 'PUBLISHED' ? 'PUBLISHED' : art.authority) : undefined;
            return (
              <React.Fragment key={s.kind}>
                {i > 0 && (
                  <span className="ci-thread-sep">
                    <span>—</span>
                  </span>
                )}
                {art ? (
                  <button
                    className={`ci-thread-node ${active ? 'is-active' : ''}`}
                    onClick={() => {
                      if (s.artifacts.length > 1) {
                        const next = (idx + 1) % s.artifacts.length;
                        setCursor((c) => ({ ...c, [s.kind]: next }));
                      }
                      onSelectArtifact(s.artifacts[idx % s.artifacts.length]);
                    }}
                    title={art.description || art.label}
                  >
                    <span className="ci-thread-dot" style={{ borderColor: art ? col : undefined }} />
                    <span className="ci-thread-meta">
                      <span className="ci-thread-kind">{s.title}{s.artifacts.length > 1 ? ` · ${idx + 1}/${s.artifacts.length}` : ''}</span>
                      <span className="ci-thread-id" style={{ display: 'block' }}>{art.id}</span>
                    </span>
                  </button>
                ) : (
                  <div className="ci-thread-node is-gap" style={{ cursor: 'default' }}>
                    <span className="ci-thread-dot" style={{ borderStyle: 'dashed', opacity: .45 }} />
                    <span className="ci-thread-meta">
                      <span className="ci-thread-kind">{s.title}</span>
                      <span className="ci-thread-id" style={{ color: 'var(--eureka-text-micro)', display: 'block', fontSize: 9 }}>DATA NOT AVAILABLE</span>
                    </span>
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
}

export default LineageRibbon;
