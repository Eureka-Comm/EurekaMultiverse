import { describe, it, expect } from 'vitest';
import { classifyModel, mapObservedPipeline } from './cognitiveTrace';

describe('classifyModel — provider-independent trace authority (no DeepSeek/Ollama branching)', () => {
  it('ACFL_DETERMINISTIC => ACFL MATH (no LLM) — the mathematical authority is never an LLM', () => {
    const c = classifyModel('EM Predictor', 'ACFL_DETERMINISTIC');
    expect(c.kind).toBe('ACFL_MATH');
    expect(c.label).toContain('ACFL');
  });

  it('deepseek-chat => LLM proposal (candidate, never ACFL/math)', () => {
    const c = classifyModel('EM Core', 'deepseek-chat');
    expect(c.kind).toBe('LLM_PROPOSAL');
    expect(c.label).not.toContain('DeepSeek');
    expect(c.label).not.toContain('ACFL');
  });

  it('an Ollama model (qwen3:8b) is LLM proposal — never mislabeled as DeepSeek', () => {
    const c = classifyModel('EM Descriptor', 'qwen3:8b');
    expect(c.kind).toBe('LLM_PROPOSAL');
    expect(c.label).not.toContain('DeepSeek');
  });

  it('EM Installer (no model) => Q4 governed effect (non-LLM)', () => {
    expect(classifyModel('EM Installer', '').kind).toBe('Q4_GOVERNED');
  });

  it('EM Publisher (no model) => freeze / publication (non-LLM)', () => {
    expect(classifyModel('EM Publisher', '').kind).toBe('FREEZE_PUBLICATION');
  });

  it('no model on a non-LLM stage => deterministic / governance', () => {
    expect(classifyModel('EM Structurer', '').kind).toBe('DETERMINISTIC_GOVERNANCE');
  });

  it('a future provider is still just an LLM proposal — never an authority', () => {
    expect(classifyModel('EM Core', 'some-future-provider-model').kind).toBe('LLM_PROPOSAL');
  });
});

// REAL backend evidence for WORK-AC8CD7B1 (captured from GET /api/work/WORK-AC8CD7B1/audit).
// Used as a regression fixture; the app never hardcodes these — it reads them live.
const REAL_CONTRACTUAL = ['EM Core','EM Structurer','EM Descriptor','EM Predictor','EM Prescriptor','EM Actioner','EM Installer','EM Publisher'];
const REAL_EM_PIPELINE = [
  { canonical_em: 'EM Core', status: 'COMPLETED' },
  { canonical_em: 'EM Structurer', status: 'COMPLETED' },
  { canonical_em: 'EM Descriptor', status: 'COMPLETED' },
  { canonical_em: 'EM Predictor', status: 'COMPLETED' },
  { canonical_em: 'EM Prescriptor', status: 'COMPLETED' },
  { canonical_em: 'EM Actioner', status: 'COMPLETED' },
  { canonical_em: 'EM Installer', status: 'NOT_APPLICABLE' },
  { canonical_em: 'EM Publisher', status: 'COMPLETED' },
];
const REAL_TRACE = [
  { em: 'EM Core', model: 'deepseek-chat', status: 'COMPLETED', capability_id: 'propose_problem' },
  { em: 'EM Descriptor', model: 'deepseek-chat', status: 'COMPLETED', capability_id: 'propose_findings' },
  { em: 'EM Predictor', model: 'ACFL_DETERMINISTIC', status: 'COMPLETED', capability_id: 'propose_predictions' },
  { em: 'EM Prescriptor', model: 'deepseek-chat', status: 'COMPLETED', capability_id: 'propose_prescription' },
  { em: 'EM Actioner', model: 'deepseek-chat', status: 'COMPLETED', capability_id: 'propose_action_plan' },
];

describe('mapObservedPipeline — CONSTELACIÓN observed EM pipeline from REAL evidence', () => {
  const observed = mapObservedPipeline(REAL_CONTRACTUAL, REAL_EM_PIPELINE, REAL_TRACE);
  const byEm = Object.fromEntries(observed.map((o) => [o.em, o]));
  it('maps every contractual EM (8 stages, no fabrication)', () => {
    expect(observed).toHaveLength(8);
  });
  it('EM Core: LLM proposal (deepseek-chat), COMPLETED', () => {
    expect(byEm['EM Core'].status).toBe('COMPLETED');
    expect(byEm['EM Core'].model).toBe('deepseek-chat');
    expect(byEm['EM Core'].classification.kind).toBe('LLM_PROPOSAL');
  });
  it('EM Predictor: ACFL MATH (deterministic), never an LLM', () => {
    expect(byEm['EM Predictor'].model).toBe('ACFL_DETERMINISTIC');
    expect(byEm['EM Predictor'].classification.kind).toBe('ACFL_MATH');
  });
  it('EM Installer: NOT_APPLICABLE (no LLM call) → Q4 governed effect', () => {
    expect(byEm['EM Installer'].status).toBe('NOT_APPLICABLE');
    expect(byEm['EM Installer'].model).toBe('');
    expect(byEm['EM Installer'].classification.kind).toBe('Q4_GOVERNED');
  });
  it('EM Publisher: no LLM call → freeze / publication', () => {
    expect(byEm['EM Publisher'].status).toBe('COMPLETED');
    expect(byEm['EM Publisher'].model).toBe('');
    expect(byEm['EM Publisher'].classification.kind).toBe('FREEZE_PUBLICATION');
  });
  it('a stage missing from em_pipeline is reported NOT_OBSERVED (honest absence)', () => {
    const partial = mapObservedPipeline(['EM Core','EM UnknownStage'], [{ canonical_em: 'EM Core', status: 'COMPLETED' }], []);
    const missing = partial.find((o) => o.em === 'EM UnknownStage');
    expect(missing?.status).toBe('NOT_OBSERVED');
  });
});
