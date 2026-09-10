import React from 'react';

/**
 * GovernanceMap — CONSTELACIÓN's GOVERNANCE observatory: where authority actually resides in EUREKA.
 * This is the architectural CONTRACT (read-only, no fabrication, no execution). It reflects the real
 * boundaries: DeepSeek/Ollama only PROPOSE; EUREKA validates/governs; ACFL is the mathematical authority;
 * the human decides (HITL); Q4 governs effects; Publisher freezes/publishes. CONSTELACIÓN never governs.
 */
interface Node { actor: string; role: string; authority: string; color: string; }
const NODES: Node[] = [
  { actor: 'DeepSeek / Ollama', role: 'PROPOSE / INTERPRET / GENERATE', authority: 'NOT authority', color: 'border-amber-500' },
  { actor: 'EUREKA (EM Core → runtime)', role: 'VALIDATE / NORMALIZE / ROUTE / GOVERN', authority: 'Python authority', color: 'border-[var(--eureka-signal-cognitive)]' },
  { actor: 'ACFL', role: 'MATHEMATICAL AUTHORITY (GCLV / engine)', authority: 'math authority', color: 'border-[var(--eureka-signal-cognitive)]' },
  { actor: 'Human', role: 'DECIDES (HITL: alternatives / execution / freeze)', authority: 'human authority', color: 'border-[var(--eureka-signal-cognitive)]' },
  { actor: 'Q4 EffectBoundary', role: 'EFFECT GOVERNANCE (DRY_RUN vs REAL_EXECUTION)', authority: 'single effect gate', color: 'border-[var(--eureka-signal-cognitive)]' },
  { actor: 'EM Publisher', role: 'FREEZE → PUBLICATION → artifact', authority: 'publication (≠ release)', color: 'border-[var(--eureka-spatial-hairline)]' },
];

export default function GovernanceMap() {
  return (
    <div className="space-y-4" data-testid="governance-map">
      <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-label)]">Governance Observatory · Authority Map</div>
      <p className="text-[11px] text-[var(--eureka-text-label)]">
        Architectural contract: DeepSeek/Ollama only propose; EUREKA validates and governs; ACFL owns math;
        the human decides; Q4 owns effects; Publisher freezes/publishes. None of these expand authority.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {NODES.map((n) => (
          <div key={n.actor} className={`border ${n.color} rounded p-3`}>
            <div className="text-[11px] font-semibold">{n.actor}</div>
            <div className="text-[10px] font-mono mt-1">{n.role}</div>
            <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">{n.authority}</div>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-[var(--eureka-text-label)]">CONSTELACIÓN observes. It never governs, decides, executes, publishes, mutates, or invents.</div>
    </div>
  );
}
