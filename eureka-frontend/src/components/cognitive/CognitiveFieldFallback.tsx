import React, { useMemo } from 'react';
import type { CognitiveFieldLayout, FieldEntity, FieldLink } from '../../domain/cognitiveFieldLayout';
import { kindColor } from './cognitiveColors';

/**
 * LS91 → LS93 v5 — DOM/SVG FALLBACK for the cognitive field.
 *
 * This is the graceful non-GPU path (WebGPU *and* WebGL both unavailable). It draws
 * the SAME pure layout top-down (x -> screen x, z -> screen y) so the cognitive
 * surface stays useful: the dominant cognitive axis, the entities with their visual
 * grammar, their real relations, focus dimming, and the honest states. Nothing is
 * GPU-dependent; every semantic is also carried as text (title/labels) so the field
 * is never the only source.
 */
function stageLabel(id: string): string { return id; }

export function CognitiveFieldFallback({ layout }: { layout: CognitiveFieldLayout }) {
  const M = useMemo(() => {
    let minX = Infinity, maxX = -Infinity, minZ = Infinity, maxZ = -Infinity;
    [...layout.entities, ...layout.thread.map((p, i) => ({ position: p, kind: 'STAGE' as const, id: `th${i}` }))].forEach((e: any) => {
      minX = Math.min(minX, e.position.x); maxX = Math.max(maxX, e.position.x);
      minZ = Math.min(minZ, e.position.z); maxZ = Math.max(maxZ, e.position.z);
    });
    if (!isFinite(minX)) { minX = -100; maxX = 300; minZ = -3; maxZ = 3; }
    const pad = 40;
    minX -= pad; maxX += pad; minZ -= pad; maxZ += pad;
    const spanX = maxX - minX;
    const spanZ = maxZ - minZ;
    const scale = Math.max(0.7, Math.min(12, 1160 / Math.max(spanX, spanZ)));
    return { minX, maxX, minZ, maxZ, scale };
  }, [layout]);

  const W = (M.maxX - M.minX) * M.scale + 40;
  const H = Math.max(320, ((M.maxZ - M.minZ) * M.scale) + 110);
  const px = (x: number) => (x - M.minX) * M.scale + 20;
  const pz = (z: number) => ((z - M.minZ) * M.scale) + 46;

  const threadPath = layout.thread.map((p, i) => `${i === 0 ? 'M' : 'L'} ${px(p.x)} ${pz(p.z)}`).join(' ');
  const byId = new Map<string, FieldEntity>();
  layout.entities.forEach((e) => byId.set(e.id, e));

  return (
    <div className="ci-field-fallback" role="img" aria-label="Cognitive visual computing surface — DOM/SVG fallback (no GPU), top-down projection">
      <div className="ci-field-fallback-note">RENDERER · DOM/SVG FALLBACK (WebGPU/WebGL unavailable) · top-down projection of the same layout</div>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="xMidYMid meet" style={{ background: 'var(--eureka-surface)' }}>
        {/* faint registration grid (never competes with data) */}
        {Array.from({ length: 12 }).map((_, i) => (
          <g key={i} stroke="rgba(0,0,0,0.03)" strokeWidth="1">
            <line x1="0" y1={i * (H / 12)} x2={W} y2={i * (H / 12)} />
            <line x1={i * (W / 12)} y1="0" x2={i * (W / 12)} y2={H} />
          </g>
        ))}

        {/* dominant cognitive axis */}
        <path d={threadPath} fill="none" stroke="#0f6e6e" strokeWidth="3" strokeOpacity="0.5" strokeLinecap="round" />

        {/* origin + terminal markers + gap notches on the axis */}
        {layout.thread.map((p, i) => (
          <circle key={`a${i}`} cx={px(p.x)} cy={pz(p.z)} r={3} fill="#0f6e6e" fillOpacity="0.5" />
        ))}
        {layout.gaps.map((g) => (
          <circle key={`g${g.id}`} cx={px(g.anchor.x)} cy={pz(g.anchor.z)} r={2.4} fill="#c4cad0" fillOpacity="0.4">
            <title>{`${g.id} · ${g.note}`}</title>
          </circle>
        ))}

        {/* stage anchors + labels (the axis walkthrough) */}
        {layout.stages.filter((s) => s.hasArtifacts).map((s) => {
          const x = px(s.anchor.x);
          const y = pz(s.anchor.z);
          return (
            <text key={s.id} x={x} y={y - 12} fontSize="8.5" fontFamily="monospace" fill="var(--eureka-text-micro)" textAnchor="middle" letterSpacing="0.12em">
              {stageLabel(s.id)}
            </text>
          );
        })}

        {/* real relations */}
        {layout.links.map((l: FieldLink) => {
          const a = byId.get(l.source);
          const b = byId.get(l.target);
          if (!a || !b) return null;
          return (
            <line key={l.id} x1={px(a.position.x)} y1={pz(a.position.z)} x2={px(b.position.x)} y2={pz(b.position.z)}
              stroke={l.kind === 'selection' ? '#8250df' : '#9aa2ab'} strokeWidth="1" strokeOpacity="0.4" />
          );
        })}

        {/* entities (visual grammar) */}
        {layout.entities.map((e) => {
          const x = px(e.position.x);
          const y = pz(e.position.z);
          const sal = layout.salience.get(e.id) ?? 1;
          const col = kindColor(e.kind);
          const opacity = 0.2 + sal * 0.8;
          const r = Math.max(5, e.radius);
          return (
            <g key={e.id} opacity={opacity} data-entity-id={e.id} data-kind={e.kind} data-tone={e.tone} role="button" tabIndex={0}
              aria-label={`${e.kind} ${e.id} — ${e.description || 'DATA NOT AVAILABLE'}`}>
              {e.geometry === 'question' && <circle cx={x} cy={y} r={r} fill="none" stroke={col} strokeWidth="2.2" />}
              {e.geometry === 'finding' && (<g><circle cx={x} cy={y} r={r} fill={col} fillOpacity={0.75} /><circle cx={x} cy={y} r={r * 1.5} fill="none" stroke={col} strokeWidth="1" strokeOpacity="0.35" /></g>)}
              {e.geometry === 'prediction' && (
                <g>
                  <rect x={x - r} y={y - r * 0.6} width={r * 2} height={r * 1.2} fill={e.numericValue != null ? col : 'none'} fillOpacity={e.numericValue != null ? 0.5 : 0} stroke={col} strokeWidth="1.3" strokeDasharray={e.numericValue != null ? '0' : '4 3'} />
                  <text x={x} y={y + r + 14} fontSize="7.5" fontFamily="monospace" fill="var(--eureka-text-micro)" textAnchor="middle">{e.numericValue != null ? `VALUE ${Number(e.numericValue).toFixed(4)}` : 'NOT EVALUATED'}</text>
                </g>
              )}
              {e.geometry === 'alternative' && (<g><circle cx={x} cy={y} r={r * 0.7} fill={col} fillOpacity={0.7} />{e.humanSelected ? <circle cx={x} cy={y} r={r} fill="none" stroke={col} strokeWidth="1.6" /> : e.recommended ? <rect x={x - r * 0.7} y={y - r * 0.7} width={r * 1.4} height={r * 1.4} transform={`rotate(45 ${x} ${y})`} fill="none" stroke={col} strokeWidth="1.3" /> : <circle cx={x} cy={y} r={r * 1.15} fill="none" stroke={col} strokeWidth="1" />}</g>)}
              {e.geometry === 'decision' && (<g><circle cx={x} cy={y} r={r * 0.7} fill={col} fillOpacity={0.8} /><circle cx={x} cy={y} r={r} fill="none" stroke={col} strokeWidth="1.8" /><circle cx={x} cy={y} r={r * 1.5} fill="none" stroke={col} strokeWidth="1.4" /></g>)}
              {e.geometry === 'action' && (<g>{Array.from({ length: Math.max(1, (e as any).stepCount ?? 0) }).map((_, i) => (<circle key={i} cx={x + (i - (Math.max(1, (e as any).stepCount ?? 0) - 1) / 2) * r} cy={y} r={r * 0.4} fill={col} fillOpacity={0.8} />))}</g>)}
              {e.geometry === 'result' && (<g><polygon points={hexPoints(x, y, r)} fill={col} fillOpacity={0.75} stroke={col} strokeWidth="1.4" /></g>)}
              {e.geometry === 'frozen' && (<g><rect x={x - r * 0.8} y={y - r * 0.8} width={r * 1.6} height={r * 1.6} transform={`rotate(45 ${x} ${y})`} fill={col} fillOpacity={0.7} /></g>)}
              {!['question', 'finding', 'prediction', 'alternative', 'decision', 'action', 'result', 'frozen'].includes(e.geometry) && <circle cx={x} cy={y} r={r * 0.7} fill={col} fillOpacity={0.7} />}
              {e.layer === 1 && <text x={x} y={y - r - 6} fontSize="8.5" fontFamily="monospace" fill={col} textAnchor="middle" fontWeight="700">{e.kind}</text>}
            </g>
          );
        })}
      </svg>
      <div className="ci-field-fallback-legend">
        <span>◎ question</span><span>· evidence</span><span>● finding</span><span>▱ prediction (ghost = NOT EVALUATED)</span><span>◎◎ human decision</span><span>⌗ result</span><span>— dominant cognitive thread</span>
      </div>
    </div>
  );
}

function hexPoints(x: number, y: number, r: number): string {
  const pts: string[] = [];
  for (let i = 0; i < 6; i++) {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    pts.push(`${x + r * Math.cos(a)},${y + r * Math.sin(a)}`);
  }
  return pts.join(' ');
}

export default CognitiveFieldFallback;
