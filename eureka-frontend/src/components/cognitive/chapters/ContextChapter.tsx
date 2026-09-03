import React from 'react';
import type { HeroProps } from './types';
import { Kicker, MicroField } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';
import { statusColor } from '../cognitiveColors';

/**
 * 02 — CONTEXT. The compact metadata-rails chapter: work id/status, problem id,
 * artifact counts, execution/frozen/dating, and the recommendation-vs-decision
 * distinction. All read from the single DTO + operational work metadata.
 */
export function ContextChapter({ dto, workId, workStatus }: HeroProps) {
  const decision = dto.humanDecision;
  const hasDecision = !!decision.selectedAlternativeId;

  const counts: Array<[string, number]> = [
    ['EVIDENCE', dto.evidence.length],
    ['FINDINGS', dto.findings.length],
    ['PREDICTIONS', dto.predictions.length],
    ['ALTERNATIVES', dto.prescription?.alternatives?.length ?? 0],
  ];

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="02" title="Context" sub="Metadata rails" />
        {workStatus && (
          <span
            className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border"
            style={{ color: statusColor(workStatus), borderColor: statusColor(workStatus) }}
          >
            {workStatus}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Identity rails */}
        <div className="space-y-4">
          <div className="ci-field-label">Work identity</div>
          <MicroField label="Work id">{workId || 'DATA NOT AVAILABLE'}</MicroField>
          <MicroField label="Problem id">{dto.problem?.id || 'DATA NOT AVAILABLE'}</MicroField>
          <MicroField label="Problem authority">
            {dto.problem ? <AuthorityChip authority={dto.problem.authority} /> : <span className="text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE</span>}
          </MicroField>
        </div>

        {/* Artifact counts */}
        <div className="space-y-4">
          <div className="ci-field-label">Governed artifact counts</div>
          <div className="grid grid-cols-2 gap-3">
            {counts.map(([label, n]) => (
              <div key={label} className="border border-[var(--eureka-spatial-hairline)] rounded-lg px-3 py-2">
                <div className="text-[9px] font-mono uppercase tracking-wider text-[var(--eureka-text-label)]">{label}</div>
                <div className="text-lg font-[var(--font-display)] font-semibold text-[var(--eureka-text-display)]">{n}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <hr className="ci-divider" />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* State rails */}
        <div className="space-y-4">
          <div className="ci-field-label">Decision & governance</div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="ci-field-label">System recommendation</span>
              <span className="text-[11px] font-mono text-[var(--eureka-text-section)]">
                {dto.recommendedOption ? dto.recommendedOption : <span className="text-[var(--eureka-text-micro)]">NONE</span>}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="ci-field-label">Human decision</span>
              {hasDecision ? (
                <span className="inline-flex items-center gap-1.5">
                  <AuthorityChip authority="HUMAN_AUTHORIZED" size="sm" />
                  <span className="text-[11px] font-mono text-[var(--eureka-signal-authority)]">{decision.selectedAlternativeId}</span>
                </span>
              ) : (
                <span className="text-[11px] font-mono text-[var(--eureka-text-micro)]">DECISION PENDING</span>
              )}
            </div>
          </div>
        </div>

        {/* Trail rails */}
        <div className="space-y-4">
          <div className="ci-field-label">Execution trail</div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-2">
              <span className="ci-field-label">Execution</span>
              <span className="text-[11px] font-mono text-[var(--eureka-text-section)]">
                {dto.execution ? `${dto.execution.status} · ${dto.execution.simulated ? 'SIMULATED' : 'EXTERNAL'}` : <span className="text-[var(--eureka-text-micro)]">NOT AVAILABLE</span>}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="ci-field-label">Frozen result</span>
              <span className="text-[11px] font-mono text-[var(--eureka-text-section)]">
                {dto.frozenResult ? `${dto.frozenResult.id} · ${dto.frozenResult.status}` : <span className="text-[var(--eureka-text-micro)]">NOT AVAILABLE</span>}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="ci-field-label">Lineage length</span>
              <span className="text-[11px] font-mono text-[var(--eureka-text-section)]">{dto.lineage.length}</span>
            </div>
          </div>
        </div>
      </div>

      {dto.projectionConflict && (
        <div className="mt-2 border border-[var(--eureka-signal-blocked)] bg-[var(--eureka-signal-blocked)]/10 rounded-lg px-3 py-2 text-[10px] font-bold uppercase text-[var(--eureka-signal-blocked)]">
          ⚠ Projection conflict — action plan ≠ human decision (not autocorrected)
        </div>
      )}
    </div>
  );
}

export default ContextChapter;
