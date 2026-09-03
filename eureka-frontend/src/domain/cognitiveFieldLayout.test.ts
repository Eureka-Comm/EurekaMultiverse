import { describe, it, expect } from 'vitest';
import { buildCognitiveProjection } from './cognitiveProjection';
import { buildCognitiveProjectionGraph } from './cognitiveProjectionGraph';
import {
  layoutCognitiveField,
  computeFocusMask,
  mathematicalFieldLabel,
} from './cognitiveFieldLayout';

const open = {
  schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
  work: { workId: 'W-OPEN', status: 'RUNNING', userIntent: 'Estado de la evidencia sobre X' },
  execution_plan: { steps: [] },
  state: {},
  evidence: [],
  extracted_evidence: { 'EVI-CONTEXT': { text_blocks: ['block one two three'] } },
  visualizations: [],
  available_capabilities: [],
  gaps: [],
  conditions: [],
  revision: 1,
  extracted_entities: {},
  problem: { problem_id: 'PROB-X', objective: 'Pregunta de investigación', governance_status: 'GOVERNED' },
  knowledge: {
    findings: [
      { finding_id: 'FND-1', statement: 'A supported finding.', status: 'VALIDATED', evidence_refs: ['EVI-CONTEXT'], provenance: ['Task[x]'], authority: 'VALIDATED' },
      { finding_id: 'FND-2', statement: 'An unsupported finding.', status: 'UNSUPPORTED', evidence_refs: ['EVI-CONTEXT'], provenance: ['Task[x]'], authority: 'UNSUPPORTED' },
    ],
  },
  predictive_knowledge: {
    status: 'NOT_EVALUATED',
    predictions: [
      { prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: null, validation_status: 'NOT_EVALUATED', mse: null },
      { prediction_id: 'PRED-2', model_type: 'GCLV', predicted_value: 0.83, validation_status: 'VALIDATED', mse: 0.02 },
    ],
  },
  open_research: {
    status: 'OPEN_INSUFFICIENT_INFORMATION',
    operation_kind: 'OPEN_RESEARCH',
    is_open: true,
    decision_reached: false,
    decision_pending: true,
    items: [{ kind: 'PENDING_HUMAN_DECISION', label: 'No human decision yet', source_ref: 'human_decision' }],
    decision_relevant_knowledge: ['FND-1', 'FND-2'],
    summary: 'Operation is open.',
  },
};

describe('LS91 COGNITIVE FIELD LAYOUT (pure / single-source)', () => {
  it('is deterministic: identical graph -> identical entity positions', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const a = layoutCognitiveField(graph);
    const b = layoutCognitiveField(graph);
    a.entities.forEach((e, i) => {
      expect(e.position).toEqual(b.entities[i].position);
    });
    expect(a.thread).toEqual(b.thread);
  });

  it('never fabricates entities or links (1:1 with the governed graph)', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const layout = layoutCognitiveField(graph);
    expect(layout.entities.length).toBe(graph.nodes.length);
    expect(layout.links.length).toBe(graph.edges.length);
    // every entity id is a real graph node
    const ids = new Set(graph.nodes.map((n) => n.id));
    layout.entities.forEach((e) => expect(ids.has(e.id)).toBe(true));
  });

  it('maps PROGRESSION, DISPERSION and AUTHORITY HEIGHT semantics', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const layout = layoutCognitiveField(graph);
    const problem = layout.entities.find((e) => e.kind === 'PROBLEM')!;
    const evi = layout.entities.find((e) => e.kind === 'EVIDENCE')!;
    const fndValid = layout.entities.find((e) => e.kind === 'FINDING' && e.tone === 'VALIDATED')!;
    const fndUnsup = layout.entities.find((e) => e.kind === 'FINDING' && e.tone === 'UNSUPPORTED')!;
    // progression: evidence is further along +X than the question origin
    expect(evi.position.x).toBeGreaterThan(problem.position.x);
    // no fabricated negatives / vanishing artifacts
    expect(evi.position.z).toBeGreaterThanOrEqual(-60).toBeLessThanOrEqual(60);
    // authority height: validated finding floats higher than unsupported
    expect(fndValid.position.y).toBeGreaterThan(fndUnsup.position.y);
  });

  it('preserves NOT_EVALUATED on the mathematical field label (never a fake surface)', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const pred1 = graph.nodes.find((n) => n.id === 'PRED-1')!;
    const pred2 = graph.nodes.find((n) => n.id === 'PRED-2')!;
    expect(mathematicalFieldLabel(pred1)).toContain('NOT EVALUATED');
    expect(mathematicalFieldLabel(pred2)).toContain('VALUE');
    // honestly NOT_EVALUATED value stays null in the graph & layout
    const layout = layoutCognitiveField(graph);
    const lp1 = layout.entities.find((e) => e.id === 'PRED-1')!;
    const lp2 = layout.entities.find((e) => e.id === 'PRED-2')!;
    expect(lp1.numericValue).toBeNull();
    expect(lp2.numericValue).toBeCloseTo(0.83);
  });

  it('computes the focus mask: focal + direct relations visible, unrelated attenuated', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const focusNode = graph.nodes.find((n) => n.kind === 'FINDING')!.id; // FND-1, linked to EVI-CONTEXT
    const mask = computeFocusMask(graph, focusNode);
    expect(mask.get(focusNode)).toBe(1.0);
    // direct neighbours (evidence) are high
    expect(mask.get('EVI-CONTEXT')).toBe(0.85);
    // unrelated (problem) attenuated
    const problem = graph.nodes.find((n) => n.kind === 'PROBLEM')!.id;
    expect(mask.get(problem)).toBeLessThan(0.3);
  });

  it('returns a uniform mask when nothing is focused (no premature dimming)', () => {
    const dto = buildCognitiveProjection(open as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const mask = computeFocusMask(graph, null);
    graph.nodes.forEach((n) => expect(mask.get(n.id)).toBe(1));
  });

  it('selects the human decision as HUMAN tone, distinct from candidate alternatives', () => {
    // Build a state that has a human decision + candidate alternatives.
    const decisionState = {
      ...open,
      human_decision: { decision_id: 'DEC-1', selected_alternative_id: 'ALT-001', decision_authority: 'HUMAN_OPERATOR' },
      prescriptive_knowledge: {
        prescriptions: [{
          prescription_id: 'PRESC-1',
          alternatives: [
            { alternative_id: 'ALT-001', description: 'Human-chosen course of action.' },
            { alternative_id: 'ALT-002', description: 'Not chosen.' },
          ],
          rationale: 'Reason.',
          authority: 'PROPOSAL',
        }],
      },
      decision_points: [{ decision_id: 'DEC-1', recommended_option: null, status: 'ANSWERED', human_selection: 'ALT-001' }],
    };
    const dto = buildCognitiveProjection(decisionState as any);
    const graph = buildCognitiveProjectionGraph(dto);
    const layout = layoutCognitiveField(graph);
    const dec = layout.entities.find((e) => e.kind === 'DECISION')!;
    const chosen = layout.entities.find((e) => e.kind === 'ALTERNATIVE' && e.humanSelected)!;
    const cand = layout.entities.find((e) => e.kind === 'ALTERNATIVE' && !e.humanSelected && !e.recommended)!;
    expect(dec.tone).toBe('HUMAN');
    expect(dec.authority).toBe('HUMAN_AUTHORIZED');
    expect(chosen.tone).toBe('HUMAN');
    expect(cand.tone).not.toBe('HUMAN');
    // the human decision always floats to the top of the stage (authority height)
    expect(dec.position.y).toBeGreaterThan(cand.position.y);
  });
});
