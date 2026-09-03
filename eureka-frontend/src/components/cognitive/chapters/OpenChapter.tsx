import React from 'react';
import type { HeroProps } from './types';
import { Kicker, MicroField, Honest } from '../primitives';
import { statusColor } from '../cognitiveColors';

/**
 * 00 — OPEN (leading edge). The governed representation of an OPEN cognitive
 * operation — an open research question that has NOT yet reached a decision.
 * This is the front of the cognitive trajectory: what remains OPEN (unresolved
 * questions / uncertainty / insufficient information / data-not-available / a
 * pending human decision) is surfaced HERE, in the LS89 spatial language,
 * before the closed-decision chapters (01…08). It reads ONLY the single
 * `CognitiveProjectionDTO.whatRemainsOpen` (the Python-derived `open_research`
 * projection) — never a fabricated decision, never a recommendation, never a
 * ranking, never a preference.
 */
const ITEM_COLOR: Record<string, string> = {
  UNRESOLVED_QUESTION: 'var(--eureka-signal-semantic)',
  UNCERTAINTY: 'var(--eureka-signal-ranking)',
  LIMITATION: 'var(--eureka-signal-cognitive)',
  CONTRADICTION: 'var(--eureka-signal-blocked)',
  INSUFFICIENT_INFORMATION: 'var(--eureka-signal-blocked)',
  INSUFFICIENT_DATA: 'var(--eureka-signal-blocked)',
  DATA_NOT_AVAILABLE: 'var(--eureka-text-technical)',
  MISSING_EVIDENCE: 'var(--eureka-signal-semantic)',
  NOT_EVALUATED: 'var(--eureka-text-technical)',
  PENDING_HUMAN_DECISION: 'var(--eureka-signal-authority)',
  PENDING_HUMAN_INPUT: 'var(--eureka-signal-authority)',
};

export function OpenChapter({ dto, workStatus }: HeroProps) {
  const open = dto.whatRemainsOpen;
  const items = open?.items ?? [];
  const kd = open?.decisionRelevantKnowledge ?? [];

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="00" title="Open" sub="What remains open" color="var(--eureka-signal-ranking)" />
        {workStatus && (
          <span
            className="inline-flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border"
            style={{ color: statusColor(workStatus), borderColor: statusColor(workStatus) }}
          >
            {workStatus}
          </span>
        )}
      </div>

      {!open ? (
        <Honest label="DATA NOT AVAILABLE">No open-state projection was emitted for this work.</Honest>
      ) : (
        <>
          {/* The open / closed signal — governed, never a decision */}
          <div className="flex-1 flex flex-col justify-center">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--eureka-signal-ranking)] mb-3">
              Leading edge · cognitive operation state
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="ci-tag-chip">{open.status}</span>
              <span className="ci-tag-chip">{open.operationKind}</span>
              <span className="text-[11px] font-mono text-[var(--eureka-text-section)]">
                {open.decisionReached ? 'decision reached' : 'decision still pending'} · {open.isOpen ? 'OPEN' : 'CLOSED'}
              </span>
            </div>
            <p className="text-[13px] text-[var(--eureka-text-label)] mt-3 max-w-[720px] leading-relaxed">
              {open.isOpen
                ? 'This is an open research operation — a human decision has NOT yet been made. The system does not decide for the human; below is the honest leading edge of what remains open.'
                : 'This operation has reached a human decision. Residual open items (if any) are listed below.'}
            </p>
            <div className="mt-6 h-px w-24" style={{ background: 'var(--eureka-signal-ranking)' }} />
          </div>

          {/* The honest open items */}
          <div className="mt-4 pt-4 border-t border-[var(--eureka-spatial-hairline)]">
            <div className="ci-field-label mb-2">What remains open · {items.length} item(s)</div>
            {items.length ? (
              <div className="space-y-1.5">
                {items.map((it, i) => (
                  <div key={i} className="flex items-start gap-3 py-1.5 border-b border-[var(--eureka-spatial-hairline)]">
                    <span
                      className="shrink-0 mt-0.5 w-2 h-2 rounded-full"
                      style={{ background: ITEM_COLOR[it.kind] || 'var(--eureka-signal-ranking)' }}
                    />
                    <span className="shrink-0 w-40 text-[9px] font-mono uppercase tracking-wider text-[var(--eureka-text-micro)]">{it.kind}</span>
                    <span className="flex-1 text-[12.5px] text-[var(--eureka-text-section)] leading-relaxed">{it.label}</span>
                    <span className="shrink-0 text-[9px] font-mono text-[var(--eureka-text-micro)]">{it.sourceRef}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Honest label="NOT_EVALUATED" tone="var(--eureka-text-technical)">No open items recorded for this work.</Honest>
            )}
          </div>

          {/* Decision-relevant knowledge (real artifacts only) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div className="space-y-4">
              <div className="ci-field-label">Decision-relevant knowledge</div>
              {kd.length ? (
                <div className="ci-tag-space">
                  {kd.map((id) => (
                    <span key={id} className="ci-tag-chip">{id}</span>
                  ))}
                </div>
              ) : (
                <span className="text-[11px] font-mono text-[var(--eureka-text-micro)]">NONE</span>
              )}
            </div>
            <div className="space-y-4">
              <div className="ci-field-label">Decision point</div>
              <MicroField label="Decision status">
                {open.decisionReached ? 'REACHED' : 'PENDING'}
              </MicroField>
              <MicroField label="Provenance">
                <span className="text-[9px] font-mono">open_research · Python-derived (governed, not LLM)</span>
              </MicroField>
            </div>
          </div>

          {open.summary && (
            <div className="mt-4 text-[11.5px] text-[var(--eureka-text-label)]">{open.summary}</div>
          )}
        </>
      )}
    </div>
  );
}

export default OpenChapter;
