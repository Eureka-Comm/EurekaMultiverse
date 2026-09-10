import React from 'react';
import type { CognitiveProjectionDTO } from '../../domain/cognitiveProjection';
import { AuthorityChip } from './AuthorityChip';
import { SourceTag } from './SourceTag';

/**
 * §12 — Decision visualization.
 *
 * Clear separation between:
 *   · ALTERNATIVES  (system candidates; the recommended_option is a CANDIDATE label,
 *                    never a "selected" label)
 *   · HUMAN DECISION (the human_decision selected_alternative_id, HUMAN_AUTHORIZED)
 *
 * It is impossible to confuse proposed / recommended / selected:
 *   - an alternative is marked `RECOMMENDED` (blue) iff it is the recommended_option;
 *   - the human selection is a separate, violet HUMAN DECISION panel that reads
 *     directly from `humanDecision`.
 */
export function DecisionView({ dto }: { dto: CognitiveProjectionDTO }) {
  const recommended = dto.recommendedOption;
  const humanSelection = dto.humanDecision.selectedAlternativeId;
  const alternatives = dto.prescription?.alternatives || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      {/* ALTERNATIVES (system candidates) */}
      <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface)] p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-cognitive)] uppercase">
            ALTERNATIVES · system candidates
          </div>
          <SourceTag sourceField="prescriptive_knowledge.prescriptions[].alternatives[]" em="EM Prescriptor" authority={dto.prescription?.authority} />
        </div>
        {alternatives.length ? (
          <ul className="space-y-1.5">
            {alternatives.map((a) => {
              const isRec = a.id === recommended;
              const isSelected = a.id === humanSelection;
              return (
                <li
                  key={a.id}
                  className={`flex items-start gap-2 rounded-lg border px-2.5 py-2 text-[11px] ${
                    isSelected
                      ? 'border-[var(--eureka-signal-authority)] bg-[var(--eureka-signal-authority)]/5'
                      : isRec
                        ? 'border-[var(--eureka-signal-cognitive)] bg-[var(--eureka-signal-cognitive)]/5'
                        : 'border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)]'
                  }`}
                >
                  <span className="font-mono text-[var(--eureka-text-display)] shrink-0">{a.id}</span>
                  <span className="text-[var(--eureka-text-section)] flex-1">{a.description}</span>
                  <span className="shrink-0 flex items-center gap-1">
                    {isRec && <span className="text-[9px] font-mono text-[var(--eureka-signal-cognitive)]">RECOMMENDED</span>}
                    {isSelected && <AuthorityChip authority="HUMAN_AUTHORIZED" label="SELECTED (HUMAN)" size="sm" />}
                  </span>
                </li>
              );
            })}
          </ul>
        ) : (
          <div className="text-xs text-[var(--eureka-text-micro)]">No alternatives proposed.</div>
        )}
        <div className="mt-2 text-[9px] text-[var(--eureka-text-micro)]">
          RECOMMENDED = EUREKA candidate (recommended_option). SELECTED = the human's choice (human_decision) — distinct surfaces.
        </div>
      </div>

      {/* HUMAN DECISION */}
      <div className="rounded-lg border border-[var(--eureka-signal-authority)] bg-[var(--eureka-surface-elevated)] p-4">
        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-authority)] uppercase">
            HUMAN DECISION
          </div>
          <SourceTag sourceField="human_decision" artifactId={dto.humanDecision.decisionId} em="EM Prescriptor / EM Installer" authority={dto.humanDecision.authority} />
        </div>
        {dto.humanDecision.selectedAlternativeId ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-2xl font-mono font-bold text-[var(--eureka-signal-authority)]">
                {dto.humanDecision.selectedAlternativeId}
              </span>
              <AuthorityChip authority={dto.humanDecision.authority} />
            </div>
            <div className="grid grid-cols-1 gap-2 text-xs">
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">Decision id</div>
                <div className="font-mono text-[var(--eureka-text-section)]">{dto.humanDecision.decisionId || 'DATA NOT AVAILABLE'}</div>
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">Status</div>
                <div className="font-mono text-[var(--eureka-text-section)]">{dto.humanDecision.status || 'PENDING'}</div>
              </div>
            </div>
            {dto.projectionConflict && (
              <div className="rounded border border-[var(--eureka-signal-blocked)] bg-[var(--eureka-signal-blocked)]/10 p-2 text-[10px] font-bold uppercase text-[var(--eureka-signal-blocked)]">
                ⚠ Projection conflict — the action plan selects a different alternative than the human decision. Not autocorrected.
              </div>
            )}
          </div>
        ) : (
          <div className="text-xs text-[var(--eureka-text-micro)]">
            DECISION PENDING — no human selection recorded (authority PENDING).
          </div>
        )}
      </div>
    </div>
  );
}

export default DecisionView;
