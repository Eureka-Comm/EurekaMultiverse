import { useMemo, useState } from 'react';
import { useWorkStore } from '../../store/workStore';
import { useCognitiveProjection } from '../../hooks/useCognitiveProjection';
import { buildCognitiveProjectionGraph, type GraphArtifact, type NodeKind } from '../../domain/cognitiveProjectionGraph';
import { kindColor, statusColor, EDGE_LABEL_COLOR } from './cognitiveColors';
import GalaxyConstellation from './GalaxyConstellation';
import CoreConstellation from './CoreConstellation';
import './cognitiveField.css';

/**
 * CognitiveOperationalField — LS-CF-01.
 * Superficie OPERATIVA (observabilidad / navegación / trazabilidad / gobernanza)
 * del estado cognitivo real. REESTILIZADA con el lenguaje visual establecido de
 * Eureka (Cognitive Field: HUD + toolbar mono + stage oscuro + legend, fuentes
 * --font-display/--font-mono, hairline, colores oficiales kindColor/statusColor).
 *
 * Modos: UNDERSTAND · EXPLORE · AUDIT · OPERATE · CONSTELLATION (galaxia/árbol
 * embebida en un contenedor, como la trabajamos). Semántica > estética; una sola
 * fuente (workStore → CognitiveProjection → Graph). Honestidad: NO inventa datos.
 */

const STAGES: NodeKind[] = ['PROBLEM', 'EVIDENCE', 'FINDING', 'PREDICTION', 'PRESCRIPTION', 'ALTERNATIVE', 'DECISION', 'ACTION', 'EXECUTION', 'RESULT', 'FROZEN'];
const STAGE_LABEL: Record<string, string> = {
  PROBLEM: 'Question', EVIDENCE: 'Evidence', FINDING: 'Finding', PREDICTION: 'Prediction',
  PRESCRIPTION: 'Prescription', ALTERNATIVE: 'Alternative', DECISION: 'Human Decision',
  ACTION: 'Action Plan', EXECUTION: 'Execution', RESULT: 'Result', FROZEN: 'Frozen',
};
const MODES = ['UNDERSTAND', 'EXPLORE', 'AUDIT', 'OPERATE', 'CONSTELLATION'] as const;
type Mode = (typeof MODES)[number];

/** "Why?" — reconstruye el provenance hacia arriba siguiendo aristas reales. */
function buildWhy(graph: { nodes: GraphArtifact[]; edges: { source: string; target: string; label: string }[] }, startId: string) {
  const byId = new Map(graph.nodes.map((n) => [n.id, n]));
  const seen = new Set<string>([startId]);
  const chain: { node: GraphArtifact; edgeLabel: string | null }[] = [{ node: byId.get(startId)! as GraphArtifact, edgeLabel: null }];
  let frontier = [startId];
  while (frontier.length) {
    const next: string[] = [];
    for (const id of frontier) {
      for (const e of graph.edges) {
        if (e.target === id && !seen.has(e.source)) {
          seen.add(e.source);
          const src = byId.get(e.source);
          if (src) { chain.push({ node: src, edgeLabel: e.label }); next.push(e.source); }
        }
      }
    }
    frontier = next;
  }
  return chain;
}

