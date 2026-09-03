import React, { useMemo, useState } from 'react';
import type { CanonicalWorkState } from '../../../domain/canonicalSchema';
import { buildWhySelectedView } from '../../../domain/cognitiveStory';
import {
  getPredictive,
  getPrescriptive,
  getSelectedAlternativeId,
  getApplicableCriteria,
  getPrescriptionConstraints,
  getAcfl,
} from '../../../domain/cognitiveView';
import { DataPendingState, ObjectMeta, ProvenanceList, RelationshipList, SectionLabel, AskCopilotButton } from './primitives';

/**
 * WHY <selected alternative>? — the flagship provenance view.
 *
 * Renders the real chain Evidence → Predictions → Evaluation → selected
 * alternative → Prescription and lets the operator ask "why this one?" against
 * any alternative. Reads ONLY real fields; shows "DATA PENDING" when absent.
 */

const chainColors: Record<string, string> = {
  evidence: 'var(--eureka-signal-semantic)',
  predictions: 'var(--eureka-signal-cognitive)',
  evaluation: 'var(--eureka-signal-scientific)',
  selected: 'var(--eureka-signal-action)',
  prescription: 'var(--eureka-signal-authority)',
};

type ChainStep = { key: string; title: string; items: string[]; color: string; note?: string };

