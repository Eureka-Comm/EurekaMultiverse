import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildHumanAuthorityView } from '../../../domain/cognitiveStory';
import { getDecisionPoints, getHumanDecision, getPublication, getFrozen } from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, AskCopilotButton } from './primitives';

/**
 * HUMAN AUTHORITY — the EUREKA-recommends → human-authorizes flow.
 * Reads the REAL decision_points (recommended_option / recommendation_reason /
 * status / human_selection) + the freeze authorization (publication_status /
 * frozen_result). Renders the APPROVE/REJECT gate and the FROZEN-if-approved
 * outcome. Never invents a decision.
 */
export default function ViewHumanAuthority({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildHumanAuthorityView(state), [state]);
  const dps = getDecisionPoints(state);
  const pending = dps.find((d) => d.status === 'PENDING') || dps[dps.length - 1];
  const hrs = ((state as any)?.human_requests || []) as any[];
  const relevantInfoReq = hrs.find((h) => h.status === 'PENDING') || hrs[hrs.length - 1];
  const humanDecision = getHumanDecision(state);
  const publication = getPublication(state);
  const frozen = getFrozen(state);

  const frozenStatus = publication?.status || (frozen != null ? 'FROZEN' : null);
  const approved =
    humanDecision?.decision_type === 'SELECT_ALTERNATIVE' ||
    publication?.status === 'FROZEN' ||
    publication?.status === 'PUBLISHED' ||
    frozen != null;

  if (view.cognitiveState === 'PENDING') {
    return <DataPendingState reason={view.dataPendingReason} />;
  }

  const flowSteps = [
    {
      label: 'EUREKA RECOMMENDS',
      color: 'var(--eureka-signal-cognitive)',
      body: pending
        ? `${pending.question} → ${pending.recommended_option || 'no explicit recommendation'}`
        : 'No open decision gate.',
      sub: pending?.recommendation_reason || '',
    },
    {
      label: 'HUMAN AUTHORIZES',
      color: 'var(--eureka-signal-authority)',
      body: pending
        ? pending.status === 'PENDING'
          ? 'AWAITING HUMAN DECISION (APPROVE / REJECT)'
          : `Human answered: ${pending.human_selection || '—'}`
        : approved
          ? humanDecision?.selected_alternative_id
            ? `Human selected: ${humanDecision.selected_alternative_id}`
            : 'Human decision recorded'
          : 'No human decision recorded',
      sub: pending?.human_selection || relevantInfoReq?.response_data?.value || '',
    },
    {
      label: 'FREEZE / PUBLISH',
      color: 'var(--eureka-signal-freeze)',
      body: frozenStatus ? `Status: ${frozenStatus}` : 'Not frozen yet.',
      sub: frozen?.result_id || '',
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{view.whatItShows}</div>
        <AskCopilotButton question="¿Qué decisión humana se tomó y por qué?" variant="authority" />
      </div>

      <div className="flex flex-col gap-2">
        {flowSteps.map((s, i) => (
          <div key={s.label} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <span className="w-3 h-3 rounded-full" style={{ background: s.color }} />
              {i < flowSteps.length - 1 && <span className="w-px h-6 bg-[var(--eureka-spatial-hairline)]" />}
            </div>
            <div className="flex-1 rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] font-bold uppercase tracking-widest" style={{ color: s.color }}>
                {s.label}
              </div>
              <div className="text-xs text-[var(--eureka-text-section)] mt-1">{s.body}</div>
              {s.sub && <div className="text-[10px] text-[var(--eureka-text-micro)] mt-0.5 break-all">{s.sub}</div>}
            </div>
          </div>
        ))}
      </div>

      {/* Decision point options (real) */}
      {pending?.options?.length > 0 && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
            Decision options
          </div>
          <div className="flex flex-wrap gap-2">
            {pending.options.map((o: any) => (
              <span
                key={o.id}
                className={`px-2 py-1 rounded text-[10px] font-mono border ${
                  o.id === pending.recommended_option
                    ? 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]'
                    : o.id === pending.human_selection
                      ? 'border-[var(--eureka-signal-authority)] text-[var(--eureka-signal-authority)]'
                      : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)]'
                }`}
              >
                {o.id}
                {o.id === pending.recommended_option && ' · REC'}
                {o.id === pending.human_selection && ' · CHOSEN'}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Information request if present */}
      {!pending && relevantInfoReq && (
        <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
            Information request
          </div>
          <div className="text-xs text-[var(--eureka-text-section)]">{relevantInfoReq.question}</div>
          {relevantInfoReq.required_information?.length > 0 && (
            <div className="text-[10px] text-[var(--eureka-text-micro)] mt-1">
              Required: {relevantInfoReq.required_information.join(', ')}
            </div>
          )}
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
