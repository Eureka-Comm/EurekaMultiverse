import React, { useMemo, useCallback, useState } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  Handle,
  Position,
  MarkerType,
  useReactFlow,
  type Node,
  type Edge,
  type NodeTypes,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import type { CognitiveProjectionGraph, GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from './AuthorityChip';
import { kindColor, EDGE_LABEL_COLOR } from './cognitiveColors';

/**
 * KNOWLEDGE SPACE — the exploration instrument. It fills the primary stage and:
 *   · zoom / pan / fit / reset (React Flow)
 *   · on node select, highlights the selected node's lineage path and dims the
 *     rest (visual focus) + opens the contextual Inspector (onSelect)
 *   · ADAPTS TO THE CHAPTER: an optional `chapterKinds` filter can be passed so
 *     the space focuses on the artifacts relevant to the current cognitive state
 *     (not all nodes at once).
 *   · edges use ONLY real semantics (derived_from | supports | produced_by |
 *     selected_by | authorized_by | executed_as | frozen_as) — never "causes".
 * Data always comes from the single governed graph (buildCognitiveProjectionGraph).
 */

const COLUMN: Record<string, number> = {
  PROBLEM: 0,
  EVIDENCE: 1,
  FINDING: 2,
  PREDICTION: 3,
  PRESCRIPTION: 4,
  ALTERNATIVE: 4,
  DECISION: 5,
  ACTION: 6,
  EXECUTION: 7,
  RESULT: 8,
  FROZEN: 9,
};

function artifactNode({ data, selected }: { data: GraphArtifact; selected: boolean }) {
  const color = kindColor(data.kind);
  return (
    <div
      data-artifact-id={data.id}
      data-kind={data.kind}
      data-authority={data.authority}
      data-status={data.status}
      className="min-w-[158px] max-w-[190px] bg-[var(--eureka-surface-elevated)] overflow-hidden"
      style={{ border: `1px solid ${color}`, borderLeft: `3px solid ${color}`, boxShadow: selected ? `0 0 0 1.5px ${color}` : undefined, borderRadius: 3 }}
    >
      {data.kind !== 'PROBLEM' && <Handle type="target" position={Position.Left} style={{ background: color }} />}
      <div className="px-2.5 py-1.5 flex items-center justify-between gap-1">
        <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color }}>{data.kind}</span>
        <span className="text-[9px] font-mono text-[var(--eureka-text-micro)] truncate max-w-[86px]">{data.id}</span>
      </div>
      <div className="px-2.5 pb-2 space-y-1">
        <div className="text-[11px] font-bold text-[var(--eureka-text-display)] leading-tight">{data.label}</div>
        <div className="text-[10px] text-[var(--eureka-text-label)] leading-snug line-clamp-2">{data.description || 'DATA NOT AVAILABLE'}</div>
        <div className="flex items-center justify-between gap-1 pt-0.5">
          <AuthorityChip authority={data.authority} />
          <span className="flex items-center gap-1">
            {data.recommended && <span className="text-[8px] font-mono text-[var(--eureka-signal-cognitive)]">REC</span>}
            {data.humanSelected && <span className="text-[8px] font-mono text-[var(--eureka-signal-authority)]">HUMAN</span>}
          </span>
        </div>
      </div>
      {data.kind !== 'FROZEN' && <Handle type="source" position={Position.Right} style={{ background: color }} />}
    </div>
  );
}

const nodeTypes: NodeTypes = { artifact: artifactNode as any };

function Toolbar({ onFit, onReset }: { onFit: () => void; onReset: () => void }) {
  return (
    <div className="absolute top-3 right-3 z-10 flex items-center gap-1.5">
      <button onClick={onFit} className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider rounded border border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)] bg-[var(--eureka-surface-active)] hover:text-[var(--eureka-text-display)] hover:border-[var(--eureka-signal-cognitive)]">
        fit
      </button>
      <button onClick={onReset} className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider rounded border border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)] bg-[var(--eureka-surface-active)] hover:text-[var(--eureka-text-display)] hover:border-[var(--eureka-signal-cognitive)]">
        reset
      </button>
    </div>
  );
}

