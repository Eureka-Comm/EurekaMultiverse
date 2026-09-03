import { useMemo } from 'react';
import type { CanonicalWorkState } from '../domain/canonicalSchema';
import {
  buildCognitiveProjection,
  type CognitiveProjectionDTO,
} from '../domain/cognitiveProjection';

/**
 * LS3 §30 — SINGLE SOURCE hook.
 *
 * `useCognitiveProjection(activeWork)` memoizes `buildCognitiveProjection(activeWork)`.
 *
 * EVERY cognitive surface in the EUREKA COGNITIVE STORY tab (Storytelling, Knowledge
 * Map, Provenance/Lineage, Inspector, Decision visualization, EM rail affordances)
 * MUST read its data from THIS DTO — never from raw `state.findings` /
 * `state.human_decision`, never from a parallel projection, never from mock data.
 *
 * The DTO is built by the pure, tested `buildCognitiveProjection` (LS86). The state
 * may be `null` before any work is active; the projection is then the empty/truthful
 * projection and the UI renders "DATA PENDING" / "No governed graph".
 */
export function useCognitiveProjection(state: CanonicalWorkState | null): CognitiveProjectionDTO {
  return useMemo(() => buildCognitiveProjection(state), [state]);
}
