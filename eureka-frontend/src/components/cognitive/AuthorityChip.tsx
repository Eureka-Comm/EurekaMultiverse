import React from 'react';

/**
 * §25 — AUTHORITY SEMANTICS chip set.
 *
 * A consistent, TEXT-LABELED state chip (color + label — never color-only).
 * Every cognitive artifact surfaces its authority through this single component
 * so the meaning of a state is identical across the Knowledge Map, Provenance,
 * Inspector and Storytelling panels.
 *
 * Mapping (authority -> chip label -> color):
 *   LLM_CANDIDATE   -> CANDIDATE         (blue)
 *   VALIDATED       -> VALIDATED         (green)
 *   PYTHON_GOVERNED -> VALIDATED         (green)
 *   PUBLISHED       -> VALIDATED         (green)
 *   UNSUPPORTED     -> UNSUPPORTED       (red)
 *   NOT_EVALUATED   -> NOT_EVALUATED     (amber)
 *   HUMAN_AUTHORIZED-> HUMAN_AUTHORIZED  (violet)
 *   SIMULATED       -> SIMULATED         (teal)
 *   FROZEN          -> FROZEN            (amber/brown)
 *   PENDING         -> PENDING           (gray)
 *   GAP / missing   -> GAP               (red)
 */
export interface ChipMeta {
  label: string;
  color: string;
}

const CHIP: Record<string, ChipMeta> = {
  LLM_CANDIDATE: { label: 'CANDIDATE', color: '#0969da' },
  VALIDATED: { label: 'VALIDATED', color: '#1a7f37' },
  PYTHON_GOVERNED: { label: 'VALIDATED', color: '#1a7f37' },
  PUBLISHED: { label: 'VALIDATED', color: '#1a7f37' },
  UNSUPPORTED: { label: 'UNSUPPORTED', color: '#cf222e' },
  NOT_EVALUATED: { label: 'NOT_EVALUATED', color: '#b08800' },
  HUMAN_AUTHORIZED: { label: 'HUMAN_AUTHORIZED', color: '#8250df' },
  SIMULATED: { label: 'SIMULATED', color: '#0f6e6e' },
  FROZEN: { label: 'FROZEN', color: '#9a6700' },
  PENDING: { label: 'PENDING', color: '#8c959f' },
  GAP: { label: 'GAP', color: '#cf222e' },
};

export function chipMeta(authority: string | null | undefined): ChipMeta {
  const key = authority || 'GAP';
  return CHIP[key] || { label: String(key).toUpperCase() || 'GAP', color: '#cf222e' };
}

/** Text-labeled authority state chip (dot + label + border). */
export function AuthorityChip({
  authority,
  label,
  size = 'sm',
}: {
  authority: string | null | undefined;
  label?: string;
  size?: 'sm' | 'md';
}) {
  const meta = chipMeta(authority);
  const text = label ?? meta.label;
  const pad = size === 'md' ? 'px-2.5 py-1 text-[11px]' : 'px-2 py-0.5 text-[10px]';
  return (
    <span
      data-authority={meta.label}
      className={`inline-flex items-center gap-1.5 rounded border font-mono uppercase tracking-wider ${pad}`}
      style={{ color: meta.color, borderColor: meta.color, background: `${meta.color}14` }}
    >
      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: meta.color }} />
      {text}
    </span>
  );
}

export default AuthorityChip;
