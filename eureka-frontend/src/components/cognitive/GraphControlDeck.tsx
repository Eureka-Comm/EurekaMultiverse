import { useMemo } from 'react';
import type { GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import type { NodeKind } from '../../domain/cognitiveProjectionGraph';
import {
  NODE_KIND_ORDER, NODE_KIND_COLOR, NODE_KIND_LABEL, FOCUS_KINDS, nodeKindColor,
} from '../../domain/graphVisualTokens';

// CONSTELACIÓN — GRAPH CONTROL DECK (P0). Presentation-only, deterministic, read-only.
// Three sections pulled from the SAME real GraphArtifact[] the renderer draws:
//   GRAPH SUMMARY  -> OBJECTS / GAPS / HUMAN DEC. / FROZEN (real counts, semantic accents)
//   VIEW LAYERS    -> per-kind real count chips (single color source)
//   FOCUS FILTER   -> All/Decision/Action/Execution/Result/Frozen (calls the parent's filter)
// It NEVER stores data, never invents a count, never changes the graph.

export const SUMMARY_TONE: Record<'objects' | 'gaps' | 'human' | 'frozen', string> = {
  objects: '#29e0ff',
  gaps: '#ffb03c',
  human: '#ff3d8c',
  frozen: '#9b6bff',
};

const DECK_BG = 'rgba(5, 15, 28, 0.82)';
const DECK_BORDER = 'rgba(120, 180, 255, 0.18)';
const DECK_SHADOW = '0 18px 60px rgba(0,0,0,0.55)';

export function countByKind(nodes: GraphArtifact[], kind: NodeKind): number {
  return nodes.reduce((acc, n) => (n.kind === kind ? acc + 1 : acc), 0);
}

function metricLabel(s: string): string {
  return s.toUpperCase();
}

export default function GraphControlDeck({
  nodes,
  focusKind,
  onFocusKind,
}: {
  nodes: GraphArtifact[];
  focusKind: NodeKind | 'ALL';
  onFocusKind?: (k: NodeKind | 'ALL') => void;
}) {
  const metrics = useMemo(() => {
    const objects = nodes.length;
    const gaps = nodes.filter((n) => /NOT_EVALUATED|UNSUPPORTED|NOT_APPLICABLE|DATA NOT AVAILABLE/i.test(n.status)).length;
    const human = countByKind(nodes, 'DECISION');
    const frozen = countByKind(nodes, 'FROZEN');
    return { objects, gaps, human, frozen };
  }, [nodes]);

  const layerCounts = useMemo(
    () => NODE_KIND_ORDER.map((k) => ({ kind: k, label: NODE_KIND_LABEL[k], count: countByKind(nodes, k), color: NODE_KIND_COLOR[k] })).filter((l) => l.count > 0),
    [nodes],
  );

  const sectionTitle: React.CSSProperties = {
    fontSize: 9, letterSpacing: '0.18em', textTransform: 'uppercase',
    color: 'rgba(233,228,255,0.5)', marginBottom: 8, fontWeight: 700,
  };

  const chip = (active: boolean, color: string): React.CSSProperties => ({
    fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
    padding: '5px 8px', borderRadius: 999, cursor: 'pointer', whiteSpace: 'nowrap',
    color: active ? '#ffffff' : 'rgba(233,228,255,0.78)',
    background: active ? `${color}33` : 'rgba(255,255,255,0.04)',
    border: active ? `1px solid ${color}` : '1px solid rgba(255,255,255,0.12)',
    boxShadow: active ? `0 0 0 1px ${color}55, 0 0 16px ${color}44` : 'none',
    backdropFilter: 'blur(4px)',
  });

  return (
    <div style={{
      width: '100%',
      background: DECK_BG,
      borderRadius: 26,
      border: `1px solid ${DECK_BORDER}`,
      boxShadow: DECK_SHADOW,
      backdropFilter: 'blur(14px)',
      WebkitBackdropFilter: 'blur(14px)',
      padding: '14px 18px',
      display: 'grid',
      // auto-fit wraps the three sections on narrow/portrait viewports (no overflow, no fixed columns)
      gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))',
      gap: 20,
      alignItems: 'start',
      fontFamily: "'IBM Plex Mono', ui-monospace, monospace",
      color: '#efeaff',
    }}>
      {/* AREA 1 — GRAPH SUMMARY */}
      <div>
        <div style={sectionTitle}>Graph Summary</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 18px' }}>
          <SummaryMetric value={metrics.objects} label="Objects" color={SUMMARY_TONE.objects} />
          <SummaryMetric value={metrics.gaps} label="Gaps" color={SUMMARY_TONE.gaps} />
          <SummaryMetric value={metrics.human} label="Human Dec." color={SUMMARY_TONE.human} />
          <SummaryMetric value={metrics.frozen} label="Frozen" color={SUMMARY_TONE.frozen} />
        </div>
      </div>

      {/* AREA 2 — VIEW LAYERS */}
      <div>
        <div style={sectionTitle}>View Layers</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {layerCounts.map((l) => (
            <span key={l.kind} style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 10, letterSpacing: '0.08em', textTransform: 'uppercase', padding: '5px 9px', borderRadius: 999, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.12)', color: 'rgba(233,228,255,0.85)' }}>
              <span style={{ width: 7, height: 7, borderRadius: 999, background: l.color, boxShadow: `0 0 6px ${l.color}` }} />
              {l.label} <b style={{ color: l.color }}>{l.count}</b>
            </span>
          ))}
          {layerCounts.length === 0 && <span style={{ fontSize: 10, color: 'rgba(233,228,255,0.4)' }}>No layers observed.</span>}
        </div>
      </div>

      {/* AREA 3 — FOCUS FILTER */}
      <div>
        <div style={sectionTitle}>Focus Filter</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          <button type="button" onClick={() => onFocusKind?.('ALL')} style={chip(focusKind === 'ALL', '#29e0ff')} aria-pressed={focusKind === 'ALL'}>All</button>
          {FOCUS_KINDS.map((k) => (
            <button key={k} type="button" onClick={() => onFocusKind?.(k)} style={chip(focusKind === k, nodeKindColor(k))} aria-pressed={focusKind === k}>
              {NODE_KIND_LABEL[k]}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

function SummaryMetric({ value, label, color }: { value: number; label: string; color: string }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
      <span style={{ fontSize: 22, lineHeight: 1, fontWeight: 800, color, fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}>{value}</span>
      <span style={{ fontSize: 8, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.5)' }}>{metricLabel(label)}</span>
    </div>
  );
}

/** Bottom-right LEGEND — same color source as the renderer + layers. Only REAL kinds present. */
export function GraphLegend({ nodes }: { nodes: GraphArtifact[] }) {
  const kinds = useMemo(
    () => NODE_KIND_ORDER.map((k) => ({ kind: k, label: NODE_KIND_LABEL[k], color: NODE_KIND_COLOR[k] })).filter((l) => nodes.some((n) => n.kind === l.kind)),
    [nodes],
  );
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px', alignItems: 'center', fontFamily: "'IBM Plex Mono', ui-monospace, monospace" }}>
      {kinds.map((l) => (
        <span key={l.kind} style={{ display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 9, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.72)' }}>
          <span style={{ width: 7, height: 7, borderRadius: 999, background: l.color, boxShadow: `0 0 6px ${l.color}` }} />
          {l.label}
        </span>
      ))}
      {kinds.length === 0 && null}
    </div>
  );
}
