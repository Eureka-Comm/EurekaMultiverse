import React, { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { CognitiveProjectionDTO } from '../../domain/cognitiveProjection';
import { buildCognitiveProjectionGraph, type GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from './AuthorityChip';
import { statusColor } from './cognitiveColors';

/**
 * §6/§7/§31 — Storytelling as a progressive visual narrative (NOT a wall of
 * text, NOT a card grid). A one-line summary is always visible; each layer
 * reveals explanation → evidence → lineage → technical detail. Technical ids are
 * micro-metadata; the human narrative is the protagonist.
 *
 * Anti-hallucination rules (mirror LS86):
 *  - DECISION reads ONLY `humanDecision` (never `recommendedOption`).
 *  - NOT_EVALUATED / SIMULATED / FROZEN / UNSUPPORTED are preserved verbatim.
 *  - Absent fields render honestly.
 */
const DEFAULT_OPEN: Record<string, boolean> = {
  WHY: true,
  WHAT: true,
  EVIDENCE: false,
  DECISION: true,
  ACTION: false,
  RESULT: false,
};

export function StorytellingPanel({
  dto,
  onSelectArtifact,
}: {
  dto: CognitiveProjectionDTO;
  onSelectArtifact?: (a: GraphArtifact) => void;
}) {
  const [open, setOpen] = useState(DEFAULT_OPEN);
  const toggle = (k: string) => setOpen((s) => ({ ...s, [k]: !s[k] }));

  const graph = useMemo(() => buildCognitiveProjectionGraph(dto), [dto]);
  const nodeById = useMemo(() => new Map(graph.nodes.map((n) => [n.id, n])), [graph.nodes]);
  const select = (id: string) => {
    const n = nodeById.get(id);
    if (n && onSelectArtifact) onSelectArtifact(n);
  };

  const humanDecision = dto.humanDecision;
  const hasDecision = !!humanDecision.selectedAlternativeId;
  const recommended = dto.recommendedOption;
  const altById = useMemo(
    () => new Map((dto.prescription?.alternatives || []).map((a) => [a.id, a])),
    [dto.prescription?.alternatives],
  );
  const recommendedDesc = recommended ? altById.get(recommended)?.description : undefined;
  const humanDesc = hasDecision ? altById.get(humanDecision.selectedAlternativeId!)?.description : undefined;

  return (
    <div className="ci-narrative">
      {/* LAYER 0 — always-visible one-line summary */}
      <div className="pb-4">
        <div className="ci-field-label mb-1">Executive summary · one line</div>
        <div className="text-[13px] text-[var(--eureka-text-display)] leading-relaxed">{dto.question || '—'}</div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3 items-start">
          <SummaryField
            label="What EUREKA proposed (recommendation)"
            value={
              recommended ? (
                <span className="font-mono text-[var(--eureka-signal-cognitive)]">
                  {recommended}
                  {recommendedDesc ? ` · ${recommendedDesc}` : ''}
                </span>
              ) : (
                <span className="text-[var(--eureka-text-micro)]">No explicit recommendation</span>
              )
            }
          />
          <SummaryField
            label="What the human decided"
            value={
              hasDecision ? (
                <span className="font-mono text-[var(--eureka-signal-authority)]">
                  {humanDecision.selectedAlternativeId}
                  {humanDesc ? ` · ${humanDesc}` : ''}
                </span>
              ) : (
                <span className="text-[var(--eureka-text-micro)]">DECISION PENDING</span>
              )
            }
          />
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-3">
          {dto.projectionConflict && <StateChip color="var(--eureka-signal-blocked)">⚠ PROJECTION CONFLICT — not autocorrected</StateChip>}
          {dto.execution && <StateChip color="var(--eureka-text-label)">Execution · {dto.execution.status} · {dto.execution.simulated ? 'SIMULATED' : 'EXTERNAL'}</StateChip>}
          {dto.frozenResult && <StateChip color="var(--eureka-signal-freeze)">Frozen {dto.frozenResult.signature ? `· sig ${dto.frozenResult.signature}` : ''}</StateChip>}
        </div>
      </div>

      <NarrativeLayer title="Why EUREKA proposed" num="01" open={!!open.WHY} onToggle={() => toggle('WHY')} color="var(--eureka-signal-cognitive)">
        <LayerField label="Rationale" value={dto.prescription?.rationale || 'DATA NOT AVAILABLE'} />
        {dto.prescription?.criteria?.length ? (
          <LayerField label="Criteria" value={dto.prescription.criteria.join(' · ')} />
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">No evaluation criteria recorded.</div>
        )}
        {dto.prescription?.alternatives?.length ? (
          <div>
            <div className="ci-field-label mb-1">Alternatives ({dto.prescription.alternatives.length})</div>
            <ul className="space-y-1">
              {dto.prescription.alternatives.map((a) => (
                <li key={a.id} className="flex items-start gap-2 text-[11px]">
                  <button onClick={() => select(a.id)} className="font-mono text-[var(--eureka-signal-cognitive)] hover:underline">{a.id}</button>
                  <span className="text-[var(--eureka-text-section)] flex-1">{a.description}</span>
                  {a.id === recommended && <span className="text-[9px] font-mono text-[var(--eureka-signal-cognitive)]">RECOMMENDED</span>}
                  {a.id === humanDecision.selectedAlternativeId && <span className="text-[9px] font-mono text-[var(--eureka-signal-authority)]">HUMAN</span>}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </NarrativeLayer>

      <NarrativeLayer title="What was discovered & predicted" num="02" open={!!open.WHAT} onToggle={() => toggle('WHAT')} color="var(--eureka-signal-action)">
        {dto.findings.length ? (
          <ListGroup label={`Findings (${dto.findings.length})`}>
            {dto.findings.map((f) => (
              <li key={f.id} className="flex items-start gap-2 text-[11px]">
                <button onClick={() => select(f.id)} className="font-mono text-[var(--eureka-text-section)] hover:underline">{f.id}</button>
                <span className="text-[var(--eureka-text-section)] flex-1">{f.statement}</span>
                <AuthorityChip authority={f.authority} />
              </li>
            ))}
          </ListGroup>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">No findings recorded.</div>
        )}
        {dto.predictions.length ? (
          <ListGroup label={`Predictions (${dto.predictions.length})`}>
            {dto.predictions.map((p) => (
              <li key={p.id} className="flex items-start gap-2 text-[11px]">
                <button onClick={() => select(p.id)} className="font-mono text-[var(--eureka-text-section)] hover:underline">{p.id}</button>
                <span className="text-[var(--eureka-text-section)] flex-1">{p.modelType}</span>
                <span className="text-[var(--eureka-text-metric)]">{p.value == null ? 'NOT EVALUATED' : `value ${p.value}`}</span>
                <AuthorityChip authority={p.authority} />
              </li>
            ))}
          </ListGroup>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)] mt-2">No predictions recorded (NOT_EVALUATED).</div>
        )}
      </NarrativeLayer>

      <NarrativeLayer title="Evidence" num="03" open={!!open.EVIDENCE} onToggle={() => toggle('EVIDENCE')} color="var(--eureka-signal-semantic)">
        {dto.evidence.length ? (
          <ul className="space-y-1">
            {dto.evidence.map((e) => (
              <li key={e.id} className="flex items-start gap-2 text-[11px]">
                <button onClick={() => select(e.id)} className="font-mono text-[var(--eureka-text-section)] hover:underline">{e.id}</button>
                <span className="text-[var(--eureka-text-section)] flex-1 line-clamp-2">{e.sourceText || 'DATA NOT AVAILABLE'}</span>
                <AuthorityChip authority={e.grounded ? 'VALIDATED' : 'UNSUPPORTED'} />
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE — no evidence in the governed state.</div>
        )}
      </NarrativeLayer>

      <NarrativeLayer title="The human decision" num="04" open={!!open.DECISION} onToggle={() => toggle('DECISION')} color="var(--eureka-signal-authority)">
        <div className="rounded-lg border border-[var(--eureka-signal-authority)] bg-[var(--eureka-signal-authority)]/5 p-3 space-y-2">
          <div className="flex items-center justify-between gap-2">
            <div className="ci-field-label">Selected alternative (human decision)</div>
            {hasDecision ? (
              <span className="font-mono text-[var(--eureka-signal-authority)]">{humanDecision.selectedAlternativeId}</span>
            ) : (
              <span className="text-[var(--eureka-text-micro)]">DECISION PENDING</span>
            )}
            <AuthorityChip authority={humanDecision.authority} />
          </div>
          <div className="flex items-center justify-between gap-2">
            <span className="ci-field-label">Decision id</span>
            <span className="font-mono text-[11px]">{humanDecision.decisionId || 'DATA NOT AVAILABLE'}</span>
          </div>
          {humanDecision.preserved && (
            <div className="text-[10px] text-[var(--eureka-text-micro)]">Preserved from human_decision (never from recommended_option).</div>
          )}
        </div>
      </NarrativeLayer>

      <NarrativeLayer title="Action" num="05" open={!!open.ACTION} onToggle={() => toggle('ACTION')} color="var(--eureka-signal-cognitive)">
        {dto.actionPlan ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
            <div><div className="ci-field-label">Plan id</div><div className="font-mono">{dto.actionPlan.id || 'DATA NOT AVAILABLE'}</div></div>
            <div><div className="ci-field-label">Selected alternative</div><div className="font-mono">{dto.actionPlan.selectedAlternativeId || '—'}</div></div>
            <div><div className="ci-field-label">Human decision id</div><div className="font-mono">{dto.actionPlan.humanDecisionId || '—'}</div></div>
            <div className="flex items-center justify-between gap-2"><span className="ci-field-label">Authority</span><AuthorityChip authority={dto.actionPlan.authority} /></div>
          </div>
        ) : (
          <div className="text-[11px] text-[var(--eureka-text-micro)]">No action plan produced.</div>
        )}
      </NarrativeLayer>

      <NarrativeLayer title="Result" num="06" open={!!open.RESULT} onToggle={() => toggle('RESULT')} color="var(--eureka-signal-action)">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
          <div className="space-y-2">
            <div><div className="ci-field-label">Result id</div><div className="font-mono">{dto.result?.id || 'DATA NOT AVAILABLE'}</div></div>
            <div><div className="ci-field-label">Status</div><div className="font-mono">{dto.result?.status || '—'}</div></div>
          </div>
          <div className="space-y-2">
            {dto.execution && <div className="ci-field-label">Execution · {dto.execution.status} · {dto.execution.simulated ? 'SIMULATED' : 'EXTERNAL'}</div>}
            {dto.frozenResult && <div className="ci-field-label">Frozen · {dto.frozenResult.id}{dto.frozenResult.signature ? ` · sig ${dto.frozenResult.signature}` : ''} · {dto.frozenResult.status}</div>}
          </div>
        </div>
      </NarrativeLayer>
    </div>
  );
}

function SummaryField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="ci-field">
      <span className="ci-field-label">{label}</span>
      <span className="ci-field-value">{value}</span>
    </div>
  );
}

function StateChip({ color, children }: { color: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[9px] font-mono uppercase tracking-wider" style={{ color, borderColor: color }}>
      {children}
    </span>
  );
}

function LayerField({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="ci-field">
      <span className="ci-field-label">{label}</span>
      <span className="ci-field-value text-[11px]">{value || '—'}</span>
    </div>
  );
}

function ListGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mt-1">
      <div className="ci-field-label mb-1">{label}</div>
      <ul className="space-y-1">{children}</ul>
    </div>
  );
}

function NarrativeLayer({
  title,
  num,
  open,
  onToggle,
  color,
  children,
}: {
  title: string;
  num: string;
  open: boolean;
  onToggle: () => void;
  color: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`ci-narrative-layer ${open ? 'is-open' : ''}`}>
      <button onClick={onToggle} className="ci-narrative-head" aria-expanded={open}>
        <span className="text-[9px] font-mono text-[var(--eureka-text-technical)]">{num}</span>
        <span className={`ni-title ${open ? 'is-open' : ''}`}>{title}</span>
        <span className="w-1.5 h-1.5 rounded-full ml-auto" style={{ background: color }} />
        <span className="text-[10px] text-[var(--eureka-text-label)]">{open ? '−' : '+'}</span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div className="space-y-2 pb-1">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default StorytellingPanel;
