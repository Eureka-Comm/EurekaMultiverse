import React, { useEffect, useMemo, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import type { GraphArtifact, GraphEdge, NodeKind } from '../../domain/cognitiveProjectionGraph';
import { nodeKindColor } from '../../domain/graphVisualTokens';
import GraphControlDeck, { GraphLegend } from './GraphControlDeck';
import {
  baseBox, zoomViewport, panViewport, viewportScale, statusTone, semanticLevel,
  GALAXY_W as W, GALAXY_H as H, GALAXY_CX as CX, GALAXY_CY as CY, type ViewportBox, type StatusTone,
} from './constellationNav';

/**
 * GalaxyConstellation v7 — REAL cognitive surface. Static, moderately-spread node layout
 * (nodes are STABLE objects so a contextual card can anchor to them), reduced particle noise
 * (dust = background), node-size hierarchy, real edges with direction + focus labels, and a
 * true CONTEXTUAL NODE CARD anchored to the selected node. Zoom/pan/reset/center mutate only
 * the SVG viewBox. Data is real (GraphArtifact/GraphEdge); never invent anything.
 */

const TONE_COLOR: Record<StatusTone, string> = {
  governed: '#29e0ff', validated: '#4dff9d', pending: '#ffb03c',
  waiting: '#ff7a3c', gap: '#ff5d5d', frozen: '#9b6bff', neutral: '#aab0c6',
};

function mulberry(seed: number) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type P = { x: number; y: number; r: number; o: number; c: string };

function buildDust() {
  const rnd = mulberry(9001);
  const pts: P[] = [];
  const RMAX = 620;
  for (let i = 0; i < 760; i++) {
    const r = 80 + Math.pow(rnd(), 0.72) * (RMAX - 80);
    const base = rnd() * Math.PI * 2;
    const spiral = r * 0.0035;
    const arm = rnd() > 0.5 ? 0 : Math.PI;
    const ang = base + spiral + arm;
    const x = CX + Math.cos(ang) * r * (1 + (rnd() - 0.5) * 0.14);
    const y = CY + Math.sin(ang) * r * 0.74;
    const t = r / RMAX;
    const c = t < 0.2 ? '#ffb0a0' : t < 0.5 ? '#ff8a6a' : '#8fb6d9';
    pts.push({ x, y, r: 0.4 + rnd() * 1.2, o: 0.06 + rnd() * 0.35, c });
  }
  return pts;
}

function buildHeart() {
  const rnd = mulberry(888);
  const pts: P[] = [];
  for (let i = 0; i < 40; i++) {
    const t = rnd() * Math.PI * 2;
    const rr = Math.pow(rnd(), 0.5);
    pts.push({ x: CX + Math.cos(t) * rr * 34, y: CY + Math.sin(t) * rr * 40, r: 1.2 + rnd() * 2.4, o: 0.6 + rnd() * 0.3, c: i % 2 === 0 ? '#ff7af0' : '#c05bff' });
  }
  return pts;
}

function buildStars() {
  const rnd = mulberry(31337);
  return Array.from({ length: 90 }, () => ({ x: rnd() * W, y: rnd() * H, r: 0.35 + rnd() * 0.8, o: 0.1 + rnd() * 0.4, tw: rnd() > 0.72 }));
}

/** Static, moderately-wide spread so nodes are distinguishable objects (not a tight cluster). */
function buildNodeLayout(nodes: GraphArtifact[]) {
  const rnd = mulberry(4242);
  const n = nodes.length;
  return nodes.map((node, i) => {
    const ang = (i / Math.max(n, 1)) * Math.PI * 2 - Math.PI / 2;
    const band = Math.round(n / 3);
    const ring = i % Math.max(band, 1) + 1;
    const radius = 230 + ring * 92 + (rnd() - 0.5) * 34;
    const prominent = node.kind === 'DECISION' || node.authority === 'HUMAN_AUTHORIZED' || node.recommended || node.humanSelected;
    // Base fill from the SINGLE kind token (matches legend + layers). Authority emphasis is a
    // secondary ring (accent) so the legend stays truthful and the human/recommended signal is kept.
    const color = nodeKindColor(node.kind);
    const accent = node.humanSelected ? '#4dff9d' : node.recommended ? '#ff6ad5' : node.authority === 'HUMAN_AUTHORIZED' ? '#ff7a3c' : null;
    return { node, x: CX + Math.cos(ang) * radius, y: CY + Math.sin(ang) * radius * 0.8, prominent, color, accent };
  });
}

function shortTitle(s: string, n = 26) {
  const t = (s || '').trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
}

export default function GalaxyConstellation({
  nodes = [],
  edges = [],
  onSelect,
  selectedId = null,
  selectedArtifact = null,
  focusedNodeIds = [],
  focusedEdgeIds = [],
  highlightRelations = true,
  resetToken = 0,
  centerRequest = 0,
  centerNodeId = null,
  traceMode = 'none',
  onTrace,
  onClose,
  onCenter,
  upstreamCount = 0,
  downstreamCount = 0,
  title = 'EUREKA COGNITIVE CORE',
}: {
  nodes?: GraphArtifact[];
  edges?: GraphEdge[];
  onSelect?: (n: GraphArtifact) => void;
  selectedId?: string | null;
  selectedArtifact?: GraphArtifact | null;
  focusedNodeIds?: string[];
  focusedEdgeIds?: string[];
  highlightRelations?: boolean;
  resetToken?: number;
  centerRequest?: number;
  centerNodeId?: string | null;
  traceMode?: 'none' | 'back' | 'forward';
  onTrace?: (mode: 'back' | 'forward') => void;
  onClose?: () => void;
  onCenter?: () => void;
  upstreamCount?: number;
  downstreamCount?: number;
  title?: string;
}) {
  const dust = useMemo(buildDust, []);
  const heart = useMemo(buildHeart, []);
  const stars = useMemo(buildStars, []);
  const layout = useMemo(() => buildNodeLayout(nodes), [nodes]);
  const posById = useMemo(() => new Map(layout.map((l) => [l.node.id, { x: l.x, y: l.y }])), [layout]);

  const [vb, setVb] = useState<ViewportBox>(() => baseBox());
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ sx: number; sy: number; svb: ViewportBox } | null>(null);
  const [size, setSize] = useState({ w: 0, h: 0 });
  const [focusKind, setFocusKind] = useState<NodeKind | 'ALL'>('ALL');

  // measure container for anchor math
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setSize({ w: el.clientWidth, h: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => { setVb(baseBox()); }, [resetToken]);

  // Center (pan+zoom) on a node, keeping neighbours in view (not extreme).
  useEffect(() => {
    if (!centerNodeId) return;
    const pos = posById.get(centerNodeId);
    if (!pos) return;
    const w = W / 1.4, h = w * (H / W);
    const nx = Math.min(CX, Math.max(CX - w, pos.x - w / 2));
    const ny = Math.min(CY, Math.max(CY - h, pos.y - h / 2));
    setVb({ x: nx, y: ny, w, h });
  }, [centerRequest, centerNodeId, posById]);

  useEffect(() => {
    const el = svgRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      const rect = el.getBoundingClientRect();
      const u = vb.x + ((e.clientX - rect.left) / rect.width) * vb.w;
      const v = vb.y + ((e.clientY - rect.top) / rect.height) * vb.h;
      const f = e.deltaY < 0 ? 1.16 : 1 / 1.16;
      setVb((cur) => zoomViewport(cur, u, v, f));
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [vb]);

  const scale = viewportScale(vb);
  const level = semanticLevel(scale);
  // Effective focus set: the Control Deck FOCUS FILTER highlights a kind (dimming others) when active;
  // otherwise fall back to the selection/trace focus coming from the parent.
  const effectiveFocusIds = useMemo(() => {
    if (focusKind === 'ALL') return focusedNodeIds;
    return nodes.filter((n) => n.kind === focusKind).map((n) => n.id);
  }, [focusKind, nodes, focusedNodeIds]);
  const focusActive = highlightRelations && effectiveFocusIds.length > 0;
  const focusNode = useMemo(() => new Set(effectiveFocusIds), [effectiveFocusIds]);
  const focusEdge = useMemo(() => {
    if (focusKind !== 'ALL') {
      return new Set(edges.filter((e) => focusNode.has(e.source) || focusNode.has(e.target)).map((e) => e.id));
    }
    return new Set(focusedEdgeIds);
  }, [focusKind, focusNode, edges, focusedEdgeIds]);

  const realNodes = nodes.length;
  const humanDecisions = nodes.filter((n) => n.kind === 'DECISION').length;
  const frozen = nodes.filter((n) => n.kind === 'FROZEN').length;
  const notEvaluated = nodes.filter((n) => /NOT_EVALUATED|UNSUPPORTED|NOT_APPLICABLE|DATA NOT AVAILABLE/i.test(n.status)).length;

  if (!realNodes) {
    return (
      <div style={{ position: 'relative', width: '100%', height: '100%', background: 'radial-gradient(1200px 900px at 50% 45%, #0d0d16 0%, #07070e 42%, #000 78%)', fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: '#efeaff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 13, letterSpacing: '0.28em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.85)' }}>EUREKA</div>
          <div style={{ marginTop: 10, fontSize: 11, letterSpacing: '0.2em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.45)' }}>No cognitive data available</div>
          <div style={{ marginTop: 22, fontSize: 10, letterSpacing: '0.16em', color: 'rgba(233,228,255,0.28)' }}>Run a governed cognitive operation to populate the constellation.</div>
        </div>
      </div>
    );
  }

  const handlePointerDown = (e: React.PointerEvent<SVGSVGElement>) => {
    const target = e.target as Element;
    if (target && target.closest && target.closest('[data-node]')) return;
    const el = svgRef.current;
    if (!el) return;
    try { el.setPointerCapture(e.pointerId); } catch { /* synthetic */ }
    dragRef.current = { sx: e.clientX, sy: e.clientY, svb: vb };
  };
  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const d = dragRef.current;
    const el = svgRef.current;
    if (!d || !el) return;
    const rect = el.getBoundingClientRect();
    const dxContent = ((e.clientX - d.sx) / rect.width) * d.svb.w;
    const dyContent = ((e.clientY - d.sy) / rect.height) * d.svb.h;
    setVb(panViewport(d.svb, dxContent, dyContent));
  };
  const endDrag = () => { dragRef.current = null; };

  // Anchor math: content coords → container px (preserveAspectRatio xMidYMid meet, no crop)
  const anchorPos = (() => {
    if (!selectedArtifact) return null;
    const pos = posById.get(selectedArtifact.id);
    const cw = size.w || 1, ch = size.h || 1;
    if (!pos || !cw) return null;
    const s = Math.min(cw / vb.w, ch / vb.h);
    const ox = (cw - vb.w * s) / 2, oy = (ch - vb.h * s) / 2;
    return { sx: (pos.x - vb.x) * s + ox, sy: (pos.y - vb.y) * s + oy };
  })();

  // Contextual card placement: side away from edge, clamped in viewport.
  let cardStyle: React.CSSProperties | null = null;
  if (anchorPos) {
    const cw = size.w || 0, ch = size.h || 0;
    const cardW = 250;
    const leftSide = anchorPos.sx > cw / 2;
    let left = leftSide ? anchorPos.sx - cardW - 30 : anchorPos.sx + 30;
    let top = anchorPos.sy - 90;
    left = Math.max(8, Math.min(left, cw - cardW - 8));
    top = Math.max(8, Math.min(top, ch - 220));
    cardStyle = { left, top, width: cardW };
  }

  const controlsStyle: React.CSSProperties = {
    fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase',
    padding: '5px 10px', borderRadius: 8, cursor: 'pointer', color: '#efeaff',
    background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.16)',
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', flexDirection: 'column', overflow: 'hidden', background: 'radial-gradient(1200px 900px at 50% 45%, #0d0d16 0%, #07070e 42%, #000 78%)', fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: '#efeaff' }}>
      {/* GRAPH SAFE AREA — the graph fills the viewport minus the bottom control deck/footer */}
      <div ref={containerRef} style={{ position: 'relative', flex: 1, minHeight: 0, overflow: 'hidden' }}>
      <svg
        ref={svgRef}
        viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
        width="100%" height="100%" preserveAspectRatio="xMidYMid meet"
        style={{ position: 'absolute', inset: 0, cursor: dragRef.current ? 'grabbing' : 'grab', touchAction: 'none' }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
        onPointerCancel={endDrag}
      >
        <defs>
          <radialGradient id="gal-core" cx="50%" cy="48%" r="55%"><stop offset="0%" stopColor="#ffffff" /><stop offset="22%" stopColor="#ffe7c9" /><stop offset="60%" stopColor="#f0836a" /><stop offset="100%" stopColor="#5a1f1f" /></radialGradient>
          <filter id="gal-glow" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="16" /></filter>
          <marker id="gal-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L7,3.5 L0,7 z" fill="#ffffff" opacity="0.8" />
          </marker>
        </defs>

        {stars.map((s, i) => <circle key={`st${i}`} cx={s.x} cy={s.y} r={s.r} fill="#fff" opacity={s.o} />)}
        <circle cx={CX} cy={CY} r={210} fill="url(#gal-core)" filter="url(#gal-glow)" opacity={0.42} />
        <circle cx={CX} cy={CY} r={660} fill="none" stroke="rgba(255,180,160,0.06)" strokeWidth={1} />
        {dust.map((p, i) => <circle key={`d${i}`} cx={p.x} cy={p.y} r={p.r} fill={p.c} opacity={p.o} />)}
        {heart.map((p, i) => <motion.circle key={`h${i}`} cx={p.x} cy={p.y} r={p.r} fill={p.c} opacity={p.o} animate={{ opacity: [p.o, p.o * 0.5, p.o] }} transition={{ duration: 2.4 + (i % 3), repeat: Infinity, ease: 'easeInOut' }} />)}
        <circle cx={CX} cy={CY} r={16} fill="#fff" filter="url(#gal-glow)" />

        {/* REAL edges with direction + focus labels */}
        {edges.map((e) => {
          const a = posById.get(e.source);
          const b = posById.get(e.target);
          if (!a || !b) return null;
          const emph = focusEdge.has(e.id);
          const dimmed = focusActive && !emph;
          const op = dimmed ? 0.05 : emph ? 0.9 : 0.34;
          const mx = a.x + (b.x - a.x) * 0.5, my = a.y + (b.y - a.y) * 0.5;
          const ang = Math.atan2(b.y - a.y, b.x - a.x);
          return (
            <g key={`e${e.id}`}>
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#ffffff" strokeWidth={emph ? 2 : 0.9} strokeOpacity={op} strokeDasharray={emph ? '' : '2 6'} markerEnd={emph ? 'url(#gal-arrow)' : undefined} />
              {emph && (
                <g transform={`translate(${mx} ${my}) rotate(${(ang * 180) / Math.PI})`}>
                  <rect x={4} y={-9} width={50} height={18} rx={4} fill="rgba(0,0,0,0.6)" stroke="rgba(255,255,255,0.35)" />
                  <text x={7} y={4} fontSize={8} fill="#ffffff" letterSpacing="0.08em">{e.label}</text>
                </g>
              )}
            </g>
          );
        })}

        {/* Static cognitive objects with size hierarchy */}
        {layout.map((l, i) => {
          const sel = l.node.id === selectedId;
          const dim = focusActive && !focusNode.has(l.node.id);
          const emph = focusNode.has(l.node.id);
          const nodeOpacity = sel ? 1 : dim ? 0.16 : 1;
          const tone = TONE_COLOR[statusTone(l.node.status)];
          const showStatus = level >= 1 || sel;
          const showTitle = (level >= 2 || sel) && !!l.node.description;
          const left = l.x < CX;
          const tx = l.x + (left ? -12 : 12);
          const anchor = left ? 'end' : 'start';
          const r = sel ? 8 : l.prominent ? 5.4 : 3.4;
          const showEm = sel;
          return (
            <g key={l.node.id} data-node onClick={(e) => { e.stopPropagation(); onSelect?.(l.node); }}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(l.node); } }}
              tabIndex={0} role="button" aria-label={`${l.node.kind} ${l.node.id}`}
              style={{ cursor: 'pointer', outline: 'none' }} opacity={nodeOpacity}>
              <circle cx={l.x} cy={l.y} r={26} fill="transparent" style={{ pointerEvents: 'all' }} />
              {sel && <circle cx={l.x} cy={l.y} r={r + 6} fill="none" stroke={l.color} strokeWidth={1.3} opacity={0.95} />}
              {l.accent && <circle cx={l.x} cy={l.y} r={r + 3.6} fill="none" stroke={l.accent} strokeWidth={1.2} opacity={0.9} />}
              <motion.circle cx={l.x} cy={l.y} r={r} fill={l.color} animate={{ opacity: [0.95, 0.4, 0.95] }} transition={{ duration: 2 + (i % 4), repeat: Infinity, ease: 'easeInOut' }} style={{ filter: `drop-shadow(0 0 ${sel ? 12 : emph ? 9 : 4}px ${l.color})` }} />
              <text x={tx} y={l.y} dominantBaseline="middle" textAnchor={anchor} fill={sel || emph ? '#ffffff' : l.color} fontSize={9} letterSpacing="0.12em">
                {l.node.kind === 'DECISION' ? `${l.node.kind}·${l.node.id}` : (l.node.label || l.node.id)}
              </text>
              {showStatus && <text x={tx} y={l.y + 13} dominantBaseline="middle" textAnchor={anchor} fill={tone} fontSize={8} letterSpacing="0.1em">{l.node.status || '—'}</text>}
              {showEm && <text x={tx} y={l.y + 26} dominantBaseline="middle" textAnchor={anchor} fill="rgba(255,255,255,0.7)" fontSize={8} letterSpacing="0.06em">{(l.node.em || '').replace(/^EM\s*/i, '')}</text>}
              {showTitle && <text x={tx} y={l.y + 39} dominantBaseline="middle" textAnchor={anchor} fill="rgba(255,255,255,0.78)" fontSize={8}>{shortTitle(l.node.description).toUpperCase()}</text>}
            </g>
          );
        })}
      </svg>

      {/* CONTEXTUAL NODE CARD — anchored to the selected node */}
      {selectedArtifact && cardStyle && (
        <div style={{ position: 'absolute', ...cardStyle, zIndex: 20, pointerEvents: 'auto' }}>
          {/* subtle connector */}
          {anchorPos && (
            <div style={{
              position: 'absolute', width: 30, height: 1, background: 'rgba(255,255,255,0.35)',
              left: (cardStyle.left as number) < anchorPos.sx ? (cardStyle.left as number) + 250 : -30,
              top: anchorPos.sy, transform: 'translateY(-50%)',
            }} />
          )}
          <div className="ci-panel" style={{ padding: 12, borderRadius: 8 }}>
            <div className="flex items-center justify-between gap-2 mb-1">
              <div className="flex items-center gap-2 min-w-0">
                <span style={{ color: TONE_COLOR[statusTone(selectedArtifact.status)], fontSize: 10, fontWeight: 700, letterSpacing: '0.16em', textTransform: 'uppercase' }}>{selectedArtifact.kind}</span>
              </div>
              <button type="button" onClick={onClose} aria-label="Close card" style={{ color: 'var(--eureka-text-label)', fontSize: 11, cursor: 'pointer', background: 'transparent', border: 'none' }}>✕</button>
            </div>
            <div className="text-[11px] font-mono text-[var(--eureka-text-display)] mb-1.5">{selectedArtifact.id}</div>
            <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: TONE_COLOR[statusTone(selectedArtifact.status)] }}>{selectedArtifact.status || '—'}</div>
            <div className="text-[11px] text-[var(--eureka-text-section)] border-l-2 border-[var(--eureka-spatial-hairline)] pl-2 mb-1.5 leading-snug">
              {selectedArtifact.description || 'DATA NOT AVAILABLE'}
            </div>
            <div className="text-[9px] font-mono text-[var(--eureka-text-label)] mb-2">{(selectedArtifact.em || '—').replace(/^EM\s*/i, '')} · {selectedArtifact.authority}</div>
            {(selectedArtifact.kind === 'RESULT' || selectedArtifact.kind === 'FROZEN') && (
              <div className="text-[9px] font-mono text-[var(--eureka-text-section)] mb-2 space-y-0.5">
                <div>STATE · {selectedArtifact.kind === 'FROZEN' ? 'frozen result' : 'result exists'} · {selectedArtifact.status || 'DATA NOT AVAILABLE'}</div>
                <div>EVIDENCE · {(selectedArtifact.evidence && selectedArtifact.evidence.length) ? `${selectedArtifact.evidence.length} item(s)` : 'DATA NOT AVAILABLE'}</div>
                <div>VALIDATION · {selectedArtifact.status === 'FROZEN' ? 'FROZEN' : /VALIDATED|COMPLETED|PUBLISHED|EVALUATED|EXECUTED/i.test(selectedArtifact.status || '') ? selectedArtifact.status : 'DATA NOT AVAILABLE'}</div>
              </div>
            )}
            <div className="flex items-center gap-3 text-[10px] font-mono text-[var(--eureka-text-label)] mb-2">
              <span>↑ <b style={{ color: '#29e0ff' }}>{upstreamCount}</b></span>
              <span>↓ <b style={{ color: '#4dff9d' }}>{downstreamCount}</b></span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              <button type="button" onClick={() => onTrace?.('back')} className="text-[9px] px-2 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-signal-semantic)]">↑ TRACE</button>
              <button type="button" onClick={() => onTrace?.('forward')} className="text-[9px] px-2 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-signal-semantic)]">↓ TRACE</button>
              {onCenter && <button type="button" onClick={onCenter} className="text-[9px] px-2 py-1 rounded border border-[var(--eureka-border)] hover:border-[var(--eureka-signal-semantic)]">◎ CENTER</button>}
            </div>
            {traceMode !== 'none' && <div className="text-[9px] mt-1" style={{ color: '#9b6bff' }}>{traceMode === 'back' ? 'tracing upstream' : 'tracing downstream'}</div>}
          </div>
        </div>
      )}

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(120% 100% at 50% 45%, transparent 60%, rgba(0,0,0,0.5) 100%)' }} />

      <div style={{ position: 'absolute', inset: '0 0 auto 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 24px', zIndex: 6, pointerEvents: 'none' }}>
        <span style={{ padding: '6px 12px', borderRadius: 6, background: 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.16)', fontSize: 11, letterSpacing: '0.14em', textTransform: 'uppercase', color: '#fff' }}>{title}</span>
        <span style={{ display: 'inline-flex', gap: 12 }}>
          <span style={{ padding: '5px 11px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 10 }}>OBJECTS <b style={{ color: '#29e0ff' }}>{realNodes}</b></span>
          <span style={{ padding: '5px 11px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 10 }}>GAPS <b style={{ color: '#ffb03c' }}>{notEvaluated}</b></span>
          <span style={{ padding: '5px 11px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 10 }}>HUMAN DEC. <b style={{ color: '#ff3d8c' }}>{humanDecisions}</b></span>
          <span style={{ padding: '5px 11px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 10 }}>FROZEN <b style={{ color: '#9b6bff' }}>{frozen}</b></span>
        </span>
      </div>

      <div style={{ position: 'absolute', left: 24, bottom: 22, display: 'flex', gap: 6, zIndex: 7 }}>
        <button type="button" onClick={() => setVb((c) => zoomViewport(c, CX, CY, 1.25))} aria-label="Zoom in" style={controlsStyle}>＋ ZOOM IN</button>
        <button type="button" onClick={() => setVb((c) => zoomViewport(c, CX, CY, 1 / 1.25))} aria-label="Zoom out" style={controlsStyle}>− ZOOM OUT</button>
        <button type="button" onClick={() => setVb(baseBox())} aria-label="Reset view" style={controlsStyle}>⟲ RESET</button>
      </div>
      </div>

      {/* GRAPH CONTROL DECK + FOOTER (dark glass instrument panel) */}
      <div style={{ padding: '0 22px 14px', zIndex: 8 }}>
        <GraphControlDeck nodes={nodes} focusKind={focusKind} onFocusKind={setFocusKind} />
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginTop: 10, flexWrap: 'wrap' }}>
          <div style={{ fontSize: 9, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.45)' }}>DRAG TO PAN · SCROLL TO ZOOM · + / − / RESET</div>
          <GraphLegend nodes={nodes} />
        </div>
      </div>
    </div>
  );
}