function ChainStepCard({ step }: { step: ChainStep }) {
  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 rounded-full" style={{ background: step.color }} />
        <div className="text-[10px] font-bold uppercase tracking-widest" style={{ color: step.color }}>
          {step.title}
        </div>
      </div>
      {step.items.length ? (
        <ul className="space-y-1">
          {step.items.map((it, i) => (
            <li key={i} className="text-[11px] text-[var(--eureka-text-section)] border-l border-[var(--eureka-spatial-hairline)] pl-2 break-all">
              {it}
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-[11px] text-[var(--eureka-text-micro)]">—</div>
      )}
      {step.note && <div className="text-[10px] text-[var(--eureka-text-micro)] mt-2">{step.note}</div>}
    </div>
  );
}

export default function ViewWhySelected({ state }: { state: CanonicalWorkState }) {
  const view = useMemo(() => buildWhySelectedView(state), [state]);
  const presc = getPrescriptive(state);
  const prescriptions: any[] = presc.prescriptions || [];
  const prescription = prescriptions[0];
  const alternatives: any[] = prescription?.alternatives || [];
  const selectedId = getSelectedAlternativeId(state);
  const [activeAlt, setActiveAlt] = useState<string | null>(null);

  const activeAltObj = useMemo(() => {
    if (!activeAlt) return null;
    return alternatives.find((a) => a.alternative_id === activeAlt) || null;
  }, [activeAlt, alternatives]);

  if (view.cognitiveState === 'PENDING') {
    return (
      <DataPendingState reason={view.dataPendingReason} />
    );
  }

  if (!prescription) {
    return <DataPendingState reason="No validated prescription is available in the backend state." />;
  }

  // Build the real chain from the selected (or active) alternative.
  const pricing = activeAltObj || prescription.selected_alternative;
  const predictions = getPredictive(state).predictions || [];
  const selectedPredictionRefs: string[] = prescription.supporting_predictions || [];
  const predictionLabels = selectedPredictionRefs.length
    ? selectedPredictionRefs
    : predictions.map((p: any) => p.prediction_id).slice(0, 5);
  const knowledgeRefs: string[] = prescription.supporting_knowledge || [];
  const criteria: any[] = getApplicableCriteria(state);
  const hardConstraints: string[] = getPrescriptionConstraints(state);
  const acfl = getAcfl(state);
  const normalizedScores = acfl.normalized_scores || {};
  const hasPerAlternativeScores = Object.keys(normalizedScores).length > 0;

  const chain: ChainStep[] = [
    {
      key: 'evidence',
      title: 'EVIDENCE',
      color: chainColors.evidence,
      items: prescription.evidence_refs || [],
    },
    {
      key: 'predictions',
      title: 'PREDICTIONS',
      color: chainColors.predictions,
      items: predictionLabels,
      note:
        predictions.length === 0 && selectedPredictionRefs.length === 0
          ? 'The prescription references NO prediction objects (predictive_knowledge.status = UNAVAILABLE). Uncertainty is unbounded.'
          : 'Referenced by the prescription; supporting_predictions.',
    },
    {
      key: 'evaluation',
      title: 'EVALUATION',
      color: chainColors.evaluation,
      items: criteria.map((c) => `${c.target || c.description}${c.direction ? ` (${c.direction})` : ''}${c.weight != null ? ` w=${c.weight}` : ''}${c.threshold != null ? ` thr=${c.threshold}` : ''}`),
      note: hasPerAlternativeScores
        ? 'Per-alternative normalized scores present.'
        : 'The backend emits NO per-alternative numeric score here — evaluation is carried by these real criterion weights/thresholds, not a fabricated score.',
    },
    {
      key: 'selected',
      title: pricing ? pricing.alternative_id : 'ALTERNATIVE',
      color: chainColors.selected,
      items: pricing ? [
        ...(pricing.description ? [pricing.description] : []),
        ...(pricing.expected_effects || []).map((e: string) => `+ ${e}`),
        ...(pricing.constraints || []).map((c: string) => `— ${c}`),
      ] : ['No selected alternative.'],
    },
    {
      key: 'prescription',
      title: 'PRESCRIPTION',
      color: chainColors.prescription,
      items: [
        prescription.prescription_id,
        [prescription.decision_rule?.status, prescription.decision_rule?.rule_type, prescription.decision_rule?.authority].filter(Boolean).join(' · ') || `Decision rule: UNSPECIFIED`,
        prescription.rationale || '',
      ],
    },
  ];

  const askWhy = (altId: string) => {
    setActiveAlt(altId);
  };

  const askCopilot = (q: string, altId?: string) => {
    window.dispatchEvent(
      new CustomEvent('eureka:ask-copilot', {
        detail: { question: altId ? `${q} (${altId})` : q },
      }),
    );
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">{view.whatItShows}</div>
        <button
          onClick={() => askCopilot(view.question, activeAlt || undefined)}
          className="px-3 py-1.5 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] text-[11px] font-bold hover:bg-[var(--eureka-surface-active)] transition-colors shrink-0"
        >
          ASK THE COPILOT
        </button>
      </div>

      {/* Choose which alternative to explain */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)]">Why this one?</span>
        {alternatives.map((a) => {
          const isSel = a.alternative_id === selectedId;
          const isActive = a.alternative_id === (activeAlt || selectedId);
          return (
            <span key={a.alternative_id} className="flex items-center gap-1">
              <button
                onClick={() => askWhy(a.alternative_id)}
                className={`px-2.5 py-1 rounded text-[10px] font-mono uppercase tracking-wider border transition-colors ${
                  isActive
                    ? isSel
                      ? 'border-[var(--eureka-signal-action)] text-[var(--eureka-signal-action)] bg-[#0f1c15]'
                      : 'border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] bg-[var(--eureka-surface-active)]'
                    : 'border-[var(--eureka-spatial-hairline)] text-[var(--eureka-text-label)] hover:text-[var(--eureka-text-section)]'
                }`}
              >
                {a.alternative_id}
                {isSel && ' · SELECTED'}
              </button>
              <button
                onClick={() => askCopilot(`¿qué habría pasado con ${a.alternative_id}?`, a.alternative_id)}
                title={`Ask the Copilot what would have happened with ${a.alternative_id}`}
                className="w-5 h-5 rounded text-[9px] font-bold border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] hover:bg-[var(--eureka-surface-active)]"
              >
                ?
              </button>
            </span>
          );
        })}
      </div>

      {/* The chain */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-3">
        {chain.map((step) => (
          <ChainStepCard key={step.key} step={step} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Rationale
            </div>
            <div className="text-xs text-[var(--eureka-text-section)] whitespace-pre-wrap">
              {prescription.rationale || '—'}
            </div>
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Decision rule / authority
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">
              {prescription.decision_rule?.status || 'None'}
              {prescription.decision_rule?.rule_type ? ` · ${prescription.decision_rule.rule_type}` : ''}
              {prescription.decision_rule?.authority ? ` · ${prescription.decision_rule.authority}` : ''}
              {' · '}{prescription.authority || 'N/A'}
            </div>
            {prescription.decision_rule?.description && (
              <div className="text-[10px] text-[var(--eureka-text-micro)] mt-1">{prescription.decision_rule.description}</div>
            )}
          </div>
          {criteria.length > 0 && (
            <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
                Real criteria evaluation ({criteria.length})
              </div>
              <ul className="space-y-1.5">
                {criteria.map((c) => (
                  <li key={c.criterion_id || c.target || c.description} className="text-[11px]">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-[var(--eureka-text-section)]">{c.target || c.description}</span>
                      {c.direction && (
                        <span className={`text-[9px] font-mono ${c.direction === 'MAXIMIZE' ? 'text-[var(--eureka-signal-action)]' : 'text-[var(--eureka-signal-blocked)]'}`}>
                          {c.direction}
                        </span>
                      )}
                      {c.weight != null && (
                        <span className="text-[9px] font-mono text-[var(--eureka-text-metric)]">w={c.weight}</span>
                      )}
                      {c.threshold != null && (
                        <span className="text-[9px] font-mono text-[var(--eureka-text-micro)]">thr={c.threshold}</span>
                      )}
                    </div>
                    {c.authority && (
                      <div className="text-[9px] text-[var(--eureka-text-micro)]">{c.authority}</div>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {hardConstraints.length > 0 && (
            <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
                Hard constraints
              </div>
              <ul className="space-y-1">
                {hardConstraints.map((c, i) => (
                  <li key={i} className="text-[11px] text-[var(--eureka-text-section)] flex gap-1.5">
                    <span className="text-[var(--eureka-signal-blocked)]">▣</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {knowledgeRefs.length > 0 && (
            <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
              <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
                Supporting knowledge
              </div>
              <ul className="space-y-1">
                {knowledgeRefs.map((k, i) => (
                  <li key={i} className="text-[11px] text-[var(--eureka-text-section)] border-l border-[var(--eureka-spatial-hairline)] pl-2">
                    {k}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Provenance
            </div>
            <ProvenanceList items={prescription.provenance || []} />
          </div>
        </div>
      </div>
    </div>
  );
}