export default function CognitiveOperationalField() {
  const activeWork = useWorkStore((s) => s.activeWork);
  const dto = useCognitiveProjection(activeWork);
  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);
  const [mode, setMode] = useState<Mode>('EXPLORE');
  const [selected, setSelected] = useState<string | null>(null);
  const [constKind, setConstKind] = useState<'galaxy' | 'tree'>('galaxy');

  const byKind = useMemo(() => {
    const m: Record<string, GraphArtifact[]> = {};
    for (const n of graph.nodes) (m[n.kind] = m[n.kind] || []).push(n);
    return m;
  }, [graph]);

  const integrity = useMemo(() => {
    const present = STAGES.filter((k) => (byKind[k]?.length ?? 0) > 0);
    const missing = STAGES.filter((k) => !(byKind[k]?.length));
    const unsupported = graph.nodes.filter((n) => n.status === 'UNSUPPORTED' || /DATA NOT AVAILABLE/i.test(n.status));
    const notEval = graph.nodes.filter((n) => /NOT_EVALUATED|NOT_APPLICABLE/i.test(n.status));
    const waitingHuman = graph.nodes.filter((n) => /WAITING_FOR_HUMAN_INPUT/i.test(n.status));
    const humanDecisions = graph.nodes.filter((n) => n.kind === 'DECISION');
    const frozen = graph.nodes.filter((n) => n.kind === 'FROZEN');
    return { present, missing, unsupported, notEval, waitingHuman, humanDecisions, frozen, holes: missing.length + unsupported.length + notEval.length };
  }, [byKind, graph]);

  const selection = selected ? graph.nodes.find((n) => n.id === selected) ?? null : null;
  const why = selected ? buildWhy(graph, selected) : [];

  const btn = (m: Mode) => (
    <button key={m} className={`ci-field-btn ${mode === m ? 'is-on' : ''}`} onClick={() => setMode(m)} style={{ textTransform: 'uppercase' }}>{m}</button>
  );

  const nodeRow = (n: GraphArtifact) => (
    <button key={n.id} onClick={() => setSelected(n.id)} className="ci-field-node" style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', width: '100%', textAlign: 'left', background: 'var(--eureka-surface)', border: `1px solid var(--eureka-spatial-hairline)`, borderRadius: 2, padding: '4px 8px', cursor: 'pointer', font: 'inherit', fontFamily: 'var(--font-mono)', color: 'var(--eureka-text-section)' }}>
      <span style={{ color: statusColor(n.status), fontSize: 9, letterSpacing: '.06em', textTransform: 'uppercase' }}>{n.label}</span>
      <span style={{ color: 'var(--eureka-text-label)', fontSize: 9 }}>· {n.status}</span>
      {n.authority === 'HUMAN_AUTHORIZED' && <span style={{ fontSize: 8.5, padding: '1px 5px', borderRadius: 999, background: 'color-mix(in srgb, #8250df 18%, transparent)', color: '#8250df', letterSpacing: '.06em', textTransform: 'uppercase' }}>Human authority</span>}
      {n.recommended && <span style={{ fontSize: 8.5, padding: '1px 5px', borderRadius: 999, background: 'color-mix(in srgb, #0969da 18%, transparent)', color: '#0969da', letterSpacing: '.06em', textTransform: 'uppercase' }}>REC</span>}
      {n.humanSelected && <span style={{ fontSize: 8.5, padding: '1px 5px', borderRadius: 999, background: 'color-mix(in srgb, #bf7d3b 18%, transparent)', color: '#bf7d3b', letterSpacing: '.06em', textTransform: 'uppercase' }}>Human select</span>}
      {n.em && <span style={{ marginLeft: 'auto', color: 'var(--eureka-text-micro)', fontSize: 8.5 }}>{n.em}</span>}
    </button>
  );

  const stageRow = (k: NodeKind) => {
    const nodes = byKind[k] ?? [];
    const empty = nodes.length === 0;
    const col = kindColor(k);
    return (
      <div key={k} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', borderBottom: '1px solid var(--eureka-spatial-grid)', padding: '6px 0' }}>
        <div style={{ minWidth: 126, textAlign: 'right', borderRight: `2px solid ${empty ? 'var(--eureka-spatial-hairline)' : col}`, paddingRight: 10, fontFamily: 'var(--font-mono)' }}>
          <div style={{ color: empty ? 'var(--eureka-text-label)' : col, fontSize: 9, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase' }}>{STAGE_LABEL[k]}</div>
          <div style={{ color: 'var(--eureka-text-micro)', fontSize: 8.5 }}>{empty ? '—' : `${nodes.length} object(s)`}</div>
        </div>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4 }}>
          {empty ? (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 9, fontStyle: 'italic', color: 'var(--eureka-text-micro)', padding: '6px 0' }}>DATA NOT AVAILABLE — cognitive chain incomplete</div>
          ) : nodes.map(nodeRow)}
        </div>
      </div>
    );
  };

  return (
    <div className="ci-field" data-cognitive-field style={{ width: '100%', height: '100%' }}>
      {/* HUD */}
      <div className="ci-field-hud">
        <span className="ci-field-hud-title">Cognitive Operational Field</span>
        <span className="ci-field-hud-sub">observability · navigation · traceability · governance</span>
        <span className="ci-field-hud-backend">single source · LS86</span>
      </div>
      {/* Toolbar */}
      <div className="ci-field-toolbar">
        {MODES.map(btn)}
        <span className="ci-field-toolbar-note">stages {integrity.present.length}/{STAGES.length} · gaps {integrity.holes} · frozen {integrity.frozen.length} · human {integrity.humanDecisions.length} · waiting {integrity.waitingHuman.length}</span>
      </div>

      {/* Stage */}
      <div className="ci-field-stage" style={{ overflow: 'auto', padding: mode === 'CONSTELLATION' ? 0 : '10px 14px' }}>
        {mode === 'CONSTELLATION' && (
          <div style={{ position: 'relative', width: '100%', height: '100%', minHeight: 620, border: '1px solid var(--eureka-spatial-hairline)', overflow: 'hidden' }}>
            <div style={{ position: 'absolute', top: 10, right: 14, zIndex: 8, display: 'flex', gap: 6 }}>
              <button className={`ci-field-btn ${constKind === 'galaxy' ? 'is-on' : ''}`} onClick={() => setConstKind('galaxy')}>Galaxy</button>
              <button className={`ci-field-btn ${constKind === 'tree' ? 'is-on' : ''}`} onClick={() => setConstKind('tree')}>Tree</button>
            </div>
            {constKind === 'galaxy' ? <GalaxyConstellation /> : <CoreConstellation />}
          </div>
        )}

        {mode === 'UNDERSTAND' && (
          <div style={{ fontFamily: 'var(--font-mono)' }}>
            <div style={{ fontFamily: 'var(--font-display)', fontWeight: 600, fontSize: 14, color: 'var(--eureka-text-display)', marginBottom: 12 }}>What Eureka did</div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: 8 }}>
              {integrity.present.map((k) => (
                <div key={k} style={{ border: '1px solid var(--eureka-spatial-hairline)', borderRadius: 2, padding: 8, background: 'var(--eureka-surface)' }}>
                  <div style={{ color: kindColor(k), fontSize: 8.5, letterSpacing: '.08em', textTransform: 'uppercase' }}>{STAGE_LABEL[k]}</div>
                  <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--eureka-text-display)' }}>{(byKind[k]?.length ?? 0)}</div>
                </div>
              ))}
            </div>
            <div style={{ color: 'var(--eureka-text-section)', fontSize: 11, marginTop: 10 }}>{integrity.holes > 0 ? `${integrity.holes} open gap(s) · chain incomplete.` : 'Cognitive chain complete.'}</div>
          </div>
        )}

        {mode === 'EXPLORE' && <div>{STAGES.map(stageRow)}</div>}

        {mode === 'AUDIT' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--eureka-text-section)' }}>Pick an object to reconstruct WHY it exists (provenance trace, upward over the real edges).</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, maxHeight: 260, overflow: 'auto', border: '1px solid var(--eureka-spatial-hairline)', borderRadius: 2, padding: 8, background: 'var(--eureka-surface)' }}>
              {STAGES.map((k) => (byKind[k]?.length ? (
                <div key={k} style={{ display: 'flex', gap: 8, alignItems: 'baseline', flexWrap: 'wrap' }}>
                  <span style={{ minWidth: 126, color: kindColor(k), fontSize: 8.5, letterSpacing: '.08em', textTransform: 'uppercase' }}>{STAGE_LABEL[k]}</span>
                  {byKind[k].map((n) => (
                    <button key={n.id} onClick={() => setSelected(n.id)} className="ci-field-btn" style={{ borderColor: selected === n.id ? kindColor(k) : undefined, color: statusColor(n.status) }}>{n.label}</button>
                  ))}
                </div>
              ) : null))}
            </div>
            {selection ? (
              <div style={{ border: '1px solid var(--eureka-spatial-hairline)', borderRadius: 2, padding: 10, background: 'var(--eureka-surface)', fontFamily: 'var(--font-mono)' }}>
                <div style={{ color: statusColor(selection.status), fontSize: 11, letterSpacing: '.1em', textTransform: 'uppercase' }}>{selection.label}</div>
                <div style={{ fontSize: 10, color: 'var(--eureka-text-label)', marginBottom: 8 }}>{selection.status} · {selection.em} · authority {selection.authority}</div>
                {selection.description && <div style={{ fontSize: 11, color: 'var(--eureka-text-section)', marginBottom: 6, fontFamily: 'var(--font-sans)' }}>{selection.description}</div>}
                {selection.evidence?.length ? <div style={{ fontSize: 10 }}>Evidence: {selection.evidence.join(', ')}</div> : null}
                <div style={{ fontSize: 10, color: 'var(--eureka-text-technical)' }}>Uncertainty: {selection.uncertainty}</div>
                {why.length > 1 && (
                  <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {why.map((w, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 10 }}>
                        <span style={{ color: kindColor(w.node.kind), minWidth: 118 }}>{w.node.label}</span>
                        {w.edgeLabel && <span style={{ color: EDGE_LABEL_COLOR[w.edgeLabel] || 'var(--eureka-text-technical)' }}>⟵ {w.edgeLabel}</span>}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--eureka-text-technical)', fontStyle: 'italic' }}>Select a node to audit its provenance.</div>
            )}
          </div>
        )}

        {mode === 'OPERATE' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 8, fontFamily: 'var(--font-mono)' }}>
            {[
              { label: 'Waiting for human input', n: integrity.waitingHuman.length, color: '#b08800' },
              { label: 'Human decisions', n: integrity.humanDecisions.length, color: '#8250df' },
              { label: 'Not evaluated', n: integrity.notEval.length, color: '#b08800' },
              { label: 'Unsupported / gaps', n: integrity.unsupported.length + integrity.missing.length, color: '#cf222e' },
              { label: 'Frozen', n: integrity.frozen.length, color: '#9a6700' },
            ].map((x) => (
              <div key={x.label} style={{ border: `1px solid ${x.color}`, borderRadius: 2, padding: 8, background: 'var(--eureka-surface)' }}>
                <div style={{ color: x.color, fontSize: 8.5, letterSpacing: '.08em', textTransform: 'uppercase' }}>{x.label}</div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--eureka-text-display)' }}>{x.n}</div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="ci-field-legend">
        {STAGES.map((k) => (
          <span key={k} className="ci-legend-item"><span className="ci-legend-mark" style={{ color: kindColor(k) }}>■</span>{STAGE_LABEL[k]}</span>
        ))}
      </div>
    </div>
  );
}
