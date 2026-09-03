import React from 'react';
import type { CognitiveProjectionDTO, ActionStepProjection } from '../../domain/cognitiveProjection';
import { AuthorityChip } from './AuthorityChip';
import { statusColor } from './cognitiveColors';
import { PathNode, MomentCell, Honest } from './primitives';

/**
 * EUREKA·COGNITIVE COMMAND CENTER — the structured completion answer shown in the
 * Chat (the PRIMARY cognitive surface). It is a spatial cognitive composition, not
 * a dashboard: a left cognition axis (01…08) drives progressive disclosure
 * ANSWER → WHY → WHAT WAS FOUND → WHAT EUREKA PROPOSED → WHAT HUMAN DECIDED →
 * ACTION PLAN (as a cognitive execution path 01…0N) → EXECUTION → RESULT MOMENT.
 *
 * Built ONLY from the single `CognitiveProjectionDTO` (never raw state, never mock
 * data). Anti-hallucination: recommended_option ≠ human_decision; NOT_EVALUATED /
 * UNSUPPORTED / SIMULATED / FROZEN preserved; DATA NOT AVAILABLE / DECISION PENDING
 * / UNKNOWN shown honestly; action steps are the REAL action_plan.actions[].
 */

export type CognitiveFocus = 'DECISION' | 'ACTION' | 'RESULT';

export const ACTION_STATUS = ['PENDING', 'RUNNING', 'COMPLETED', 'FAILED', 'BLOCKED'] as const;

