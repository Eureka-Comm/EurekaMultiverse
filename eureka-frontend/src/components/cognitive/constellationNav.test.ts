import { describe, it, expect } from 'vitest';
import type { GraphArtifact, GraphEdge, NodeKind } from '../../domain/cognitiveProjectionGraph';
import {
  baseBox, zoomViewport, panViewport, viewportScale,
  upstreamClosure, downstreamClosure, upstreamChain, downstreamChain,
  edgesTouching, edgesWithin, kindRank, directUpstreamIds, directDownstreamIds,
  semanticLevel, statusTone, isGapStatus, gapNodeIds, stageCounts, kindNodeIds,
  GALAXY_W, GALAXY_H, GALAXY_CX, GALAXY_CY, MIN_SCALE, MAX_SCALE,
} from './constellationNav';

function node(id: string, kind: NodeKind): GraphArtifact {
  return {
    id, kind, artifactId: id.toLowerCase(), label: id, status: 'EVALUATED',
    authority: 'PYTHON_GOVERNED', provenance: [], evidence: [], uncertainty: 'MEDIUM',
    em: 'EM', sourceField: 'x', recommended: false, humanSelected: false, description: id,
  };
}

// Pipeline nodes in EUREKA stage order.
const NODES: GraphArtifact[] = [
  node('EVI-1', 'EVIDENCE'),
  node('FND-1', 'FINDING'),
  node('PRED-1', 'PREDICTION'),
  node('PRESC-1', 'PRESCRIPTION'),
  node('ALT-1', 'ALTERNATIVE'),
  node('DEC-1', 'DECISION'),
  node('ACT-1', 'ACTION'),
  node('EXEC-1', 'EXECUTION'),
  node('RESULT-1', 'RESULT'),
  node('FROZEN-1', 'FROZEN'),
];

// Real edges connecting consecutive stages (as `produced_by`/`derived_from` etc. would exist).
const EDGES: GraphEdge[] = [
  { id: 'e1', source: 'EVI-1', target: 'FND-1', label: 'derived_from' },
  { id: 'e2', source: 'FND-1', target: 'PRED-1', label: 'produced_by' },
  { id: 'e3', source: 'PRED-1', target: 'PRESC-1', label: 'produced_by' },
  { id: 'e4', source: 'PRESC-1', target: 'ALT-1', label: 'produced_by' },
  { id: 'e5', source: 'ALT-1', target: 'DEC-1', label: 'selected_by' },
  { id: 'e6', source: 'DEC-1', target: 'ACT-1', label: 'authorized_by' },
  { id: 'e7', source: 'ACT-1', target: 'EXEC-1', label: 'executed_as' },
  { id: 'e8', source: 'EXEC-1', target: 'RESULT-1', label: 'executed_as' },
  { id: 'e9', source: 'RESULT-1', target: 'FROZEN-1', label: 'frozen_as' },
];

