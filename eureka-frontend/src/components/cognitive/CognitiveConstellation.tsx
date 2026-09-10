import { useMemo, useState } from 'react';
import { useWorkStore } from '../../store/workStore';
import { useCognitiveProjection } from '../../hooks/useCognitiveProjection';
import { buildCognitiveProjectionGraph, type GraphArtifact, type NodeKind } from '../../domain/cognitiveProjectionGraph';
import { nodeKindColor } from '../../domain/graphVisualTokens';
import GalaxyConstellation from './GalaxyConstellation';
import { ArtifactDetail } from './Inspector';
import {
  upstreamClosure, downstreamClosure, upstreamChain, downstreamChain,
  edgesTouching, edgesWithin, directUpstreamIds, directDownstreamIds,
  gapNodeIds, kindNodeIds,
} from './constellationNav';

const chipStyle = (color: string) => ({
  fontSize: 10, textTransform: 'uppercase' as const, letterSpacing: '0.06em',
  padding: '3px 8px', borderRadius: 999, cursor: 'pointer', color,
  border: `1px solid ${color}44`, background: 'rgba(255,255,255,0.03)',
  fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
});

/**
 * §25 — CONSTELLATION SURFACE (interactive). Real cognitive state of EUREKA, honest & navigable.
 * workStore.activeWork → CognitiveProjectionDTO → CognitiveProjectionGraph → GalaxyConstellation.
 * Zoom/pan/reset = viewport (presentation). Selection/focus/trace = semantic, driven by REAL edges
 * (derived_from/supports/produced_by/selected_by/authorized_by/executed_as/frozen_as — never "causes").
 * Inspector = re-used ArtifactDetail. Honest states preserved. No invented data/nodes/edges/metrics.
 */
