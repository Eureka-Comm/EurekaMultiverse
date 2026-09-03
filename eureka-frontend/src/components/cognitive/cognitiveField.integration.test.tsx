import { describe, it, expect } from 'vitest';
import { renderToString } from 'react-dom/server';
import { createElement } from 'react';
import { buildCognitiveProjection } from '../../domain/cognitiveProjection';
import { buildCognitiveProjectionGraph } from '../../domain/cognitiveProjectionGraph';
import { layoutCognitiveField } from '../../domain/cognitiveFieldLayout';
import { CognitiveFieldFallback } from './CognitiveFieldFallback';
import { CognitiveField } from './CognitiveField';

/**
 * LS91 — renderer integration smoke (node env, react-dom/server). Verifies the
 * field layer mounts without a WebGL context (the GPU renderer is only created in
 * a browser effect), and that the DOM/SVG fallback carries the SAME honest
 * semantics (no fabricated surface, human-authority preserved, real labels).
 */
function openState() {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'W-OPEN', status: 'RUNNING', userIntent: 'Pregunta de investigación' },
    execution_plan: { steps: [] },
    state: {},
    evidence: [],
    extracted_evidence: { 'EVI-CONTEXT': { text_blocks: ['block one two three four five'] } },
    visualizations: [],
    available_capabilities: [],
    gaps: [],
    conditions: [],
    revision: 1,
    extracted_entities: {},
    problem: { problem_id: 'PROB-X', objective: 'Pregunta', governance_status: 'GOVERNED' },
    knowledge: { findings: [{ finding_id: 'FND-1', statement: 'A finding.', status: 'VALIDATED', evidence_refs: ['EVI-CONTEXT'], provenance: ['Task[x]'], authority: 'VALIDATED' }] },
    predictive_knowledge: {
      status: 'NOT_EVALUATED',
      predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: null, validation_status: 'NOT_EVALUATED', mse: null }],
    },
    open_research: {
      status: 'OPEN_INSUFFICIENT_INFORMATION',
      operation_kind: 'OPEN_RESEARCH',
      is_open: true,
      decision_reached: false,
      decision_pending: true,
      items: [{ kind: 'PENDING_HUMAN_DECISION', label: 'No decision yet', source_ref: 'human_decision' }],
      decision_relevant_knowledge: ['FND-1'],
      summary: 'Operation is open.',
    },
  };
}

describe('LS91 COGNITIVE FIELD renderer integration (SSR, no GPU)', () => {
  it('CognitiveField mounts without a WebGL context (server render does not throw)', () => {
    const dto = buildCognitiveProjection(openState() as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const html = renderToString(createElement(CognitiveField, { graph, onSelect: () => {} }));
    // first paint is the instrument HUD + field container (renderer created only in a browser effect)
    expect(html).toContain('Cognitive Field');
    expect(html).toContain('data-cognitive-field');
  });

  it('shows the honest "no governed graph" state when there is no data', () => {
    const dto = buildCognitiveProjection(openState() as any);
    const graph = buildCognitiveProjectionGraph({ ...dto, problem: null, evidence: [], findings: [], predictions: [], prescription: null, humanDecision: { decisionId: null, selectedAlternativeId: null, authority: 'PENDING' as const, status: 'PENDING', preserved: false }, actionPlan: null, execution: null, result: null, frozenResult: null, recommendedOption: null, lineage: [] } as any);
    const html = renderToString(createElement(CognitiveField, { graph }));
    expect(html).toContain('No governed graph');
  });

  it('DOM/SVG fallback carries honest semantics (NOT EVALUATED, real ids, thread)', () => {
    const dto = buildCognitiveProjection(openState() as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const layout = layoutCognitiveField(graph);
    const html = renderToString(createElement(CognitiveFieldFallback, { layout }));
    expect(html).toContain('svg');
    expect(html).toContain('FND-1');
    expect(html).toContain('PRED-1');
    expect(html).toContain('NOT EVALUATED');
    expect(html).toContain('QUESTION');
    expect(html).toContain('cognitive thread');
  });

  it('HTTP renderer never mutates the graph (output is pure layout of the same nodes)', () => {
    const dto = buildCognitiveProjection(openState() as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const idsBefore = graph.nodes.map((n) => n.id).sort().join(',');
    const layout = layoutCognitiveField(graph, { focusedId: 'FND-1' });
    // focus only changes salience, never the entity set (single source untouched)
    expect(layout.entities.map((e) => e.id).sort().join(',')).toBe(idsBefore);
    expect(layout.entities.length).toBe(graph.nodes.length);
  });
});
