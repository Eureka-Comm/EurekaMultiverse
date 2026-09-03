import React, { useState, useMemo } from 'react';
import { useWorkStore } from '../../store/workStore';
import {
  buildNarrativeStages,
  findActiveHITLStage,
  type NarrativeStage,
  type CognitiveState,
} from '../../domain/narrative';
import { buildCognitiveStory, chapterByStage } from '../../domain/cognitiveStory';
import CognitiveViewRenderer from './cognitiveViews/CognitiveViewRenderer';

/**
 * EUREKA "Dark Intelligence" Cognitive Console — Cognitive Visualization +
 * Cognitive Storytelling.
 *
 * Renders the full reasoning chain (Question → Context → Data → Discovery →
 * Prediction → Evaluation → Alternatives → Decision → Prescription → Freeze →
 * Action → Result → Learning) as ONE coherent EUREKA COGNITIVE STORY. Each stage
 * is a CHAPTER that ANSWERS A QUESTION; the question is rendered by a Cognitive
 * View (not a chart) built from REAL CanonicalWorkState data. Stages without
 * backend data render a truthful "DATA PENDING" state (no invented numbers).
 */

const STATE_META: Record<CognitiveState, { label: string; color: string; cls: string; pulse?: boolean }> = {
  LIVE: { label: 'LIVE', color: '#2e8fff', cls: 'border-[#2e8fff] text-[#2e8fff]', pulse: true },
  RESOLVED: { label: 'RESOLVED', color: '#059669', cls: 'border-[#059669] text-[#059669]' },
  REQUIRES_HUMAN: { label: 'REQUIRES HUMAN', color: '#f59e0b', cls: 'border-[#f59e0b] text-[#f59e0b]', pulse: true },
  PENDING: { label: 'DATA PENDING', color: '#52525b', cls: 'border-[#52525b] text-[#52525b]', pulse: false },
};