export default function CognitiveConstellation() {
  const activeWork = useWorkStore((s) => s.activeWork);
  const dto = useCognitiveProjection(activeWork);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [traceMode, setTraceMode] = useState<'none' | 'back' | 'forward'>('none');
  const [resetToken, setResetToken] = useState(0);
  const [highlightRelations, setHighlightRelations] = useState(true);
  const [centerToken, setCenterToken] = useState(0);
  const [centerNodeId, setCenterNodeId] = useState<string | null>(null);
  const [focusQuery, setFocusQuery] = useState<'all' | 'gaps' | 'decision' | 'frozen' | NodeKind>('all');
  const loadWorkById = useWorkStore((s) => s.loadWorkById);
  const [loadId, setLoadId] = useState('');
  const [loadErr, setLoadErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const doLoadWork = async () => {
    setLoading(true); setLoadErr(null);
    const id = loadId.trim();
    if (!id) { setLoadErr('Enter a Work id.'); setLoading(false); return; }
    const r = await loadWorkById(id);
    if (r && (r.status === 'ERROR' || r.status === 'CONTRACT_ERROR')) setLoadErr(String(r.message || r.status));
    setLoading(false);
  };

  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);

  const selected = useMemo(
    () => (selectedId ? graph.nodes.find((n) => n.id === selectedId) ?? null : null),
    [selectedId, graph.nodes]
  );

  const focusedNodeIds = useMemo<string[]>(() => {
    if (!highlightRelations) return [];
    if (focusQuery !== 'all') {
      if (focusQuery === 'gaps') return gapNodeIds(graph.nodes);
      return kindNodeIds(graph.nodes, focusQuery); // 'decision' | 'frozen' | NodeKind
    }
    if (!selected) return [];
    if (traceMode === 'back') return [...upstreamClosure(selected.id, graph.edges, graph.nodes)];
    if (traceMode === 'forward') return [...downstreamClosure(selected.id, graph.edges, graph.nodes)];
    const set = new Set<string>([selected.id]);
    for (const e of graph.edges) {
      if (e.source === selected.id) set.add(e.target);
      else if (e.target === selected.id) set.add(e.source);
    }
    return [...set];
  }, [selected, traceMode, graph.edges, graph.nodes, highlightRelations, focusQuery]);

  const focusedEdgeIds = useMemo<string[]>(() => {
    if (!highlightRelations) return [];
    if (focusQuery !== 'all') {
      const ids = focusQuery === 'gaps' ? gapNodeIds(graph.nodes) : kindNodeIds(graph.nodes, focusQuery);
      return [...edgesWithin(new Set(ids), graph.edges)];
    }
    if (!selected) return [];
    let set: Set<string>;
    if (traceMode === 'back') set = edgesWithin(upstreamClosure(selected.id, graph.edges, graph.nodes), graph.edges);
    else if (traceMode === 'forward') set = edgesWithin(downstreamClosure(selected.id, graph.edges, graph.nodes), graph.edges);
    else set = edgesTouching(selected.id, graph.edges);
    return [...set];
  }, [selected, traceMode, graph.edges, graph.nodes, highlightRelations, focusQuery]);

  // Chips for the active trace (or direct neighbors when no trace).
  const upstreamList = useMemo(
    () => (traceMode === 'back' ? upstreamChain(selected?.id ?? '', graph.edges, graph.nodes) : []),
    [traceMode, selected?.id, graph.edges, graph.nodes]
  );
  const downstreamList = useMemo(
    () => (traceMode === 'forward' ? downstreamChain(selected?.id ?? '', graph.edges, graph.nodes) : []),
    [traceMode, selected?.id, graph.edges, graph.nodes]
  );
  const directUp = useMemo(() => {
    if (!selected || traceMode !== 'none') return [];
    return directUpstreamIds(selected.id, graph.edges, graph.nodes)
      .map((id) => graph.nodes.find((n) => n.id === id))
      .filter((n): n is GraphArtifact => !!n);
  }, [selected, traceMode, graph.edges, graph.nodes]);
  const directDown = useMemo(() => {
    if (!selected || traceMode !== 'none') return [];
    return directDownstreamIds(selected.id, graph.edges, graph.nodes)
      .map((id) => graph.nodes.find((n) => n.id === id))
      .filter((n): n is GraphArtifact => !!n);
  }, [selected, traceMode, graph.edges, graph.nodes]);

  const edgeCount = useMemo(
    () => (selected ? edgesTouching(selected.id, graph.edges).size : 0),
    [selected, graph.edges]
  );

  const centerOn = (id: string) => {
    setCenterNodeId(id);
    setCenterToken((t) => t + 1);
  };

  if (!activeWork) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center gap-3 text-sm text-[var(--eureka-text-label)]" data-testid="constellation-empty">
        <div>No active work. Load an existing Work (read-only) or open a governed cognitive operation to populate the constellation.</div>
        <div className="flex items-center gap-2">
          <input value={loadId} onChange={(e) => setLoadId(e.target.value)} placeholder="Work id (e.g. WORK-…)" className="px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded text-sm" />
          <button type="button" onClick={doLoadWork} disabled={loading} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
            {loading ? 'Loading…' : 'Load Work'}
          </button>
        </div>
        {loadErr && <div className="text-[11px] text-[var(--eureka-signal-blocked)]">Error (fail-closed): {loadErr}</div>}
      </div>
    );
  }

  const selectNode = (id: string) => {
    setSelectedId(id);
    // Keep the active trace mode (back/forward) so it re-anchors on the newly selected node.
  };

  const clearAll = () => {
    setSelectedId(null);
    setTraceMode('none');
    setFocusQuery('all');
    setResetToken((t) => t + 1); // reset viewport too
  };

  const clearFocus = () => {
    setTraceMode('none');
    setSelectedId(null);
    setFocusQuery('all');
  };

  return (
    <div className="relative w-full h-full flex" style={{ fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}>
      {/* Galaxia interactiva (nodos REALES) — Control Deck + legend are rendered inside */}
      <div className="absolute inset-0">
        <GalaxyConstellation
          nodes={graph.nodes}
          edges={graph.edges}
          onSelect={(n) => selectNode(n.id)}
          selectedId={selectedId}
          selectedArtifact={selected}
          focusedNodeIds={focusedNodeIds}
          focusedEdgeIds={focusedEdgeIds}
          highlightRelations={highlightRelations}
          resetToken={resetToken}
          centerRequest={centerToken}
          centerNodeId={centerNodeId}
          traceMode={traceMode}
          onTrace={(m) => setTraceMode((c) => (c === m ? 'none' : m))}
          onClose={() => setSelectedId(null)}
          onCenter={() => centerOn(selected?.id ?? '')}
          upstreamCount={directUp.length}
          downstreamCount={directDown.length}
        />
      </div>

      {/* INSPECTOR + NAVEGACIÓN (solo al seleccionar) — no ocupa el espacio primario */}
      {selected && (
        <div className="absolute right-2 top-2 bottom-2 w-[340px] overflow-y-auto z-20" style={{ scrollbarWidth: 'thin' }}>
          <div className="ci-panel p-3 space-y-2">
            <ArtifactDetail a={selected} />

            <div className="pt-1 mt-1 border-t border-[var(--eureka-spatial-hairline)] space-y-2">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">NAVIGATION</div>
              <div className="flex flex-wrap gap-1.5">
                <button type="button" onClick={() => setTraceMode((c) => (c === 'back' ? 'none' : 'back'))}
                  className="text-[10px] px-2.5 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-signal-semantic)]"
                  aria-pressed={traceMode === 'back'}>↑ TRACE BACK</button>
                <button type="button" onClick={() => setTraceMode((c) => (c === 'forward' ? 'none' : 'forward'))}
                  className="text-[10px] px-2.5 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-signal-semantic)]"
                  aria-pressed={traceMode === 'forward'}>↓ TRACE FORWARD</button>
                <button type="button" onClick={() => centerOn(selected.id)}
                  className="text-[10px] px-2.5 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-text-display)]">◎ CENTER ON NODE</button>
                <button type="button" onClick={clearFocus}
                  className="text-[10px] px-2.5 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-text-display)]">⇤ SHOW ALL</button>
                <button type="button" onClick={() => setSelectedId(null)}
                  className="text-[10px] px-2.5 py-1 rounded border border-[var(--eureka-border)] hover:text-[var(--eureka-text-display)]">✕ CLOSE</button>
              </div>
            </div>

            {/* Relation counts (real) */}
            <div className="pt-1 flex items-center gap-3 text-[10px] text-[var(--eureka-text-label)]">
              <span>↑ upstream <b style={{ color: '#29e0ff' }}>{directUp.length}</b></span>
              <span>↓ downstream <b style={{ color: '#4dff9d' }}>{directDown.length}</b></span>
              <span>↔ relations <b style={{ color: '#9b6bff' }}>{edgeCount}</b></span>
            </div>

            {/* Native-content-free HIGHLIGHT RELATIONS toggle */}
            <label className="flex items-center gap-2 text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">
              <input type="checkbox" checked={highlightRelations} onChange={(e) => setHighlightRelations(e.target.checked)} />
              Highlight relations
            </label>

            {/* TRACE visual — real edges only */}
            {traceMode === 'back' && (
              <div className="pt-1">
                <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">↑ Trace back (real upstream)</div>
                {upstreamList.length ? (
                  <div className="flex flex-wrap gap-1">
                    {upstreamList.map((id) => {
                      const n = graph.nodes.find((x) => x.id === id);
                      return n ? (
                        <button type="button" key={id} onClick={() => setSelectedId(id)} style={chipStyle(nodeKindColor(n.kind))}>
                          {n.kind}·{n.id}
                        </button>
                      ) : null;
                    })}
                  </div>
                ) : (
                  <div className="text-[11px] text-[var(--eureka-text-label)]">Stops here — no further real upstream provenance.</div>
                )}
              </div>
            )}
            {traceMode === 'forward' && (
              <div className="pt-1">
                <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">↓ Trace forward (real downstream)</div>
                {downstreamList.length ? (
                  <div className="flex flex-wrap gap-1">
                    {downstreamList.map((id) => {
                      const n = graph.nodes.find((x) => x.id === id);
                      return n ? (
                        <button type="button" key={id} onClick={() => setSelectedId(id)} style={chipStyle(nodeKindColor(n.kind))}>
                          {n.kind}·{n.id}
                        </button>
                      ) : null;
                    })}
                  </div>
                ) : (
                  <div className="text-[11px] text-[var(--eureka-text-label)]">Stops here — no further real downstream provenance.</div>
                )}
              </div>
            )}

            {/* Direct provenance neighbors (real edges) when not tracing */}
            {traceMode === 'none' && (
              <div className="pt-1 space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">PROVENANCE (direct)</div>
                {directUp.length === 0 && directDown.length === 0 && (
                  <div className="text-[11px] text-[var(--eureka-text-label)]">No direct links in the graph.</div>
                )}
                {directUp.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">↑ Upstream</div>
                    <div className="flex flex-wrap gap-1">
                      {directUp.map((n) => (
                        <button type="button" key={n.id} onClick={() => setSelectedId(n.id)} style={chipStyle(nodeKindColor(n.kind))}>
                          {n.kind}·{n.id}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {directDown.length > 0 && (
                  <div>
                    <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">↓ Downstream</div>
                    <div className="flex flex-wrap gap-1">
                      {directDown.map((n) => (
                        <button type="button" key={n.id} onClick={() => setSelectedId(n.id)} style={chipStyle(nodeKindColor(n.kind))}>
                          {n.kind}·{n.id}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <button type="button" onClick={clearAll}
              className="w-full mt-1 text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-display)]">
              ⟲ RESET VIEW
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
