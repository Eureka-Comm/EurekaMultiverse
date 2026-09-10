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
