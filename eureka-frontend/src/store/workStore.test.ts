import { describe, it, expect, vi, afterEach } from 'vitest';
import { useWorkStore } from './workStore';

// A minimal but schema-valid canonical state (same shape used across the projection tests).
const validState = {
  schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
  work: { workId: 'WORK-AC8CD7B1', status: 'COMPLETED', userIntent: 'real' },
  execution_plan: { steps: [] },
  state: {
    acfl: { weights: {}, criteria: [], alternatives: [], normalized_scores: {}, frontier: [], sensitivity: {} },
    feasible_only: false,
  },
  evidence: [],
  extracted_evidence: {},
  visualizations: [],
  available_capabilities: [],
  gaps: [],
  conditions: [],
  revision: 1,
  extracted_entities: {},
};

afterEach(() => {
  useWorkStore.setState({ activeWork: null, appState: 'NO_WORK' });
  vi.unstubAllGlobals();
});

describe('workStore.loadWorkById — read-only load of an existing Work', () => {
  it('loads a work into activeWork from the real /api/work/{id}/state endpoint', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => validState })) as unknown as typeof fetch);
    const result = await useWorkStore.getState().loadWorkById('WORK-AC8CD7B1');
    const s = useWorkStore.getState();
    expect(s.activeWork?.work.workId).toBe('WORK-AC8CD7B1');
    expect(s.appState).toBe('READY');
    expect(result?.work.workId).toBe('WORK-AC8CD7B1');
    const url = (fetch as unknown as { mock: { calls: [string][] } }).mock.calls[0][0];
    expect(url).toBe('/api/work/WORK-AC8CD7B1/state');
  });

  it('fail-closed (no fabricated activeWork) when the Work is unknown (404)', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 404, json: async () => ({ detail: 'WORK_NOT_FOUND' }) })) as unknown as typeof fetch);
    const result = await useWorkStore.getState().loadWorkById('WORK-NOPE');
    const s = useWorkStore.getState();
    expect(s.activeWork).toBeNull();
    expect(s.appState).toBe('NO_WORK');
    expect(result?.status).toBe('ERROR');
  });
});

// ============================================================================================= //
// TEST 4 — an active poll must NOT be able to change the Work identity of the projection
// ============================================================================================= //
describe('workStore.pollState — work identity correlation (no drift, no time travel)', () => {
  const otherWorkState = { ...validState, work: { ...validState.work, workId: 'WORK-OTHER' }, revision: 9 };

  it('drops a response that belongs to a DIFFERENT work', async () => {
    useWorkStore.setState({ activeWork: validState as any, appState: 'READY' });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => otherWorkState })) as unknown as typeof fetch);
    await useWorkStore.getState().pollState();
    expect(useWorkStore.getState().activeWork?.work.workId).toBe('WORK-AC8CD7B1');
    const url = (fetch as unknown as { mock: { calls: [string][] } }).mock.calls[0][0];
    expect(url).toBe('/api/work/WORK-AC8CD7B1/state');   // it polled the ACTIVE work, not the other one
  });

  it('drops a stale response for the same work (older revision)', async () => {
    useWorkStore.setState({ activeWork: { ...validState, revision: 5 } as any, appState: 'READY' });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ ...validState, revision: 4 }) })) as unknown as typeof fetch);
    await useWorkStore.getState().pollState();
    expect(useWorkStore.getState().activeWork?.revision).toBe(5);
  });

  it('applies a newer response for the SAME work', async () => {
    useWorkStore.setState({ activeWork: { ...validState, revision: 5 } as any, appState: 'READY' });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ ...validState, revision: 6 }) })) as unknown as typeof fetch);
    await useWorkStore.getState().pollState();
    expect(useWorkStore.getState().activeWork?.revision).toBe(6);
  });

  it('does nothing when there is no active work (never invents one)', async () => {
    const spy = vi.fn();
    vi.stubGlobal('fetch', spy as unknown as typeof fetch);
    useWorkStore.setState({ activeWork: null, appState: 'NO_WORK' });
    await useWorkStore.getState().pollState();
    expect(spy).not.toHaveBeenCalled();
  });
});