function GraphInner({
  graph,
  onSelect,
  selectedId,
  chapterKinds,
}: {
  graph: CognitiveProjectionGraph;
  onSelect?: (artifact: GraphArtifact) => void;
  selectedId?: string | null;
  chapterKinds?: string[];
}) {
  const { fitView } = useReactFlow();

  const focus = useMemo(() => {
    if (!selectedId) return null;
    const highlight = new Set<string>([selectedId]);
    const frontier = [selectedId];
    const adj = new Map<string, string[]>();
    graph.edges.forEach((e) => {
      if (!adj.has(e.source)) adj.set(e.source, []);
      if (!adj.has(e.target)) adj.set(e.target, []);
      adj.get(e.source)!.push(e.target);
      adj.get(e.target)!.push(e.source);
    });
    for (let d = 0; d < 2; d++) {
      const next: string[] = [];
      frontier.forEach((id) => {
        (adj.get(id) || []).forEach((n) => {
          if (!highlight.has(n)) {
            highlight.add(n);
            next.push(n);
          }
        });
      });
      frontier.splice(0, frontier.length, ...next);
    }
    return highlight;
  }, [graph.edges, selectedId]);

  const inChapter = useMemo(() => {
    if (!chapterKinds?.length) return null;
    return new Set(chapterKinds);
  }, [chapterKinds]);

  const { nodes, edges } = useMemo(() => {
    if (!graph.nodes.length) return { nodes: [], edges: [] as Edge[] };
    const perCol: Record<string, number> = {};
    const rNodes: Node[] = graph.nodes.map((a, i) => {
      const col = COLUMN[a.kind] ?? 4;
      const idx = perCol[col] ?? 0;
      perCol[col] = idx + 1;
      const inFocusNode = !focus || focus.has(a.id);
      const inChapterNode = !inChapter || inChapter.has(a.kind) || selectedId === a.id;
      return {
        id: a.id,
        type: 'artifact',
        position: { x: col * 215 + 30, y: idx * 128 + 30 },
        data: a as unknown as Record<string, unknown>,
        style: { opacity: inFocusNode ? (inChapterNode ? 1 : 0.12) : 0.12, transition: 'opacity .25s ease' },
      };
    });

    const rEdges: Edge[] = graph.edges.map((e) => {
      const onFocus = !focus || (focus.has(e.source) && focus.has(e.target));
      const col = EDGE_LABEL_COLOR[e.label] || '#8c959f';
      return {
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: e.label === 'selected_by',
        markerEnd: { type: MarkerType.ArrowClosed, color: col },
        style: { stroke: col, strokeWidth: 1.2, opacity: onFocus ? 1 : 0.12, transition: 'opacity .25s ease' },
        labelStyle: { fill: col, fontSize: 9.5, fontFamily: 'monospace', fontWeight: 600 },
        labelBgStyle: { fill: '#ffffff', fillOpacity: 0.92 },
        labelBgPadding: [4, 2],
        labelBgBorderRadius: 3,
      };
    });

    return { nodes: rNodes, edges: rEdges };
  }, [graph, focus, inChapter, selectedId]);

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const art = node.data as unknown as GraphArtifact;
      if (art && onSelect) onSelect(art);
    },
    [onSelect],
  );

  if (!graph.nodes.length) {
    return (
      <div className="ci-empty h-full">
        <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">No governed graph</div>
        <p className="text-xs max-w-md">Data pending — the canonical state has not emitted any artifact for this work.</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={onNodeClick}
        fitView
        fitViewOptions={{ padding: 0.22 }}
        minZoom={0.15}
        maxZoom={1.8}
        nodesConnectable={false}
        nodesDraggable
        panOnDrag
        proOptions={{ hideAttribution: true }}
        className="bg-transparent"
      >
        <Background color="var(--eureka-spatial-grid)" gap={26} size={1} />
        <Controls showInteractive={false} position="bottom-left" style={{ borderRadius: 3, border: '1px solid var(--eureka-spatial-hairline)', boxShadow: 'none' }} />
        <MiniMap pannable zoomable nodeColor={(n) => kindColor((n.data as Record<string, unknown>).kind as string)} style={{ borderRadius: 3, border: '1px solid var(--eureka-spatial-hairline)' }} />
      </ReactFlow>
      <Toolbar onFit={() => fitView({ padding: 0.22, duration: 300 })} onReset={() => fitView({ padding: 0.22, duration: 300 })} />
    </div>
  );
}

export function KnowledgeMap({
  graph,
  onSelect,
  selectedId,
  chapterKinds,
}: {
  graph: CognitiveProjectionGraph;
  onSelect?: (artifact: GraphArtifact) => void;
  selectedId?: string | null;
  chapterKinds?: string[];
}) {
  return (
    <ReactFlowProvider>
      <GraphInner graph={graph} onSelect={onSelect} selectedId={selectedId} chapterKinds={chapterKinds} />
    </ReactFlowProvider>
  );
}

export default KnowledgeMap;
