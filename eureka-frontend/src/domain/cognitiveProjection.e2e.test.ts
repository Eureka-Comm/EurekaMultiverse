import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { buildCognitiveProjection } from './cognitiveProjection';
import { buildCognitiveProjectionGraph, relatedArtifactsForEM, emRoleLabel } from './cognitiveProjectionGraph';

/**
 * §28 E2E (data layer) — real backend output → cognitive story/decision render.
 *
 * This drives the projection + graph with a REAL canonical state emitted by the
 * 8-EM pipeline (captured to src/fixtures/eureka_completed_state.json). It proves
 * the COGNITIVE STORY + DECISION surfaces show the actual human selection and the
 * real authorities, and that absent artifacts (action_plan / execution_state) are
 * NOT fabricated.
 */
const fixturePath = fileURLToPath(new URL('../fixtures/eureka_completed_state.json', import.meta.url));

describe('E2E — real completed canonical state → COGNITIVE STORY / DECISION render', () => {
  it('maps a REAL completed state to its true cognitive projection', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const p = buildCognitiveProjection(state);

    // The human decision is HUMAN_AUTHORIZED and reads from human_decision.
    expect(p.humanDecision.selectedAlternativeId).toBe('ALT-001');
    expect(p.humanDecision.decisionId).toBe('DEC-8b8482');
    expect(p.humanDecision.authority).toBe('HUMAN_AUTHORIZED');

    // The system recommendation is separate and actually empty for this work.
    expect(p.recommendedOption === null || p.recommendedOption === '').toBe(true);

    // Predictions are NOT_EVALUATED (no numeric value) — preserved, not invented.
    expect(p.predictions.length).toBeGreaterThan(0);
    p.predictions.forEach((pr) => {
      expect(pr.value).toBeNull();
      expect(pr.status).toBe('NOT_EVALUATED');
    });

    // Findings are VALIDATED from grounded evidence.
    expect(p.findings.length).toBeGreaterThan(0);
    p.findings.forEach((f) => expect(f.authority).toBe('VALIDATED'));

    // Frozen result carries its real signature.
    expect(p.frozenResult?.status).toBe('FROZEN');
    expect(p.frozenResult?.signature).toMatch(/^[0-9a-f]{64}$/);

    // The final result is published.
    expect(p.result?.status).toBe('AVAILABLE');
    expect(p.result?.summary).toBeTruthy();

    // The backend emitted NO action plan / execution for this run — the projection
    // must NOT fabricate them.
    expect(p.actionPlan).toBeNull();
    expect(p.execution).toBeNull();
  });

  it('builds an honest governed graph from the real state', () => {
    const state = JSON.parse(readFileSync(fixturePath, 'utf8'));
    const p = buildCognitiveProjection(state);
    const g = buildCognitiveProjectionGraph(p);

    const dec = g.nodes.find((n) => n.kind === 'DECISION');
    expect(dec?.authority).toBe('HUMAN_AUTHORIZED');
    expect(dec?.id).toBe('DEC-8b8482');

    const fz = g.nodes.find((n) => n.kind === 'FROZEN');
    expect(fz?.authority).toBe('FROZEN');
    expect(fz?.provenance.some((x) => x.includes('freeze_signature'))).toBe(true);

    const res = g.nodes.find((n) => n.kind === 'RESULT');
    expect(res?.authority).toBe('PUBLISHED');

    // Honest absence: no ACTION / EXECUTION nodes because the backend produced none.
    expect(g.nodes.some((n) => n.kind === 'ACTION')).toBe(false);
    expect(g.nodes.some((n) => n.kind === 'EXECUTION')).toBe(false);

    // Predictor maps to ACFL_DETERMINISTIC / MathEngine / GCLV and its artifacts.
    expect(emRoleLabel('EM Predictor')).toBe('ACFL_DETERMINISTIC · MathEngine · GCLV');
    expect(relatedArtifactsForEM('EM Predictor', g).some((a) => a.kind === 'PREDICTION')).toBe(true);
  });
});
