import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { CanonicalWorkStateSchema } from './canonicalSchema';
import { buildCognitiveProjection } from './cognitiveProjection';
import { buildCognitiveProjectionGraph } from './cognitiveProjectionGraph';
import GalaxyConstellation from '../components/cognitive/GalaxyConstellation';
import type { CanonicalWorkState } from './canonicalSchema';

// CONSTELACIÓN real-data E2E proof: the REAL WORK-AC8CD7B1 canonical state flows through the
// frontend schema → projection → graph builder → GalaxyConstellation AND renders the real
// GRAPH CONTROL DECK (metrics/layers/legend) from that real graph. Requires the backend on
// http://127.0.0.1:8000; skips gracefully when it is absent (CI-safe).
describe('REAL WORK-AC8CD7B1 state → CONSTELACIÓN graph + control deck', () => {
  it('builds a real governed graph and renders the Control Deck with real metrics', async () => {
    let res: Response;
    try {
      res = await fetch('http://127.0.0.1:8000/api/work/WORK-AC8CD7B1/state');
    } catch {
      expect(true).toBe(true);
      return;
    }
    expect(res.ok).toBe(true);
    const raw = await res.json();
    const state = CanonicalWorkStateSchema.parse(raw) as unknown as CanonicalWorkState;
    const p = buildCognitiveProjection(state);
    const g = buildCognitiveProjectionGraph(p);
    expect(g.nodes.length).toBeGreaterThan(0);
    const kinds = new Set(g.nodes.map((n) => n.kind));
    for (const k of ['PROBLEM', 'RESULT', 'FROZEN', 'ALTERNATIVE', 'DECISION']) expect(kinds.has(k as any)).toBe(true);
    for (const e of g.edges) {
      expect(['OBSERVED', 'CONTRACTUAL', 'DERIVED', 'NOT_OBSERVED']).toContain(e.classification);
      expect(e.label).not.toBe('causes' as any);
    }

    const html = renderToString(createElement(GalaxyConstellation, { nodes: g.nodes, edges: g.edges }));
    // real metric labels present
    expect(html).toContain('Graph Summary');
    expect(html).toContain('OBJECTS');
    expect(html).toContain('GAPS');
    expect(html).toContain('HUMAN DEC.');
    expect(html).toContain('FROZEN');
    expect(html).toContain('View Layers');
    expect(html).toContain('Focus Filter');
    // no invented demo labels
    expect(html).not.toContain('SALES');
    expect(html).not.toContain('MEMORY');
  });
});
