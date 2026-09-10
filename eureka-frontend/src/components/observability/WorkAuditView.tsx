import React, { useState } from 'react';
import { getWorkAudit, getWorkPublication, ApiError, type WorkAuditResponse, type WorkPublicationResponse } from '../../lib/scenarioApi';

/**
 * WorkAuditView — READ-ONLY CANONICAL observability: Work → Execution → Result → Publish →
 * Published artifact → integrity verification → CURRENT/HISTORICAL.
 *
 * It only READS the real backend (canonical work authority + Publisher + consumption verification).
 * It NEVER computes a fingerprint/signature, NEVER authorizes/executes/publishes/freezes, and NEVER
 * invents a timestamp or a stage. A TAMPERED artifact is shown as an integrity failure; a HISTORICAL
 * artifact is shown as VALID historical evidence (NOT corrupt). There is NO release/deliver/ship UI —
 * the repository defines no such contract.
 */
export default function WorkAuditView({ initialWorkId = '' }: { initialWorkId?: string }) {
  const [workId, setWorkId] = useState(initialWorkId);
  const [audit, setAudit] = useState<WorkAuditResponse | null>(null);
  const [consumption, setConsumption] = useState<WorkPublicationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true); setError(null);
    if (!workId.trim()) { setAudit(null); setConsumption(null); setBusy(false); return; }
    try {
      const a = await getWorkAudit(workId.trim());
      setAudit(a);
      setConsumption(a.consumption ? await getWorkPublication(workId.trim()) : null);
    } catch (e) {
      setError(e instanceof ApiError ? `Observability error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const statusBadge = (s: string) => (
    <span className={`px-2 py-1 rounded border text-[11px] font-mono ${
      s === 'RECORDED' ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]'
      : s === 'DERIVED' ? 'border-amber-500 text-amber-500'
      : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]'
    }`}>{s}</span>
  );

  const ver = audit?.consumption?.verification;
  const integrity = ver?.integrity ?? 'NOT_RECORDED';
  const currentness = ver?.currentness ?? 'N/A';
  const exec = (audit?.execution ?? null) as Record<string, any> | null;
  const res = (audit?.result ?? null) as Record<string, any> | null;
  const pub = (audit?.publication ?? null) as Record<string, any> | null;
  const pubState = pub?.publication_state as Record<string, any> | undefined;
  const frozen = pub?.frozen_result as Record<string, any> | undefined;

  return (
    <div className="space-y-6 p-6" data-testid="work-audit-view">
      <h2 className="text-lg font-mono uppercase tracking-widest">EUREKA · Canonical Work Observability</h2>

      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Work id
          <input value={workId} onChange={(e) => setWorkId(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <button onClick={load} disabled={busy} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
          {busy ? 'Loading…' : 'Load canonical audit (read-only)'}
        </button>
      </div>

      {error && <div className="text-sm text-[var(--eureka-signal-blocked)] border border-[var(--eureka-signal-blocked)] rounded p-3">Error (fail-closed): {error}</div>}

      {!audit && !error && !workId.trim() && (
        <div className="text-sm text-[var(--eureka-text-label)]">Enter a Work id to observe the canonical audit (read-only).</div>
      )}

      {audit && (
        <>
          {/* pipeline bar */}
          <div className="flex flex-wrap gap-2">
            {audit.stages.map((st) => (
              <div key={st.stage} className="text-[11px] font-mono">{st.stage}: <span className="ml-1">{statusBadge(st.status)}</span></div>
            ))}
          </div>

          {/* WORK (canonical) */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Work · Canonical</div>
            <div className="text-[11px] font-mono">
              <div>work_id · {audit.work_id}</div>
              <div className="break-all">canonical_state_identity · {audit.canonical_state_identity}</div>
              <div>revision · {audit.revision ?? 'NOT_RECORDED'} · status · {audit.status ?? 'NOT_RECORDED'}</div>
            </div>
          </section>

          {/* EXECUTION */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Execution · Canonical</div>
            {exec ? (
              <div className="text-[11px] font-mono">
                <div>status · {exec.status ?? 'N/A'}</div>
                <div>result · {exec.result?.status ?? 'NOT_RECORDED'}</div>
                <div className="text-[10px] text-[var(--eureka-text-label)]">successful · {String(exec.result?.successful_actions ?? 'n/a')}</div>
              </div>
            ) : <div className="text-[11px] text-[var(--eureka-text-label)]">Execution evidence NOT_RECORDED.</div>}
          </section>

          {/* RESULT (canonical, NOT projected) */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Canonical Result (≠ projected)</div>
            {res ? (
              <div className="text-[11px] font-mono">
                <div>status · {res.status ?? 'N/A'} · result_id · {res.result_id ?? 'n/a'}</div>
                <div className="text-[10px] text-[var(--eureka-text-label)] break-all">summary · {String(res.summary ?? 'NOT_RECORDED')}</div>
              </div>
            ) : <div className="text-[11px] text-[var(--eureka-text-label)]">Canonical result NOT_RECORDED.</div>}
          </section>

          {/* PUBLISH / FREEZE */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Publish / Freeze</div>
            {pub ? (
              <div className="text-[11px] font-mono">
                <div>publication_status · {pubState?.status ?? 'NOT_RECORDED'}</div>
                <div className="break-all">freeze_signature · {String(frozen?.freeze_signature ?? 'NOT_RECORDED')}</div>
                <div>publication_count · {pubState?.publications?.length ?? 0}</div>
              </div>
            ) : <div className="text-[11px] text-[var(--eureka-text-label)]">Publication NOT_RECORDED.</div>}
          </section>

          {/* CONSUMPTION / INTEGRITY / CURRENTNESS */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Consumption · Integrity Verification (server-side)</div>
            <div className="flex flex-wrap gap-2 mt-1 text-[11px] font-mono">
              <span className={`px-2 py-1 rounded border ${
                integrity === 'VALID' ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]'
                : integrity === 'TAMPERED' ? 'border-[var(--eureka-signal-blocked)] text-[var(--eureka-signal-blocked)]'
                : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]'
              }`}>integrity · {integrity}</span>
              <span className="px-2 py-1 rounded border border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]">currentness · {currentness}</span>
              <span className="px-2 py-1 rounded border border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]">signature_match · {String(ver?.signature_match)}</span>
              <span className="px-2 py-1 rounded border border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]">schema_valid · {String(ver?.schema_valid)}</span>
            </div>
            {(integrity === 'TAMPERED') && (
              <div className="text-[11px] text-[var(--eureka-signal-blocked)] mt-2">INTEGRITY FAILURE — the published artifact snapshot is NOT trustworthy (was altered/does not match its content signature).</div>
            )}
            {(integrity === 'VALID' && currentness === 'HISTORICAL') && (
              <div className="text-[11px] text-[var(--eureka-text-label)] mt-2">VALID HISTORICAL EVIDENCE — the artifact is internally valid but represents an earlier state of the Work.</div>
            )}
            {integrity === 'VALID' && currentness === 'CURRENT' && (
              <div className="text-[11px] text-[var(--eureka-signal-cognitive)] mt-2">Verified current publication evidence.</div>
            )}
          </section>

          {/* provenance */}
          <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
            <div className="text-[10px] uppercase text-[var(--eureka-label)]">Provenance</div>
            <div className="text-[11px] font-mono break-all">{audit.provenance.join(' → ')}</div>
          </section>
        </>
      )}
    </div>
  );
}
