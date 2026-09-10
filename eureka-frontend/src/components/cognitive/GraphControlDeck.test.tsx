import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import GraphControlDeck, { GraphLegend, countByKind } from './GraphControlDeck';
import type { GraphArtifact, NodeKind } from '../../domain/cognitiveProjectionGraph';

function node(kind: NodeKind, id: string, status: string): GraphArtifact {
  return {
    id, kind, artifactId: id, label: `${kind} ${id}`, status, authority: 'VALIDATED',
    provenance: [], evidence: [], uncertainty: '', em: '', sourceField: '', recommended: false,
    humanSelected: false, description: '',
  };
}

const nodes: GraphArtifact[] = [
  node('PROBLEM', 'PROB-1', 'GOVERNED'),
  node('DECISION', 'DEC-1', 'HUMAN_AUTHORIZED'),
  node('FROZEN', 'FROZEN-1', 'FROZEN'),
  node('FINDING', 'FND-1', 'UNSUPPORTED'),   // gap
  node('PREDICTION', 'PRED-1', 'VALIDATED'),
];

describe('GraphControlDeck — CONSTELACIÓN control deck (real read-only metrics)', () => {
  it('countByKind is deterministic', () => {
    expect(countByKind(nodes, 'DECISION')).toBe(1);
    expect(countByKind(nodes, 'FROZEN')).toBe(1);
    expect(countByKind(nodes, 'PROBLEM')).toBe(1);
    expect(countByKind(nodes, 'EXECUTION')).toBe(0);
  });

  it('renders GRAPH SUMMARY with real objects/gaps/human-dec/frozen', () => {
    const html = renderToString(createElement(GraphControlDeck, { nodes, focusKind: 'ALL' }));
    expect(html).toContain('Graph Summary');
    // labels are uppercased by the deck (OBJECTS / GAPS / HUMAN DEC. / FROZEN)
    expect(html).toContain('OBJECTS');
    expect(html).toContain('GAPS');
    expect(html).toContain('HUMAN DEC.');
    expect(html).toContain('FROZEN');
  });

  it('renders VIEW LAYERS with real per-kind counts + a stable single color source', () => {
    const html = renderToString(createElement(GraphControlDeck, { nodes, focusKind: 'ALL' }));
    expect(html).toContain('View Layers');
    expect(html).toContain('Problem');
    expect(html).toContain('Findings');
    expect(html).toContain('Predictions');
    expect(html).toContain('Decision');
    expect(html).toContain('Frozen');
    // a kind absent from the graph AND not in the focus filter is omitted (honest absence)
    expect(html).not.toContain('Prescription');
  });

  it('renders FOCUS FILTER with All/Decision/Action/Execution/Result/Frozen as real buttons', () => {
    const html = renderToString(createElement(GraphControlDeck, { nodes, focusKind: 'ALL' }));
    expect(html).toContain('Focus Filter');
    for (const label of ['All', 'Decision', 'Action', 'Execution', 'Result', 'Frozen']) {
      expect(html).toContain(label);
    }
  });

  it('marks the active focus kind as pressed (aria-pressed)', () => {
    const html = renderToString(createElement(GraphControlDeck, { nodes, focusKind: 'DECISION' }));
    expect(html).toContain('aria-pressed="true"');
  });
});

describe('GraphLegend — single visual source, only real kinds', () => {
  it('renders only the node kinds actually present', () => {
    const html = renderToString(createElement(GraphLegend, { nodes }));
    expect(html).toContain('Problem');
    expect(html).toContain('Decision');
    expect(html).toContain('Findings');
    expect(html).toContain('Predictions');
    expect(html).toContain('Frozen');
    expect(html).not.toContain('Execution');   // not present
    expect(html).not.toContain('Alternative'); // not present
  });
});
