import React from 'react';
import type { NodeKind } from '../../domain/cognitiveProjectionGraph';
import { NODE_KIND_COLOR, NODE_KIND_ORDER } from './cognitiveColors';

/**
 * Primitives shared by every hero / surface of the SPATIAL COGNITIVE INSTRUMENT.
 * These carry the "scientific instrument" vocabulary: thin mono id fields, a
 * technical panel (hairline, not a rounded card), registration crosshairs, an
 * honest-state block, and the cognitive execution path node.
 */

/** A labelled technical micro-field (label above, mono value below). */
export function MicroField({
  label,
  children,
  mono = true,
}: {
  label: string;
  children: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="ci-field">
      <span className="ci-field-label">{label}</span>
      <span className={`ci-field-value ${mono ? 'mono' : ''}`}>{children || '—'}</span>
    </div>
  );
}

/** A compact labelled value used inside a row (label left, value right). */
export function MetricPair({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="ci-field-label">{label}</span>
      <span className="text-[11.5px] font-mono text-[var(--eureka-text-section)]">{children}</span>
    </div>
  );
}

/** A section kicker: numbered chapter / surface title + optional sub-line. */
export function Kicker({
  num,
  title,
  sub,
  color,
}: {
  num?: string;
  title: string;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="ci-kicker">
      {num && <span className="ci-kick-num">{num}</span>}
      <span>{title}</span>
      {sub && <span className="ci-kick-sub">{sub}</span>}
      {color && <span className="w-2 h-2 rounded-full" style={{ background: color }} />}
    </div>
  );
}

/** The status legend strip (kind → color → label) shown with the heroes. */
export function StatusLegend({
  kinds,
  caption = 'Status legend',
}: {
  kinds: NodeKind[];
  caption?: string;
}) {
  return (
    <div className="ci-legend">
      <span className="ci-field-label" style={{ alignSelf: 'center' }}>
        {caption}
      </span>
      {kinds.map((k) => (
        <span key={k} className="ci-legend-item">
          <span className="ci-legend-dot" style={{ color: NODE_KIND_COLOR[k] || '#8c959f', background: `${NODE_KIND_COLOR[k] || '#8c959f'}14` }} />
          {k}
        </span>
      ))}
    </div>
  );
}

export const ALL_KINDS: NodeKind[] = NODE_KIND_ORDER;

/** A technical panel (hairline container) with an optional title bar. */
export function Panel({
  title,
  children,
  className = '',
  accent,
}: {
  title?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  accent?: string;
}) {
  return (
    <div className={`ci-panel ${className}`} style={accent ? { borderLeftColor: accent } : undefined}>
      {title != null && <div className="ci-panel-title">{title}</div>}
      <div className="p-3">{children}</div>
    </div>
  );
}

/** An explicit honest state block (NOT EVALUATED / DATA NOT AVAILABLE / etc). */
export function Honest({
  label,
  children,
  tone = 'var(--eureka-signal-ranking)',
}: {
  label: string;
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <div className="ci-honest">
      <div className="ci-honest-label" style={{ color: tone }}>
        {label}
      </div>
      <p className="text-[11.5px] text-[var(--eureka-text-section)] leading-relaxed">{children}</p>
    </div>
  );
}

/** A registration crosshair mark (instrument feel) placed at a corner. */
export function RegisterPlus({ pos }: { pos: 'tl' | 'tr' | 'bl' | 'br' }) {
  return <span className={`ci-reg-plus ${pos}`} aria-hidden />;
}

/** The stage coordinate HUD readout (top-left of the field). */
export function CoordReadout({ children }: { children: React.ReactNode }) {
  return <span className="ci-stage-coord">{children}</span>;
}

const PATH_STATE_CLASS: Record<string, string> = {
  COMPLETED: 'is-completed',
  RUNNING: 'is-running',
  FAILED: 'is-failed',
  BLOCKED: 'is-failed',
  PENDING: 'is-pending',
};

/** One step of the cognitive execution path (01…0N), rendered as a thread node. */
export function PathNode({
  order,
  id,
  status,
  owner,
  description,
  onClick,
}: {
  order: number;
  id: string;
  status: string;
  owner?: string;
  description: string;
  onClick?: () => void;
}) {
  const cls = PATH_STATE_CLASS[status] || 'is-pending';
  return (
    <div className={`ci-path-node ${cls}`} onClick={onClick} role="button" tabIndex={0}>
      <div className="ci-path-marker">
        <span>{String(order).padStart(2, '0')}</span>
      </div>
      <div className="ci-path-body">
        <div className="ci-path-head">
          <span className="ci-path-id">{id}</span>
          {owner && <span className="ci-path-owner">{owner}</span>}
          <span className="ci-path-state" style={{ color: `var(--eureka-text-${status.toUpperCase() === 'COMPLETED' ? 'metric' : 'label'})` }}>
            {status}
          </span>
        </div>
        <div className="ci-path-desc">{description}</div>
      </div>
    </div>
  );
}

/** One labelled value cell inside a Result Moment / outcome field. */
export function MomentCell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="ci-moment-cell">
      <span className="ci-field-label">{label}</span>
      <div className="ci-moment-val">{children}</div>
    </div>
  );
}
