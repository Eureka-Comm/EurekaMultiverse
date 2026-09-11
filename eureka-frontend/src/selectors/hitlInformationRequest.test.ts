// Governed HITL contract (UI side): which INFORMATION request is surfaced to the human.
//
// Regression context (production WORK-D120C202): the human answered with an ECHO of the question.
// After the repair, an insufficient answer keeps the work BLOCKED and the backend creates a NEW
// blocking INFORMATION request that names exactly what is still missing. The UI must therefore
// surface the NEWEST still-PENDING request (never the already-ANSWERED one) and must surface
// nothing when no human gate is actually open.
import { describe, expect, it } from 'vitest';
import { selectActiveInformationRequest } from './decisionSelectors.ts';
import type { CanonicalWorkState } from '../domain/canonicalSchema';

function makeState(overrides: Record<string, unknown> = {}): CanonicalWorkState {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'W-HITL', taskCategory: null, status: 'WAITING_FOR_HUMAN_INPUT', userIntent: '' },
    execution_plan: { steps: [] },
    em_pipeline: [],
    state: { acfl: {}, feasible_only: true },
    evidence: [],
    extracted_evidence: {},
    visualizations: [],
    available_capabilities: [],
    gaps: [],
    conditions: [],
    tool_call_id: null,
    revision: 0,
    extracted_entities: {},
    active_em: null,
    active_step_id: null,
    active_capability: null,
    execution_progress: 0,
    execution_events: [],
    decision_points: [],
    human_requests: [],
    ...overrides,
  } as unknown as CanonicalWorkState;
}

const answeredOriginal = {
  request_id: 'REQ-original', type: 'INFORMATION', status: 'ANSWERED', blocking: true,
  question: 'Para determinar cómo ganar dinero con EUREKA, necesito información específica…',
  required_information: ['qué es EUREKA', 'sus capacidades actuales y limitaciones conocidas'],
  sufficiency_status: 'INSUFFICIENT', resolution: 'AWAITING_MORE',
};
const followUp = {
  request_id: 'REQ-followup', type: 'INFORMATION', status: 'PENDING', blocking: true, attempt: 2,
  follows_request_id: 'REQ-original',
  question: 'La información recibida no es suficiente. Sigue faltando información sobre: 1) qué es EUREKA…',
  required_information: ['qué es EUREKA'],
};

describe('selectActiveInformationRequest — governed follow-up loop', () => {
  it('surfaces the NEWEST pending request, not the answered original', () => {
    const state = makeState({ human_requests: [answeredOriginal, followUp] });
    const active = selectActiveInformationRequest(state);
    expect(active).toBeDefined();
    expect(active.request_id).toBe('REQ-followup');
    expect(active.status).toBe('PENDING');
  });

  it('surfaces nothing when every request was answered with sufficient information', () => {
    const state = makeState({
      human_requests: [{ ...answeredOriginal, sufficiency_status: 'SUFFICIENT', resolution: 'RESOLVED_SUFFICIENT' }],
    });
    expect(selectActiveInformationRequest(state)).toBeUndefined();
  });

  it('surfaces nothing while the work is not blocked on human input', () => {
    for (const status of ['RUNNING', 'COMPLETED', 'READY', 'WAITING_FOR_EVIDENCE']) {
      const state = makeState({
        work: { workId: 'W-HITL', taskCategory: null, status, userIntent: '' },
        human_requests: [followUp],
      });
      expect(selectActiveInformationRequest(state)).toBeUndefined();
    }
  });

  it('handles a missing human_requests field without inventing a gate', () => {
    expect(selectActiveInformationRequest(makeState({ human_requests: undefined }))).toBeUndefined();
    expect(selectActiveInformationRequest(null)).toBeUndefined();
  });
});
