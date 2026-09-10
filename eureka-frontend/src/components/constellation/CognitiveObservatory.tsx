import React, { useEffect, useState } from 'react';
import { getWorkAudit, ApiError, type WorkAuditResponse } from '../../lib/scenarioApi';
import { TRACE_TONE, mapObservedPipeline } from '../../domain/cognitiveTrace';

/**
 * CognitiveObservatory — the EM pipeline trace for a canonical Work: CONTRACTUAL pipeline (the EM
 * architecture order EUREKA defines) vs OBSERVED pipeline (what actually happened, per-EM status +
 * provider/model/latency/governance). Read-only; never fabricates a non-observed stage (NOT_OBSERVED).
 * DeepSeek only PROPOSES; Predictor uses ACFL math (no LLM); Installer/Publisher are non-LLM (Q4 / freeze).
 */
export default function CognitiveObservatory({ workId }: { workId: string }) {
  const [audit, setAudit] = useState<WorkAuditResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = async () => {
    setBusy(true); setError(null);
    if (!workId.trim()) { setAudit(null); setBusy(false); return; }
    try {
      setAudit(await getWorkAudit(workId.trim()));
    } catch (e) {
      setError(e instanceof ApiError ? `Cognitive observatory error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, [workId]);

  if (busy && !audit) return <div className="text-[11px] text-[var(--eureka-text-label)]">Loading cognitive trace…</div>;
  if (error) return <div className="text-[11px] text-[var(--eureka-signal-blocked)]">Error (fail-closed): {error}</div>;
  if (!workId.trim()) return <div className="text-[11px] text-[var(--eureka-text-label)]">Enter a Work id to observe the cognitive trace (read-only).</div>;

  const observedPipeline = mapObservedPipeline(
    audit?.contractual_pipeline ?? [],
    audit?.em_pipeline ?? [],
    audit?.cognitive_trace ?? [],
  );

  return (
    <div className="space-y-4" data-testid="cognitive-observatory">
      <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-label)]">Cognitive Observatory · Cognitive Pipeline</div>
      <div className="text-[11px] text-[var(--eureka-text-label)]">Contractual pipeline (architecture) vs Observed (per Work). An LLM only proposes; EUREKA governs.</div>

      {/* CONTRACTUAL pipeline */}
      <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
        <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Contractual pipeline (EM order)</div>
        <div className="flex flex-wrap gap-1 mt-1">
          {(audit?.contractual_pipeline ?? []).map((em, i) => (
            <span key={em} className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-[var(--eureka-spatial-hairline)]">
              {em.replace('EM ', '')}{i < (audit?.contractual_pipeline.length ?? 0) - 1 ? ' →' : ''}
            </span>
          ))}
        </div>
      </section>

      {/* OBSERVED pipeline */}
      <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
        <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Observed pipeline (per Work)</div>
        <div className="mt-1 flex flex-wrap gap-2">
          {observedPipeline.map((o) => {
            return (
              <div key={o.em} className="border border-[var(--eureka-spatial-hairline)] rounded p-2 min-w-[150px]">
                <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">{o.em.replace('EM ', '')}</div>
                <div className={`text-[11px] font-mono ${o.status === 'COMPLETED' ? 'text-[var(--eureka-signal-cognitive)]' : o.status === 'WAITING_FOR_HUMAN_INPUT' ? 'text-amber-600' : 'text-[var(--eureka-text-label)]'}`}>
                  {o.status}
                </div>
                <div className="text-[10px] text-[var(--eureka-text-label)]">{o.model || '—'}</div>
                <div className={`text-[10px] ${TRACE_TONE[o.classification.kind]}`}>{o.classification.label}</div>
                {o.latencyMs > 0 && <div className="text-[10px] text-[var(--eureka-text-label)]">{Math.round(o.latencyMs)}ms</div>}
              </div>
            );
          })}
        </div>
      </section>

      {/* LLM / ACFL trace */}
      <section className="border border-[var(--eureka-spatial-hairline)] rounded p-3">
        <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Cognitive trace (invocations)</div>
        {(audit?.cognitive_trace ?? []).length === 0
          ? <div className="text-[11px] text-[var(--eureka-text-label)]">No cognitive invocation recorded (NOT_RECORDED).</div>
          : (
            <table className="w-full text-[11px] font-mono mt-1">
              <thead><tr className="text-left text-[10px] text-[var(--eureka-text-label)]">
                <th className="p-1">EM</th><th className="p-1">capability</th><th className="p-1">model</th><th className="p-1">status</th><th className="p-1">latency</th>
              </tr></thead>
              <tbody>
                {(audit?.cognitive_trace ?? []).map((t, i) => (
                  <tr key={i} className="border-t border-[var(--eureka-spatial-hairline)]">
                    <td className="p-1">{t.em}</td>
                    <td className="p-1">{t.capability_id}</td>
                    <td className="p-1">{t.model}</td>
                    <td className="p-1">{t.status}</td>
                    <td className="p-1">{Math.round(t.latency_ms ?? 0)}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </section>
    </div>
  );
}
