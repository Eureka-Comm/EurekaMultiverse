// Manual test script for selectActiveDecision – replaces previous Jest tests
import { selectActiveDecision } from './decisionSelectors.ts';
import type { CanonicalWorkState } from '../domain/canonicalSchema';

/** Helper to create a minimal CanonicalWorkState for manual tests */
function makeState(overrides: Partial<CanonicalWorkState> = {}): CanonicalWorkState {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'W1', taskCategory: null, status: 'WAITING_FOR_HUMAN_INPUT', userIntent: '' },
    execution_plan: { steps: [] },
    em_pipeline: [],
    state: {
      acfl: { weights: {}, criteria: [], alternatives: [], normalized_scores: {}, frontier: [], sensitivity: {} },
      feasible_only: true,
    },
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
    ...overrides,
  } as unknown as CanonicalWorkState;
}

// Manual test cases covering the ACTIVE_NOW contract
const cases = [
  {
    name: 'Active now single decision',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: 'step1',
      decision_points: [{ decision_id: 'd1', task_id: 'step1', status: 'PENDING' }],
    }),
    expected: true,
  },
  {
    name: 'Canonical not waiting',
    state: makeState({
      work: { ...makeState().work, status: 'RUNNING' },
      active_step_id: 'step1',
      decision_points: [{ decision_id: 'd1', task_id: 'step1', status: 'PENDING' }],
    }),
    expected: false,
  },
  {
    name: 'No active_step_id',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: null,
      decision_points: [{ decision_id: 'd1', task_id: 'step1', status: 'PENDING' }],
    }),
    expected: false,
  },
  {
    name: 'Multiple pending decisions',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: 'step1',
      decision_points: [
        { decision_id: 'd1', task_id: 'step1', status: 'PENDING' },
        { decision_id: 'd2', task_id: 'step1', status: 'PENDING' },
      ],
    }),
    expected: false,
  },
  {
    name: 'Pending decision with mismatched task_id',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: 'step1',
      decision_points: [{ decision_id: 'd1', task_id: 'other', status: 'PENDING' }],
    }),
    expected: false,
  },
  {
    name: 'Decision not pending',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: 'step1',
      decision_points: [{ decision_id: 'd1', task_id: 'step1', status: 'COMPLETED' }],
    }),
    expected: false,
  },
  {
    name: 'No decisions at all',
    state: makeState({
      work: { ...makeState().work, status: 'WAITING_FOR_HUMAN_INPUT' },
      active_step_id: 'step1',
      decision_points: [],
    }),
    expected: false,
  },
  {
    name: 'All fields missing (fallback)',
    state: makeState({}),
    expected: false,
  },
];

function run() {
  let passed = 0;
  for (const c of cases) {
    const result = selectActiveDecision(c.state);
    const ok = (result !== undefined) === c.expected;
    console.log(`${c.name}: ${ok ? 'PASS' : 'FAIL'}`);
    if (ok) passed++;
  }
  console.log(`Passed ${passed}/${cases.length} cases`);
}

run();
