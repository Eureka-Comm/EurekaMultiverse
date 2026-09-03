import React from 'react';
import type { CognitiveObject, CognitiveRelationship } from '../../../domain/cognitiveView';

/**
 * Shared primitives for the EUREKA "Dark Intelligence" Cognitive Views.
 * These keep the visual language consistent (control-room aesthetic) while the
 * data they render is always the REAL canonical state.
 */

export function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-cognitive)] uppercase mb-2">
      {children}
    </div>
  );
}

/** Truthful "DATA PENDING" state — never invents values. */
export function DataPendingState({ reason }: { reason: string }) {
  return (
    <div className="rounded-lg border border-dashed border-[var(--eureka-signal-blocked)] bg-[var(--eureka-surface-elevated)] p-4 flex flex-col items-start gap-1">
      <div className="text-[var(--eureka-signal-blocked)] text-xs font-bold uppercase tracking-wider">
        DATA PENDING
      </div>
      <p className="text-xs text-[var(--eureka-text-label)]">{reason}</p>
      <p className="text-[10px] text-[var(--eureka-text-micro)]">
        This view is not inventing values — the backend state has no data for it yet.
      </p>
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="text-[11px] text-[var(--eureka-text-micro)]">{text}</div>;
}

/** A standard "ASK THE COPILOT" button that dispatches a question to the narrator. */
export function AskCopilotButton({
  question,
  label = 'ASK THE COPILOT',
  variant = 'cognitive',
}: {
  question: string;
  label?: string;
  variant?: 'cognitive' | 'action' | 'authority';
}) {
  const color =
    variant === 'action'
      ? 'var(--eureka-signal-action)'
      : variant === 'authority'
        ? 'var(--eureka-signal-authority)'
        : 'var(--eureka-signal-cognitive)';
  return (
    <button
      onClick={() => window.dispatchEvent(new CustomEvent('eureka:ask-copilot', { detail: { question } }))}
      className="px-3 py-1.5 rounded border text-[11px] font-bold hover:bg-[var(--eureka-surface-active)] transition-colors shrink-0"
      style={{ borderColor: color, color }}
    >
      {label}
    </button>
  );
}

export function Pill({ label, color = 'var(--eureka-signal-cognitive)' }: { label: string; color?: string }) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-[10px] font-mono uppercase tracking-wider"
      style={{ color, borderColor: color, background: `${color}12` }}
    >
      {label}
    </span>
  );
}

export function ProvenanceList({ items }: { items: string[] }) {
  if (!items.length) return <Empty text="No provenance chain recorded." />;
  return (
    <ul className="space-y-1 border-l-2 border-[var(--eureka-spatial-hairline)] pl-3">
      {items.map((p, i) => (
        <li key={i} className="flex gap-2 text-[11px] font-mono text-[var(--eureka-text-section)]">
          <span className="text-[var(--eureka-signal-semantic)]">→</span>
          <span className="break-all">{p}</span>
        </li>
      ))}
    </ul>
  );
}

