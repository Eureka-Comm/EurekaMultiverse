import React, { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import type { CognitiveProjectionGraph, GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import { layoutCognitiveField } from '../../domain/cognitiveFieldLayout';
import { CognitiveFieldRenderer } from './cognitiveFieldRenderer';
import { CognitiveFieldFallback } from './CognitiveFieldFallback';
import { kindColor } from './cognitiveColors';
import './cognitiveField.css';

/**
 * LS91 → LS93 v5 — COGNITIVE VISUAL COMPUTING SURFACE.
 *
 * A spatial, GPU-accelerated cognitive surface that makes the real cognitive
 * operation legible + navigable: a dominant cognitive axis (the PATH:
 * QUESTION→DISCOVERY→EVALUATION→DECISION→ACTION→RESULT) with secondary FIELD
 * context converging into it, rendered over a 4-layer composition
 * (structure / artifact / relation / context).
 *
 * The renderer owns continuous rendering + the semantic camera; React owns state,
 * the Inspector selection, the provenance toggle and the lifecycle. The layout is
 * the SINGLE pure `CognitiveProjectionGraph` → `layoutCognitiveField` projection.
 * The renderer path is WebGPU (opt-in) → WebGL2 (guaranteed) → DOM/SVG; the actual
 * backend is reported honestly via `data-backend`.
 *
 * Focus (Cognitive Focus) is spatial: on select, the focal entity + its real direct
 * chain stay legible and everything unrelated attenuates in 3D. Labels appear by
 * zoom/selection, never all at once.
 */

type RendererMode = 'gpu' | 'dom' | null;

/** The real, renderable backend detected by the honest probe. */
export type DetectedBackend = 'webgl2' | 'webgl1' | 'none';

/**
 * Honest backend probe. Reports the backend that ACTUALLY renders, not merely
 * one that is "available". Critical fix: a browser exposing ONLY WebGL1 must
 * report 'webgl1' (never 'webgl2') — previously the WebGL1 fallback branch
 * returned 'webgl2', falsely labeling a WebGL1-only browser as WebGL2.
 */
export async function detectGpuBackend(): Promise<DetectedBackend> {
  try {
    const c = document.createElement('canvas');
    if (c.getContext('webgl2')) return 'webgl2';
  } catch { /* ignore */ }
  try {
    const c = document.createElement('canvas');
    if (c.getContext('webgl')) return 'webgl1';
  } catch { /* ignore */ }
  return 'none';
}

/** Visual grammar key (shape → class) for the legend + ARIA, never color-only. */
const LEGACY_GRAMMAR = [
  { glyph: '◎', label: 'QUESTION', kind: 'PROBLEM', layer: 'PATH' },
  { glyph: '·', label: 'EVIDENCE', kind: 'EVIDENCE', layer: 'FIELD' },
  { glyph: '●', label: 'FINDING', kind: 'FINDING', layer: 'FIELD' },
  { glyph: '▱', label: 'PREDICTION', kind: 'PREDICTION', layer: 'FIELD' },
  { glyph: '⋔', label: 'PRESCRIPTION', kind: 'PRESCRIPTION', layer: 'FIELD' },
  { glyph: '◇', label: 'ALTERNATIVE', kind: 'ALTERNATIVE', layer: 'FIELD' },
  { glyph: '◎◎', label: 'HUMAN DECISION', kind: 'DECISION', layer: 'PATH' },
  { glyph: '≡', label: 'ACTION', kind: 'ACTION', layer: 'PATH' },
  { glyph: '⌗', label: 'RESULT', kind: 'RESULT', layer: 'PATH' },
  { glyph: '◆', label: 'FROZEN', kind: 'FROZEN', layer: 'PATH' },
];

export function CognitiveField({
  graph,
  onSelect,
  selectedId,
  chapterKinds,
}: {
  graph: CognitiveProjectionGraph;
  onSelect?: (artifact: GraphArtifact) => void;
  selectedId?: string | null;
  chapterKinds?: string[] | null;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const rendererRef = useRef<CognitiveFieldRenderer | null>(null);
  const layoutRef = useRef<ReturnType<typeof layoutCognitiveField> | null>(null);

  const [mode, setMode] = useState<RendererMode>(null);
  const [backendReport, setBackendReport] = useState<string | null>(null);
  const [provenanceVisible, setProvenanceVisible] = useState(false);

  const preferWebgpu = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('webgpu') === '1';
  // ?nolabels=1 hides ONLY the 3D node sprites (labels); the HUD / toolbar / legend /
  // sr block keep their text. ?bare=1 is the NEW stricter readability mode that ALSO
  // hides HUD / toolbar / legend / sr so geometry is judged with no text at all.
  const bareMode = typeof window !== 'undefined' && new URLSearchParams(window.location.search).get('bare') === '1';
  const hideLabels = typeof window !== 'undefined' && (new URLSearchParams(window.location.search).get('nolabels') === '1' || bareMode);

  const layout = useMemo(
    () => layoutCognitiveField(graph, { focusedId: selectedId ?? null, chapterKinds, provenanceVisible }),
    [graph, selectedId, chapterKinds, provenanceVisible],
  );
  layoutRef.current = layout;

  // ---- backend detection (honest: report what will actually render) ----------
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const backend = await detectGpuBackend();
      if (cancelled) return;
      // three/r185 renders GPU only on a WebGL2 context; a WebGL1-only (or no-GL)
      // browser therefore falls back to the DOM/SVG projection (the real renderer)
      // instead of crashing. detectGpuBackend() still reports the true capability
      // ('webgl2' | 'webgl1' | 'none') so the honesty probe is never misleading.
      setMode(backend === 'webgl2' ? 'gpu' : 'dom');
    })();
    return () => { cancelled = true; };
  }, []);

  const onEntitySelect = useCallback(
    (id: string) => {
      const art = graph.nodes.find((n) => n.id === id);
      if (art && onSelect) onSelect(art);
    },
    [graph, onSelect],
  );

  // ---- renderer lifecycle ----------------------------------------------------
  useEffect(() => {
    if (mode !== 'gpu' || !containerRef.current) return;
    let disposed = false;
    // LS94 fix — mount three.js on a DEDICATED host div (created imperatively) so
    // React/Framer's AnimatePresence NEVER reconciles the three.js canvas. This avoids
    // the `insertBefore ... not a child` DOM error during the Operation-Map <-> Knowledge-Space toggle.
    const host = document.createElement('div');
    host.style.width = '100%';
    host.style.height = '100%';
    host.style.position = 'absolute';
    host.style.inset = '0';
    containerRef.current.appendChild(host);
    const renderer = new CognitiveFieldRenderer(
      host,
      { onEntitySelect, onBackend: (b) => { if (!disposed) setBackendReport(b); } },
      { preferWebgpu, hideLabels },
    );
    rendererRef.current = renderer;
    if (layoutRef.current) renderer.setLayout(layoutRef.current);
    return () => {
      disposed = true;
      renderer.dispose();
      host.remove();
      rendererRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // ---- push layout to the renderer -------------------------------------------
  useEffect(() => {
    const r = rendererRef.current;
    if (!r || mode !== 'gpu') return;
    r.setLayout(layout);
  }, [layout, mode]);

  // ---- semantic camera on focus ----------------------------------------------
  useEffect(() => {
    const r = rendererRef.current;
    if (!r || mode !== 'gpu') return;
    if (selectedId) {
      r.setFocused(selectedId);
      r.focusEntity(selectedId);
    } else {
      r.setFocused(layout.cameraStartId);
      r.present();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, mode]);

  const activeBackend = mode === 'gpu' ? (backendReport || 'detecting') : mode === 'dom' ? 'DOM/SVG' : null;

  const artifactById = useMemo(() => {
    const m = new Map<string, GraphArtifact>();
    graph.nodes.forEach((n) => m.set(n.id, n));
    return m;
  }, [graph]);

  const goTo = (id: string | null) => {
    if (!id) { rendererRef.current?.present(); return; }
    const art = graph.nodes.find((n) => n.id === id);
    if (art && onSelect) onSelect(art);
    else rendererRef.current?.focusEntity(id);
  };

  if (!graph.nodes.length) {
    return (
      <div className="ci-empty h-[560px]">
        <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">No governed graph</div>
        <p className="text-xs max-w-md">Data pending — the canonical state has not emitted any artifact for this work.</p>
      </div>
    );
  }

  const cameraStart = layout.cameraStartId;

  return (
    <div
      className="ci-field"
      data-cognitive-field="1"
      data-backend={activeBackend || 'detecting'}
      data-focused={selectedId || cameraStart || 'none'}
      data-open={layout.isOpen ? '1' : '0'}
    >
      {!bareMode && (
        <div className="ci-field-hud">
          <span className="ci-field-hud-title">Cognitive Field</span>
          <span className="ci-field-hud-sub">cognitive visual computing surface · CognitiveProjectionDTO · single source</span>
          <span className="ci-field-hud-backend">{activeBackend ? `renderer · ${activeBackend}` : 'renderer · detecting…'}</span>
          <span className="ci-field-hud-hint">{selectedId ? `focal · ${selectedId}` : layout.isOpen ? 'OPEN · decision pending' : 'drag to orbit · wheel to zoom'}</span>
        </div>
      )}

      {!bareMode && (
        <div className="ci-field-toolbar">
          <button className={`ci-field-btn ${provenanceVisible ? 'is-on' : ''}`} onClick={() => setProvenanceVisible((v) => !v)} title="Reveal provenance on the focused entity">
            provenance
          </button>
          <button className="ci-field-btn" onClick={() => goTo(null)} title="Frame the whole cognitive axis">path</button>
          <button className="ci-field-btn" onClick={() => goTo(cameraStart)} title="Focus the outcome">outcome</button>
          <button className="ci-field-btn" onClick={() => goTo(layout.entities.find((e) => e.kind === 'DECISION')?.id ?? null)} title="Focus the decision">decision</button>
          <button className="ci-field-btn" onClick={() => goTo(layout.entities.find((e) => e.kind === 'PROBLEM')?.id ?? null)} title="Focus the question">question</button>
          <span className="ci-field-toolbar-note">1 cognitive axis · 4 layers · labels on zoom/select</span>
        </div>
      )}

      <div className="ci-field-stage" ref={containerRef}>
        {mode === null && <div className="ci-field-pending">probing renderer backend…</div>}
        {mode === 'dom' && <CognitiveFieldFallback layout={layout} />}
      </div>

      {/* Layer grammar legend — readable, grouped, never overlapping */}
      {!bareMode && (
        <div className="ci-field-legend" role="legend">
          <div className="ci-legend-col">
            <div className="ci-legend-head">COGNITIVE AXIS (L1) · structure</div>
            <div className="ci-legend-row">
              {LEGACY_GRAMMAR.filter((g) => g.layer === 'PATH').map((g) => (
                <span key={g.kind} className="ci-legend-item">
                  <span className="ci-legend-mark" style={{ color: kindColor(g.kind) }}>{g.glyph}</span>
                  {g.label}
                </span>
              ))}
            </div>
          </div>
          <div className="ci-legend-col">
            <div className="ci-legend-head">FIELD (L2) · semantic artifacts</div>
            <div className="ci-legend-row">
              {LEGACY_GRAMMAR.filter((g) => g.layer === 'FIELD').map((g) => (
                <span key={g.kind} className="ci-legend-item">
                  <span className="ci-legend-mark" style={{ color: kindColor(g.kind) }}>{g.glyph}</span>
                  {g.label}
                </span>
              ))}
            </div>
          </div>
          <div className="ci-legend-col ci-legend-tone">
            <div className="ci-legend-head">STATE (height) · real authority</div>
            <div className="ci-legend-row">
              <span className="ci-legend-item"><span className="ci-legend-mark">▲</span>validated</span>
              <span className="ci-legend-item"><span className="ci-legend-mark">▽</span>not-evaluated / unsupported</span>
              <span className="ci-legend-item"><span className="ci-legend-mark">─</span>relations (provenance)</span>
            </div>
          </div>
        </div>
      )}

      {/* accessible textual state — the field is never the only semantic source */}
      {!bareMode && (
        <div className="ci-field-sr" aria-live="polite">
          {selectedId ? (
            <div>
              <strong>Focal: {selectedId}</strong> · {(artifactById.get(selectedId)?.description || 'DATA NOT AVAILABLE')}
            </div>
          ) : (
            <div>
              {graph.nodes.length} governed artifacts · {layout.isOpen ? 'decision pending (OPEN)' : 'decision reached'} · axis {layout.isOpen ? 'QUESTION → REPORT' : 'QUESTION → RESULT'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default CognitiveField;
