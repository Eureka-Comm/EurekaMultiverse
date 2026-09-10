import { describe, it, expect, vi, afterEach } from 'vitest';
import { getWorkAudit, getWorkPublication } from './scenarioApi';

function mockFetch(json: unknown): void {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => json,
  }) as unknown as Response));
}
afterEach(() => vi.unstubAllGlobals());

describe('CONSTELACIÓN work observability API must target the Work authority', () => {
  it('getWorkAudit hits /api/work/{id}/audit (not the scenario API)', async () => {
    mockFetch({ work_id: 'WORK-X' });
    await getWorkAudit('WORK-X');
    const url = (fetch as unknown as { mock: { calls: [string][] } }).mock.calls[0][0];
    expect(url).toBe('/api/work/WORK-X/audit');
    expect(url).not.toContain('/api/scenario');
  });

  it('getWorkPublication hits /api/work/{id}/publication (not the scenario API)', async () => {
    mockFetch({ work_id: 'WORK-X' });
    await getWorkPublication('WORK-X');
    const url = (fetch as unknown as { mock: { calls: [string][] } }).mock.calls[0][0];
    expect(url).toBe('/api/work/WORK-X/publication');
    expect(url).not.toContain('/api/scenario');
  });

  it('encodes the work id in the path', async () => {
    mockFetch({ work_id: 'A WORK' });
    await getWorkAudit('A WORK');
    const url = (fetch as unknown as { mock: { calls: [string][] } }).mock.calls[0][0];
    expect(url).toBe('/api/work/A%20WORK/audit');
  });
});