export function ObjectMeta({ obj }: { obj: CognitiveObject }) {
  const rows: Array<[string, string | string[]]> = [
    ['DATA SOURCE', obj.dataSource],
    ['TRANSFORMATION', obj.transformation],
    ['PRODUCING EM', obj.producingEM],
    ['PREDICATES / VARIABLES', obj.predicatesVariables],
    ['EVIDENCE', obj.evidence],
    ['UNCERTAINTY', obj.uncertainty],
    ['RELATIONSHIPS', obj.relationshipSet],
    ['SUPPORTS DECISION', obj.supportsDecision],
    ['PROVENANCE', obj.provenance],
    ['CONFIDENCE', obj.confidence],
  ];
  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3 space-y-3">
      <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-signal-cognitive)] uppercase">
        PRIMARY KNOWLEDGE OBJECT
      </div>
      <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed border-l-2 border-[var(--eureka-signal-cognitive)] pl-3">
        {obj.whatItRepresents}
      </div>
      {rows.map(([label, value]) => {
        const isArr = Array.isArray(value);
        return (
          <div key={label} className="text-xs">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              {label}
            </div>
            {isArr ? (
              (value as string[]).length ? (
                <ul className="space-y-0.5">
                  {(value as string[]).map((v, i) => (
                    <li key={i} className="text-[var(--eureka-text-section)] border-l border-[var(--eureka-spatial-hairline)] pl-2">
                      {v}
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-[var(--eureka-text-micro)]">—</div>
              )
            ) : (
              <div className="text-[var(--eureka-text-section)] whitespace-pre-wrap">{value || '—'}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function RelationshipList({ relationships }: { relationships: CognitiveRelationship[] }) {
  if (!relationships.length) return null;
  return (
    <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
      <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-2">
        Relationships
      </div>
      <div className="flex flex-wrap gap-1.5">
        {relationships.map((r, i) => (
          <span
            key={i}
            className="inline-flex items-center gap-1 text-[10px] font-mono px-2 py-1 rounded bg-[var(--eureka-surface)] border border-[var(--eureka-spatial-hairline)]"
          >
            <span className="text-[var(--eureka-signal-semantic)]">{r.from}</span>
            <span className="text-[var(--eureka-text-micro)]">—{r.label}→</span>
            <span className="text-[var(--eureka-text-section)]">{r.to}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/** Header strip for a Cognitive View: the question + a status chip. */
export function ViewHeader({
  question,
  stateLabel,
  stateColor,
}: {
  question: string;
  stateLabel: string;
  stateColor: string;
}) {
  return (
    <div className="flex items-center justify-between gap-3 mb-3">
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: stateColor }} />
        <h3 className="text-base font-bold tracking-tight text-[var(--eureka-text-display)]">
          <span className="text-[var(--eureka-signal-cognitive)] mr-2">›</span>
          {question}
        </h3>
      </div>
      <span
        className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
        style={{ color: stateColor, borderColor: stateColor }}
      >
        {stateLabel}
      </span>
    </div>
  );
}

/** A generic shell that renders the question + object + relationships. */
export function ViewShell({
  view,
  onAsk,
  children,
}: {
  view: {
    question: string;
    whatItShows: string;
    cognitiveState: string;
    dataPendingReason: string;
    primaryObject: CognitiveObject;
    relationships: CognitiveRelationship[];
    uncertainty: string;
    decisionSupport: string;
    provenance: string[];
  };
  onAsk?: (q: string) => void;
  children: React.ReactNode;
}) {
  const stateColor =
    view.cognitiveState === 'REQUIRES_HUMAN'
      ? '#f59e0b'
      : view.cognitiveState === 'PENDING'
        ? '#52525b'
        : '#059669';
  const stateLabel =
    view.cognitiveState === 'REQUIRES_HUMAN'
      ? 'REQUIRES HUMAN'
      : view.cognitiveState === 'PENDING'
        ? 'DATA PENDING'
        : 'RESOLVED';
  return (
    <div className="space-y-4">
      <ViewHeader question={view.question} stateLabel={stateLabel} stateColor={stateColor} />
      <div className="text-xs text-[var(--eureka-text-section)] leading-relaxed">
        {view.whatItShows}
      </div>

      {view.cognitiveState === 'PENDING' ? (
        <DataPendingState reason={view.dataPendingReason} />
      ) : (
        children
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ObjectMeta obj={view.primaryObject} />
        <div className="flex flex-col gap-4">
          <RelationshipList relationships={view.relationships} />
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Decision support
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">{view.decisionSupport || '—'}</div>
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Uncertainty
            </div>
            <div className="text-xs text-[var(--eureka-text-section)]">{view.uncertainty || 'Not quantified.'}</div>
          </div>
          <div className="rounded-lg border border-[var(--eureka-spatial-hairline)] bg-[var(--eureka-surface-elevated)] p-3">
            <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
              Provenance
            </div>
            <ProvenanceList items={view.provenance} />
          </div>
        </div>
      </div>

      {onAsk && view.cognitiveState !== 'PENDING' && (
        <div className="flex items-center gap-2">
          <button
            onClick={() => onAsk(view.question)}
            className="px-3 py-1.5 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)] text-[11px] font-bold hover:bg-[var(--eureka-surface-active)] transition-colors"
          >
            ASK THE COPILOT
          </button>
        </div>
      )}
    </div>
  );
}
