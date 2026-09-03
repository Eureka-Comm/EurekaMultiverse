import React from 'react';

/**
 * §30 — CONNECTIVITY / source annotation.
 *
 * Every visual datum must answer "which canonical field does this come from?".
 * This tag renders the chain (canonical field → artifact id → EM → authority).
 * It is intended as a DEV-only affordance (rendered subtly, gated by VITE/DOM
 * so it never pollutes a production view). If a component cannot identify its
 * source field it labels `DATA_SOURCE_NOT_IDENTIFIED` — never a fabricated one.
 */
export function SourceTag({
  sourceField,
  artifactId,
  em,
  authority,
}: {
  sourceField: string;
  artifactId?: string | null;
  em?: string;
  authority?: string | null;
}) {
  const field = sourceField || 'DATA_SOURCE_NOT_IDENTIFIED';
  const chain: string[] = [field, artifactId || '—', em || '—', authority || '—'];
  return (
    <span
      data-source-field={field}
      data-artifact-id={artifactId || '—'}
      data-em={em || '—'}
      data-authority={authority || '—'}
      className="inline-flex items-center gap-1 text-[9px] font-mono text-[var(--eureka-text-micro)] bg-[var(--eureka-surface-elevated)] border border-[var(--eureka-spatial-hairline)] rounded px-1.5 py-0.5"
      title={`SOURCE → ${chain.join(' → ')}`}
    >
      <span className="text-[var(--eureka-signal-semantic)]">ⓘ</span>
      <span className="break-all">{field}</span>
    </span>
  );
}

export default SourceTag;
