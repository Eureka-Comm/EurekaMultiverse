import React, { useMemo } from 'react';
import type { HeroProps } from './types';
import { Kicker, PathNode, MicroField, Honest, Panel } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';
import { statusColor } from '../cognitiveColors';

/**
 * 07 — ACTION. The cognitive EXECUTION PATH. From the governed state we render the
 * real action_plan.actions[] as a connected sequence (step 01…0N), each node
 * carrying step_id + action + state. There is no artificial summary; the exact N
 * real steps are shown. If no governed action plan exists, the honest state is
 * shown (never an invented action / execution / external change).
 */
export function ActionChapter({ dto, graph, onSelectArtifact }: HeroProps) {
  const actionPlan = dto.actionPlan;
  const decision = dto.humanDecision;
  const execution = dto.execution;

  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);

  const selectNode = (kind: string, id?: string | null) => {
    const node =
      (id && nodeById.get(id)) ||
      graph.nodes.find((n) => n.kind === kind);
    if (node) onSelectArtifact(node);
  };

  const steps = actionPlan?.steps || [];
  const hasSteps = steps.length > 0;

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="07" title="Action" sub="Cognitive execution path" />
        <span className="ci-field-label">EM Actioner · EM Installer</span>
      </div>

      {/* Lineage entry rail: decision → action → execution */}
      <Panel title="Lineage · decision → action → execution" accent="var(--eureka-signal-cognitive)">
        <div className="flex flex-wrap items-center gap-y-3">
          <ChainNode
            label="Decision"
            present={!!(decision.decisionId || decision.selectedAlternativeId)}
            value={decision.decisionId || decision.selectedAlternativeId || 'DATA NOT AVAILABLE'}
            chip={decision.selectedAlternativeId ? <AuthorityChip authority="HUMAN_AUTHORIZED" size="sm" /> : null}
            onClick={() => selectNode('DECISION')}
          />
          <Arrow text="→" />
          <ChainNode
            label="Action plan"
            present={!!actionPlan?.id}
            value={actionPlan?.id || 'DATA NOT AVAILABLE'}
            chip={actionPlan ? <AuthorityChip authority={actionPlan.authority} size="sm" /> : null}
            onClick={() => actionPlan && selectNode('ACTION', actionPlan.id)}
          />
          <Arrow text="→" />
          <ChainNode
            label="Execution"
            present={!!execution?.id}
            value={execution ? `${execution.status} · ${execution.simulated ? 'SIMULATED' : 'EXTERNAL'}` : 'DATA NOT AVAILABLE'}
            chip={execution ? <span className="text-[9px] font-mono" style={{ color: statusColor(execution.status) }}>{execution.status}</span> : null}
            onClick={() => execution && selectNode('EXECUTION', execution.id)}
          />
        </div>
      </Panel>

      {/* EXECUTION PATH — the exact N real steps */}
      {actionPlan ? (
        <Panel title={`Execution path · ${steps.length} step${steps.length === 1 ? '' : 's'}`} accent="var(--eureka-signal-cognitive)">
          <div>
            {hasSteps ? (
              <div className="ci-path">
                {steps.map((s) => (
                  <PathNode
                    key={`${s.order}-${s.id}`}
                    order={s.order}
                    id={s.id}
                    status={s.status}
                    owner={s.owner}
                    description={s.description || 'DATA NOT AVAILABLE'}
                    onClick={() => selectNode('ACTION', actionPlan.id)}
                  />
                ))}
              </div>
            ) : (
              <div className="ci-micro">Plan exists but no steps were emitted by the backend.</div>
            )}
          </div>
        </Panel>
      ) : (
        <Honest label="No governed action plan">
          The human decision{decision.selectedAlternativeId ? ` (${decision.selectedAlternativeId})` : ''} was recorded, but no
          governed action plan, execution or external change exists for this work. Nothing is fabricated to fill the gap.
        </Honest>
      )}

      {/* Action plan micro-metadata */}
      {actionPlan && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <MicroField label="Plan id">{actionPlan.id || 'DATA NOT AVAILABLE'}</MicroField>
          <MicroField label="Selected alternative">{actionPlan.selectedAlternativeId || '—'}</MicroField>
          <MicroField label="Human decision id">{actionPlan.humanDecisionId || '—'}</MicroField>
        </div>
      )}

      {actionPlan?.selectedAlternativeId &&
        decision.selectedAlternativeId &&
        actionPlan.selectedAlternativeId !== decision.selectedAlternativeId && (
          <div className="ci-honest" style={{ borderColor: 'var(--eureka-signal-blocked)', background: 'var(--eureka-signal-blocked)/5' }}>
            <div className="ci-honest-label" style={{ color: 'var(--eureka-signal-blocked)' }}>
              ⚠ Projection conflict
            </div>
            <p className="text-[11px] text-[var(--eureka-text-section)]">
              The action plan selects <span className="font-mono">{actionPlan.selectedAlternativeId}</span> but the human decided{' '}
              <span className="font-mono">{decision.selectedAlternativeId}</span> — NOT autocorrected.
            </p>
          </div>
        )}
    </div>
  );
}

function ChainNode({
  label,
  present,
  value,
  chip,
  onClick,
}: {
  label: string;
  present: boolean;
  value: string;
  chip?: React.ReactNode;
  onClick?: () => void;
}) {
  const col = present ? 'var(--eureka-signal-cognitive)' : 'var(--eureka-text-micro)';
  return (
    <button
      onClick={onClick}
      disabled={!present}
      className="flex flex-col items-start gap-1.5 min-w-[150px] text-left hover:opacity-90 disabled:cursor-default"
      style={{ opacity: present ? 1 : 0.55 }}
    >
      <span className="text-[8px] font-mono uppercase tracking-wider text-[var(--eureka-text-micro)]">{label}</span>
      <span className="flex items-center gap-2">
        <span className="w-2.5 h-2.5 rounded-full border" style={{ borderColor: col, background: present ? `${col}` : 'transparent' }} />
        <span className="text-[11px] font-mono font-bold text-[var(--eureka-text-display)] break-all">{value}</span>
      </span>
      {chip}
    </button>
  );
}

function Arrow({ text }: { text: string }) {
  return <span className="text-[13px] text-[var(--eureka-text-technical)] px-2">{text}</span>;
}

export default ActionChapter;