export function ExecutiveCognitiveAnswer({
  dto,
  onExplore,
}: {
  dto: CognitiveProjectionDTO;
  onExplore: (chapter: CognitiveFocus) => void;
}) {
  const relevant: CognitiveFocus = dto.actionPlan?.id ? 'ACTION' : dto.result?.id ? 'RESULT' : 'DECISION';

  return (
    <div className="ci-command">
      {/* Command-centre header — the instrument's faceplate */}
      <div className="ci-command-head">
        <div className="ci-command-title">
          EUREKA · Cognitive Command Center
          <span className="ci-title-rule" />
          <span className="ci-sub">single source · CognitiveProjectionDTO</span>
        </div>
      </div>

      <div className="ci-command-body">
        {/* Left cognition axis + main column */}
        <Axis n="01">
          <Section k="01" title="ANSWER · What did EUREKA conclude?" id="answer" accent="var(--eureka-signal-cognitive)">
            <div className="ci-answer-statement">{dto.result?.summary || dto.question || 'DATA NOT AVAILABLE'}</div>
            {dto.problem?.id && (
              <div className="ci-micro-row mt-2">
                <IdTag>{dto.problem.id}</IdTag>
                <AuthorityChip authority={dto.problem.authority} size="sm" />
              </div>
            )}
            {/* LS90 — never present an open research as a closed decision. */}
            {dto.whatRemainsOpen?.isOpen && (
              <div className="ci-note is-cog mt-2">
                OPEN RESEARCH OPERATION · <span className="font-mono uppercase">no decision yet</span> — EUREKA has not concluded; the human decision is still pending.
              </div>
            )}
          </Section>
        </Axis>

        <Axis n="02">
          <Section k="02" title="WHY EUREKA PROPOSED" id="why" accent="var(--eureka-signal-action)">
            {dto.prescription?.rationale ? (
              <div className="ci-prose">{dto.prescription.rationale}</div>
            ) : (
              <span className="ci-micro">DATA NOT AVAILABLE — no rationale recorded.</span>
            )}
            {dto.prescription?.criteria?.length ? (
              <div className="ci-tag-space mt-2">
                {dto.prescription.criteria.map((c, i) => (
                  <span key={i} className="ci-tag-chip">{c}</span>
                ))}
              </div>
            ) : null}
          </Section>
        </Axis>

        <Axis n="03">
          <Section k="03" title="WHAT WAS FOUND" id="found" accent="var(--eureka-signal-semantic)">
            {dto.findings.length ? (
              <div className="ci-list">
                {dto.findings.map((f) => (
                  <div key={f.id} className="ci-list-row">
                    <span className="ci-list-id">{f.id}</span>
                    <span className="ci-list-text">{f.statement}</span>
                    <span className="ci-list-state" style={{ color: statusColor(f.authority) }}>{f.status}</span>
                  </div>
                ))}
              </div>
            ) : (
              <Honest label="DATA NOT AVAILABLE">No governed findings were emitted for this work.</Honest>
            )}
          </Section>
        </Axis>

        <Axis n="04">
          <Section k="04" title="WHAT EUREKA PROPOSED · system candidates" id="proposed" accent="var(--eureka-signal-scientific)">
            {dto.prescription?.alternatives?.length ? (
              <div className="ci-list">
                {dto.prescription.alternatives.map((a) => {
                  const isRec = a.id === dto.recommendedOption;
                  return (
                    <div key={a.id} className="ci-list-row" style={isRec ? { background: 'var(--eureka-surface-selected)', borderLeft: '2px solid var(--eureka-signal-cognitive)' } : undefined}>
                      <span className="ci-list-id">{a.id}</span>
                      <span className="ci-list-text">{a.description}</span>
                      {isRec && <span className="ci-tag-chip is-rec">RECOMMENDED</span>}
                    </div>
                  );
                })}
              </div>
            ) : (
              <Honest label="DATA NOT AVAILABLE">No alternatives were proposed by EM Prescriptor.</Honest>
            )}
            <div className="ci-note">Recommended = EM Prescriptor candidate. The system never decides — the human does (below).</div>
          </Section>
        </Axis>

        <Axis n="05">
          <Section k="05" title="WHAT THE HUMAN DECIDED" id="decided" accent="var(--eureka-signal-authority)">
            {dto.humanDecision.selectedAlternativeId ? (
              <div className="ci-human-decision">
                <div className="ci-human-decision-mark" />
                <div className="ci-human-choice">{dto.humanDecision.selectedAlternativeId}</div>
                <div className="ci-human-grid">
                  <MomentCell label="decision id">{dto.humanDecision.decisionId || 'DATA NOT AVAILABLE'}</MomentCell>
                  <MomentCell label="status">{dto.humanDecision.status || 'PENDING'}</MomentCell>
                  <MomentCell label="authority"><AuthorityChip authority={dto.humanDecision.authority} size="sm" /></MomentCell>
                </div>
                {dto.humanDecision.preserved && (
                  <div className="ci-note mt-2">Preserved from human_decision — never from recommended_option.</div>
                )}
                {dto.recommendedOption && dto.recommendedOption !== dto.humanDecision.selectedAlternativeId && (
                  <div className="ci-note is-cog mt-1">EUREKA proposed <span className="font-mono">{dto.recommendedOption}</span>; the human chose differently — not autocorrected.</div>
                )}
              </div>
            ) : (
              <Honest label="DECISION PENDING" tone="var(--eureka-text-technical)">No human selection recorded (authority PENDING).</Honest>
            )}
          </Section>
        </Axis>

        <Axis n="06">
          <Section k="06" title="ACTION PLAN · cognitive execution path" id="action" accent="var(--eureka-signal-cognitive)" priority>
            {dto.actionPlan?.id ? (
              <ActionPath dto={dto} />
            ) : (
              <Honest label="ACTION PLAN · DATA NOT AVAILABLE">No governed action plan was emitted for this work.</Honest>
            )}
          </Section>
        </Axis>

        <Axis n="07">
          <Section k="07" title="EXECUTION" id="execution" accent="var(--eureka-signal-semantic)">
            {dto.execution ? (
              <div className="ci-execution">
                <IdTag>{dto.execution.id || 'EXECUTION'}</IdTag>
                <ExecutionChip status={dto.execution.status} />
                <span className="ci-micro">{dto.execution.simulated ? 'SIMULATED' : 'EXTERNAL'} · level {dto.execution.level || 'n/a'}</span>
              </div>
            ) : (
              <Honest label="DATA NOT AVAILABLE" tone="var(--eureka-text-technical)">No execution was recorded.</Honest>
            )}
          </Section>
        </Axis>

        <Axis n="08">
          <Section k="08" title="RESULT MOMENT" id="result" accent="var(--eureka-signal-action)" priority>
            {dto.result ? (
              <ResultMoment dto={dto} />
            ) : (
              <div className="ci-moment">
                <div className="ci-moment-label">Result moment · destination</div>
                <Honest label="DATA NOT AVAILABLE" tone="var(--eureka-signal-action)">No published outcome yet for this work.</Honest>
              </div>
            )}
          </Section>
        </Axis>

        <Axis n="09">
          <Section k="09" title="WHAT REMAINS OPEN" id="open" accent="var(--eureka-signal-ranking)">
            <OpenRemainder dto={dto} />
          </Section>
        </Axis>

        <ExploreButton onExplore={() => onExplore(relevant)} focus={relevant} />
      </div>
    </div>
  );
}

