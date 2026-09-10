import React, { useMemo } from 'react';
import { motion } from 'framer-motion';

/**
 * CoreConstellation v3 — "cerebro / constelación de agentes" cinematográfico.
 * Rediseñado para NO verse genérico: campo de estrellas, nebulosa, viñeta, grano,
 * cerebro denso, clústeres por dominio como ÁRBOLES que ramifican, filamentos con
 * flujo de energía animado y glow neón. Presentacional (recibe `clusters`) con un
 * default simulado por dominio para evaluar el look.
 */

const W = 1440, H = 900, CX = W / 2, CY = H / 2 - 10;

export type ClusterNode = { x: number; y: number; r: number; live: boolean; label: string };
export type Branch = { x: number; y: number; leaves: ClusterNode[] };
export type ClusterSpec = { name: string; color: string; glow: string; x: number; y: number; nodes?: ClusterNode[]; branches?: Branch[] };

const DOMAINS = [
  { name: 'SALES', color: '#ff3d8c', glow: 'rgba(255,61,140,0.5)' },
  { name: 'DEALS', color: '#29e0ff', glow: 'rgba(41,224,255,0.5)' },
  { name: 'OPERATIONS', color: '#ffb03c', glow: 'rgba(255,176,60,0.5)' },
  { name: 'INTELLIGENCE', color: '#6fe94b', glow: 'rgba(111,233,75,0.5)' },
  { name: 'DATA', color: '#9b6bff', glow: 'rgba(155,107,255,0.5)' },
  { name: 'CUSTOMER', color: '#ff6ad5', glow: 'rgba(255,106,213,0.5)' },
];

