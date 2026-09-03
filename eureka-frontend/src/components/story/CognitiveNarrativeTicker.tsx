import React, { useMemo } from 'react';
import { useWorkStore } from '../../store/workStore';
import { buildNarrativeStages, findActiveHITLStage, type CognitiveState } from '../../domain/narrative';

const STATE_LABEL: Record<CognitiveState, string> = {
  LIVE: 'LIVE',
  RESOLVED: 'RESOLVED',
  REQUIRES_HUMAN: 'HITL',
  PENDING: 'PENDING',
};
const STATE_DOT: Record<CognitiveState, string> = {
  LIVE: '#2e8fff',
  RESOLVED: '#059669',
  REQUIRES_HUMAN: '#f59e0b',
  PENDING: '#52525b',
};

/**
 * Compact narrative ticker for the Copilot area. Shows the 13 cognitive stages as
 * a mini node-rail with a live cognitive-state highlight, so the operator can see
 * where the reasoning chain stands without leaving the Copilot.
 */
export default function CognitiveNarrativeTicker() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const stages = useMemo(() => buildNarrativeStages(activeWork), [activeWork]);

  if (!activeWork || stages.length === 0) return null;
  const hitl = findActiveHITLStage(stages);

  return (
    <div className="mb-3 p-3 rounded-lg bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)]">
      <div className="flex items-center justify-between mb-2">
        <div className="text-[9px] font-bold tracking-widest text-[var(--eureka-signal-cognitive)] uppercase">
          Cognitive Narrative
        </div>
        {hitl && (
          <span className="text-[9px] font-bold uppercase text-[var(--eureka-signal-authority)] animate-pulse">
            ● {hitl.shortTitle}
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1">
        {stages.map((s) => {
          const active = s.active || s.cognitiveState === 'REQUIRES_HUMAN';
          return (
            <span
              key={s.id}
              title={`${s.order}. ${s.title} — ${STATE_LABEL[s.cognitiveState]}`}
              className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[8px] font-mono uppercase tracking-wider ${
                active
                  ? 'bg-[var(--eureka-surface-active)] text-white'
                  : 'text-[var(--eureka-text-label)]'
              }`}
              style={active ? { outline: `1px solid ${STATE_DOT[s.cognitiveState]}` } : undefined}
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: STATE_DOT[s.cognitiveState] }}
              />
              {s.order}
            </span>
          );
        })}
      </div>
    </div>
  );
}