/* ---- composition atoms ---------------------------------------------------- */

function Axis({ n, children }: { n: string; children: React.ReactNode }) {
  return (
    <div className="ci-command-axis">
      <div className="ci-axis-num">{n}</div>
      <div className="ci-axis-rule" />
      <div className="ci-axis-content">{children}</div>
    </div>
  );
}

function Section({
  k,
  title,
  id,
  accent,
  priority,
  children,
}: {
  k: string;
  title: string;
  id: string;
  accent?: string;
  priority?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div data-cognitive-answer={id} className="ci-sect">
      <div className="ci-sect-head">
        <span className="ci-sect-k" style={{ color: priority ? accent : 'var(--eureka-text-technical)' }}>{k}</span>
        <span className="ci-sect-title">{title}</span>
        {priority && <span className="ci-sect-priority">PRIMARY</span>}
      </div>
      <div className="ci-sect-body" style={{ borderLeftColor: accent || 'var(--eureka-spatial-hairline)' }}>
        {children}
      </div>
    </div>
  );
}

function ActionPath({ dto }: { dto: CognitiveProjectionDTO }) {
  const ap = dto.actionPlan!;
  const steps: ActionStepProjection[] = ap.steps || [];
  return (
    <div>
      <div className="ci-micro-row mb-2">
        <IdTag>{ap.id}</IdTag>
        <span className="ci-micro">{ap.status}</span>
        <AuthorityChip authority={ap.authority} size="sm" />
        {ap.selectedAlternativeId && <span className="ci-micro">→ {ap.selectedAlternativeId}</span>}
        <span className="ci-micro">{`${steps.length} step${steps.length === 1 ? '' : 's'}`}</span>
      </div>
      {steps.length ? (
        <div className="ci-path">
          {steps.map((s) => (
            <PathNode
              key={`${s.order}-${s.id}`}
              order={s.order}
              id={s.id}
              status={s.status}
              owner={s.owner}
              description={s.description || 'DATA NOT AVAILABLE'}
            />
          ))}
        </div>
      ) : (
        <div className="ci-micro">Plan exists but no steps were emitted by the backend.</div>
      )}
    </div>
  );
}

function ResultMoment({ dto }: { dto: CognitiveProjectionDTO }) {
  const ex = dto.execution;
  const frozen = dto.frozenResult;
  const changed = !ex ? 'UNKNOWN' : ex.simulated ? 'SIMULATED' : 'REAL CHANGE';
  const resultStatus = dto.result?.status || '—';
  return (
    <div className="ci-moment">
      <div className="ci-moment-label">Result moment · destination</div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <IdTag>{dto.result?.id || 'DATA NOT AVAILABLE'}</IdTag>
        <span className="ci-micro">{resultStatus}</span>
        {dto.execution && <ExecutionChip status={dto.execution.status} />}
      </div>
      <div className="ci-moment-summary">{dto.result?.summary || 'DATA NOT AVAILABLE'}</div>
      <hr className="ci-divider" />
      <div className="ci-moment-grid">
        <MomentCell label="What happened">{resultStatus}</MomentCell>
        <MomentCell label="What changed">{changed}</MomentCell>
        <MomentCell label="What is frozen">
          {frozen ? `${frozen.id || ''}${frozen.signature ? ` · ${frozen.signature}` : ''}` : 'NONE'}
        </MomentCell>
        <MomentCell label="Current state">{dto.execution ? `${dto.execution.status} · ${dto.execution.simulated ? 'SIMULATED' : 'EXTERNAL'}` : 'NOT AVAILABLE'}</MomentCell>
      </div>
    </div>
  );
}

