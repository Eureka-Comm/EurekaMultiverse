import { describe, it, expect } from 'vitest';
import { buildCognitiveProjection } from './cognitiveProjection';
import type { CanonicalWorkState } from './canonicalSchema';

// Minimal valid canonical state helper (tolerant projection reads via `any`).
function base(): any {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'W1', status: 'COMPLETED', userIntent: 'Quiero analizar costos' },
    execution_plan: { steps: [] },
    state: {},
    evidence: [],
    extracted_evidence: {},
    visualizations: [],
    available_capabilities: [],
    gaps: [],
    conditions: [],
    revision: 1,
    extracted_entities: {},
  };
}

describe('CognitiveProjection (LS86)', () => {
  it('TEST 1 — normal canonical state -> complete DTO', () => {
    const p = buildCognitiveProjection(base() as any);
    expect(p.question).toBe('Quiero analizar costos');
    expect(p.humanDecision.authority).toBe('PENDING');
    expect(p.humanDecision.preserved).toBe(false);
    expect(p.projectionConflict).toBe(false);
  });

  it('TEST 2 — human decision ALT-01 is preserved', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01');
    expect(p.humanDecision.decisionId).toBe('DEC-1');
    expect(p.humanDecision.authority).toBe('HUMAN_AUTHORIZED');
  });

  it('TEST 3 — recommendation != human decision', () => {
    const s = base();
    s.decision_points = [{ recommended_option: 'ALT-02' }];
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    expect(p.recommendedOption).toBe('ALT-02');
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01');
    expect(p.recommendedOption).not.toBe(p.humanDecision.selectedAlternativeId);
  });

  it('TEST 4 — NOT_EVALUATED prediction preserved', () => {
    const s = base();
    s.predictive_knowledge = {
      predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: null, validation_status: 'NOT_EVALUATED', evidence_refs: [] }],
    };
    const p = buildCognitiveProjection(s as any);
    expect(p.predictions[0].status).toBe('NOT_EVALUATED');
    expect(p.predictions[0].value).toBeNull();
  });

  it('TEST 5 — UNSUPPORTED finding preserved', () => {
    const s = base();
    s.knowledge = { findings: [{ finding_id: 'FND-1', statement: 'x', status: 'UNSUPPORTED', evidence_refs: [], provenance: [] }] };
    const p = buildCognitiveProjection(s as any);
    expect(p.findings[0].status).toBe('UNSUPPORTED');
  });

  it('TEST 6 — SIMULATED execution preserved', () => {
    const s = base();
    s.execution_state = { status: 'COMPLETED' };
    const p = buildCognitiveProjection(s as any);
    expect(p.execution?.simulated).toBe(true);
    expect(p.execution?.status).toBe('COMPLETED');
  });

  it('TEST 7 — frozen result signature preserved', () => {
    const s = base();
    s.frozen_result = { result_id: 'FROZEN-1', freeze_signature: 'abc123', status: 'FROZEN' };
    const p = buildCognitiveProjection(s as any);
    expect(p.frozenResult?.signature).toBe('abc123');
  });

  it('TEST 8 — provenance lineage via real IDs', () => {
    const s = base();
    s.knowledge = { findings: [{ finding_id: 'FND-1', status: 'VALIDATED', statement: 'y', evidence_refs: [], provenance: ['Task[task_001]'] }] };
    s.predictive_knowledge = { predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', status: 'VALIDATED', evidence_refs: [] }] };
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    expect(p.lineage).toContain('FND-1');
    expect(p.lineage).toContain('PRED-1');
    expect(p.lineage).toContain('DEC-1');
  });

  it('TEST 9 — actionPlan selected_alternative_id == human_selection -> PASS', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    s.action_plan = { plan_id: 'AP-1', selected_alternative_id: 'ALT-01', human_decision_id: 'DEC-1', validation_status: 'VALIDATED', authority: 'HUMAN' };
    const p = buildCognitiveProjection(s as any);
    expect(p.humanDecision.selectedAlternativeId).toBe(p.actionPlan?.selectedAlternativeId);
    expect(p.projectionConflict).toBe(false);
  });

  it('TEST 10 — actionPlan mismatch -> PROJECTION_CONFLICT (never autocorrect)', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    s.action_plan = { plan_id: 'AP-1', selected_alternative_id: 'ALT-02', human_decision_id: 'DEC-1', validation_status: 'VALIDATED', authority: 'HUMAN' };
    const p = buildCognitiveProjection(s as any);
    expect(p.projectionConflict).toBe(true);
    expect(p.actionPlan?.selectedAlternativeId).toBe('ALT-02');
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01');
  });

  it('TEST No-invention — null value + NOT_EVALUATED + recommendation/decision distinct + SIMULATED', () => {
    const s = base();
    s.predictive_knowledge = { predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: null, validation_status: 'NOT_EVALUATED', evidence_refs: [] }] };
    s.decision_points = [{ recommended_option: 'ALT-02' }];
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    s.execution_state = { status: 'COMPLETED' };
    const p = buildCognitiveProjection(s as any);
    expect(p.predictions[0].status).toBe('NOT_EVALUATED');
    expect(p.predictions[0].value).toBeNull();
    expect(p.recommendedOption).toBe('ALT-02');
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01');
    expect(p.execution?.simulated).toBe(true);
  });
});
