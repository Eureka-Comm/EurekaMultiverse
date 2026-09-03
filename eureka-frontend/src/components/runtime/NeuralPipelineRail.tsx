import React, { useEffect, useMemo } from "react";

// Paleta (estilo NeuralPipelineRail, más pequeño)
const C = {
  bg: "#FFFFFF",
  border: "#E8E5DE",
  text: "#14140F",
  textMuted: "#6B6B63",
  textFaint: "#A8A59C",
  accent: "#0F6E6E",
  accent2: "#5B5BD6",
  gray: "#D9D6CD",
  warning: "#B98900",
};

const fontDisplay = "'Space Grotesk', 'Inter', sans-serif";
const fontMono = "'IBM Plex Mono', ui-monospace, monospace";

function useGoogleFonts() {
  useEffect(() => {
    if (document.getElementById("neural-rail-fonts")) return;
    const link = document.createElement("link");
    link.id = "neural-rail-fonts";
    link.rel = "stylesheet";
    link.href =
      "https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@600&family=IBM+Plex+Mono:wght@400;500&display=swap";
    document.head.appendChild(link);
  }, []);
}

// status: "completed" | "waiting" | "pending"
const STATUS_META = {
  completed: { color: C.accent, caption: "COMPLETED" },
  waiting: { color: C.warning, caption: "WAITING FOR HUMAN INPUT" },
  pending: { color: C.textFaint, caption: "PENDING" },
};

// Tamaño reducido (más pequeño)
const W = 1200;
const H = 90;
const NODES_PER_LAYER = 3;
const MARGIN_X = 60;
const TOP_Y = 12;
const BOTTOM_Y = 50;

function layerX(i: number, count: number) {
  return MARGIN_X + (i * (W - 2 * MARGIN_X)) / (count - 1);
}

function nodesForLayer(i: number) {
  return Array.from({ length: NODES_PER_LAYER }, (_, n) => {
    const jitter = 4 * Math.sin(i * 2.3 + n * 1.7);
    return { y: TOP_Y + (n * (BOTTOM_Y - TOP_Y)) / (NODES_PER_LAYER - 1) + jitter };
  });
}

function GlobalStyle() {
  return (
    <style>{`
      @keyframes npr-pulse-ring {
        0%, 100% { r: 3.4; opacity: 1; }
        50% { r: 5.4; opacity: 0.35; }
      }
    `}</style>
  );
}

export default function NeuralPipelineRail({ stages = [], onStageClick }: { stages?: { key: string; label: string; status: "completed" | "waiting" | "pending"; caption?: string }[]; onStageClick?: (key: string) => void }) {
  useGoogleFonts();
  const count = stages.length;

  const layers = useMemo(
    () => stages.map((s, i) => ({ ...s, x: layerX(i, count), nodes: nodesForLayer(i) })),
    [stages, count]
  );

  const connections = useMemo(() => {
    const conns: any[] = [];
    for (let g = 0; g < layers.length - 1; g++) {
      const a = layers[g];
      const b = layers[g + 1];
      a.nodes.forEach((na, i) => {
        b.nodes.forEach((nb, j) => {
          conns.push({ gap: g, x1: a.x, y1: na.y, x2: b.x, y2: nb.y, sourceStatus: a.status, key: `${g}-${i}-${j}` });
        });
      });
    }
    return conns;
  }, [layers]);

  // ONE flow, not many: the traveling circles only render on the SINGLE segment that
  // transitions into the currently-active EM (the first non-completed stage). As the
  // pipeline advances, that segment moves forward, so it reads as a single "walk" through
  // the EMs instead of a static mesh of many simultaneous flows. When all stages are done
  // there is no in-flight flow (the pipeline has finished).
  const activeIdx = useMemo(() => {
    const idx = stages.findIndex((s) => s.status !== "completed");
    return idx === -1 ? -1 : idx;
  }, [stages]);

  const particles = useMemo(() => {
    const items: any[] = [];
    if (activeIdx <= 0) return items; // nothing in flight yet (or pipeline finished)
    const flowGap = activeIdx - 1; // the segment: last completed -> active EM
    connections.forEach((c, i) => {
      if (c.gap === flowGap) {
        items.push({ ...c, dur: 0.9, delay: (i % 8) * 0.09 });
      }
    });
    return items;
  }, [connections, activeIdx]);

  return (
    <div style={{ background: C.bg }}>
      <GlobalStyle />
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block", overflow: "visible" }}>
        <defs>
          <filter id="npr-glow" x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="2.4" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {connections.map((c) => {
          const meta = STATUS_META[(c.sourceStatus as keyof typeof STATUS_META)];
          const isCompleted = c.sourceStatus === "completed";
          const isWaiting = c.sourceStatus === "waiting";
          return (
            <line key={c.key} x1={c.x1} y1={c.y1} x2={c.x2} y2={c.y2} stroke={meta.color}
              strokeWidth={isCompleted ? 0.5 : isWaiting ? 0.4 : 0.3} strokeOpacity={isCompleted ? 0.28 : isWaiting ? 0.22 : 0.35} />
          );
        })}

        {particles.map((p, idx) => (
          <circle key={`p-${idx}`} r="1.8" fill={`url(#pgrad)`}>
            <animateMotion dur={`${p.dur}s`} begin={`${p.delay}s`} repeatCount="indefinite" path={`M${p.x1},${p.y1} L${p.x2},${p.y2}`} />
          </circle>
        ))}
        <linearGradient id="pgrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor={C.accent} /><stop offset="100%" stopColor={C.accent2} />
        </linearGradient>

        {layers.map((l, li) => {
          const meta = STATUS_META[l.status];
          return (
            <g
              key={`${l.key}-${li}`}
              onClick={() => onStageClick?.(l.key)}
              style={{ cursor: onStageClick ? 'pointer' : 'default' }}
            >
              {l.nodes.map((n, ni) => {
                if (l.status === "completed") return <circle key={ni} cx={l.x} cy={n.y} r="3" fill={C.accent} filter="url(#npr-glow)" />;
                if (l.status === "waiting") return (
                  <circle key={ni} cx={l.x} cy={n.y} r="3.4" fill="#fff" stroke={C.warning} strokeWidth="1.5"
                    style={{ transformOrigin: `${l.x}px ${n.y}px`, animation: "npr-pulse-ring 1.8s ease-in-out infinite", animationDelay: `${ni * 0.15}s` }} />
                );
                return <circle key={ni} cx={l.x} cy={n.y} r="2.4" fill="#fff" stroke={C.gray} strokeWidth="1" />;
              })}
              <text x={l.x} y={H - 22} textAnchor="middle" style={{ fontFamily: fontDisplay, fontSize: 10, fontWeight: 600, fill: C.text }}>{l.label}</text>
              <text x={l.x} y={H - 9} textAnchor="middle" style={{ fontFamily: fontMono, fontSize: 6.5, letterSpacing: "0.05em", fill: meta.color }}>
                {l.caption || meta.caption}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