/**
 * LS90 — WHAT REMAINS OPEN. The governed leading edge of an OPEN cognitive operation
 * (an open research question that has NOT yet reached a decision). Reads ONLY the
 * single `CognitiveProjectionDTO.whatRemainsOpen` (backed by the Python-derived
 * `open_research` projection). Never invents a decision/ranking/preference; missing
 * backend projection renders an honest "DATA NOT AVAILABLE".
 */
function OpenRemainder({ dto }: { dto: CognitiveProjectionDTO }) {
  const open = dto.whatRemainsOpen;
  if (!open) {
    return <Honest label="DATA NOT AVAILABLE">No open-state projection was emitted for this work.</Honest>;
  }

  const items = open.items || [];
  const kd = open.decisionRelevantKnowledge || [];

  return (
    <div className="space-y-3">
      {/* Operation status — the governed OPEN / CLOSED signal */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="ci-tag-chip">{open.status}</span>
        <span className="ci-tag-chip">{open.operationKind}</span>
        <span className="ci-micro">
          {open.decisionReached ? 'decision reached' : 'decision still pending'}
          {open.isOpen ? ' · OPEN' : ' · CLOSED'}
        </span>
      </div>

      {/* Never present an open research as a closed decision */}
      {open.isOpen ? (
        <div className="ci-note is-cog">
          This is an <span className="font-mono uppercase">open research operation</span> — a human decision has
          <span className="font-mono"> NOT </span>yet been made. The system does not decide for the human.
        </div>
      ) : (
        <div className="ci-note">A human decision has been reached. Residual open items (if any) are listed below.</div>
      )}

      {/* The honest open items */}
      {items.length ? (
        <div className="ci-list">
          {items.map((it, i) => (
            <div key={i} className="ci-list-row">
              <span className="ci-list-id">{it.kind}</span>
              <span className="ci-list-text">{it.label}</span>
              <span className="ci-list-state font-mono" style={{ color: 'var(--eureka-text-micro)' }}>{it.sourceRef}</span>
            </div>
          ))}
        </div>
      ) : (
        <Honest label="NOT_EVALUATED" tone="var(--eureka-text-technical)">No open items recorded for this work.</Honest>
      )}

      {/* Decision-relevant knowledge (real artifacts only) */}
      {kd.length > 0 && (
        <>
          <div className="ci-micro">Decision-relevant knowledge</div>
          <div className="ci-tag-space">
            {kd.map((id) => (
              <span key={id} className="ci-tag-chip">{id}</span>
            ))}
          </div>
        </>
      )}

      {open.summary && <div className="ci-micro mt-1">{open.summary}</div>}
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const col = statusColor(status);
  return (
    <span className="shrink-0 inline-flex items-center gap-1 border rounded px-1.5 py-0.5 text-[8px] font-mono uppercase tracking-wider" style={{ color: col, borderColor: col }}>
      <span className="w-1 h-1 rounded-full" style={{ background: col }} />
      {status}
    </span>
  );
}

function ExecutionChip({ status }: { status: string }) {
  const col = statusColor(status);
  return (
    <span className="inline-flex items-center gap-1 border rounded px-1.5 py-0.5 text-[8px] font-mono uppercase tracking-wider" style={{ color: col, borderColor: col }}>
      {status}
    </span>
  );
}

function IdTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] text-[9px] font-mono text-[var(--eureka-text-section)]">
      {children}
    </span>
  );
}

function ExploreButton({ onExplore, focus }: { onExplore: () => void; focus: CognitiveFocus }) {
  const chapter = focus === 'ACTION' ? '07 · ACTION' : focus === 'RESULT' ? '08 · RESULT' : '06 · DECISION';
  return (
    <div className="ci-command-explore">
      <button
        onClick={onExplore}
        className="px-3 py-1.5 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] text-[11px] font-mono uppercase tracking-wider hover:bg-[var(--eureka-surface-active)] transition-colors"
      >
        Open spatial cognitive story → <span className="font-bold">{chapter}</span>
      </button>
    </div>
  );
}

export default ExecutiveCognitiveAnswer;