function StateDot({ state }: { state: CognitiveState }) {
  const meta = STATE_META[state];
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full shrink-0 ${meta.pulse ? 'animate-pulse' : ''}`}
      style={{ background: meta.color }}
      title={meta.label}
    />
  );
}

function ChapterTitle({ stage, stageNo, question }: { stage: string; stageNo: number; question: string }) {
  return (
    <div className="space-y-1 mb-3">
      <div className="text-[10px] uppercase tracking-widest text-[var(--eureka-text-label)]">
        CHAPTER {stageNo} · {stage}
      </div>
      <h3 className="text-lg font-bold tracking-tight text-[var(--eureka-text-display)]">
        <span className="text-[var(--eureka-signal-cognitive)] mr-2">›</span>
        {question}
      </h3>
    </div>
  );
}

export default function CognitiveNarrativeConsole() {
  const activeWork = useWorkStore((state) => state.activeWork);
  const stages = useMemo(() => buildNarrativeStages(activeWork), [activeWork]);
  const story = useMemo(() => buildCognitiveStory(activeWork), [activeWork]);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  if (!activeWork || stages.length === 0) return null;

  const activeHITL = findActiveHITLStage(stages);
  const defaultStage = activeHITL || stages.find((s) => s.active) || stages[0];
  const selected = stages.find((s) => s.id === selectedId) || defaultStage;
  const totalResolved = stages.filter((s) => s.cognitiveState === 'RESOLVED').length;
  const chapter = chapterByStage(activeWork, selected.id);

  const work = activeWork.work;
  const meta = STATE_META[selected.cognitiveState];

  const viewKey = chapter?.viewKey || 'LEARNING';

  return (
    <div className="fabric-panel bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)] rounded-lg overflow-hidden flex flex-col shadow-2xl">
      {/* COGNITIVE STATE HEADER */}
      <div className="px-5 py-3 border-b border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] flex items-center justify-between gap-6 flex-wrap">
        <div className="flex items-center gap-3">
          <span className="w-2.5 h-2.5 rounded-full bg-[var(--eureka-signal-cognitive)] animate-pulse" />
          <div>
            <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-text-label)] uppercase">
              EUREKA COGNITIVE STORY · COGNITIVE TABLE
            </div>
            <div className="text-sm font-mono text-[var(--eureka-text-display)]">
              {work.workId}
              <span className="text-[var(--eureka-signal-cognitive)] ml-3">{work.status}</span>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-5 text-xs">
          <div className="text-center">
            <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Chapters resolved</div>
            <div className="text-lg font-mono text-[var(--eureka-text-display)]">
              {totalResolved}/{story.length || stages.length}
            </div>
          </div>
          <div className="text-center">
            <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Active EM</div>
            <div className="font-mono text-[var(--eureka-text-section)]">{activeWork.active_em || '—'}</div>
          </div>
          <div className="text-center">
            <div className="text-[10px] uppercase text-[var(--eureka-text-label)]">Revision</div>
            <div className="font-mono text-[var(--eureka-text-section)]">{activeWork.revision}</div>
          </div>
          {activeHITL && (
            <div className="px-3 py-1 rounded bg-[var(--eureka-signal-authority)]/10 border border-[var(--eureka-signal-authority)] text-[var(--eureka-signal-authority)] text-[10px] font-bold uppercase tracking-wider animate-pulse">
              Human-in-the-loop
            </div>
          )}
        </div>
      </div>

      {/* STAGE / CHAPTER NODE RAIL */}
      <div className="px-5 py-3 border-b border-[var(--eureka-spatial-hairline)] flex items-center gap-1 overflow-x-auto">
        {stages.map((s) => {
          const m = STATE_META[s.cognitiveState];
          const isSel = selected.id === s.id;
          const chap = chapterByStage(activeWork, s.id);
          return (
            <button
              key={s.id}
              data-stage={s.id}
              onClick={() => setSelectedId(s.id)}
              className={`group flex flex-col items-center gap-1 min-w-[72px] px-2 py-1.5 rounded transition-all ${
                isSel ? 'bg-[var(--eureka-surface-active)] ring-1 ring-[var(--eureka-signal-cognitive)]' : 'hover:bg-[var(--eureka-surface-active)]'
              }`}
              title={chap?.question || s.title}
            >
              <span className={`flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider ${
                isSel ? 'text-[var(--eureka-text-display)]' : 'text-[var(--eureka-text-label)]'
              }`}>
                <StateDot state={s.cognitiveState} />
                <span>{s.order}</span>
              </span>
              <span className={`text-[11px] leading-tight text-center ${
                isSel ? 'text-white' : 'text-[var(--eureka-text-label)] group-hover:text-[var(--eureka-text-section)]'
              }`}>
                {s.shortTitle}
              </span>
            </button>
          );
        })}
      </div>

      {/* DETAIL */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 p-5">
        {/* Left: chapter framing + narrative metadata */}
        <div className="lg:col-span-1 flex flex-col gap-4">
          <ChapterTitle stage={selected.id} stageNo={selected.order} question={chapter?.question || selected.title} />

          <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">
            {selected.explanation}
          </div>

          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Cognitive state
            </div>
            <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border ${meta.cls}`}>
              {meta.label}
            </span>
          </div>

          {/* Evidence list for the chapter */}
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">Supporting evidence</div>
            {(selected.knowledgeObject.supportingEvidence.length > 0) ? (
              <ul className="space-y-1">
                {selected.knowledgeObject.supportingEvidence.map((e, i) => (
                  <li key={i} className="text-[11px] font-mono text-[var(--eureka-text-section)] flex gap-1.5">
                    <span className="text-[var(--eureka-signal-semantic)]">◆</span>
                    <span className="break-all">{e}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="text-[11px] text-[var(--eureka-text-micro)]">No supporting evidence referenced.</div>
            )}
          </div>
        </div>

        {/* Right: the Cognitive View that ANSWERS the question (not a chart) */}
        <div className="lg:col-span-2 rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-4">
          <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-3">
            Cognitive View · {viewKey}
          </div>
          <CognitiveViewRenderer state={activeWork} viewKey={viewKey} />
        </div>
      </div>
    </div>
  );
}
