// CONSTELACIÓN — cognitive-trace authority classification. PURE, provider-independent.
//
// The real EUREKA trace (`cognitive_trace` / `runtime_metadata`) records the MODEL that served each
// EM invocation — e.g. `deepseek-chat` (DeepSeek), `qwen3:8b` / `deepseek-r1:14b` (Ollama),
// `ACFL_DETERMINISTIC` (the mathematical predictor). It does NOT hardcode a provider name; a provider
// is identified only by the real model string. This classifier maps that EVIDENCE to an authority kind
// WITHOUT ever branching on a provider name (`if provider == "DeepSeek"` is forbidden).
//
// Read-only, non-authoritative, deterministic.

export type TraceAuthorityKind =
  | 'ACFL_MATH'
  | 'LLM_PROPOSAL'
  | 'Q4_GOVERNED'
  | 'FREEZE_PUBLICATION'
  | 'DETERMINISTIC_GOVERNANCE';

export interface TraceClassification {
  kind: TraceAuthorityKind;
  label: string;
}

/**
 * Classify one EM invocation from its real model + role label.
 * - `ACFL_DETERMINISTIC` is the mathematical authority (never an LLM).
 * - any other non-empty model is an LLM PROPOSAL (candidate only, never fact).
 * - EM Installer / Publisher are non-LLM (Q4 governed effect / freeze-publication).
 */
export function classifyModel(em: string, model: string): TraceClassification {
  if (model === 'ACFL_DETERMINISTIC') {
    return { kind: 'ACFL_MATH', label: 'ACFL MATH (no LLM)' };
  }
  if (model && model !== '') {
    return { kind: 'LLM_PROPOSAL', label: 'LLM proposal' };
  }
  if (em === 'EM Installer') {
    return { kind: 'Q4_GOVERNED', label: 'Q4 governed effect' };
  }
  if (em === 'EM Publisher') {
    return { kind: 'FREEZE_PUBLICATION', label: 'freeze / publication' };
  }
  return { kind: 'DETERMINISTIC_GOVERNANCE', label: 'deterministic / governance' };
}

export const TRACE_TONE: Record<TraceAuthorityKind, string> = {
  ACFL_MATH: 'text-[var(--eureka-signal-cognitive)]',
  LLM_PROPOSAL: 'text-amber-600',
  Q4_GOVERNED: 'text-[var(--eureka-text-label)]',
  FREEZE_PUBLICATION: 'text-[var(--eureka-text-label)]',
  DETERMINISTIC_GOVERNANCE: 'text-[var(--eureka-text-label)]',
};

// --- Observed-pipeline mapper (pure, read-only, deterministic) --------------- //
// Given the CONTRACTUAL EM order + the real `em_pipeline` statuses + the real `cognitive_trace`,
// produce the per-EM OBSERVED view. A stage in the contractual order that has NO observed status is
// reported as `NOT_OBSERVED` (honest absence) — never `ASSUMED`. A provider is never hardcoded.
export interface EmObserved {
  em: string;
  status: string;
  model: string;
  latencyMs: number;
  capabilityId: string;
  classification: TraceClassification;
}

interface EmPipelineLike { canonical_em: string; status: string; }
interface TraceLike { em: string; model: string; status: string; latency_ms?: number; capability_id: string; }

export function mapObservedPipeline(
  contractual: string[],
  emPipeline: EmPipelineLike[],
  trace: TraceLike[],
): EmObserved[] {
  const statusByEm = new Map<string, string>();
  for (const e of emPipeline) statusByEm.set(e.canonical_em, e.status);
  const traceByEm = new Map<string, TraceLike>();
  for (const t of trace) traceByEm.set(t.em, t);
  return contractual.map((em) => {
    const t = traceByEm.get(em);
    return {
      em,
      status: statusByEm.get(em) ?? 'NOT_OBSERVED',
      model: t?.model ?? '',
      latencyMs: t?.latency_ms ?? 0,
      capabilityId: t?.capability_id ?? '',
      classification: classifyModel(em, t?.model ?? ''),
    };
  });
}
