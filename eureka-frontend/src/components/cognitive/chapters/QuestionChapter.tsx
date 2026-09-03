import React from 'react';
import type { HeroProps } from './types';
import { MicroField, Kicker } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';

/**
 * 01 — QUESTION. The cognitive framing: the governing objective as the hero, not
 * a card. Reads ONLY from `dto.question` + `dto.problem` (the single DTO). If the
 * problem/governance is absent it renders honestly (never invents framing).
 */
export function QuestionChapter({ dto }: HeroProps) {
  const problem = dto.problem;
  const question = dto.question;
  const evidenceCount = dto.evidence.length;
  const findingsCount = dto.findings.length;
  const predictionsCount = dto.predictions.length;

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="01" title="The Question" sub="Cognitive framing" />
        {problem && <AuthorityChip authority={problem.authority} />}
      </div>

      {/* Governing objective as the primary instrument readout */}
      <div className="flex-1 flex flex-col justify-center">
        <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--eureka-signal-cognitive)] mb-3">
          Governing objective
        </div>
        <h1 className="font-[var(--font-display)] text-2xl md:text-[28px] leading-[1.25] text-[var(--eureka-text-display)] max-w-[760px]">
          {question || 'DATA NOT AVAILABLE'}
        </h1>
        {problem?.objective && problem.objective !== question && (
          <p className="text-[12px] text-[var(--eureka-text-label)] mt-2 max-w-[760px]">{problem.objective}</p>
        )}
        <div className="mt-6 h-px w-24" style={{ background: 'var(--eureka-signal-cognitive)' }} />
      </div>

      {/* Framing metadata rails */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-5 mt-4 pt-4 border-t border-[var(--eureka-spatial-hairline)]">
        <MicroField label="Problem id">{problem?.id || 'DATA NOT AVAILABLE'}</MicroField>
        <MicroField label="Authority">
          {problem ? (
            <AuthorityChip authority={problem.authority} />
          ) : (
            <span className="text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE</span>
          )}
        </MicroField>
        <MicroField label="Evidence">{evidenceCount}</MicroField>
        <MicroField label="Findings">{findingsCount}</MicroField>
      </div>

      {predictionsCount === 0 && evidenceCount === 0 && findingsCount === 0 && (
        <div className="ci-empty mt-6 border-t border-dashed border-[var(--eureka-spatial-hairline)] pt-4">
          <div className="text-xs font-bold uppercase tracking-widest text-[var(--eureka-signal-semantic)]">Data pending</div>
          <p className="text-xs text-[var(--eureka-text-label)]">No governed artifacts emitted for this work yet.</p>
        </div>
      )}
    </div>
  );
}

export default QuestionChapter;
