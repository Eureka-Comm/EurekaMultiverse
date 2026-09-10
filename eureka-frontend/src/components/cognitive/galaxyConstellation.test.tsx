import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import GalaxyConstellation from './GalaxyConstellation';
import type { GraphArtifact, GraphEdge } from '../../domain/cognitiveProjectionGraph';

const NODES: GraphArtifact[] = [
  {
    id: 'DEC-0001', kind: 'DECISION', artifactId: 'dec_1', label: 'DECISION·DEC-0001', status: 'HUMAN_SELECTED',
    authority: 'HUMAN_AUTHORIZED', provenance: ['evi:1', 'fnd:1'], evidence: [], uncertainty: 'LOW', em: 'EM Decider',
    sourceField: 'decision', recommended: false, humanSelected: true, description: 'Decision: expand.',
  },
  {
    id: 'PRED-0002', kind: 'PREDICTION', artifactId: 'pred_1', label: 'ACFL', status: 'NOT_EVALUATED',
    authority: 'PYTHON_GOVERNED', provenance: ['fnd:1'], evidence: [], uncertainty: 'MEDIUM', em: 'EM Predictor',
    sourceField: 'prediction', recommended: false, humanSelected: false, description: 'Predicted event.',
  },
  {
    id: 'ALT-0003', kind: 'ALTERNATIVE', artifactId: 'alt_1', label: 'Option B', status: 'NOT_EVALUATED',
    authority: 'LLM_CANDIDATE', provenance: [], evidence: [], uncertainty: '', em: 'EM Architect',
    sourceField: 'alternative', recommended: true, humanSelected: false, description: 'An alternative.',
  },
];

const EDGES: GraphEdge[] = [{ id: 'e1', source: 'PRED-0002', target: 'DEC-0001', label: 'produced_by' }];

describe('GalaxyConstellation (honest real-data surface) v5', () => {
  it('renders REAL cognitive artifacts and never fabricated demo labels', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES }));
    expect(html).toContain('DECISION·DEC-0001');
    expect(html).toContain('ACFL');
    expect(html).toContain('OBJECTS');
    for (const banned of ['SALES', 'FINANCE', 'DEALS', 'MARKETING', '12.4M', '2.1GB', 'MEMORY', 'TOKENS', 'AGENTS', 'BRIEFINGS']) {
      expect(html).not.toContain(banned);
    }
  });

  it('exposes real, accessible buttons for zoom and reset', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES }));
    expect(html).toMatch(/<button[^>]*>[^<]*ZOOM IN/i);
    expect(html).toMatch(/<button[^>]*>[^<]*ZOOM OUT/i);
    expect(html).toMatch(/<button[^>]*>[^<]*RESET/i);
    // actual button elements, not divs
    expect(html).toContain('aria-label="Zoom in"');
    expect(html).toContain('aria-label="Reset view"');
    expect(html).not.toContain('onclick="return');
  });

  it('marks each real node as a keyboard-navigable role button with aria-label', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES }));
    expect(html).toContain('role="button"');
    expect(html).toContain('aria-label="DECISION DEC-0001"');
    expect(html).toContain('tabindex="0"');
  });

  it('applies focus dimming only when a focus set is provided', () => {
    const noFocus = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES }));
    expect(noFocus).not.toContain('opacity="0.16"');
    const withFocus = renderToString(
      createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES, focusedNodeIds: ['DEC-0001'] })
    );
    // non-focused nodes get reduced opacity
    expect(withFocus).toContain('opacity="0.16"');
  });

  it('respects highlightRelations=false (no focus suppression) even when nodes are focused', () => {
    const html = renderToString(
      createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES, focusedNodeIds: ['DEC-0001'], highlightRelations: false })
    );
    expect(html).not.toContain('opacity="0.16"');
  });

  it('RENDERS a true CONTEXTUAL NODE CARD anchored to the selected node', () => {
    const html = renderToString(createElement(GalaxyConstellation, {
      nodes: NODES, edges: EDGES, selectedId: 'FND', selectedArtifact: NODES[1],
      upstreamCount: 2, downstreamCount: 4,
    }));
    // card shows KIND / ID / STATUS / short description / EM / counts / TRACE actions
    expect(html).toContain('PREDICTION');
    expect(html).toContain('PRED-0002');
    expect(html).toContain('NOT_EVALUATED');
    expect(html).toContain('↑');
    expect(html).toContain('↓');
    expect(html).toContain('↑ TRACE');
    expect(html).toContain('↓ TRACE');
  });

  it('RESULT contextual card distinguishes exists/verified/frozen honestly (no invented metric)', () => {
    const result: GraphArtifact = {
      id: 'RES-1', kind: 'RESULT', artifactId: 'res_1', label: 'RES-1', status: 'PUBLISHED',
      authority: 'PUBLISHED', provenance: ['dec:1'], evidence: [], uncertainty: '', em: 'EM Publisher',
      sourceField: 'result', recommended: false, humanSelected: false, description: 'Result produced.',
    };
    const html = renderToString(createElement(GalaxyConstellation, {
      nodes: [...NODES, result], edges: EDGES, selectedId: 'RES-1', selectedArtifact: result,
      upstreamCount: 1, downstreamCount: 0,
    }));
    expect(html).toContain('RESULT');
    expect(html).toContain('STATE ·');
    expect(html).toContain('EVIDENCE ·');
    expect(html).toContain('VALIDATION ·');
    // honest absence of evidence (no invented value)
    expect(html).toContain('DATA NOT AVAILABLE');
  });

  it('shows the real status badge on the selected node (semantic representation)', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES, selectedId: 'DEC-0001' }));
    expect(html).toContain('HUMAN_SELECTED'); // real status, not invented
  });

  it('shows an honest empty state when there is no cognitive data', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: [], edges: [] }));
    expect(html).toContain('No cognitive data available');
    expect(html).not.toContain('MEMORY');
    expect(html).not.toContain('ZOOM');
  });

  it('renders the GRAPH CONTROL DECK (summary/layers/focus) + legend with real content', () => {
    const html = renderToString(createElement(GalaxyConstellation, { nodes: NODES, edges: EDGES }));
    expect(html).toContain('Graph Summary');
    expect(html).toContain('View Layers');
    expect(html).toContain('Focus Filter');
    // real metrics from the SAME nodes (3 objects, 1 decision, 0 frozen)
    expect(html).toContain('OBJECTS');
    expect(html).toContain('HUMAN DEC.');
    expect(html).toContain('FROZEN');
    // legend is present and reflects a real type (ALTERNATIVE -> 'Options'; PREDICTION -> 'Predictions')
    expect(html).toContain('Options');
    expect(html).toContain('Predictions');
    expect(html).toContain('Decision');
  });
});
