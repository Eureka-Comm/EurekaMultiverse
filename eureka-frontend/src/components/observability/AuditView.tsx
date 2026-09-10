import React, { useState } from 'react';
import { getAudit, ApiError, type AuditResponse } from '../../lib/scenarioApi';

/**
 * AuditView — a READ-ONLY observability projection over the REAL, durable EUREKA pipeline:
 * Work → WHAT-IF (multi-metric) → COMPARE → Human DECISION → Execution → audit/provenance.
 *
 * It only READS from the backend audit endpoint (which composes the existing authorities). It NEVER
 * computes GCLV / predictions / prescriptions, NEVER decides a winner, NEVER authorizes, NEVER
 * executes, and NEVER fabricates an event or timestamp. Missing stages are shown as NOT_RECORDED.
 */
export default function AuditView() {
  const [scenarioId, setScenarioId] = useState('SCN-OBS');
  const [workId, setWorkId] = useState('W-OBS');
  const [audit, setAudit] = useState<AuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true); setError(null);
    try {
      setAudit(await getAudit(scenarioId.trim(), workId.trim() || undefined));
    } catch (e) {
      setError(e instanceof ApiError ? `Observability error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const stages = audit?.stages ?? [];
  const stageStatus = (s: string) => stages.find((x) => x.stage === s)?.status ?? 'NOT_RECORDED';

  return (
    <div className="space-y-6 p-6" data-testid="audit-view">
      <h2 className="text-lg font-mono uppercase tracking-widest">EUREKA · Observability / Audit</h2>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Scenario id
          <input value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <label className="text-sm">Work id (optional)
          <input value={workId} onChange={(e) => setWorkId(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <button onClick={load} disabled={busy} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
          {busy ? 'Loading…' : 'Load audit (read-only)'}
        </button>
      </div>

      {error && <div className="text-sm text-[var(--eureka-signal-blocked)] border border-[var(--eureka-signal-blocked)] rounded p-3">Error (fail-closed): {error}</div>}

      {audit && (
        <>
          {/* pipeline bar */}
          <div className="flex flex-wrap gap-2 text-[11px] font-mono">
            {['WORK', 'WHAT-IF', 'COMPARE', 'DECISION', 'EXECUTION'].map((s) => (
              <span key={s} className={`px-2 py-1 rounded border ${stageStatus(s) === 'RECORDED' ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]' : stageStatus(s) === 'DERIVED' ? 'border-amber-500 text-amber-500' : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]'} ${s ? '' : ''}`}>
                {s} · {stageStatus(s)}
              </span>
            ))}
          </div>

          {/* WORK */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Work</div>
            {audit.work ? (
              <div className="text-[11px] font-mono">
                <div>work_id · {audit.work.work_id}</div>
                <div className="break-all">source identity · {audit.work.source_state_identity}</div>
                <div>revision · {audit.work.revision ?? 'n/a'} · status · {audit.work.status ?? 'n/a'}</div>
                <div>linked to scenario (Q2) · {String(audit.work.linked_to_scenario)}</div>
                <div className="text-[10px] text-[var(--eureka-text-label)] break-all">provenance · {audit.work.provenance.join(' → ')}</div>
              </div>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-label)]">NOT_RECORDED — no Work resolved for this scenario.</div>
            )}
          </section>

          {/* WHAT-IF projected artifacts */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">WHAT-IF · Projected artifacts (PROJECTED / NON_CANONICAL)</div>
            {audit.projected_artifacts.length === 0
              ? <div className="text-[11px] text-[var(--eureka-text-label)]">None recorded.</div>
              : audit.projected_artifacts.map((a, i) => (
                <div key={a.artifact_id ?? i} className="mt-2 border border-[var(--eureka-spatial-hairline)] rounded p-2">
                  <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">{a.artifact_id} · {a.artifact_kind} · {a.authority} · {a.canonical_status}</div>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {Object.entries(a.payload ?? {}).map(([k, v]) => (
                      <div key={k} className="text-xs font-mono border border-[var(--eureka-spatial-hairline)] rounded p-2">
                        <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">{k}</div>
                        <div className="text-sm max-w-xs break-all">{typeof v === 'number' ? v.toFixed(6) : String(JSON.stringify(v))}</div>
                      </div>
                    ))}
                  </div>
                  <div className="text-[10px] text-[var(--eureka-text-label)] break-all mt-1">provenance · {a.provenance.join(' → ')}</div>
                </div>
              ))}
          </section>

          {/* DECISION */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Human Decision (record-only)</div>
            {audit.decision ? (
              <div className="text-[11px] font-mono">
                <div>decision_id · {audit.decision.decision_id}</div>
                <div>type · {audit.decision.decision_type} · lifecycle · {audit.decision.lifecycle_state}</div>
                <div>authority · {audit.decision.authority} · scope · {audit.decision.scope} · {audit.decision.canonical_status}</div>
                <div>actor · {audit.decision.human_actor} · {audit.decision.created_at}</div>
                <div className="text-[10px] text-[var(--eureka-text-label)] break-all">provenance · {audit.decision.provenance.join(' → ')}</div>
              </div>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-label)]">NOT_RECORDED — no human decision.</div>
            )}
          </section>

          {/* EXECUTION */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Execution (governed)</div>
            {audit.execution ? (
              <div className="text-[11px] font-mono">
                <div>execution_id · {audit.execution.execution_id}</div>
                <div>action · {audit.execution.action_id} · status · {audit.execution.status}</div>
                <div>authority · {audit.execution.authority} · {audit.execution.canonical_status}</div>
                <div>mode · {audit.execution.governance?.mode} · effect class · {audit.execution.governance?.effect_class} · boundary · {audit.execution.governance?.decision}</div>
                <div>effect · {audit.execution.effect?.artifact_path ?? 'n/a'} · exists={String(audit.execution.effect?.exists)}</div>
                <div className="text-[10px] text-[var(--eureka-text-label)] break-all">provenance · {audit.execution.provenance.join(' → ')}</div>
              </div>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-label)]">NOT_RECORDED — no governed execution.</div>
            )}
          </section>

          {/* audit / provenance */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Audit / Provenance</div>
            <div className="text-[11px] font-mono break-all">scenario source identity · {audit.source_state_identity}</div>
            <div className="text-[10px] text-[var(--eureka-text-label)] break-all mt-1">provenance · {audit.provenance.join(' → ')}</div>
          </section>
        </>
      )}
    </div>
  );
}