function mulberry(seed: number) {
  return function () {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Clústeres simulados tipo ÁRBOL (hub → ramas → agentes), como el mapa de los reels.
function buildSimulated(): ClusterSpec[] {
  const rnd = mulberry(20260906);
  return DOMAINS.map((dom, i) => {
    const ang = (i / DOMAINS.length) * Math.PI * 2 - Math.PI / 2;
    const rad = 300 + rnd() * 60;
    const ax = CX + Math.cos(ang) * rad;
    const ay = CY + Math.sin(ang) * rad * 0.8;
    const branches: Branch[] = [];
    const B = 3 + Math.floor(rnd() * 3);
    for (let b = 0; b < B; b++) {
      const ba = rnd() * Math.PI * 2;
      const br = 40 + rnd() * 34;
      const bx = ax + Math.cos(ba) * br;
      const by = ay + Math.sin(ba) * br;
      const leaves: ClusterNode[] = [];
      const L = 4 + Math.floor(rnd() * 5);
      for (let l = 0; l < L; l++) {
        const la = rnd() * Math.PI * 2;
        const lr = 20 + rnd() * 58;
        leaves.push({ x: bx + Math.cos(la) * lr, y: by + Math.sin(la) * lr, r: 2.1 + rnd() * 3.2, live: rnd() > 0.68, label: `${dom.name}.R${b + 1}.A${l + 1}` });
      }
      branches.push({ x: bx, y: by, leaves });
    }
    return { name: dom.name, color: dom.color, glow: dom.glow, x: ax, y: ay, branches };
  });
}

// Campo de estrellas de fondo.
function buildStars() {
  const rnd = mulberry(4242);
  const stars: { x: number; y: number; r: number; o: number; tw: boolean }[] = [];
  for (let i = 0; i < 300; i++) {
    stars.push({ x: rnd() * W, y: rnd() * H, r: 0.5 + rnd() * 1.4, o: 0.15 + rnd() * 0.7, tw: rnd() > 0.75 });
  }
  return stars;
}

function buildBrain() {
  const rnd = mulberry(777);
  const brain: { x: number; y: number; r: number; a: number; core: boolean }[] = [];
  for (let i = 0; i < 240; i++) {
    const t = rnd() * Math.PI * 2;
    const rr = Math.pow(rnd(), 0.55);
    brain.push({ x: CX + Math.cos(t) * rr * 70, y: CY + Math.sin(t) * rr * 66, r: 0.9 + rnd() * 2.4, a: 0.35 + rnd() * 0.6, core: rr < 0.42 });
  }
  return brain;
}

export default function CoreConstellation({ clusters, title = 'EUREKA CORE', subtitle = '137 AGENTS · 6 DEPARTMENTS' }: { clusters?: ClusterSpec[]; title?: string; subtitle?: string }) {
  const cls = useMemo(() => (clusters && clusters.length ? clusters : buildSimulated()), [clusters]);
  const stars = useMemo(buildStars, []);
  const brain = useMemo(buildBrain, []);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden', background: 'radial-gradient(1400px 900px at 50% 8%, #2a1150 0%, #160b31 42%, #08040f 74%, #000 100%)', fontFamily: "'IBM Plex Mono', ui-monospace, monospace", color: '#e9e4ff' }}>
      {/* nebulosa */}
      <motion.div aria-hidden style={{ position: 'absolute', left: '-12%', top: '-22%', width: '60%', height: '72%', background: 'radial-gradient(circle, rgba(255,61,140,0.24), transparent 62%)', filter: 'blur(80px)' }} animate={{ x: [0, 140, 0], y: [0, -40, 0] }} transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }} />
      <motion.div aria-hidden style={{ position: 'absolute', right: '-14%', bottom: '-26%', width: '62%', height: '78%', background: 'radial-gradient(circle, rgba(41,224,255,0.20), transparent 62%)', filter: 'blur(90px)' }} animate={{ x: [0, -160, 0], y: [0, 55, 0] }} transition={{ duration: 24, repeat: Infinity, ease: 'easeInOut' }} />
      <motion.div aria-hidden style={{ position: 'absolute', left: '28%', bottom: '-32%', width: '48%', height: '62%', background: 'radial-gradient(circle, rgba(155,107,255,0.24), transparent 62%)', filter: 'blur(90px)' }} animate={{ x: [0, 110, 0], y: [0, -70, 0] }} transition={{ duration: 27, repeat: Infinity, ease: 'easeInOut' }} />

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
        <defs>
          <radialGradient id="core" cx="50%" cy="42%" r="60%"><stop offset="0%" stopColor="#ffffff" /><stop offset="28%" stopColor="#ffdbff" /><stop offset="66%" stopColor="#b455ff" /><stop offset="100%" stopColor="#2a0f51" /></radialGradient>
          {cls.map((d, i) => (<radialGradient key={i} id={`node-${i}`} cx="50%" cy="50%" r="55%"><stop offset="0%" stopColor="#ffffff" /><stop offset="40%" stopColor={d.color} /><stop offset="100%" stopColor={d.color} stopOpacity="0.08" /></radialGradient>))}
          <filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="12" /></filter>
          <filter id="noise"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" /><feColorMatrix type="saturate" values="0" /></filter>
          <clipPath id="frame"><rect x="0" y="0" width={W} height={H} /></clipPath>
        </defs>

        {/* estrellas */}
        {stars.map((s, i) => (s.tw
          ? <motion.circle key={`st${i}`} cx={s.x} cy={s.y} r={s.r} fill="#fff" opacity={s.o} animate={{ opacity: [s.o, s.o * 0.25, s.o] }} transition={{ duration: 2.5 + (i % 6), repeat: Infinity, ease: 'easeInOut' }} />
          : <circle key={`st${i}`} cx={s.x} cy={s.y} r={s.r} fill="#fff" opacity={s.o} />))}

        {/* filamentos core -> cluster (flujo) */}
        {cls.map((c, ci) => (
          <g key={`f${ci}`}>
            <line x1={CX} y1={CY} x2={c.x} y2={c.y} stroke={c.color} strokeOpacity={0.10} strokeWidth={1.6} style={{ filter: `drop-shadow(0 0 8px ${c.glow})` }} />
            <motion.line x1={CX} y1={CY} x2={c.x} y2={c.y} stroke={c.color} strokeOpacity={0.55} strokeWidth={1.4} strokeDasharray="5 14" animate={{ strokeDashoffset: [0, -200] }} transition={{ duration: 6, repeat: Infinity, ease: 'linear' }} style={{ filter: `drop-shadow(0 0 6px ${c.glow})` }} />
          </g>
        ))}

        {/* cerebro denso */}
        {brain.map((b, i) => <motion.circle key={`b${i}`} cx={b.x} cy={b.y} r={b.r} fill={b.core ? '#ffffff' : '#e6c8ff'} opacity={b.a} animate={{ opacity: [b.a, b.a * 0.3, b.a] }} transition={{ duration: 2 + (i % 4), repeat: Infinity, ease: 'easeInOut' }} />)}

        {/* núcleo */}
        <circle cx={CX} cy={CY} r={150} fill="url(#core)" filter="url(#glow)" opacity={0.5} />
        <motion.circle cx={CX} cy={CY} r={80} fill="none" stroke="rgba(255,218,255,0.45)" strokeWidth={1} animate={{ opacity: [0.5, 0.22, 0.5] }} transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut' }} />
        <motion.circle cx={CX} cy={CY} r={94} fill="none" stroke="rgba(180,85,255,0.55)" strokeWidth={1.4} strokeDasharray="2 12" animate={{ rotate: 360 }} transition={{ duration: 28, repeat: Infinity, ease: 'linear' }} style={{ transformOrigin: `${CX}px ${CY}px` }} />
        <circle cx={CX} cy={CY} r={54} fill="url(#core)" />
        <circle cx={CX} cy={CY} r={54} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
        <text x={CX} y={CY - 7} textAnchor="middle" fill="#fff" fontSize={15} fontWeight={700} letterSpacing="0.3em">CORE</text>
        <text x={CX} y={CY + 18} textAnchor="middle" fill="rgba(255,255,255,0.7)" fontSize={9} letterSpacing="0.2em">★ {title}</text>

        {/* clusters (árboles o estrella) */}
        {cls.map((c, ci) => {
          const kind = c.branches && c.branches.length;
          return (
            <g key={`c${ci}`}>
              <text x={c.x} y={c.y - 58} textAnchor="middle" fill={c.color} fontSize={12} fontWeight={700} letterSpacing="0.2em" style={{ filter: `drop-shadow(0 0 8px ${c.glow})` }}>{c.name}</text>
              <text x={c.x} y={c.y - 44} textAnchor="middle" fill="rgba(255,255,255,0.45)" fontSize={9} letterSpacing="0.14em">{kind ? c.branches!.reduce((a, b) => a + b.leaves.length, 0) : (c.nodes?.length ?? 0)} AGENTS</text>

              {kind ? (
                // árbol: hub -> rama -> hoja
                <g key={`tree${ci}`}>
                  {c.branches!.map((br, b) => (
                    <g key={`br${ci}-${b}`}>
                      <motion.line x1={c.x} y1={c.y} x2={br.x} y2={br.y} stroke={c.color} strokeOpacity={0.35} strokeWidth={0.9} animate={{ strokeOpacity: [0.2, 0.6, 0.2] }} transition={{ duration: 2.6 + b * 0.3, repeat: Infinity, ease: 'easeInOut' }} />
                      <circle cx={br.x} cy={br.y} r={2.4} fill={c.color} opacity={0.9} style={{ filter: `drop-shadow(0 0 5px ${c.glow})` }} />
                      {br.leaves.map((n, l) => (
                        <g key={`lf${ci}-${b}-${l}`}>
                          <motion.line x1={br.x} y1={br.y} x2={n.x} y2={n.y} stroke={c.color} strokeOpacity={n.live ? 0.35 : 0.12} strokeWidth={0.6} strokeDasharray="2 8" animate={{ strokeDashoffset: [0, -80] }} transition={{ duration: 5, repeat: Infinity, ease: 'linear' }} />
                          {n.live && <circle cx={n.x} cy={n.y} r={n.r + 3.4} fill="none" stroke={c.color} strokeOpacity={0.3} strokeWidth={0.6} />}
                          <motion.circle cx={n.x} cy={n.y} r={n.r} fill={`url(#node-${ci})`} style={{ filter: `drop-shadow(0 0 ${n.live ? 7 : 3}px ${c.glow})` }} animate={{ opacity: n.live ? [0.95, 0.35, 0.95] : [0.85, 0.5, 0.85] }} transition={n.live ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : { duration: 3 + (ci % 3), repeat: Infinity, ease: 'easeInOut' }} />
                          <title>{n.label}</title>
                        </g>
                      ))}
                    </g>
                  ))}
                </g>
              ) : (
                // fallback: constelación radial (datos reales) hub -> nodo
                <g key={`star${ci}`}>
                  {c.nodes?.map((n, j) => {
                    const nx = c.nodes![(j + 1) % c.nodes!.length];
                    return <g key={`sn${ci}-${j}`}><line x1={c.x} y1={c.y} x2={n.x} y2={n.y} stroke={c.color} strokeOpacity={0.18} strokeWidth={0.6} /><line x1={n.x} y1={n.y} x2={nx.x} y2={nx.y} stroke={c.color} strokeOpacity={0.12} strokeWidth={0.5} /><motion.circle cx={n.x} cy={n.y} r={n.r} fill={`url(#node-${ci})`} style={{ filter: `drop-shadow(0 0 ${n.live ? 6 : 3}px ${c.glow})` }} animate={{ opacity: n.live ? [0.95, 0.4, 0.95] : [0.85, 0.55, 0.85] }} transition={n.live ? { duration: 1.6, repeat: Infinity, ease: 'easeInOut' } : { duration: 3 + (ci % 3), repeat: Infinity, ease: 'easeInOut' }} /><title>{n.label}</title></g>;
                  })}
                </g>
              )}
            </g>
          );
        })}

        {/* grano / viñeta */}
        <rect x="0" y="0" width={W} height={H} fill="transparent" filter="url(#noise)" opacity="0.04" />
      </svg>

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(120% 100% at 50% 45%, transparent 55%, rgba(0,0,0,0.55) 100%)' }} />

      {/* top bar */}
      <div style={{ position: 'absolute', inset: '0 0 auto 0', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 28px', zIndex: 6 }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
          <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center', padding: '6px 12px', borderRadius: 999, border: '1px solid rgba(255,255,255,0.14)', background: 'rgba(255,255,255,0.04)', fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase' }}><motion.span style={{ width: 8, height: 8, borderRadius: 999, background: '#4dff9d', boxShadow: '0 0 10px #4dff9d' }} animate={{ opacity: [1, 0.25, 1] }} transition={{ duration: 1.4, repeat: Infinity }} /> LIVE</span>
          <span style={{ fontSize: 11, letterSpacing: '0.16em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.6)' }}>BRIEFINGS · 24:59:17</span>
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <span style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 11 }}>AGENTS <b style={{ color: '#29e0ff' }}>{cls.reduce((a, c) => a + (c.nodes?.length ?? (c.branches?.reduce((x, y) => x + y.leaves.length, 0) ?? 0)), 0)}</b></span>
          <span style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 11 }}>OPS <b style={{ color: '#ffb03c' }}>98%</b></span>
          <span style={{ padding: '6px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.12)', background: 'rgba(255,255,255,0.03)', fontSize: 11 }}>$ <b style={{ color: '#ff3d8c' }}>2.4M</b></span>
        </div>
      </div>

      {/* right labels */}
      <div style={{ position: 'absolute', right: 28, top: '50%', transform: 'translateY(-50%)', textAlign: 'right', display: 'flex', flexDirection: 'column', gap: 12, zIndex: 6 }}>
        <span style={{ color: '#9b6bff', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Neuro</span>
        <span style={{ color: '#29e0ff', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Memory</span>
        <span style={{ color: '#ff3d8c', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Context</span>
        <span style={{ color: '#ffb03c', fontSize: 10, letterSpacing: '0.2em', textTransform: 'uppercase' }}>Tools</span>
      </div>

      {/* legend */}
      <div style={{ position: 'absolute', left: 28, bottom: 26, zIndex: 6, display: 'flex', gap: 16, flexWrap: 'wrap', maxWidth: '46%' }}>
        {cls.map((c, i) => (
          <span key={i} style={{ display: 'inline-flex', gap: 7, alignItems: 'center', fontSize: 10, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(233,228,255,0.75)' }}><span style={{ width: 9, height: 9, borderRadius: 999, background: c.color, boxShadow: `0 0 8px ${c.glow}` }} /> {c.name}</span>
        ))}
      </div>
    </div>
  );
}
