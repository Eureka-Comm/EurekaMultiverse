import React, { useState } from 'react';
import WorkAuditView from './WorkAuditView';
import AuditView from './AuditView';
import WhatIfView from '../whatif/WhatIfView';
import CognitiveObservatory from '../constellation/CognitiveObservatory';
import GovernanceMap from '../constellation/GovernanceMap';

type Tab = 'canonical' | 'cognitive' | 'hypothetical' | 'evidence' | 'governance';

/**
 * CONSTELACIÓN — EUREKA's Cognitive Observatory. A single READ-ONLY entry that lets a human observe and
 * reconstruct the real evolution of EUREKA across DISTINCT, never-merged observatories:
 *
 *   CANONICAL    → WorkAuditView         (Work → Execution → Result → Publish → Consumption → integrity/currentness)
 *   COGNITIVE    → CognitiveObservatory  (contractual vs observed EM pipeline + DeepSeek/ACFL trace)
 *   HYPOTHETICAL → WhatIfView            (Scenario → WHAT-IF → projected → decision)
 *   EVIDENCE     → AuditView             (Scenario audit trail / provenance)
 *   GOVERNANCE   → GovernanceMap         (LLM proposes · EUREKA governs · ACFL math · Human · Q4 · Publisher)
 *
 * CONSTELACIÓN observes only. It NEVER governs, decides, executes, publishes, mutates, or invents. It has
 * NO authority, NO persistence (localStorage/sessionStorage/IndexedDB), NO release/deliver/ship/deploy
 * controls (no such contract), and NO Work↔Scenario relationship (absent/ambiguous). Work and Scenario
 * remain independent inputs.
 */
export default function ObservabilityConsole() {
  const [tab, setTab] = useState<Tab>('canonical');
  const [workId, setWorkId] = useState('');

  const tabStyles: Record<Tab, { label: string; badge: string; active: string }> = {
    canonical: { label: 'Canonical · Work', badge: 'CANONICAL', active: 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]' },
    cognitive: { label: 'Cognitive · Pipeline', badge: 'COGNITIVE', active: 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]' },
    hypothetical: { label: 'Hypothetical · What-If', badge: 'HYPOTHETICAL', active: 'border-amber-500 text-amber-500' },
    evidence: { label: 'Evidence · Scenario Audit', badge: 'EVIDENCE', active: 'border-[var(--eureka-text-label)] text-[var(--eureka-text-label)]' },
    governance: { label: 'Governance · Authority', badge: 'GOVERNANCE', active: 'border-[var(--eureka-text-label)] text-[var(--eureka-text-label)]' },
  };

  return (
    <div className="space-y-4 p-6" data-testid="observability-console">
      <h2 className="text-lg font-mono uppercase tracking-widest">EUREKA · CONSTELACIÓN · Observatorio Cognitivo</h2>
      <p className="text-[11px] text-[var(--eureka-text-label)]">
        Observe only. Distinct, never-merged observatories: CANONICAL ≠ COGNITIVE ≠ HYPOTHETICAL ≠ EVIDENCE ≠
        GOVERNANCE. This observatory never authorizes, executes, publishes, releases, or invents anything.
      </p>

      {/* shared Work selection for the canonical/cognitive observatories */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Work id (canonical / cognitive)
          <input value={workId} onChange={(e) => setWorkId(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
      </div>

      {/* observatory tabs */}
      <div className="flex flex-wrap gap-2">
        {(['canonical', 'cognitive', 'hypothetical', 'evidence', 'governance'] as Tab[]).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-3 py-1.5 rounded border text-[11px] font-mono uppercase ${tab === t ? tabStyles[t].active : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]'}`}>
            {tabStyles[t].badge} · {tabStyles[t].label}
          </button>
        ))}
      </div>

      {/* active observatory — only the selected view is mounted */}
      {tab === 'canonical' && <WorkAuditView initialWorkId={workId} />}
      {tab === 'cognitive' && <CognitiveObservatory workId={workId} />}
      {tab === 'hypothetical' && <WhatIfView />}
      {tab === 'evidence' && <AuditView />}
      {tab === 'governance' && <GovernanceMap />}
    </div>
  );
}
