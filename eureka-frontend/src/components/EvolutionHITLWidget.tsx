import React, { useEffect, useState } from 'react';

const API = import.meta.env.VITE_EUREKA_API_URL || 'http://localhost:8000';

type Proposal = {
  version?: string;
  version_propuesta?: string;
  propuesta_id?: string;
  capa_afectada?: string;
  cambio?: string;
  hipotesis?: string;
  metrica_a_observar?: string;
  riesgo?: string;
  status?: string;
};

type LedgerRecord = {
  version: string;
  status?: string;
  created_at?: string;
  proposal?: Proposal;
  outcomes?: { metrics?: Record<string, any> }[];
};

export default function EvolutionHITLWidget() {
  const [history, setHistory] = useState<LedgerRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [msg, setMsg] = useState('');
  const [form, setForm] = useState({
    capa_afectada: 'cognitiva',
    cambio: '',
    hipotesis: '',
    metrica_a_observar: '',
    riesgo: '',
    cost: '50',
    risk: '50',
  });

  const load = async () => {
    setLoading(true);
    try {
      const [h, p] = await Promise.all([
        fetch(`${API}/api/evolution/history`).then((r) => r.json()),
        fetch(`${API}/api/evolution/pending`).then((r) => r.json()),
      ]);
      setHistory(h.history || []);
      setPending(p.pending || []);
    } catch (e: any) {
      setMsg(`ERROR loading: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };
  const [pending, setPending] = useState<any[]>([]);

  useEffect(() => {
    load();
  }, []);

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const propose = async () => {
    if (!form.cambio.trim()) { setMsg('cambio es obligatorio'); return; }
    setMsg('Proponiendo variante...');
    try {
      const payload = {
        version_propuesta: 'v-propuesta',
        capa_afectada: form.capa_afectada,
        cambio: form.cambio,
        hipotesis: form.hipotesis || '(sin hipótesis)',
        metrica_a_observar: form.metrica_a_observar || 'satisfaccion_ponderada',
        riesgo: form.riesgo || '(sin riesgo declarado)',
        capa_fuzzy: { weights: { cost: Number(form.cost), risk: Number(form.risk) } },
      };
      const r = await fetch(`${API}/api/evolution/propose`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.message || `HTTP ${r.status}`);
      setMsg(`Propuesta ${d.entry?.version || ''} pendiente de aprobación.`);
      await load();
      setForm((f) => ({ ...f, cambio: '', hipotesis: '', metrica_a_observar: '', riesgo: '' }));
    } catch (e: any) {
      setMsg(`ERROR proponiendo: ${e.message}`);
    }
  };

  const act = async (version: string, action: 'approve' | 'reject') => {
    setMsg(`${action.toUpperCase()} ${version}...`);
    try {
      const r = await fetch(`${API}/api/evolution/${version}/${action}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.message || `HTTP ${r.status}`);
      setMsg(`${action.toUpperCase()} ${version} -> ${d.status}`);
      await load();
    } catch (e: any) {
      setMsg(`ERROR ${action}: ${e.message}`);
    }
  };

  const statusColor = (s?: string) =>
    s === 'PENDING' ? 'text-[var(--eureka-signal-warning)]' :
    s === 'APPROVED' ? 'text-[var(--eureka-signal-semantic)]' :
    s === 'MEASURED' ? 'text-[var(--eureka-signal-action)]' :
    s === 'REJECTED' ? 'text-[var(--eureka-signal-blocked)]' : 'text-[var(--eureka-text-label)]';

  // `history` now carries versioned entries: {version, proposal, status, outcomes}.
  // Only render version records (all of them are proposals from the reducer).
  const versions = history;

  return (
    <div className="fabric-panel p-6 bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] space-y-6">
      <h3 className="text-xs font-bold text-[var(--eureka-text-display)] mb-1 tracking-widest uppercase">Evolución supervisada</h3>
      <p className="text-[11px] text-[var(--eureka-text-label)]">
        Motor multicapa con gate humano. Se propone UNA variante a la vez; nada se aplica sin tu aprobación explícita.
      </p>

      {/* Propose form */}
      <div className="border border-[var(--eureka-spatial-hairline)] rounded p-4 space-y-3">
        <div className="text-[11px] font-bold uppercase tracking-widest text-[var(--eureka-signal-cognitive)]">Proponer variante</div>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-[11px] text-[var(--eureka-text-label)]">Capa afectada
            <select value={form.capa_afectada} onChange={(e) => set('capa_afectada', e.target.value)}
              className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm">
              <option value="fuzzy">fuzzy</option><option value="estadistica">estadistica</option>
              <option value="cognitiva">cognitiva</option><option value="prompt_base">prompt_base</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-[11px] text-[var(--eureka-text-label)]">Peso cost
              <input value={form.cost} onChange={(e) => set('cost', e.target.value)} className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm" />
            </label>
            <label className="text-[11px] text-[var(--eureka-text-label)]">Peso risk
              <input value={form.risk} onChange={(e) => set('risk', e.target.value)} className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm" />
            </label>
          </div>
        </div>
        <label className="block text-[11px] text-[var(--eureka-text-label)]">Cambio
          <input value={form.cambio} onChange={(e) => set('cambio', e.target.value)} placeholder="Descripción concreta y mínima del cambio" className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm" />
        </label>
        <label className="block text-[11px] text-[var(--eureka-text-label)]">Hipótesis
          <input value={form.hipotesis} onChange={(e) => set('hipotesis', e.target.value)} placeholder="Por qué debería mejorar" className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm" />
        </label>
        <label className="block text-[11px] text-[var(--eureka-text-label)]">Métrica a observar
          <input value={form.metrica_a_observar} onChange={(e) => set('metrica_a_observar', e.target.value)} placeholder="Ej. satisfacción_ponderada" className="mt-1 w-full bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-2 py-1.5 text-sm" />
        </label>
        <button onClick={propose} className="px-4 py-2 text-[11px] font-mono uppercase tracking-wider rounded bg-[var(--eureka-signal-cognitive)] text-white">Proponer</button>
      </div>

      {msg && <div className="text-[11px] text-[var(--eureka-text-label)]">{msg}</div>}

      {/* Pending */}
      {pending.length > 0 && (
        <div>
          <div className="text-[11px] font-bold uppercase tracking-widest text-[var(--eureka-signal-warning)] mb-2">Pendientes de aprobación</div>
          <div className="space-y-3">
            {pending.map((p) => (
              <div key={p.version} className="border border-[var(--eureka-spatial-hairline)] rounded p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-sm text-[var(--eureka-text-display)]">{p.version}</span>
                  <span className={`text-[11px] font-bold uppercase ${statusColor(p.status)}`}>{p.status}</span>
                </div>
                <div className="text-sm text-[var(--eureka-text-display)]">{p.proposal?.cambio}</div>
                <div className="text-[11px] text-[var(--eureka-text-label)]">hipótesis: {p.proposal?.hipotesis}</div>
                <div className="text-[11px] text-[var(--eureka-text-label)]">riesgo: {p.proposal?.riesgo}</div>
                <div className="flex gap-2">
                  <button onClick={() => act(p.version, 'approve')} className="px-3 py-1.5 text-[11px] font-mono uppercase rounded bg-[var(--eureka-signal-action)] text-white">Aprobar</button>
                  <button onClick={() => act(p.version, 'reject')} className="px-3 py-1.5 text-[11px] font-mono uppercase rounded border border-[var(--eureka-signal-blocked)] text-[var(--eureka-signal-blocked)]">Rechazar</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* History / versions */}
      <div>
        <div className="text-[11px] font-bold uppercase tracking-widest text-[var(--eureka-text-display)] mb-2">Versiones registradas</div>
        {versions.length === 0 && <div className="text-[11px] text-[var(--eureka-text-micro)]">Sin variantes aún.</div>}
        <div className="space-y-2">
          {versions.slice().reverse().map((r) => (
            <div key={r.version} className="border border-[var(--eureka-spatial-hairline)] rounded px-4 py-3 flex items-start justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm text-[var(--eureka-text-display)]">{r.version}</span>
                  <span className={`text-[10px] font-bold uppercase ${statusColor(r.status || r.proposal?.status)}`}>{r.status || r.proposal?.status}</span>
                  <span className="text-[10px] text-[var(--eureka-text-micro)]">({r.proposal?.capa_afectada || '—'})</span>
                </div>
                <div className="text-sm truncate text-[var(--eureka-text-display)]">{r.proposal?.cambio || r.proposal?.version_propuesta}</div>
                {r.outcomes?.length ? (
                  <div className="text-[10px] font-mono text-[var(--eureka-text-label)]">metrics: {JSON.stringify(r.outcomes[r.outcomes.length - 1].metrics)}</div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
