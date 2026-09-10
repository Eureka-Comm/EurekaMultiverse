import React, { useState } from 'react';
import { runWhatIf, getScenario, getResult, compareScenario, authorizeScenario, discardScenario,
         executeScenario, ApiError, type WhatIfResponse, type CompareResponse, type DecisionResponse,
         type ExecutionResponse } from '../../lib/scenarioApi';

/**
 * WhatIfView — minimal human decision-support surface over the governed Scenario WHAT-IF API.
 * The UI only represents the domain authority returned by the backend. It never computes gclv/m,
 * never implements authority/governance, never promotes or executes. Results are clearly labelled
 * HYPOTHETICAL / PROJECTED / NON_CANONICAL. Governance errors are shown fail-closed.
 */
export default function WhatIfView() {
  const [delta, setDelta] = useState('0.1');
  const [scenarioId, setScenarioId] = useState('SCN-1');
  const [workId, setWorkId] = useState('');
  const [result, setResult] = useState<WhatIfResponse | null>(null);
  const [loaded, setLoaded] = useState<WhatIfResponse | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [decision, setDecision] = useState<DecisionResponse | null>(null);
  const [decisionType, setDecisionType] = useState<'CONFIRM' | 'REJECT' | 'ESCALATE'>('CONFIRM');
  const [rationale, setRationale] = useState('');
  const [humanActor, setHumanActor] = useState('analyst');
  const [execution, setExecution] = useState<ExecutionResponse | null>(null);

  const run = async () => {
    setBusy(true); setError(null);
    try {
      const r = await runWhatIf(scenarioId, Number(delta) || 0, workId.trim() || undefined);
      setResult(r);
      setLoaded(r);
      setSelected((s) => (s.includes(r.scenario_id) ? s : [...s, r.scenario_id]));
    } catch (e) {
      setError(e instanceof ApiError ? `Governance error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const retrieve = async (id: string) => {
    setBusy(true); setError(null);
    try {
      // prove multi-request persistence: fetch the persisted scenario + result by id
      await getScenario(id);
      const r = await getResult(id);
      setLoaded(r);
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? `Retrieval error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const compare = async () => {
    setBusy(true); setError(null);
    try {
      setComparison(await compareScenario(selected, selected[0]));
    } catch (e) {
      setError(e instanceof ApiError ? `Comparison error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const runExecution = async () => {
    if (!id || !workId.trim()) { setError('A "Real work id" is required to execute the governed action.'); return; }
    setBusy(true); setError(null);
    try {
      setExecution(await executeScenario(id, workId.trim()));
    } catch (e) {
      setError(e instanceof ApiError ? `Execution error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  const toggle = (id: string) => setSelected((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));

  const id = loaded?.scenario_id ?? result?.scenario_id;
  const recordDecision = async (kind: 'AUTHORIZE' | 'DISCARD') => {
    if (!id || !workId.trim()) { setError('A "Real work id" is required to record a governed decision.'); return; }
    setBusy(true); setError(null);
    try {
      const body = { decision_type: decisionType, rationale, human_actor: humanActor };
      const d = kind === 'AUTHORIZE'
        ? await authorizeScenario(id, workId.trim(), body)
        : await discardScenario(id, workId.trim(), body);
      setDecision(d);
    } catch (e) {
      setError(e instanceof ApiError ? `Decision error (${e.status}): ${e.message}` : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6 p-6" data-testid="whatif-view">
      <h2 className="text-lg font-mono uppercase tracking-widest">What-If · Hypothetical Scenario</h2>

      {/* create */}
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">Scenario id
          <input value={scenarioId} onChange={(e) => setScenarioId(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <label className="text-sm">Delta
          <input value={delta} onChange={(e) => setDelta(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <label className="text-sm">Real work id (optional)
          <input value={workId} onChange={(e) => setWorkId(e.target.value)} placeholder="e.g. W-REAL" className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
        </label>
        <button onClick={run} disabled={busy} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
          {busy ? 'Running WHAT-IF…' : 'Run WHAT-IF'}
        </button>
        {loaded && (
          <button onClick={() => retrieve(loaded.scenario_id)} className="px-4 py-2 rounded border border-[var(--eureka-spatial-hairline)] text-sm">
            Re-fetch persisted result
          </button>
        )}
      </div>

      {error && <div className="text-sm text-[var(--eureka-signal-blocked)] border border-[var(--eureka-signal-blocked)] rounded p-3">Error (fail-closed): {error}</div>}

      {/* result */}
      {(result || loaded) && (
        <section className="fabric-panel p-4 border border-[var(--eureka-spatial-hairline)] rounded">
          <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-label)]">ScenarioResultCard</div>
          <div className="text-sm font-mono">{result?.scenario_id ?? loaded?.scenario_id}</div>
          <div className="flex flex-wrap gap-2 text-[11px] font-mono mt-1">
            <span>Scope · {result?.scope ?? loaded?.scope}</span>
            <span>Authority · {result?.authority ?? loaded?.authority}</span>
            <span>Canonical Status · {result?.canonical_status ?? loaded?.canonical_status}</span>
            <span>Status · {result?.status ?? loaded?.status}</span>
          </div>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-2 break-all">Source State Identity · {result?.source_state_identity ?? loaded?.source_state_identity}</div>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">Assumptions · {(result?.assumptions ?? loaded?.assumptions ?? []).map((a) => JSON.stringify(a)).join(', ')}</div>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">Provenance · {(result?.provenance ?? loaded?.provenance ?? []).join(' → ')}</div>
          <div className="mt-2 space-y-2">
            {(result?.projected_artifacts ?? loaded?.projected_artifacts ?? []).map((art, i) => (
              <div key={art.artifact_id ?? i} className="border border-[var(--eureka-spatial-hairline)] rounded p-2">
                <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">{art.artifact_id} · {art.artifact_kind} · {art.authority} · {art.canonical_status}</div>
                <div className="flex flex-wrap gap-2 mt-1">
                  {Object.entries(art.payload ?? {}).map(([k, v]) => (
                    <div key={k} className="text-xs font-mono border border-[var(--eureka-spatial-hairline)] rounded p-2">
                      <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">{k}</div>
                      <div className="text-sm max-w-xs break-all">{typeof v === 'number' ? v.toFixed(6) : String(JSON.stringify(v))}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* governed human decision (record-only) */}
      {(result || loaded) && (
        <section className="fabric-panel p-4 border border-[var(--eureka-spatial-hairline)] rounded">
          <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-label)]">ScenarioDecision · record-only · non-canonical</div>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">
            A human AUTHORIZE/DISCARD records an explicit decision about this hypothetical scenario.
            It never promotes, executes, or canonicalizes it. Authority is server-derived (HUMAN_DECISION / SCENARIO / NON_CANONICAL).
          </div>
          <div className="flex flex-wrap items-end gap-3 mt-2">
            <label className="text-sm">Decision
              <select value={decisionType} onChange={(e) => setDecisionType(e.target.value as typeof decisionType)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded">
                <option value="CONFIRM">CONFIRM</option>
                <option value="REJECT">REJECT</option>
                <option value="ESCALATE">ESCALATE</option>
              </select>
            </label>
            <label className="text-sm">Actor
              <input value={humanActor} onChange={(e) => setHumanActor(e.target.value)} className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
            </label>
            <label className="text-sm">Rationale
              <input value={rationale} onChange={(e) => setRationale(e.target.value)} placeholder="why" className="ml-2 px-2 py-1 border border-[var(--eureka-spatial-hairline)] rounded" />
            </label>
            <button onClick={() => recordDecision('AUTHORIZE')} disabled={busy || !workId.trim()} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
              {busy ? 'Recording…' : 'Record AUTHORIZE'}
            </button>
            <button onClick={() => recordDecision('DISCARD')} disabled={busy || !workId.trim()} className="px-4 py-2 rounded border border-[var(--eureka-signal-blocked)] text-sm disabled:opacity-50">
              Record DISCARD
            </button>
          </div>
          {decision && (
            <div className="mt-2 text-[11px] font-mono border border-[var(--eureka-spatial-hairline)] rounded p-2">
              <div><span className="text-[var(--eureka-text-label)]">decision_id</span> · {decision.decision_id}</div>
              <div><span className="text-[var(--eureka-text-label)]">lifecycle_state</span> · {decision.lifecycle_state}</div>
              <div>Scope · {decision.scope} · Authority · {decision.authority} · Canonical · {decision.canonical_status}</div>
              <div className="text-[10px] text-[var(--eureka-text-label)] break-all">source · {decision.source_state_identity}</div>
              <div className="text-[10px] text-[var(--eureka-text-label)] break-all">Provenance · {decision.provenance.join(' → ')}</div>
            </div>
          )}
        </section>
      )}

      {/* governed action execution (REAL_EXECUTION under Q4, record-only UI) */}
      {decision?.lifecycle_state === 'AUTHORIZED' && (
        <section className="fabric-panel p-4 border border-[var(--eureka-spatial-hairline)] rounded">
          <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-label)]">ScenarioExecution · governed REAL_EXECUTION (Q4)</div>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">
            The human decision AUTHORIZED a single action. Executing crosses the Q4 EffectBoundary under REAL_EXECUTION and materializes
            a governed artifact. The UI never declares authority — status/mode/effect are server-derived and shown below.
          </div>
          <button onClick={runExecution} disabled={busy || !workId.trim()} className="px-4 py-2 rounded bg-[var(--eureka-signal-cognitive)] text-white text-sm disabled:opacity-50">
            {busy ? 'Executing…' : 'Execute governed action'}
          </button>
          {execution && (
            <div className="mt-2 text-[11px] font-mono border border-[var(--eureka-spatial-hairline)] rounded p-2">
              <div><span className="text-[var(--eureka-text-label)]">execution_id</span> · {execution.execution_id}</div>
              <div><span className="text-[var(--eureka-text-label)]">action</span> · {execution.action_id}</div>
              <div>Status · {execution.status} · Scope · {execution.scope} · Authority · {execution.authority} · Canonical · {execution.canonical_status}</div>
              <div className="text-[10px] text-[var(--eureka-text-label)]">Mode · {execution.governance?.mode} · Effect class · {execution.governance?.effect_class} · Boundary · {execution.governance?.decision} · {execution.governance?.reason_code}</div>
              <div className="text-[10px] text-[var(--eureka-text-label)]">Effect · {execution.effect?.artifact_id} · {execution.effect?.artifact_path} · {execution.effect?.bytes ?? 0} bytes · exists={String(execution.effect?.exists)}</div>
              <div className="text-[10px] text-[var(--eureka-text-label)] break-all">Provenance · {execution.provenance.join(' → ')}</div>
            </div>
          )}
        </section>
      )}

      {/* compare */}
      <section className="space-y-2">
        <div className="text-sm">Select scenarios to compare (evidence only):</div>
        <div className="flex flex-wrap gap-2">
          {selected.map((id) => (
            <label key={id} className="flex items-center gap-1 text-sm">
              <input type="checkbox" checked={selected.includes(id)} onChange={() => toggle(id)} />
              {id}
            </label>
          ))}
        </div>
        <button onClick={compare} disabled={selected.length < 2 || busy} className="px-4 py-2 rounded border border-[var(--eureka-spatial-hairline)] text-sm disabled:opacity-50">
          Compare ({selected.length})
        </button>
      </section>

      {comparison && (
        <section className="overflow-x-auto">
          <table className="w-full text-sm border border-[var(--eureka-spatial-hairline)]">
            <thead>
              <tr className="text-left text-[10px] uppercase text-[var(--eureka-text-label)]">
                <th className="p-2">Scenario</th>
                {(comparison.metric_comparisons ?? []).filter((d, i, arr) => arr.findIndex((x) => x.metric === d.metric) === i).map((d) => (
                  <th key={d.metric} className="p-2 text-right">{d.metric}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {comparison.scenario_ids.map((sid) => (
                <tr key={sid}>
                  <td className="p-2 font-mono">{sid}</td>
                  {(comparison.metric_comparisons ?? []).filter((d) => d.scenario_id === sid).map((d) => (
                    <td key={d.metric} className="p-2 text-right font-mono">
                      {d.value == null ? '—' : d.value.toFixed(4)}
                      {d.relative_delta != null && <span className="block text-[10px] text-[var(--eureka-text-label)]">{d.relative_delta >= 0 ? '+' : ''}{(d.relative_delta * 100).toFixed(1)}% vs baseline</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          <div className="text-[10px] text-[var(--eureka-text-label)] mt-1">Comparison evidence · scope {comparison.scope} · authority {comparison.authority} · {comparison.canonical_status}</div>
        </section>
      )}
    </div>
  );
}
