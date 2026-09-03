import React, { useMemo, useState } from 'react';
import { useWorkStore } from '../../store/workStore';
import { useCognitiveProjection } from '../../hooks/useCognitiveProjection';
import { buildCognitiveProjectionGraph, type GraphArtifact, type NodeKind } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from '../cognitive/AuthorityChip';
import { SourceTag } from '../cognitive/SourceTag';
import { ArtifactDetail } from '../cognitive/Inspector';

/**
 * IntelligenceNetwork — governed cognitive chain (LS85 role, LS86 single source).
 *
 * Renders a READABLE vertical chain of the governed cognitive state, reading
 * EXCLUSIVELY from the single `CognitiveProjectionDTO` (via `useCognitiveProjection`
 * + `buildCognitiveProjectionGraph`). It never reads raw `state.findings` /
 * `state.human_decision` directly and never fabricates a relationship.
 *
 * Every node carries id / kind / label / status / authority / provenance, and a
 * dev source annotation (field → artifact → EM → authority). Clicking a node opens
 * the Inspector.
 */
const ORDER: NodeKind[] = [
  'PROBLEM',
  'EVIDENCE',
  'FINDING',
  'PREDICTION',
  'PRESCRIPTION',
  'ALTERNATIVE',
  'DECISION',
  'ACTION',
  'EXECUTION',
  'RESULT',
  'FROZEN',
];

export default function IntelligenceNetwork() {
  const activeWork = useWorkStore((s) => s.activeWork);
  const dto = useCognitiveProjection(activeWork);
  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);
  const [selected, setSelected] = useState<GraphArtifact | null>(null);

  if (!activeWork) return null;

  if (graph.nodes.length === 0) {
    return (
      <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] h-full flex flex-col">
        <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 tracking-widest">COGNITIVE CHAIN</h3>
        <div className="flex-1 flex flex-col items-center justify-center text-center gap-2 p-4 border border-[var(--eureka-spatial-hairline)] rounded">
          <span className="text-xs text-[var(--eureka-signal-semantic)]">COGNITIVE CHAIN UNAVAILABLE</span>
          <p className="text-xs text-[var(--eureka-text-label)] max-w-sm">
            No hay una cadena cognitiva gobernada en el estado canónico. El sistema no fabrica relaciones causales.
          </p>
        </div>
      </div>
    );
  }

  const ordered = ORDER.map((k) => graph.nodes.filter((n) => n.kind === k)).flat();

  return (
    <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] h-full flex flex-col overflow-auto">
      <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 tracking-widest flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-[var(--eureka-signal-semantic)]"></span> COGNITIVE CHAIN
        <span className="ml-auto text-[9px] text-[var(--eureka-text-micro)]">única fuente: CognitiveProjectionDTO</span>
      </h3>

      <div className="flex flex-col gap-1">
        {ordered.map((s) => (
          <button
            key={s.id}
            onClick={() => setSelected(s.id === selected?.id ? null : s)}
            className={`w-full text-left px-3 py-2 rounded border text-xs transition-colors ${
              selected?.id === s.id ? 'ring-2 ring-[var(--eureka-signal-cognitive)]' : ''
            } border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)]`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono font-bold text-[var(--eureka-text-section)] truncate">{s.id}</span>
              <AuthorityChip authority={s.authority} size="sm" />
            </div>
            <div className="text-[10px] text-[var(--eureka-text-section)] mt-0.5 line-clamp-1">{s.description || s.kind}</div>
            <div className="mt-1">
              <SourceTag sourceField={s.sourceField} artifactId={s.artifactId} em={s.em} authority={s.authority} />
            </div>
          </button>
        ))}
      </div>

      {selected && (
        <div className="mt-4">
          <ArtifactDetail a={selected} />
        </div>
      )}
    </div>
  );
}
