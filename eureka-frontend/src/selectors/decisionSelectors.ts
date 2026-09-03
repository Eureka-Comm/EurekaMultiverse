import type { CanonicalWorkState } from '../domain/canonicalSchema';

/**
 * Pure selector that determines the ACTIVE_NOW HumanDecisionPoint according to the
 * verified backend contract.
 *
 * Contract:
 *   canonical.status === "WAITING_FOR_HUMAN_INPUT"
 *   && decision.status === "PENDING"
 *   && decision.task_id === canonical.active_step_id
 *   && canonical.active_step_id != null
 *
 * Returns the matching HumanDecisionPoint or undefined if none (including the case of
 * multiple matches, which logs a warning for diagnostic purposes).
 */
export function selectActiveDecision(state: CanonicalWorkState | null): any | undefined {
  if (!state) return undefined;

  // Guard the required fields exist
  const canonicalStatus = state.work?.status;
  const activeStepId = state.active_step_id;

  if (canonicalStatus !== 'WAITING_FOR_HUMAN_INPUT') return undefined;
  if (activeStepId == null) return undefined;

  const pendingDecisions = (state.decision_points ?? []).filter(
    (dp: any) => dp.status === 'PENDING' && dp.task_id === activeStepId
  );

  // H-1: never return undefined when there is a pending decision. With F-2 idempotency there should be
  // exactly 1, but the UI must stay robust to >1 (surface the highest-priority one, not collapse).
  if (pendingDecisions.length >= 1) {
    if (pendingDecisions.length > 1) {
      // Anomaly: multiple active decisions – log for debugging/test detection, still surface one.
      console.warn('MULTIPLE_ACTIVE_DECISIONS', { count: pendingDecisions.length, activeStepId, decisions: pendingDecisions });
    }
    return pendingDecisions[0] as any;
  }

  return undefined;
}

/**
 * LS49: select the active HumanInteractionRequest (INFORMATION-type) to surface in the UI.
 * The request model has no task_id binding, so the "active" request is the newest still-PENDING
 * one while the canonical work is waiting for human input. Prefer the newest so a stale leftover
 * does not shadow a fresh gate.
 */
export function selectActiveInformationRequest(state: CanonicalWorkState | null): any | undefined {
  if (!state) return undefined;
  if (state.work?.status !== 'WAITING_FOR_HUMAN_INPUT') return undefined;

  const pending = (state.human_requests ?? []).filter(
    (hr: any) => hr.status === 'PENDING'
  );

  if (pending.length === 0) return undefined;
  return pending[pending.length - 1] as any;
}
