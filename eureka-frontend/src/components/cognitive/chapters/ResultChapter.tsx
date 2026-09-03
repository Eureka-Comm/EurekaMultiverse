import React, { useMemo } from 'react';
import type { HeroProps } from './types';
import { Kicker, MomentCell, Honest } from '../primitives';
import { AuthorityChip } from '../AuthorityChip';
import { statusColor } from '../cognitiveColors';

/**
 * 08 — RESULT. The OUTCOME FIELD / RESULT MOMENT — the destination of the
 * cognitive trajectory. It answers, from the real state, WHAT HAPPENED / WHAT
 * CHANGED / CURRENT STATE / WHAT IS FROZEN / NEXT. Honest by construction:
 *   · result        -> published outcome (PUBLISHED)
 *   · execution     -> SIMULATED stays SIMULATED (never EXECUTED)
 *   · frozenResult  -> FROZEN (signature)
 *   · absent data   -> DATA NOT AVAILABLE / UNKNOWN (never invented)
 */
export function ResultChapter({ dto, graph, onSelectArtifact }: HeroProps) {
  const result = dto.result;
  const execution = dto.execution;
  const frozen = dto.frozenResult;
  const decision = dto.humanDecision;

  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const select = (id?: string | null, kind?: string) => {
    const node = (id && nodeById.get(id)) || graph.nodes.find((n) => n.kind === kind);
    if (node) onSelectArtifact(node);
  };

  const changed = !execution ? 'UNKNOWN' : execution.simulated ? 'SIMULATED' : 'REAL CHANGE';

  return (
    <div className="ci-hero">
      <div className="ci-hero-head">
        <Kicker num="08" title="Result" sub="Outcome field" />
        {result && <AuthorityChip authority="PUBLISHED" />}
      </div>

      {/* Outcome state matrix — four real axes of the outcome */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <OutcomeCell label="What changed" present={!!execution} value={<span className="text-[var(--eureka-text-micro)]">{changed}</span>} />
        <OutcomeCell
          label="Executed"
          present={!!execution}
          value={
            execution ? (
              <span className="font-mono font-bold" style={{ color: statusColor(execution.status) }}>
                {execution.status} · {execution.simulated ? 'SIMULATED' : 'EXTERNAL'}
              </span>
            ) : (
              <span className="text-[var(--eureka-text-micro)]">NOT EXECUTED</span>
            )
          }
          onClick={() => execution && select(execution.id, 'EXECUTION')}
        />
        <OutcomeCell
          label="Simulated"
          present={!!execution?.simulated}
          value={
            execution?.simulated ? (
              <span className="font-mono font-bold text-[var(--eureka-signal-semantic)]">SIMULATED</span>
            ) : (
              <span className="text-[var(--eureka-text-micro)]">NO</span>
            )
          }
          onClick={() => execution && select(execution.id, 'EXECUTION')}
        />
        <OutcomeCell
          label="Frozen"
          present={!!frozen}
          value={
            frozen ? (
              <span className="font-mono font-bold" style={{ color: statusColor(frozen.status) }}>{frozen.status}</span>
            ) : (
              <span className="text-[var(--eureka-text-micro)]">NO</span>
            )
          }
          onClick={() => frozen && select(frozen.id, 'FROZEN')}
        />
      </div>

      {/* RESULT MOMENT — the destination */}
      {result ? (
        <div className="ci-moment flex-1">
          <div className="ci-moment-label">Result moment · destination</div>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <button onClick={() => select(result.id, 'RESULT')} className="text-left">
              <span className="font-mono text-[13px] font-bold text-[var(--eureka-text-display)]">{result.id}</span>
            </button>
            <span className="text-[9px] font-mono text-[var(--eureka-text-label)]">
              {result.status} · {decision.selectedAlternativeId ? `human decided ${decision.selectedAlternativeId}` : 'no decision'}
            </span>
          </div>
          <div className="ci-moment-summary">{result.summary || 'DATA NOT AVAILABLE'}</div>
          <hr className="ci-divider" />
          <div className="ci-moment-grid">
            <MomentCell label="What happened">{result.status}</MomentCell>
            <MomentCell label="What changed">{changed}</MomentCell>
            <MomentCell label="Current state">{execution ? `${execution.status} · ${execution.simulated ? 'SIMULATED' : 'EXTERNAL'}` : 'NOT AVAILABLE'}</MomentCell>
            <MomentCell label="Next">{execution?.simulated ? 'SIMULATION COMPLETE' : 'REAL CHANGE PENDING'}</MomentCell>
          </div>
        </div>
      ) : (
        <Honest label="DATA NOT AVAILABLE" tone="var(--eureka-signal-action)">
          No published outcome for this work yet. The trajectory has not reached a result moment.
        </Honest>
      )}

      {/* Frozen result metadata */}
      {frozen && (
        <div className="ci-honest" style={{ borderColor: 'var(--eureka-signal-freeze)', background: 'color-mix(in srgb, var(--eureka-signal-freeze) 6%, var(--eureka-surface))' }}>
          <div className="ci-honest-label" style={{ color: 'var(--eureka-signal-freeze)' }}>
            Frozen result · {frozen.id}
          </div>
          <p className="text-[11px] font-mono text-[var(--eureka-text-section)] mt-1">
            signature {frozen.signature || 'DATA NOT AVAILABLE'} · {frozen.status}
          </p>
        </div>
      )}
    </div>
  );
}

function OutcomeCell({
  label,
  present,
  value,
  onClick,
}: {
  label: string;
  present: boolean;
  value: React.ReactNode;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`border px-3 py-2.5 text-left transition-colors ${present ? 'border-[var(--eureka-spatial-hairline)]' : 'border-dashed border-[var(--eureka-text-micro)]/50'} ${onClick ? 'hover:border-[var(--eureka-signal-cognitive)]' : 'cursor-default'}`}
    >
      <div className="ci-field-label mb-1">{label}</div>
      <div className="text-[12px]">{value}</div>
    </button>
  );
}

export default ResultChapter;
