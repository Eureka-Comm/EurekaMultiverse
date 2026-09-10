import React from 'react';
import type { GraphArtifact } from '../../domain/cognitiveProjectionGraph';
import { AuthorityChip } from './AuthorityChip';
import { SourceTag } from './SourceTag';

/**
 * §23/§24 — INSPECTOR. An on-demand contextual side panel: artifact / id / type /
 * status / authority / producing-EM / provenance / evidence. It never occupies the
 * primary space (only appears on selection). Driven ONLY by `GraphArtifact`
 * values from `buildCognitiveProjectionGraph` (fed exclusively by the single
 * `CognitiveProjectionDTO`). Missing fields render honestly — never invented.
 */
function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="text-xs">
      <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-0.5">
        {label}
      </div>
      <div className="text-[var(--eureka-text-section)] break-words whitespace-pre-wrap">{value}</div>
    </div>
  );
}

export function ArtifactDetail({ a, compact }: { a: GraphArtifact; compact?: boolean }) {
  return (
    <div className="ci-panel p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-[var(--eureka-signal-semantic)]">◆</span>
          <span className="font-mono text-[12px] font-bold text-[var(--eureka-text-display)] truncate" title={a.id}>
            {a.id}
          </span>
          <span className="text-[9px] font-mono uppercase text-[var(--eureka-text-micro)]">{a.kind}</span>
        </div>
        <AuthorityChip authority={a.authority} size={compact ? 'sm' : 'md'} />
      </div>

      <div className="text-[11px] text-[var(--eureka-text-section)] border-l-2 border-[var(--eureka-spatial-hairline)] pl-2">
        {a.description || 'DATA NOT AVAILABLE'}
      </div>

      {/* Recommendation vs Human decision — real booleans only, never conflated */}
      {(a.recommended || a.humanSelected) && (
        <div className="flex flex-wrap gap-1 pt-0.5">
          {a.recommended && (
            <span className="text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border border-[var(--eureka-signal-cognitive)] text-[var(--eureka-signal-cognitive)]">
              Recommending · EUREKA
            </span>
          )}
          {a.humanSelected && (
            <span className="text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 rounded border border-[var(--eureka-signal-semantic)] text-[var(--eureka-signal-semantic)]">
              Human selected
            </span>
          )}
        </div>
      )}
      {a.kind === 'DECISION' && a.authority === 'HUMAN_AUTHORIZED' && (
        <div className="text-[9px] font-mono uppercase tracking-wider text-[var(--eureka-text-label)]">
          Authority: human decision
        </div>
      )}

      {/* Honest real computed/typological data when present (never synthesized) */}
      {(a.modelType != null || a.numericValue != null || a.stepCount != null) && (
        <div className="grid grid-cols-1 gap-2 pt-1">
          {a.modelType != null && <Row label="Model" value={<span className="font-mono">{a.modelType}</span>} />}
          {a.numericValue != null && <Row label="Value" value={<span className="font-mono">{a.numericValue}</span>} />}
          {a.stepCount != null && <Row label="Steps" value={<span className="font-mono">{a.stepCount}</span>} />}
        </div>
      )}

      {!compact && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
          <Row label="Status" value={<span className="font-mono">{a.status || '—'}</span>} />
          <Row label="Producing EM" value={<span className="font-mono">{a.em || '—'}</span>} />
          <Row label="Uncertainty" value={a.uncertainty || 'DATA NOT AVAILABLE'} />
          <Row
            label="Evidence"
            value={
              a.evidence?.length ? (
                <span className="font-mono">{a.evidence.join(', ')}</span>
              ) : (
                <span className="text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE</span>
              )
            }
          />
        </div>
      )}

      <div className="pt-1">
        <div className="text-[10px] uppercase tracking-wider text-[var(--eureka-text-label)] mb-1">
          Provenance
        </div>
        {a.provenance?.length ? (
          <ul className="space-y-0.5 border-l-2 border-[var(--eureka-spatial-hairline)] pl-2">
            {a.provenance.map((p, i) => (
              <li key={i} className="text-[10px] font-mono text-[var(--eureka-text-section)] break-all">
                → {p}
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-[10px] text-[var(--eureka-text-micro)]">DATA NOT AVAILABLE</div>
        )}
      </div>

      <div className="pt-1">
        <SourceTag sourceField={a.sourceField} artifactId={a.artifactId} em={a.em} authority={a.authority} />
      </div>
    </div>
  );
}

export function Inspector({
  title,
  emRole,
  artifacts,
  emptyText,
}: {
  title?: string;
  emRole?: string;
  artifacts: GraphArtifact[];
  emptyText?: string;
}) {
  const list = artifacts || [];
  const heading = title || (emRole ? `EM INSPECT · ${emRole}` : 'INSPECTOR');
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-[10px] font-bold tracking-widest text-[var(--eureka-text-label)] uppercase">
          {heading}
        </div>
        {emRole && <span className="text-[10px] font-mono text-[var(--eureka-signal-semantic)]">{emRole}</span>}
      </div>
      {list.length ? (
        <div className="grid grid-cols-1 gap-2">
          {list.map((a) => (
            <ArtifactDetail key={a.id} a={a} />
          ))}
        </div>
      ) : (
        <div className="ci-honest" style={{ borderColor: 'var(--eureka-spatial-hairline)', background: 'var(--eureka-surface-elevated)' }}>
          <div className="ci-honest-label" style={{ color: 'var(--eureka-text-label)' }}>DATA NOT AVAILABLE</div>
          <p className="text-[11px] text-[var(--eureka-text-label)]">{emptyText || 'No governed artifacts for this selection.'}</p>
        </div>
      )}
    </div>
  );
}

export default Inspector;
