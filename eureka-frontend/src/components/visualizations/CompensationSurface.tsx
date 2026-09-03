import React, { useState, useEffect, useMemo } from 'react';
import { useWorkStore } from '../../store/workStore';

// Helper: value -> 0..1 clamped.
const norm = (v: number) => Math.max(0, Math.min(1, v));

export default function CompensationSurface() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const toolCall = useWorkStore((state) => state.toolCall);

  const [localCost, setLocalCost] = useState(50);
  const [localRisk, setLocalRisk] = useState(50);

  useEffect(() => {
    if (activeWork?.state?.acfl?.weights) {
      setLocalCost(activeWork.state.acfl.weights.cost ?? 50);
      setLocalRisk(activeWork.state.acfl.weights.risk ?? 50);
    }
  }, [activeWork]);

  // V-1: read the REAL ACFL state (no hardcoded ALT A/B/C, no fabricated WINNER).
  const acfl = (activeWork?.state?.acfl as any) || {};
  const scores: Record<string, Record<string, number>> = acfl.normalized_scores || {};
  const alternatives: string[] = (acfl.alternatives?.length ? acfl.alternatives : Object.keys(scores)) || [];
  const weights: Record<string, number> = acfl.weights || {};
  const frontier: string[] = acfl.frontier || [];
  const hasData = alternatives.length > 0 && Object.keys(scores).length > 0;

  // Weighted satisfaction per alternative (equal weights for criteria not covered).
  const weighted = useMemo(() => {
    const out: Record<string, number> = {};
    for (const a of alternatives) {
      const row = scores[a] || {};
      const keys = Object.keys(row);
      if (!keys.length) { out[a] = 0; continue; }
      let num = 0, den = 0;
      for (const k of keys) {
        const w = typeof weights[k] === 'number' ? weights[k] : 0.5;
        num += w * row[k]; den += w;
      }
      out[a] = den ? num / den : 0;
    }
    return out;
  }, [alternatives, scores, weights]);

  const handleWeightChange = (type: 'cost' | 'risk', val: number) => {
    if (type === 'cost') { setLocalCost(val); toolCall('adjust_acfl_weights', { cost: val, risk: localRisk }); }
    else { setLocalRisk(val); toolCall('adjust_acfl_weights', { cost: localCost, risk: val }); }
  };

  // Winner: the frontier (Pareto-optimal) if present, else the highest-weighted alternative — both DERIVED.
  const winner = frontier.length ? frontier : (alternatives.length ? [alternatives.reduce((b, a) => weighted[a] > weighted[b] ? a : b, alternatives[0])] : []);
  const winnerIsDerived = !frontier.length && alternatives.length > 0;

  // Position each alternative in [0,1]^2 from its first two criteria scores (or weighted as fallback).
  const position = (a: string) => {
    const row = scores[a] || {};
    const keys = Object.keys(row);
    const x = keys[0] ? norm(row[keys[0]]) : norm(weighted[a] || 0);
    const y = keys[1] ? norm(row[keys[1]]) : norm(1 - (weighted[a] || 0));
    return { x, y };
  };

  if (!hasData) {
    return (
      <div className="fabric-panel p-6 flex flex-col justify-center items-center text-center bg-[var(--eureka-surface-elevated)] border-[var(--eureka-signal-blocked)] border-dashed h-full">
        <div className="text-[var(--eureka-signal-blocked)] text-sm mb-2">ACFL FRONTIER DATA UNAVAILABLE</div>
        <p className="text-[var(--eureka-text-label)] text-xs">Ninguna matriz de satisfacción ACFL fue emitida por el estado.</p>
      </div>
    );
  }

  return (
    <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] h-full flex flex-col">
      <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-4 tracking-widest flex justify-between items-center">
        COMPENSATION SURFACE
        <span className="text-[10px] text-[var(--eureka-signal-semantic)] font-normal border border-[var(--eureka-signal-semantic)] px-2 py-0.5 rounded">ACFL</span>
      </h3>

      <div className="flex-1 border-l-2 border-b-2 border-[var(--eureka-spatial-hairline)] relative mb-6">
        <span className="absolute -top-4 -left-4 text-[10px] text-[var(--eureka-text-label)] rotate-90 origin-left">BENEFIT</span>
        <span className="absolute -bottom-6 right-0 text-[10px] text-[var(--eureka-text-label)]">COST / RISK</span>

        {/* Decision Frontier Line (Pareto) */}
        <div className="absolute top-[20%] left-0 right-0 border-t border-dashed border-[var(--eureka-text-technical)] opacity-50"></div>
        <div className="absolute top-0 bottom-0 left-[60%] border-l border-dashed border-[var(--eureka-text-technical)] opacity-50"></div>

        {/* Alternatives — positioned from REAL scores */}
        {alternatives.map((a) => {
          const { x, y } = position(a);
          const isWinner = winner.includes(a);
          return (
            <div key={a}
              className={`absolute w-3 h-3 rounded-full transition-all duration-500 ${isWinner ? 'bg-[var(--eureka-signal-action)] shadow-[0_0_10px_var(--eureka-signal-action)] scale-150' : 'bg-gray-500'}`}
              style={{ left: `${(x * 80) + 8}%`, bottom: `${(y * 80) + 8}%` }}>
              <span className="absolute left-4 top-0 text-xs text-[var(--eureka-text-display)]">{a}</span>
            </div>
          );
        })}
      </div>

      <div className="space-y-4">
        <div className="flex justify-between text-xs text-[var(--eureka-text-label)] mb-1"><span>WEIGHT: COST</span><span>{localCost}%</span></div>
        <input type="range" min="0" max="100" value={localCost} onChange={(e) => handleWeightChange('cost', Number(e.target.value))} className="w-full accent-[var(--eureka-signal-cognitive)]" />
        <div className="flex justify-between text-xs text-[var(--eureka-text-label)] mb-1"><span>WEIGHT: RISK</span><span>{localRisk}%</span></div>
        <input type="range" min="0" max="100" value={localRisk} onChange={(e) => handleWeightChange('risk', Number(e.target.value))} className="w-full accent-[var(--eureka-signal-cognitive)]" />
      </div>

      <div className="mt-4 p-3 bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded text-xs flex justify-between items-center">
        <div>
          <p className="text-[var(--eureka-text-section)]">{frontier.length ? 'Frente de Pareto (no dominadas) desde el estado.' : 'Satisfacción ponderada derivada del estado.'}</p>
          <p className="text-[var(--eureka-signal-action)] font-bold mt-1">{winnerIsDerived ? 'DERIVED' : 'FRONTIER'}: {winner.join(', ')}</p>
        </div>
        {activeWork?.state?.feasible_only && <span className="text-[10px] bg-purple-500 text-white px-2 py-1 rounded">FEASIBLE ONLY</span>}
      </div>
    </div>
  );
}
