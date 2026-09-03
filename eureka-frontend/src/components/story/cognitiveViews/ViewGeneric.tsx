import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import {
  buildQuestionView,
  buildContextView,
  buildDataView,
  buildDiscoveryView,
  buildEvaluationView,
  buildLearningView,
} from '../../../domain/cognitiveStory';
import type { CognitiveView, CognitiveViewKey } from '../../../domain/cognitiveView';
import { getKnowledge } from '../../../domain/cognitiveView';
import { ViewShell, Empty } from './primitives';

/**
 * Generic cognitive view for the stages whose answer is best expressed by the
 * Knowledge Object + a real item list (Question / Context / Data / Discovery /
 * Evaluation / Learning). Renders REAL data only.
 */

const builders: Partial<Record<CognitiveViewKey, (s: CanonicalWorkState) => CognitiveView>> = {
  QUESTION: buildQuestionView,
  CONTEXT: buildContextView,
  DATA: buildDataView,
  DISCOVERY: buildDiscoveryView,
  EVALUATION: buildEvaluationView,
  LEARNING: buildLearningView,
};

export default function ViewGeneric({ state, viewKey }: { state: CanonicalWorkState; viewKey: CognitiveViewKey }) {
  const view = useMemo(() => (builders[viewKey] ? builders[viewKey]!(state) : buildLearningView(state)), [state, viewKey]);

  // Real item list specific to the stage.
  const anyState = state as any;
  const items: string[] = useMemo(() => {
    switch (viewKey) {
      case 'QUESTION': {
        const structured = anyState.problem?.structured_problem || {};
        const qs = (structured.questions || []).slice();
        if (anyState.problem?.objective) qs.push(`Objective: ${anyState.problem.objective}`);
        if (state?.work?.userIntent) qs.push(`Intent: ${state.work.userIntent}`);
        return qs;
      }
      case 'CONTEXT': {
        const structured = anyState.problem?.structured_problem || {};
        return [
          ...(structured.entities || []).map((e: string) => `Entity: ${e}`),
          ...(structured.variables || []).map((v: string) => `Variable: ${v}`),
          ...(structured.relationships || []).map((r: string) => `Relationship: ${r}`),
          ...(structured.assumptions || []).map((a: string) => `Assumption: ${a}`),
          ...(structured.constraints || []).map((c: string) => `Constraint: ${c}`),
        ];
      }
      case 'DATA':
        return state?.evidence?.map((e) => `${e.evidence_id} · ${e.filename} · ${e.ingestion_status}${e.extraction_status && e.extraction_status !== 'NOT_STARTED' ? ` / ${e.extraction_status}` : ''}`) || [];
      case 'DISCOVERY':
        return ((anyState.knowledge || {}).findings || []).map((f: any) => `${f.finding_id} [${f.status}] ${f.statement}`);
      case 'EVALUATION': {
        const weights: Record<string, number> = anyState.state?.acfl?.weights || {};
        return Object.keys(weights).map((k) => `${k}: ${weights[k]}`);
      }
      case 'LEARNING': {
        const k = getKnowledge(state);
        const conditions: any[] = anyState.conditions || [];
        const gaps: string[] = anyState.gaps || [];
        return [
          ...(k.unknowns || []).map((u: string) => `Unknown: ${u}`),
          ...(k.contradictions || []).map((c: string) => `Contradiction: ${c}`),
          ...gaps.map((g: string) => `Gap: ${g}`),
          ...conditions.map((c: any) => `${c.status}: ${c.message}`),
        ];
      }
      default:
        return [];
    }
  }, [viewKey, state, anyState]);

  return (
    <ViewShell
      view={view}
      onAsk={(q) => {
        // Handled by the parent (the console) to push a question into the Copilot.
        window.dispatchEvent(new CustomEvent('eureka:ask-copilot', { detail: { question: q } }));
      }}
    >
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Real items ({items.length})
        </div>
        {items.length ? (
          <ul className="space-y-1.5 max-h-64 overflow-y-auto pr-1">
            {items.map((it, i) => (
              <li key={i} className="text-[11px] text-[var(--eureka-text-section)] border-l border-[var(--eureka-spatial-hairline)] pl-2 break-words">
                {it}
              </li>
            ))}
          </ul>
        ) : (
          <Empty text="No items recorded for this stage." />
        )}
      </div>
    </ViewShell>
  );
}
