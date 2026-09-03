import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildOutcomeStoryView } from '../../../domain/cognitiveStory';
import {
  getKnowledge,
  getPredictive,
  getPrescriptive,
  getExecutionState,
  getPublication,
  getHumanDecision,
  getStateResult,
  getDecisionPoints,
  getSelectedAlternativeId,
  getActionPlan,
} from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';

/**
 * RESULT — the Outcome Story.
 * Renders Question → What EUREKA found → predicted → recommended → human
 * approved → executed → happened, plus an EXECUTIVE ANSWER, evidence count and
 * an expected-vs-actual gap ONLY if real data supports it (else DATA PENDING).
 */
export default function ViewOutcomeStory({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildOutcomeStoryView(state), [state]);
  const result = getStateResult(state);
  const knowledge = getKnowledge(state);
  const findings: any[] = knowledge.findings || [];
  const predictions = getPredictive(state).predictions || [];
  const prescription = getPrescriptive(state).prescriptions?.[0];
  const selectedId = getSelectedAlternativeId(state);
  const humanDecision = getHumanDecision(state);
  const decisionPoints = getDecisionPoints(state);
  const executionState = getExecutionState(state);
  const publication = getPublication(state);
  const actionPlan = getActionPlan(state);
  const pubSections = (publication?.publications || []).flatMap((p: any) => p.sections || []);
  const evidenceCount = state.evidence?.length ?? 0;

  const resultAvailable = result?.status === 'AVAILABLE';
  const execResultStatus = executionState?.result?.status;
  const effectiveRecommendation = prescription?.rationale || (result?.recommendations || []).join('; ');
  const humanApproved = humanDecision?.selected_alternative_id || decisionPoints.find((d) => d.human_selection)?.human_selection || (publication?.status === 'FROZEN' || publication?.status === 'PUBLISHED' ? 'yes' : null);

  const hasData = resultAvailable || pubSections.length > 0;

  if (!hasData && view.cognitiveState === 'PENDING') {
    return <DataPendingState reason={view.dataPendingReason} />;
  }

  // Expected vs actual: only if there is both a predicted value and a real
  // measured outcome for the same target. Otherwise report DATA PENDING.
  const expectedActual: Array<{ target: string; expected: string; actual: string }> = [];
  predictions.forEach((p: any) => {
    const actualVal = result?.calculations?.[p.target_variable];
    if (p.predicted_value != null && actualVal != null) {
      expectedActual.push({
        target: p.target_variable || p.prediction_id,
        expected: String(p.predicted_value),
        actual: String(actualVal),
      });
    }
  });

  const progression = [
    { step: 'QUESTION', body: state?.work?.userIntent || `Objective: ${(state as any)?.problem?.objective || '—'}`, color: 'var(--eureka-signal-cognitive)' },
    { step: 'FOUND', body: findings.length ? findings.slice(0, 4).map((f) => f.statement).join('; ') : '—', color: 'var(--eureka-signal-semantic)' },
    { step: 'PREDICTED', body: predictions.length ? predictions.slice(0, 3).map((p: any) => `${p.target_variable || p.prediction_id}=${p.predicted_value ?? 'n/a'}`).join('; ') : '—', color: 'var(--eureka-signal-cognitive)' },
    { step: 'RECOMMENDED', body: selectedId ? `${selectedId} — ${effectiveRecommendation}` : '—', color: 'var(--eureka-signal-action)' },
    { step: 'HUMAN APPROVED', body: humanApproved ? `Approved: ${humanApproved}` : '—', color: 'var(--eureka-signal-authority)' },
    { step: 'EXECUTED', body: execResultStatus ? `${execResultStatus}` : '—', color: 'var(--eureka-signal-scientific)' },
    { step: 'HAPPENED', body: resultAvailable ? (result.summary || 'Result available.') : pubSections.length ? `${pubSections.length} section(s) published.` : '—', color: 'var(--eureka-signal-freeze)' },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">
          {resultAvailable ? (result.summary || 'Result available.') : `${pubSections.length} section(s) published.`}
        </div>
        <AskCopilotButton question={selectedId ? `¿Qué pasó finalmente con ${selectedId}?` : '¿Cuál fue el resultado final?'} variant="action" />
      </div>

      {/* Executive Answer */}
      {resultAvailable && (
        <div className="rounded-lg border border-[var(--eureka-signal-authority)] bg-[var(--eureka-surface-elevated)] p-4">
          <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-authority)] uppercase mb-2">
            Executive answer
          </div>
          <div className="text-sm text-[var(--eureka-text-display)] leading-relaxed whitespace-pre-wrap">
            {result.summary || 'The result is available.'}
          </div>
          {result.recommendations?.length > 0 && (
            <ul className="mt-3 space-y-1 text-xs text-[var(--eureka-text-section)]">
              {result.recommendations.map((r: string, i: number) => (
                <li key={i} className="flex gap-2">
                  <span className="text-[var(--eureka-signal-action)]">◆</span>
                  <span>{r}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Outcome progression chain */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Outcome story
        </div>
        <div className="flex flex-col gap-2">
          {progression.map((p, i) => (
            <div key={p.step} className="flex items-start gap-3">
              <div className="flex flex-col items-center">
                <span className="w-2.5 h-2.5 rounded-full" style={{ background: p.color }} />
                {i < progression.length - 1 && <span className="w-px h-5 bg-[var(--eureka-spatial-hairline)]" />}
              </div>
              <div className="flex-1">
                <span className="text-[9px] font-bold uppercase tracking-widest" style={{ color: p.color }}>
                  {p.step}
                </span>
                <div className="text-[11px] text-[var(--eureka-text-section)]">{p.body}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Evidence count */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">Evidence sources</span>
        <span className="font-mono text-[var(--eureka-text-display)]">{evidenceCount}</span>
      </div>

      {/* Expected vs actual */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Expected vs actual
        </div>
        {expectedActual.length ? (
          <div className="space-y-2">
            {expectedActual.map((e, i) => (
              <div key={i} className="flex items-center gap-3 text-xs">
                <span className="text-[var(--eureka-text-section)] flex-1">{e.target}</span>
                <span className="text-[var(--eureka-signal-cognitive)] font-mono">{e.expected}</span>
                <span className="text-[var(--eureka-text-micro)]">→</span>
                <span className="text-[var(--eureka-signal-action)] font-mono">{e.actual}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">
            DATA PENDING — no measured outcome exists to compare against the prediction.
          </div>
        )}
      </div>

      {/* Published sections */}
      {pubSections.length > 0 && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 space-y-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">
            Published sections ({pubSections.length})
          </div>
          {pubSections.map((s: any, i: number) => (
            <div key={i} className="border-l-2 border-[var(--eureka-signal-cognitive)] pl-3">
              <div className="text-[10px] font-mono uppercase text-[var(--eureka-signal-cognitive)]">
                {s.section_type || 'SECTION'}
              </div>
              <div className="text-[11px] text-[var(--eureka-text-section)] whitespace-pre-wrap">{s.content}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Uncertainty
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">{view.uncertainty}</div>
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
