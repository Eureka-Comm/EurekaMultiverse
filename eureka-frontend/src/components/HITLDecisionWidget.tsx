import React, { useState } from 'react';
import { useWorkStore } from '../store/workStore';
import { selectActiveDecision, selectActiveInformationRequest } from '../selectors/decisionSelectors';
import { API_BASE } from '../lib/apiBase';

export default function HITLDecisionWidget() {
  const activeWork = useWorkStore((state) => state.activeWork);

  if (!activeWork) return null;

  const activeDecision = selectActiveDecision(activeWork);
  if (activeDecision) {
    return (
      <DecisionItem
        decision={activeDecision}
        workId={activeWork.work.workId}
      />
    );
  }

  // LS49: no active decision, but the backend may be waiting on an INFORMATION request
  const activeRequest = selectActiveInformationRequest(activeWork);
  if (activeRequest) {
    return (
      <InformationItem
        request={activeRequest}
        workId={activeWork.work.workId}
      />
    );
  }

  return null;
}

function DecisionItem({ decision, workId }: { decision: any, workId: string }) {
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState<'IDLE' | 'SUBMITTING' | 'SUBMITTED' | 'ERROR'>('IDLE');
  const [errorMsg, setErrorMsg] = useState('');

  const pollState = useWorkStore((state) => state.pollState);

  const handleSubmit = async () => {
    if (!selected) return;
    setStatus('SUBMITTING');
    setErrorMsg('');
    try {
      const apiUrl = API_BASE;
      const res = await fetch(`${apiUrl}/api/work/${workId}/human_input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'SELECTION',
          decision_id: decision.decision_id,
          value: selected,
          rationale: 'Human selected alternative from UI'
        })
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${String(detail).slice(0, 120) || 'error'}`);
      }
      setStatus('SUBMITTED');
      pollState();
    } catch (e: any) {
      // 404 => the work is stale (backend reset). Reset the session so the user starts fresh.
      if (/404|not found/i.test(e.message)) {
        try { useWorkStore.getState().clearWork?.(); } catch {}
        setErrorMsg('El trabajo ya no existe (el backend fue reiniciado). Se reinicia la sesión.');
      } else {
        setErrorMsg('No se pudo conectar con el backend (:8000). Revisa que esté activo y reintenta.');
      }
      setStatus('ERROR');
    }
  };

  if (status === 'SUBMITTED') return null;
  const disabled = status === 'SUBMITTING';

  return (
    <div className="lift-card rounded-xl border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span style={{ width: 8, height: 8, borderRadius: 999, background: 'var(--eureka-signal-authority)', animation: 'breatheAccent 2s ease-in-out infinite' }} />
        <div className="text-[var(--eureka-signal-authority)] text-xs font-bold uppercase tracking-widest">
          EUREKA necesita tu decisión
        </div>
      </div>
      <div className="text-sm text-[var(--eureka-text-display)] font-semibold">
        {decision.question}
      </div>

      <div className="flex flex-col gap-2 mt-1">
        {decision.options?.map((opt: any) => (
          <label key={opt.id} className={`flex items-start gap-2 p-2 rounded-lg cursor-pointer border transition-colors ${selected === opt.id ? 'border-[var(--eureka-signal-authority)] bg-[var(--eureka-surface-selected)]' : 'border-[var(--eureka-spatial-hairline)] hover:bg-[var(--eureka-surface-elevated)]'}`}>
            <input
              type="radio"
              name={`decision-${decision.decision_id}`}
              className="mt-1 accent-[var(--eureka-signal-authority)]"
              value={opt.id}
              checked={selected === opt.id}
              onChange={() => setSelected(opt.id)}
              disabled={disabled}
            />
            <div className="flex flex-col">
              <span className="text-[var(--eureka-text-label)] text-xs font-bold">{opt.id}</span>
              <span className="text-[var(--eureka-text-display)] text-sm">{opt.desc ?? opt.label ?? opt.id}</span>
            </div>
          </label>
        ))}
      </div>
      {errorMsg && <div className="text-[var(--eureka-signal-blocked)] text-xs">Error: {errorMsg}</div>}
      <div className="mt-2 flex justify-end">
        <button
          className="bg-[var(--eureka-signal-authority)] text-white px-4 py-2 rounded-lg text-xs font-bold disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={disabled || !selected}
          onClick={handleSubmit}
        >
          {status === 'SUBMITTING' ? 'Enviando...' : 'Confirmar decisión'}
        </button>
      </div>
    </div>
  );
}

function InformationItem({ request, workId }: { request: any, workId: string }) {
  const [value, setValue] = useState('');
  const [status, setStatus] = useState<'IDLE' | 'SUBMITTING' | 'SUBMITTED' | 'ERROR'>('IDLE');
  const [errorMsg, setErrorMsg] = useState('');

  const pollState = useWorkStore((state) => state.pollState);

  const handleSubmit = async () => {
    if (!value.trim()) return;
    setStatus('SUBMITTING');
    setErrorMsg('');
    try {
      const apiUrl = API_BASE;
      const res = await fetch(`${apiUrl}/api/work/${workId}/human_input`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'INFORMATION',
          request_id: request.request_id,
          value,
          rationale: 'Human provided information from UI'
        })
      });
      if (!res.ok) {
        const detail = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${String(detail).slice(0, 120) || 'error'}`);
      }
      setStatus('SUBMITTED');
      pollState();
    } catch (e: any) {
      if (/404|not found/i.test(e.message)) {
        try { useWorkStore.getState().clearWork?.(); } catch {}
        setErrorMsg('El trabajo ya no existe (el backend fue reiniciado). Se reinicia la sesión.');
      } else {
        setErrorMsg('No se pudo conectar con el backend (:8000). Revisa que esté activo y reintenta.');
      }
      setStatus('ERROR');
    }
  };

  if (status === 'SUBMITTED') return null;
  const disabled = status === 'SUBMITTING';

  return (
    <div className="lift-card rounded-xl border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-5 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span style={{ width: 8, height: 8, borderRadius: 999, background: 'var(--eureka-signal-cognitive)', animation: 'breatheAccent 2s ease-in-out infinite' }} />
        <div className="text-[var(--eureka-signal-cognitive)] text-xs font-bold uppercase tracking-widest">
          EUREKA necesita tu información
        </div>
      </div>
      <div className="text-sm text-[var(--eureka-text-display)] font-semibold">
        {request.question}
      </div>
      {request.required_information && request.required_information.length > 0 && (
        <div className="text-xs text-[var(--eureka-text-label)]">
          Requerido: {request.required_information.join(', ')}
        </div>
      )}
      <textarea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={disabled}
        rows={3}
        className="w-full bg-transparent border border-[var(--eureka-spatial-hairline)] rounded-lg p-3 text-sm text-[var(--eureka-text-display)] focus:outline-none focus:border-[var(--eureka-signal-cognitive)] resize-none"
        placeholder="Proporciona la información solicitada..."
      />
      {errorMsg && <div className="text-[var(--eureka-signal-blocked)] text-xs">Error: {errorMsg}</div>}
      <div className="mt-2 flex justify-end">
        <button
          className="bg-[var(--eureka-signal-cognitive)] text-white px-4 py-2 rounded-lg text-xs font-bold disabled:opacity-50 disabled:cursor-not-allowed"
          disabled={disabled || !value.trim()}
          onClick={handleSubmit}
        >
          {status === 'SUBMITTING' ? 'Enviando...' : 'Enviar información'}
        </button>
      </div>
    </div>
  );
}
