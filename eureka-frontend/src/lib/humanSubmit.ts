// EUREKA 5.1 — CANONICAL single-flight + association guards for HUMAN INPUT submissions.
//
// Production evidence that motivated this module:
//   GET  /api/work/WORK-B39C51D1/state          (status = WAITING_FOR_HUMAN_INPUT)
//   POST /api/work/WORK-8DD6B1D1/human_input    <- another Work (identity drift)
//   POST /api/work/WORK-8DD6B1D1/human_input    <- again, another request_id (double submit)
//
// Rules implemented here (ONE implementation, shared by the HITL widget and the chat — no second
// API client, no duplicated store):
//   1. a submission may reach the HITL gate ONLY when it is an EXPLICIT human answer (auto-narration
//      and viewer questions can never be consumed as the human's answer);
//   2. at most ONE in-flight submission per (work, request);
//   3. the request must belong to the work the submission targets (fail closed otherwise).

const inFlight = new Set<string>();

export function humanSubmitKey(workId: string, requestId: string): string {
  return `${workId}::${requestId}`;
}

/** Returns true when the caller OWNS the flight (and must call `endHumanSubmit`). False = duplicate. */
export function beginHumanSubmit(workId: string, requestId: string): boolean {
  const key = humanSubmitKey(workId, requestId);
  if (inFlight.has(key)) return false;
  inFlight.add(key);
  return true;
}

export function endHumanSubmit(workId: string, requestId: string): void {
  inFlight.delete(humanSubmitKey(workId, requestId));
}

export function isHumanSubmitInFlight(workId: string, requestId: string): boolean {
  return inFlight.has(humanSubmitKey(workId, requestId));
}

/**
 * The HITL gate is for ANSWERS. A narration/auto-message (mount auto-submit) or a viewer question
 * ("ask the copilot") must never be routed there — that is what turned the ORIGINAL QUESTION into a
 * human answer (the echo of WORK-D120C202).
 */
export function shouldRouteToHumanGate(opts: { asHumanAnswer?: boolean } | undefined,
                                       hasOpenRequest: boolean): boolean {
  return opts?.asHumanAnswer === true && hasOpenRequest === true;
}

/**
 * Fail-closed association check. A request without `work_id` (legacy) is left to the server-side
 * containment validation; a request that NAMES another work is refused client-side.
 */
export function requestBelongsToWork(requestWorkId: string | null | undefined,
                                     targetWorkId: string | null | undefined): boolean {
  if (!targetWorkId) return false;
  if (!requestWorkId) return true;
  return requestWorkId === targetWorkId;
}
