import { describe, it, expect } from 'vitest';
import { buildCognitiveProjection } from './cognitiveProjection';
import { CanonicalWorkStateSchema } from './canonicalSchema';
import {
  buildCognitiveProjectionGraph,
  relatedArtifactsForEM,
  emRoleLabel,
} from './cognitiveProjectionGraph';
import type { CanonicalWorkState } from './canonicalSchema';

// Minimal valid canonical state (tolerant projection).
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

describe('Forensic validation (§28) — projection/UI truthfulness', () => {
  it('A — LLM says "ALT-02 best" but humanSelection stays ALT-01 (recommendation != decision)', () => {
    const s = base();
    s.decision_points = [{ recommended_option: 'ALT-02', recommendation_reason: 'LLM: ALT-02 best' }];
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    expect(p.recommendedOption).toBe('ALT-02'); // system recommendation (LLM) is preserved
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01'); // human choice is NEVER overwritten
    expect(p.humanDecision.authority).toBe('HUMAN_AUTHORIZED');
    expect(p.recommendedOption).not.toBe(p.humanDecision.selectedAlternativeId);
  });

  it('B — recommended_option=ALT-02 + human_selection=ALT-01 → RECOMMENDED=ALT-02 / HUMAN DECISION=ALT-01', () => {
    const s = base();
    s.decision_points = [{ recommended_option: 'ALT-02' }];
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    s.prescriptive_knowledge = {
      prescriptions: [{
        prescription_id: 'PRESC-1',
        alternatives: [
          { alternative_id: 'ALT-01', description: 'Option one' },
          { alternative_id: 'ALT-02', description: 'Option two' },
        ],
        rationale: 'x',
      }],
    };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);

    expect(p.recommendedOption).toBe('ALT-02');
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-01');

    const alt02 = g.nodes.find((n) => n.kind === 'ALTERNATIVE' && n.id === 'ALT-02')!;
    const alt01 = g.nodes.find((n) => n.kind === 'ALTERNATIVE' && n.id === 'ALT-01')!;
    expect(alt02.recommended).toBe(true);        // RECOMMENDED = ALT-02
    expect(alt01.humanSelected).toBe(true);      // HUMAN DECISION = ALT-01
    expect(alt02.humanSelected).toBe(false);
    expect(alt01.recommended).toBe(false);
  });

  it('C — prediction NOT_EVALUATED (value null) → shows NOT_EVALUATED', () => {
    const s = base();
    s.predictive_knowledge = {
      predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: null, validation_status: 'NOT_EVALUATED', evidence_refs: [] }],
    };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    expect(p.predictions[0].status).toBe('NOT_EVALUATED');
    expect(p.predictions[0].value).toBeNull();
    const pred = g.nodes.find((n) => n.kind === 'PREDICTION')!;
    expect(pred.authority).toBe('NOT_EVALUATED');
    expect(pred.status).toBe('NOT_EVALUATED');
    expect(pred.uncertainty).toContain('NOT EVALUATED');
  });

  it('D — finding UNSUPPORTED → shows UNSUPPORTED', () => {
    const s = base();
    s.knowledge = { findings: [{ finding_id: 'FND-1', statement: 'x', status: 'UNSUPPORTED', evidence_refs: [], provenance: [] }] };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    expect(p.findings[0].status).toBe('UNSUPPORTED');
    const fnd = g.nodes.find((n) => n.kind === 'FINDING')!;
    expect(fnd.authority).toBe('UNSUPPORTED');
    expect(fnd.status).toBe('UNSUPPORTED');
  });

  it('E — execution SIMULATED → shows SIMULATED', () => {
    const s = base();
    s.execution_state = { execution_id: 'EXEC-1', status: 'COMPLETED', execution_level: '1/2' };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    expect(p.execution?.simulated).toBe(true);
    const exec = g.nodes.find((n) => n.kind === 'EXECUTION')!;
    expect(exec.authority).toBe('SIMULATED');
    expect(exec.uncertainty).toContain('SIMULATED');
  });

  it('F — ActionPlan ALT-01 vs human ALT-02 → projectionConflict (never autocorrect)', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-02' };
    s.action_plan = { plan_id: 'AP-1', selected_alternative_id: 'ALT-01', human_decision_id: 'DEC-1', validation_status: 'VALIDATED', authority: 'HUMAN' };
    const p = buildCognitiveProjection(s as any);
    expect(p.projectionConflict).toBe(true);
    // Both are PRESERVED — the conflict is never resolved/corrected by the projection.
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-02');
    expect(p.actionPlan?.selectedAlternativeId).toBe('ALT-01');
  });

  it('G — no evidence → DATA NOT AVAILABLE (never invent a node)', () => {
    const s = base();
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    expect(g.nodes.some((n) => n.kind === 'EVIDENCE')).toBe(false);
    expect(g.nodes.some((n) => n.kind === 'FINDING')).toBe(false);
    expect(g.nodes.some((n) => n.kind === 'PREDICTION')).toBe(false);
  });

  it('H — changing Publisher narrative text does not corrupt canonical truth', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    s.action_plan = { plan_id: 'AP-1', selected_alternative_id: 'ALT-01', human_decision_id: 'DEC-1', validation_status: 'VALIDATED', authority: 'HUMAN' };
    const p1 = buildCognitiveProjection(s as any);
    // Simulate a Publisher that rewrites only narrative text (result summary).
    s.state = { result: { result_id: 'WR-1', summary: 'Rewritten narrative text', status: 'AVAILABLE' } };
    const p2 = buildCognitiveProjection(s as any);
    // Canonical decision/authority/conflict are UNCHANGED by narrative rewriting.
    expect(p2.humanDecision.selectedAlternativeId).toBe('ALT-01');
    expect(p2.actionPlan?.selectedAlternativeId).toBe('ALT-01');
    expect(p2.projectionConflict).toBe(false);
    expect(p2.humanDecision.authority).toBe('HUMAN_AUTHORIZED');
    // It does surface the rewritten result, but only as the result field.
    expect(p2.result?.summary).toBe('Rewritten narrative text');
  });

  it('I — click Predictor → ACFL_DETERMINISTIC / MathEngine / GCLV / prediction artifacts', () => {
    const s = base();
    s.predictive_knowledge = {
      predictions: [{ prediction_id: 'PRED-1', model_type: 'ACFL_ENGINE', predicted_value: 4.2, validation_status: 'VALIDATED', evidence_refs: [] }],
    };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    const arts = relatedArtifactsForEM('EM Predictor', g);
    expect(arts.some((a) => a.kind === 'PREDICTION')).toBe(true);
    const role = emRoleLabel('EM Predictor');
    expect(role).toContain('ACFL_DETERMINISTIC');
    expect(role).toContain('MathEngine');
    expect(role).toContain('GCLV');
  });

  it('J — click HITL (Prescriptor/Installer) → human authority + decision', () => {
    const s = base();
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    const dec = g.nodes.find((n) => n.kind === 'DECISION')!;
    expect(dec.authority).toBe('HUMAN_AUTHORIZED');
    const arts = relatedArtifactsForEM('EM Prescriptor', g);
    expect(arts.some((a) => a.kind === 'DECISION')).toBe(true);
    expect(emRoleLabel('EM Prescriptor')).toContain('HITL');
  });

  it('Edges never use causation — allowed semantics only', () => {
    const s = base();
    s.knowledge = { findings: [{ finding_id: 'FND-1', statement: 'x', status: 'VALIDATED', evidence_refs: ['EVI-1'], provenance: [] }] };
    s.extracted_evidence = { 'EVI-1': { text_blocks: ['t'] } };
    s.human_decision = { decision_id: 'DEC-1', selected_alternative_id: 'ALT-01' };
    const p = buildCognitiveProjection(s as any);
    const g = buildCognitiveProjectionGraph(p);
    const labels = g.edges.map((e) => e.label);
    const allowed = ['derived_from', 'supports', 'produced_by', 'selected_by', 'authorized_by', 'executed_as', 'frozen_as'];
    labels.forEach((l) => expect(allowed).toContain(l));
    expect(labels.includes('causes' as any)).toBe(false);
  });

  // ---- LS90 — OPEN RESEARCH cognitive operation (what remains open) ----
  describe('LS90 — what remains open (governed, never a decision)', () => {
    it('maps an OPEN_RESEARCH projection truthfully (no decision reached, insufficient info)', () => {
      const s = base();
      s.open_research = {
        status: 'OPEN_INSUFFICIENT_INFORMATION',
        operation_kind: 'OPEN_RESEARCH',
        is_open: true,
        decision_reached: false,
        decision_pending: true,
        items: [
          { kind: 'UNRESOLVED_QUESTION', label: 'No hay datos sobre X', source_ref: 'knowledge.unknowns[0]' },
          { kind: 'PENDING_HUMAN_DECISION', label: 'No human decision yet', source_ref: 'human_decision' },
          { kind: 'DATA_NOT_AVAILABLE', label: 'No predictive knowledge', source_ref: 'predictive_knowledge.status' },
        ],
        decision_relevant_knowledge: ['FND-1', 'PRED-1'],
        summary: 'Operation is open - no human decision has been reached.',
        provenance: ['LS90 Python-derived open-research projection'],
        built: 'now',
      };
      const p = buildCognitiveProjection(s as any);
      expect(p.whatRemainsOpen).not.toBeNull();
      expect(p.whatRemainsOpen!.operationKind).toBe('OPEN_RESEARCH');
      expect(p.whatRemainsOpen!.isOpen).toBe(true);
      expect(p.whatRemainsOpen!.decisionReached).toBe(false);
      expect(p.whatRemainsOpen!.decisionPending).toBe(true);
      expect(p.whatRemainsOpen!.status).toBe('OPEN_INSUFFICIENT_INFORMATION');
      // honest items preserved verbatim (kind, label, sourceRef), never invented
      expect(p.whatRemainsOpen!.items.length).toBe(3);
      expect(p.whatRemainsOpen!.items.map((i) => i.kind)).toEqual(['UNRESOLVED_QUESTION', 'PENDING_HUMAN_DECISION', 'DATA_NOT_AVAILABLE']);
      // decision-relevant knowledge = real artifact ids
      expect(p.whatRemainsOpen!.decisionRelevantKnowledge).toEqual(['FND-1', 'PRED-1']);
      // It is NEVER presented as a closed decision (decision remains pending)
      expect(p.whatRemainsOpen!.decisionPending).toBe(true);
      expect(p.humanDecision.selectedAlternativeId).toBeNull();
    });

    it('maps a CLOSED (decision reached) projection truthfully', () => {
      const s = base();
      s.open_research = {
        status: 'CLOSED', operation_kind: 'DECISION', is_open: false,
        decision_reached: true, decision_pending: false,
        items: [], decision_relevant_knowledge: ['FND-1'], summary: 'Operation reached a human decision.',
      };
      const p = buildCognitiveProjection(s as any);
      expect(p.whatRemainsOpen!.operationKind).toBe('DECISION');
      expect(p.whatRemainsOpen!.isOpen).toBe(false);
      expect(p.whatRemainsOpen!.decisionReached).toBe(true);
      expect(p.whatRemainsOpen!.decisionPending).toBe(false);
    });

    it('returns null when the backend did not emit an open-research projection (honest absence)', () => {
      const s = base();
      const p = buildCognitiveProjection(s as any);
      expect(p.whatRemainsOpen).toBeNull();
      // never fabricates a decision/ranking for the absent projection
      expect(p.humanDecision.selectedAlternativeId).toBeNull();
    });

    it('the Zod state contract RETAINS open_research (live path, not just the shot harness)', () => {
      const s = base();
      s.state = { acfl: { weights: {}, criteria: [], alternatives: [], normalized_scores: {}, frontier: [], sensitivity: {} }, feasible_only: false };
      s.open_research = { status: 'OPEN', operation_kind: 'OPEN_RESEARCH', is_open: true, decision_reached: false, decision_pending: true, items: [], decision_relevant_knowledge: [], summary: '' };
      const parsed = CanonicalWorkStateSchema.parse(s);
      const p = buildCognitiveProjection(parsed as unknown as CanonicalWorkState);
      expect((parsed as any).open_research).toBeTruthy();
      expect(p.whatRemainsOpen).not.toBeNull();
      expect(p.whatRemainsOpen!.operationKind).toBe('OPEN_RESEARCH');
    });

    it('coerces an invalid open-item kind to INSUFFICIENT_INFORMATION (never crashes)', () => {
      const s = base();
      s.open_research = {
        status: 'OPEN', operation_kind: 'OPEN_RESEARCH', is_open: true,
        decision_reached: false, decision_pending: true,
        items: [{ kind: 'NOT_A_REAL_KIND', label: 'x', source_ref: 'y' }],
        decision_relevant_knowledge: [], summary: '',
      };
      const p = buildCognitiveProjection(s as any);
      expect(p.whatRemainsOpen!.items[0].kind).toBe('INSUFFICIENT_INFORMATION');
    });
  });
});