describe('constellationNav — zoom/pan (presentation only)', () => {
  it('zoom in shrinks the visible viewBox and raises the effective scale', () => {
    const vb = zoomViewport(baseBox(), GALAXY_CX, GALAXY_CY, 1.25);
    expect(vb.w).toBeLessThan(GALAXY_W);
    expect(viewportScale(vb)).toBeGreaterThan(1);
  });

  it('zoom out never exceeds MIN_SCALE floor', () => {
    const vb = zoomViewport(baseBox(), GALAXY_CX, GALAXY_CY, 1 / 1.25);
    expect(viewportScale(vb)).toBeGreaterThanOrEqual(MIN_SCALE);
  });

  it('zoom keeps the anchor content point fixed on screen', () => {
    const start = { x: 900, y: 600 };
    const vb = zoomViewport(baseBox(), start.x, start.y, 1.5);
    const frX0 = (start.x - 0) / GALAXY_W;
    const frY0 = (start.y - 0) / GALAXY_H;
    const frX1 = (start.x - vb.x) / vb.w;
    const frY1 = (start.y - vb.y) / vb.h;
    expect(frX1).toBeCloseTo(frX0, 4);
    expect(frY1).toBeCloseTo(frY0, 4);
  });

  it('pan moves the viewBox origin opposite to the drag (grab-to-move)', () => {
    const vb = panViewport(baseBox(), 100, 50);
    expect(vb.x).toBe(-100);
    expect(vb.y).toBe(-50);
  });

  it('clamp keeps the galactic core on-screen (never lose the galaxy)', () => {
    const vb = panViewport(baseBox(), 100000, -100000);
    expect(GALAXY_CX).toBeGreaterThanOrEqual(vb.x - 0.001);
    expect(GALAXY_CX).toBeLessThanOrEqual(vb.x + vb.w + 0.001);
    expect(GALAXY_CY).toBeGreaterThanOrEqual(vb.y - 0.001);
    expect(GALAXY_CY).toBeLessThanOrEqual(vb.y + vb.h + 0.001);
  });

  it('zooms bounded within [MIN_SCALE, MAX_SCALE]', () => {
    let vb = baseBox();
    for (let i = 0; i < 40; i++) vb = zoomViewport(vb, GALAXY_CX, GALAXY_CY, 1.25);
    expect(viewportScale(vb)).toBeLessThanOrEqual(MAX_SCALE);
    for (let i = 0; i < 80; i++) vb = zoomViewport(vb, GALAXY_CX, GALAXY_CY, 1 / 1.25);
    expect(viewportScale(vb)).toBeGreaterThanOrEqual(MIN_SCALE);
  });

  it('baseBox is the full galaxy view', () => {
    expect(baseBox()).toEqual({ x: 0, y: 0, w: GALAXY_W, h: GALAXY_H });
  });

  it('kindRank orders stages EVIDENCE < ... < FROZEN', () => {
    expect(kindRank('EVIDENCE')).toBeLessThan(kindRank('PREDICTION'));
    expect(kindRank('PREDICTION')).toBeLessThan(kindRank('DECISION'));
    expect(kindRank('DECISION')).toBeLessThan(kindRank('FROZEN'));
  });
});

