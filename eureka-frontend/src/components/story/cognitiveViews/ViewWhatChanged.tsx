import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildWhatChangedView } from '../../../domain/cognitiveStory';
import {
  getPrescriptive,
  getSelectedAlternativeId,
  getPrescriptionConstraints,
  getHistoricalContext,
  getExecutionState,
} from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';

/**
 * WHAT CHANGED? — before/after prescription. Uses ONLY real fields:
 *   - historical_context.delta_assessment.items[] (real DeltaItems) when present,
 *   - the selected alternative's expected_effects[] (gains) and constraints[] (binds).
 * A truthful explanation sentence is built from these real fields. When there is
 * no before/after delta in the backend, it says so (never invents numbers).
 */
export default function ViewWhatChanged({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildWhatChangedView(state), [state]);
  const presc = getPrescriptive(state);
  const prescription = presc.prescriptions?.[0];
  const selected = prescription?.selected_alternative;
  const selectedId = getSelectedAlternativeId(state);
  const histCtx = getHistoricalContext(state) || {};
  const deltaAssess = histCtx?.delta_assessment || {};
  const deltaItems: any[] = deltaAssess?.items || [];
  const effects: string[] = selected?.expected_effects || [];
  const constraints: string[] = selected?.constraints || [];
  const hardConstraints: string[] = getPrescriptionConstraints(state);
  const execState = getExecutionState(state);
  const execStatus = execState?.status || execState?.result?.status;

  const hasDelta = deltaItems.length > 0;
  const hasSelectedAlt = !!(selected || selectedId);

  if (!hasDelta && !effects.length && !constraints.length && !selected && !hardConstraints.length) {
    return <DataPendingState reason="No before/after delta is recorded in the backend state." />;
  }

  const explanation =
    selectedId && (effects.length || constraints.length)
      ? `Committing to ${selectedId} is expected to yield ${effects.length} effect(s) (${effects.slice(0, 3).join('; ')}${effects.length > 3 ? '…' : ''}) subject to ${constraints.length} alternative constraint(s) and ${hardConstraints.length} hard invariant(s)${execStatus ? `; execution ${execStatus}` : ''}.`
      : hasDelta
        ? `${deltaItems.length} material change(s) were detected against the frozen/reference state.`
        : 'No expected effect or constraint is recorded for the selected alternative.';

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{explanation}</div>
        <AskCopilotButton question="¿Qué cambió realmente tras la ejecución?" />
      </div>

      {/* Hard invariants (real) */}
      {hardConstraints.length > 0 && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            Hard constraints (invariants that bound the change)
          </div>
          <ul className="space-y-1">
            {hardConstraints.map((c, i) => (
              <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                <span className="text-[var(--eureka-signal-blocked)]">▣</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Real execution delta (authorized vs executed) */}
      {execState && (
        <div className="rounded-lg border border-[var(--eureka-signal-freeze)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            What actually changed after execution (real)
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-center">
            <div className="rounded bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] p-2">
              <div className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Authorized actions</div>
              <div className="font-mono text-[var(--eureka-text-display)]">{(execState.authorization?.authorized_actions || []).length}</div>
            </div>
            <div className="rounded bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] p-2">
              <div className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Succeeded</div>
              <div className="font-mono text-[var(--eureka-signal-action)]">{(execState.result?.successful_actions || []).length}</div>
            </div>
            <div className="rounded bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] p-2">
              <div className="text-[9px] uppercase tracking-wider text-[var(--eureka-text-label)]">Failed</div>
              <div className="font-mono text-[var(--eureka-signal-blocked)]">{(execState.result?.failed_actions || []).length}</div>
            </div>
          </div>
          {execState.result?.successful_actions?.length > 0 && (
            <div className="mt-2 text-[10px] text-[var(--eureka-text-micro)]">
              Executed: {execState.result.successful_actions.join(', ')} · Executive result: {execState.result.status}
            </div>
          )}
        </div>
      )}

      {/* Real DeltaItems */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Before / after deltas (real)
        </div>
        {hasDelta ? (
          <div className="space-y-2">
            {deltaItems.map((d, i) => (
              <div key={i} className="border-l-2 border-[var(--eureka-signal-scientific)] pl-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] font-mono uppercase text-[var(--eureka-signal-scientific)]">
                    {d.delta_type}
                  </span>
                  <span className="text-[9px] uppercase text-[var(--eureka-text-micro)]">
                    materiality: {d.materiality}
                  </span>
                </div>
                <div className="text-[11px] text-[var(--eureka-text-section)] mt-1">
                  {d.historical_value != null || d.current_value != null ? (
                    <>
                      <span className="text-[var(--eureka-text-label)]">{d.historical_value ?? '—'}</span>
                      <span className="text-[var(--eureka-signal-cognitive)] mx-1">→</span>
                      <span className="text-[var(--eureka-text-metric)]">{d.current_value ?? '—'}</span>
                    </>
                  ) : (
                    <span>{d.explanation}</span>
                  )}
                </div>
                {d.explanation && (
                  <div className="text-[10px] text-[var(--eureka-text-micro)] mt-0.5">{d.explanation}</div>
                )}
              </div>
            ))}
            {deltaAssess.status && (
              <div className="text-[10px] text-[var(--eureka-text-micro)]">
                Delta assessment status: {deltaAssess.status}
              </div>
            )}
          </div>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">
            No before/after delta items recorded against the reference state.
          </div>
        )}
      </div>

      {/* Expected effects + constraints of the selected alternative */}
      {selected && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-signal-action)] mb-2">
              Expected effects (gain)
            </div>
            {effects.length ? (
              <ul className="space-y-1">
                {effects.map((e, i) => (
                  <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                    <span className="text-[var(--eureka-signal-action)]">+</span>
                    <span>{e}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-micro)]">None recorded.</div>
            )}
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-signal-blocked)] mb-2">
              Constraints / risk (binds)
            </div>
            {constraints.length ? (
              <ul className="space-y-1">
                {constraints.map((c, i) => (
                  <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                    <span className="text-[var(--eureka-signal-blocked)]">—</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-micro)]">None recorded.</div>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Decision support
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">{view.decisionSupport}</div>
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Provenance
            </div>
            <ProvenanceList items={view.provenance} />
          </div>
        </div>
      </div>
    </div>
  );
}
