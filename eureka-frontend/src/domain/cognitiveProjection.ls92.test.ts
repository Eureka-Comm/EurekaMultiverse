import { describe, it, expect } from 'vitest';
import { buildCognitiveProjection } from './cognitiveProjection';

/**
 * LS92 — governed LLM cognitive answer: ANSWER-first + honest states.
 *
 * A KNOWLEDGE_ANSWER operation carries: an AVAILABLE result (the LLM semantic answer),
 * NOT_APPLICABLE pruned EMs, a PENDING human decision, and NO fabricated execution.
 * The projection must deliver the answer first while preserving these honest
 * NOT_EVALUATED / PENDING / NOT_EXECUTED states — never inventing a decision or an action.
 */
function knowledgeState(overrides: any = {}): any {
  return {
    schema_version: 'EUREKA_CANONICAL_WORK_STATE_V2',
    work: { workId: 'WK', status: 'COMPLETED', userIntent: '¿Qué es el aprendizaje activo?' },
    execution_plan: { steps: [] },
    state: {
      result: {
        result_id: 'WR-1',
        status: 'AVAILABLE',
        summary: 'El aprendizaje activo es un enfoque pedagógico donde el estudiante participa activamente...',
      },
    },
    evidence: [],
    extracted_evidence: {},
    visualizations: [],
    available_capabilities: [],
    gaps: [],
    conditions: [],
    revision: 3,
    extracted_entities: {},
    problem: {
      problem_id: 'PROB-1',
      objective: '¿Qué es el aprendizaje activo?',
      operation_mode: 'KNOWLEDGE_ANSWER',
      governance_status: 'GOVERNED',
    },
    em_pipeline: [
      { canonical_em: 'EM Core', status: 'COMPLETED', step_ids: [] },
      { canonical_em: 'EM Structurer', status: 'COMPLETED', step_ids: [] },
      { canonical_em: 'EM Descriptor', status: 'COMPLETED', step_ids: [] },
      { canonical_em: 'EM Predictor', status: 'NOT_APPLICABLE', step_ids: [] },
      { canonical_em: 'EM Prescriptor', status: 'NOT_APPLICABLE', step_ids: [] },
      { canonical_em: 'EM Actioner', status: 'NOT_APPLICABLE', step_ids: [] },
      { canonical_em: 'EM Installer', status: 'NOT_APPLICABLE', step_ids: [] },
      { canonical_em: 'EM Publisher', status: 'COMPLETED', step_ids: [] },
    ],
    knowledge: {
      findings: [
        { finding_id: 'FND-1', statement: 'El aprendizaje activo involucra participación.', status: 'VALIDATED', evidence_refs: [], provenance: [] },
      ],
    },
    predictive_knowledge: { status: 'NONE', predictions: [] },
    prescriptive_knowledge: { prescriptions: [] },
    human_decision: null,
    execution_state: null,
    open_research: {
      status: 'OPEN_INSUFFICIENT_INFORMATION',
      operation_kind: 'OPEN_RESEARCH',
      is_open: true,
      decision_reached: false,
      decision_pending: true,
      items: [
        { kind: 'NOT_EVALUATED', label: 'Predicción no evaluada (sin valor numérico).', source_ref: 'predictive_knowledge.predictions[0]' },
        { kind: 'PENDING_HUMAN_DECISION', label: 'Sin decisión humana aún.', source_ref: 'human_decision' },
      ],
      decision_relevant_knowledge: ['FND-1'],
      summary: 'Operación abierta — sin decisión humana.',
    },
    ...overrides,
  };
}

describe('CognitiveProjection · LS92 governed LLM answer', () => {
  it('delivers the LLM semantic answer FIRST with result.status AVAILABLE', () => {
    const p = buildCognitiveProjection(knowledgeState() as any);
    expect(p.result?.status).toBe('AVAILABLE');
    expect(p.result?.summary).toContain('El aprendizaje activo es un enfoque pedagógico');
  });

  it('preserves the honest OPEN state (decision still pending, never concluded)', () => {
    const p = buildCognitiveProjection(knowledgeState() as any);
    expect(p.whatRemainsOpen?.isOpen).toBe(true);
    expect(p.whatRemainsOpen?.decisionReached).toBe(false);
    expect(p.whatRemainsOpen?.decisionPending).toBe(true);
    const kinds = (p.whatRemainsOpen?.items || []).map((i) => i.kind);
    expect(kinds).toContain('NOT_EVALUATED');
    expect(kinds).toContain('PENDING_HUMAN_DECISION');
  });

  it('does NOT fabricate a human decision or an execution when none exists', () => {
    const p = buildCognitiveProjection(knowledgeState() as any);
    expect(p.humanDecision.selectedAlternativeId).toBeNull();
    expect(p.humanDecision.decisionId).toBeNull();
    expect(p.execution).toBeNull();
    expect(p.recommendedOption).toBeNull();
  });

  it('keeps the answer available alongside NOT_APPLICABLE pruned EMs', () => {
    const p = buildCognitiveProjection(knowledgeState() as any);
    expect(p.result?.status).toBe('AVAILABLE'); // answer present
    expect(p.predictions.length).toBe(0); // math NOT_EVALUATED / not evaluated
  });

  it('keeps a DECISION operation distinct: recommended != human decision (no autocorrect)', () => {
    const s = knowledgeState({
      state: { result: { result_id: 'WR-2', status: 'AVAILABLE', summary: 'Recomiendo ALT-002.' } },
      prescriptive_knowledge: {
        prescriptions: [
          {
            prescription_id: 'PRESC-1',
            alternatives: [
              { alternative_id: 'ALT-001', description: 'Opción A' },
              { alternative_id: 'ALT-002', description: 'Opción B' },
            ],
            selected_alternative: { alternative_id: 'ALT-002', description: 'Opción B' },
          },
        ],
      },
      human_decision: {
        decision_id: 'DEC-1',
        decision_type: 'SELECT_ALTERNATIVE',
        selected_alternative_id: 'ALT-001',
      },
      action_plan: {
        plan_id: 'AP-1',
        selected_alternative_id: 'ALT-002',
      },
    } as any);
    const p = buildCognitiveProjection(s);
    // The projection must keep recommendation and decision distinct, never autocorrect.
    expect(p.projectionConflict).toBe(true);
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-001');
  });
});
