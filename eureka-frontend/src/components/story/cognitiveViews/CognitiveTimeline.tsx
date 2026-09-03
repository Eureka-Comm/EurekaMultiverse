import React, { useMemo } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildWhatHappenedView } from '../../../domain/cognitiveStory';
import { getExecutionEvents } from '../../../domain/cognitiveView';
import { DataPendingState, Empty, ObjectMeta, ProvenanceList, RelationshipList } from './primitives';

/**
 * WHAT HAPPENED? — the cognitive timeline.
 * Renders the REAL execution_events as a chronological stream
 * (Question → Context → Data → Discovery → Prediction → Evaluation →
 * Alternatives → Human decision → Prescription → Action → Result → Published),
 * labeled by canonical_em. Never invents events.
 */

const EM_TO_LABEL: Record<string, string> = {
  'EM Core': 'Question',
  'EM Structurer': 'Context · Data',
  'EM Descriptor': 'Discovery',
  'EM Predictor': 'Prediction',
  'EM Prescriptor': 'Evaluation · Alternatives · Prescription',
  'EM Actioner': 'Action',
  'EM Installer': 'Human decision · Freeze',
  'EM Publisher': 'Result · Published',
};

const eventColor = (status: string) => {
  if (status === 'COMPLETED' || status === 'SUCCEEDED') return 'var(--eureka-signal-action)';
  if (status === 'FAILED' || status === 'BLOCKED') return 'var(--eureka-signal-blocked)';
  if (status === 'WAITING_FOR_HUMAN_INPUT') return 'var(--eureka-signal-authority)';
  if (status === 'WAITING_FOR_EVIDENCE') return 'var(--eureka-signal-freeze)';
  return 'var(--eureka-signal-cognitive)';
};

export default function CognitiveTimeline({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildWhatHappenedView(state), [state]);
  const events = getExecutionEvents(state);

  if (view.cognitiveState === 'PENDING') {
    return <DataPendingState reason={view.dataPendingReason} />;
  }

  return (
    <div className="space-y-4">
      <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{view.whatItShows}</div>

      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 max-h-[380px] overflow-y-auto">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
          Execution trace (chronological)
        </div>
        {events.length ? (
          <div className="space-y-2">
            {events.map((e, i) => {
              const label = EM_TO_LABEL[e.canonical_em] || e.canonical_em || e.event;
              const color = eventColor(e.status);
              return (
                <div key={i} className="flex items-start gap-3">
                  <div className="flex flex-col items-center">
                    <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: color }} />
                    {i < events.length - 1 && <span className="w-px h-5 bg-[var(--eureka-spatial-hairline)]" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-[10px] font-mono text-[var(--eureka-text-micro)]">{e.timestamp}</span>
                      <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color }}>
                        {e.status}
                      </span>
                      <span className="text-[10px] text-[var(--eureka-signal-semantic)]">{label}</span>
                    </div>
                    <div className="text-[11px] text-[var(--eureka-text-section)] break-words">
                      {e.event}{e.message ? ` — ${e.message}` : ''}
                    </div>
                    <div className="text-[10px] text-[var(--eureka-text-micro)] font-mono">
                      {e.canonical_em} · {e.capability_id} · {e.step_id}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <Empty text="No execution trace recorded." />
        )}
      </div>

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