describe('constellationNav — provenance trace (REAL edges only, pipeline order)', () => {
  it('upstreamClosure walks the real chain back to EVIDENCE and stops at the root', () => {
    const s = upstreamClosure('RESULT-1', EDGES, NODES);
    ['EVI-1', 'FND-1', 'PRED-1', 'PRESC-1', 'ALT-1', 'DEC-1', 'ACT-1', 'EXEC-1', 'RESULT-1'].forEach((id) => expect(s.has(id)).toBe(true));
    // FROZEN is downstream of RESULT, so it is NOT upstream.
    expect(s.has('FROZEN-1')).toBe(false);
    // never invents
    expect(s.has('INVENTED')).toBe(false);
  });

  it('downstreamClosure walks the real chain forward to FROZEN and stops at the end', () => {
    const s = downstreamClosure('EVI-1', EDGES, NODES);
    ['EVI-1', 'FND-1', 'PRED-1', 'PRESC-1', 'ALT-1', 'DEC-1', 'ACT-1', 'EXEC-1', 'RESULT-1', 'FROZEN-1'].forEach((id) => expect(s.has(id)).toBe(true));
  });

  it('upstreamChain/downstreamChain are ordered and exclude the seed', () => {
    const up = upstreamChain('RESULT-1', EDGES, NODES);
    expect(up[0]).toBe('EXEC-1');
    expect(up).not.toContain('RESULT-1');
    const down = downstreamChain('EVI-1', EDGES, NODES);
    expect(down[0]).toBe('FND-1');
    expect(down).not.toContain('EVI-1');
  });

  it('stops honestly when a hop is missing (no invented path)', () => {
    const frag: GraphEdge[] = [
      { id: 'f1', source: 'EXEC-1', target: 'RESULT-1', label: 'executed_as' },
      { id: 'f2', source: 'ACT-1', target: 'EXEC-1', label: 'executed_as' },
    ];
    const s = upstreamClosure('RESULT-1', frag, NODES.filter((n) => ['EXEC-1', 'RESULT-1', 'ACT-1'].includes(n.id)));
    expect(s.has('EXEC-1')).toBe(true);
    expect(s.has('ACT-1')).toBe(true);
    expect(s.has('DEC-1')).toBe(false); // not reachable — stops honestly
  });

  it('edgesTouching finds incident edges of the selected node', () => {
    const s = edgesTouching('RESULT-1', EDGES);
    expect(s.has('e8')).toBe(true);
    expect(s.has('e9')).toBe(true);
    expect(s.has('e7')).toBe(false);
  });

  it('edgesWithin finds edges whose two endpoints are in a set', () => {
    const set = new Set(['DEC-1', 'ACT-1']);
    const s = edgesWithin(set, EDGES);
    expect(s.has('e6')).toBe(true);
    expect(s.has('e7')).toBe(false);
  });

  it('directUpstreamIds/directDownstreamIds are pipeline-correct, not source/target flipped', () => {
    // FINDING (stage 2): upstream = EVIDENCE (stage 1), downstream = PREDICTION (stage 3).
    expect(directUpstreamIds('FND-1', EDGES, NODES)).toEqual(['EVI-1']);
    expect(directDownstreamIds('FND-1', EDGES, NODES)).toEqual(['PRED-1']);
    // EVIDENCE is the root: no upstream.
    expect(directUpstreamIds('EVI-1', EDGES, NODES)).toEqual([]);
  });

  it('semanticLevel maps effective scale to 3 levels (FAR/MEDIUM/CLOSE)', () => {
    expect(semanticLevel(0.9)).toBe(0);       // FAR
    expect(semanticLevel(1.25)).toBe(1);       // MEDIUM
    expect(semanticLevel(1.9)).toBe(1);
    expect(semanticLevel(2.0)).toBe(2);        // CLOSE
    expect(semanticLevel(3.0)).toBe(2);
  });

  it('statusTone classifies honest states, never conflating signal states', () => {
    expect(statusTone('VALIDATED')).toBe('validated');
    expect(statusTone('NOT_EVALUATED')).toBe('gap');
    expect(statusTone('DATA NOT AVAILABLE')).toBe('gap');
    expect(statusTone('WAITING_FOR_HUMAN_INPUT')).toBe('waiting');
    expect(statusTone('FROZEN')).toBe('frozen');
    expect(statusTone('GOVERNED')).toBe('governed');
    expect(statusTone('PENDING')).toBe('pending');
    // unknown/foreign states are NOT upgraded to a confident tone
    expect(statusTone('SUCCESS')).toBe('neutral');
    expect(statusTone('')).toBe('neutral');
  });

  it('isGapStatus/gapNodeIds identify real open states only', () => {
    expect(isGapStatus('NOT_EVALUATED')).toBe(true);
    expect(isGapStatus('UNSUPPORTED')).toBe(true);
    expect(isGapStatus('DATA NOT AVAILABLE')).toBe(true);
    expect(isGapStatus('WAITING_FOR_HUMAN_INPUT')).toBe(true);
    expect(isGapStatus('VALIDATED')).toBe(false);
    expect(isGapStatus('GOVERNED')).toBe(false);
    const g = gapNodeIds(NODES);
    // NODES fixture statuses: all 'EVALUATED' (not gaps) → expect empty
    expect(g).toEqual([]);
    const withGap = [...NODES.map((n) => ({ ...n })), { ...NODES[0], id: 'GAP-1', status: 'NOT_EVALUATED' }];
    expect(gapNodeIds(withGap)).toEqual(['GAP-1']);
  });

  it('stageCounts/kindNodeIds derive real counts per kind, 0 when absent (never invent)', () => {
    const c = stageCounts(NODES);
    expect(c['EVIDENCE']).toBe(1);
    expect(c['DECISION']).toBe(1);
    expect(c['PRESCRIPTION']).toBe(1);
    expect(c['FROZEN']).toBe(1);
    expect(kindNodeIds(NODES, 'DECISION')).toEqual(['DEC-1']);
    expect(kindNodeIds(NODES, 'RESULT')).toEqual(['RESULT-1']);
    // absent kind → 0, NOT an invented object
    const noFrozen = NODES.filter((n) => n.kind !== 'FROZEN');
    expect(stageCounts(noFrozen)['FROZEN']).toBe(0);
    expect(kindNodeIds(noFrozen, 'FROZEN')).toEqual([]);
  });
});
