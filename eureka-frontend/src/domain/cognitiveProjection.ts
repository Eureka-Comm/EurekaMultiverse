import type { CanonicalWorkState } from './canonicalSchema';

/**
 * LS86 — Cognitive Projection Unification.
 *
 * CognitiveProjectionDTO is the SINGLE frontend projection of the governed
 * canonical state. It is the only source of COGNITIVE MEANING for the
 * Visualization + Storytelling layers.
 *
 *      CANONICAL STATE   (truth)
 *            |
 *            v
 *      CognitiveProjectionDTO   (meaning)   <- this module
 *            |
 *            v
 *   VisualModel / StoryModel   (presentation)
 *
 * Hard rules (never invent):
 *   - null != value, NOT_EVALUATED != evaluated, UNSUPPORTED != VALIDATED.
 *   - LLM_CANDIDATE != fact; recommendation != human decision.
 *   - alternative != optimal; simulated != externally executed.
 *   - conceptual structure != evidence-validated knowledge.
 *   - The human decision comes ONLY from human_decision, never from
 *     recommended_option / recommendation / LLM narrative.
 */

export type Authority =
  | 'LLM_CANDIDATE'
  | 'PYTHON_GOVERNED'
  | 'VALIDATED'
  | 'UNSUPPORTED'
  | 'NOT_EVALUATED'
  | 'HUMAN_AUTHORIZED'
  | 'SIMULATED'
  | 'PENDING'
  | 'FROZEN'
  | 'PUBLISHED';

export interface ProvenanceNodeDTO {
  id: string;
  kind: string;          // QUESTION | EVIDENCE | FINDING | PREDICTION | PRESCRIPTION | DECISION | ACTION | EXECUTION | RESULT | FROZEN
  sourceRef: string;     // real artifact id (PROB-*/EVI-*/FND-*/PRED-*/PRESC-*/DEC-*/AP-*/EV-*/WR-*/FROZEN-*) or NOT_AVAILABLE
  status: string;        // validation/generation status
  authority: Authority;
  provenance: string[];
  label: string;
}

export interface HumanDecisionDTO {
  decisionId: string | null;
  selectedAlternativeId: string | null;
  authority: Authority;          // HUMAN_AUTHORIZED when present
  status: string | null;         // ANSWERED | PENDING
  preserved: boolean;            // true when the decision comes from human_decision
}

/** A REAL action-plan step (action_plan.actions[]), projected faithfully. */
export interface ActionStepProjection {
  id: string;                    // real action id (PDH-*/AP-*)
  order: number;                 // 1-based position in the plan
  description: string;
  status: string;                // PENDING | RUNNING | COMPLETED | FAILED | BLOCKED (real)
  owner: string;
  dependencies: string[];
}

/**
 * LS90 — What remains OPEN. A governed, Python-derived projection of the leading
 * edge of an OPEN cognitive operation (an open research question that has NOT yet
 * reached a decision). Aggregates the REAL canonical open signals (unknowns,
 * uncertainty, limitations, contradictions, not-evaluated, insufficient
 * information, data-not-available, a pending human decision) WITHOUT inventing a
 * decision, a ranking, a utility, or a preference. `isOpen` is the GOVERNED
 * "no decision yet" signal, never a recommendation.
 */
export type OpenItemKind =
  | 'UNRESOLVED_QUESTION'
  | 'INSUFFICIENT_INFORMATION'
  | 'INSUFFICIENT_DATA'
  | 'MISSING_EVIDENCE'
  | 'UNCERTAINTY'
  | 'LIMITATION'
  | 'CONTRADICTION'
  | 'PENDING_HUMAN_DECISION'
  | 'PENDING_HUMAN_INPUT'
  | 'NOT_EVALUATED'
  | 'DATA_NOT_AVAILABLE';

export interface WhatRemainsOpenItemDTO {
  kind: OpenItemKind;
  label: string;
  sourceRef: string;
}

export interface WhatRemainsOpenDTO {
  status: string;                    // OPEN | OPEN_INSUFFICIENT_INFORMATION | CLOSED
  operationKind: string;             // OPEN_RESEARCH (no decision yet) | DECISION (decision made)
  isOpen: boolean;                   // == NOT decision_reached (the governed OPEN signal)
  decisionReached: boolean;
  decisionPending: boolean;
  items: WhatRemainsOpenItemDTO[];
  decisionRelevantKnowledge: string[];
  summary: string;
}

export interface CognitiveProjectionDTO {
  question: string;
  problem: { id: string | null; objective: string; authority: Authority } | null;
  evidence: { id: string; sourceText: string; grounded: boolean }[];
  findings: { id: string; statement: string; status: string; evidenceRefs: string[]; provenance: string[]; authority: Authority }[];
  predictions: { id: string; modelType: string; value: number | null; status: string; evidenceRefs: string[]; predictorVariables: string[]; provenance: string[]; authority: Authority }[];
  prescription: { id: string | null; alternatives: { id: string; description: string }[]; criteria: string[]; rationale: string; authority: Authority } | null;
  humanDecision: HumanDecisionDTO;
  actionPlan: { id: string | null; selectedAlternativeId: string | null; humanDecisionId: string | null; status: string; authority: Authority; steps: ActionStepProjection[] } | null;
  execution: { id: string | null; status: string; level: string | null; simulated: boolean } | null;
  result: { id: string | null; summary: string; status: string } | null;
  frozenResult: { id: string | null; signature: string | null; status: string } | null;
  recommendedOption: string | null;   // system recommendation (NEVER conflated with decision)
  lineage: string[];                  // real EVI->FND->PRED->PRESC->DEC->ACT->EXEC->FROZEN ids in order (only existing)
  projectionConflict: boolean;        // true when actionPlan.selectedAlternativeId != humanDecision.selectedAlternativeId
  /** LS90 — the governed "what remains open" leading edge (null when not projected by the backend). */
  whatRemainsOpen: WhatRemainsOpenDTO | null;
}

const str = (v: unknown): string => (typeof v === 'string' ? v : v == null ? '' : String(v));
const strList = (v: unknown): string[] => (Array.isArray(v) ? v.map(str).filter(Boolean) : []);
const bool = (v: unknown): boolean => (v == null ? false : Boolean(v));
const authOf = (role: string): Authority =>
  (['VALIDATED', 'UNSUPPORTED', 'NOT_EVALUATED', 'SIMULATED', 'FROZEN', 'PUBLISHED', 'HUMAN_AUTHORIZED', 'PENDING'] as Authority[]).includes(role as Authority)
    ? (role as Authority)
    : 'LLM_CANDIDATE';

const OPEN_ITEM_KINDS = [
  'UNRESOLVED_QUESTION', 'INSUFFICIENT_INFORMATION', 'INSUFFICIENT_DATA',
  'MISSING_EVIDENCE', 'UNCERTAINTY', 'LIMITATION', 'CONTRADICTION',
  'PENDING_HUMAN_DECISION', 'PENDING_HUMAN_INPUT', 'NOT_EVALUATED', 'DATA_NOT_AVAILABLE',
] as const;
const isValidOpenKind = (kind: string): boolean => (OPEN_ITEM_KINDS as readonly string[]).includes(kind);

export function buildCognitiveProjection(state: CanonicalWorkState | null): CognitiveProjectionDTO {
  const project = state as any;

  // QUESTION / PROBLEM
  const problem = project?.problem || null;
  const objProblemId = problem?.problem_id || 'NOT_AVAILABLE';
  const question = str(problem?.objective) || str(project?.work?.userIntent) || '';
  const problemAuthority: Authority = problem?.governance_status === 'GOVERNED' ? 'PYTHON_GOVERNED' : 'LLM_CANDIDATE';

  // EVIDENCE (from extracted_evidence EVI-CONTEXT / evidence fabric)
  const evidence = Object.entries(project?.extracted_evidence || {}).map(([eid, ev]: [string, any]) => ({
    id: eid,
    sourceText: strList(ev?.text_blocks).join(' ') || '',
    grounded: (ev?.text_blocks?.length || 0) > 0,
  }));

  // FINDINGS (grounding gate; VALIDATED/UNSUPPORTED)
  const findings = (project?.knowledge?.findings || []).map((f: any) => ({
    id: str(f.finding_id),
    statement: str(f.statement),
    status: str(f.status || 'UNSUPPORTED'),
    evidenceRefs: strList(f.evidence_refs),
    provenance: strList(f.provenance),
    authority: authOf(str(f.status)),
  }));

  // PREDICTIONS (ACFL_ENGINE, deterministic; preserve NOT_EVALUATED)
  const preds = strList((project?.predictive_knowledge?.predictions || []).map((p: any) => p)).length
    ? project.predictive_knowledge.predictions
    : (project?.predictive_knowledge?.predicates || []);
  const predictions = (preds || []).map((p: any) => {
    const val = p?.predicted_value ?? p?.mse;   // real value or null (NOT_EVALUATED)
    return {
      id: str(p.prediction_id || p.predicate_id),
      modelType: str(p.model_type || 'ACFL_ENGINE'),
      value: typeof val === 'number' && Number.isFinite(val) ? val : null,
      status: str(p.validation_status || (p.mse == null ? 'NOT_EVALUATED' : 'VALIDATED')),
      evidenceRefs: strList(p.evidence_refs),
      predictorVariables: strList(p.predictor_variables),
      provenance: strList(p.provenance),
      authority: authOf(str(p.validation_status || (p.mse == null ? 'NOT_EVALUATED' : 'VALIDATED'))),
    };
  });

  // PRESCRIPTION (alternatives + criteria; PROPOSAL, never decision)
  const presc = (project?.prescriptive_knowledge?.prescriptions || [])[0] || null;
  const prescription = presc
    ? {
        id: str(presc.prescription_id) || 'NOT_AVAILABLE',
        alternatives: (presc.alternatives || []).map((a: any) => ({ id: str(a.alternative_id || a.id), description: str(a.description) })),
        // Criteria may be strings (legacy) or objects { id, target, description, direction, threshold, weight }.
        // Format them into a single readable label so presentation shows meaning, not "[object Object]".
        criteria: (presc.applicable_criteria || (presc.criteria || [])).map((c: any) => {
          if (typeof c === 'string') return c;
          const name = str(c.description || c.target || c.criterion_id || '');
          const dir = c.direction ? ` (${str(c.direction)})` : '';
          const weight = c.weight != null ? ` w=${c.weight}` : '';
          const thr = c.threshold != null ? ` thr=${c.threshold}` : '';
          return `${name}${dir}${weight}${thr}`;
        }).filter(Boolean),
        rationale: str(presc.rationale),
        authority: authOf(str(presc.authority)),
      }
    : null;

  // DECISION — ONLY from human_decision (never recommendation)
  const hd = project?.human_decision;
  const humanDecision: HumanDecisionDTO = hd?.selected_alternative_id
    ? {
        decisionId: str(hd.decision_id) || null,
        selectedAlternativeId: str(hd.selected_alternative_id),
        authority: 'HUMAN_AUTHORIZED',
        status: hd.human_authority != null ? str(hd.human_authority) : (hd.decision_authority || 'HUMAN_OPERATOR'),
        preserved: true,
      }
    : { decisionId: null, selectedAlternativeId: null, authority: 'PENDING', status: 'PENDING', preserved: false };

  // Recommended option (system candidate — distinct from decision)
  const dp = (project?.decision_points || [])[0];
  const recommendedOption = dp?.recommended_option ? str(dp.recommended_option) : null;

  // ACTION PLAN (governed) — projects the REAL action_plan.actions[].steps, never invents anew.
  const ap = project?.action_plan || null;
  const actionSteps: ActionStepProjection[] = Array.isArray(ap?.actions)
    ? ap.actions.map((a: any, i: number) => ({
        id: str(a.action_id) || str(a.id) || `AP-${i + 1}`,
        order: i + 1,
        description: str(a.description || a.action_id),
        status: str(a.status || a.execution_status || 'PENDING'),
        owner: str(a.owner || ''),
        dependencies: strList(a.dependencies),
      }))
    : [];
  const actionPlan = ap
    ? {
        id: str(ap.plan_id) || 'NOT_AVAILABLE',
        selectedAlternativeId: str(ap.selected_alternative_id) || null,
        humanDecisionId: str(ap.human_decision_id) || null,
        status: str(ap.validation_status || 'UNVERIFIED'),
        authority: ap.authority === 'HUMAN' ? 'HUMAN_AUTHORIZED' : authOf(str(ap.authority)),
        steps: actionSteps,
      }
    : null;

  // PROJECTION CONFLICT: actionPlan selection != human decision selection (never autocorrect)
  const projectionConflict = Boolean(
    humanDecision.selectedAlternativeId &&
    actionPlan?.selectedAlternativeId &&
    humanDecision.selectedAlternativeId !== actionPlan.selectedAlternativeId,
  );

  // EXECUTION (SIMULATED preserved)
  const es = project?.execution_state || null;
  const execution = es
    ? {
        id: str(es.execution_id) || 'EXECUTION',
        status: str(es.status || 'SIMULATED'),
        level: str(es.execution_level || '1/2'),
        simulated: true,
      }
    : null;

  // RESULT
  const res = project?.state?.result || project?.result || null;
  const result = res?.status === 'AVAILABLE'
    ? { id: str(res.result_id) || 'NOT_AVAILABLE', summary: str(res.summary), status: str(res.status) }
    : null;

  // FROZEN RESULT
  const fz = project?.frozen_result || null;
  const frozenResult = fz
    ? { id: str(fz.result_id) || 'NOT_AVAILABLE', signature: str(fz.freeze_signature) || null, status: str(fz.status) }
    : null;

  // LINEAGE (real chain; only existing artifact ids, in order)
  const lineage: string[] = [];
  findings.forEach((f: { id: string }) => f.id && lineage.push(f.id));
  predictions.forEach((p: { id: string }) => p.id && lineage.push(p.id));
  if (prescription?.id) lineage.push(prescription.id);
  if (humanDecision.decisionId) lineage.push(humanDecision.decisionId);
  if (actionPlan?.id) lineage.push(actionPlan.id);
  if (result?.id) lineage.push(result.id);
  if (frozenResult?.id) lineage.push(frozenResult.id);

  // LS90 — WHAT REMAINS OPEN (governed, Python-derived). Reads the single backend
  // `open_research` projection; never recomputes, never invents a decision/ranking.
  const open = (project?.open_research as any) || null;
  const whatRemainsOpen: WhatRemainsOpenDTO | null = open
    ? {
        status: str(open.status) || 'OPEN',
        operationKind: str(open.operation_kind) || 'OPEN_RESEARCH',
        isOpen: bool(open.is_open),
        decisionReached: bool(open.decision_reached),
        decisionPending: bool(open.decision_pending),
        items: Array.isArray(open.items)
          ? open.items.map((i: any) => ({
              kind: (isValidOpenKind(str(i.kind)) ? str(i.kind) : 'INSUFFICIENT_INFORMATION') as OpenItemKind,
              label: str(i.label),
              sourceRef: str(i.source_ref),
            }))
          : [],
        decisionRelevantKnowledge: strList(open.decision_relevant_knowledge),
        summary: str(open.summary),
      }
    : null;

  return {
    question,
    problem: problem ? { id: objProblemId, objective: question, authority: problemAuthority } : null,
    evidence,
    findings,
    predictions,
    prescription,
    humanDecision,
    actionPlan,
    execution,
    result,
    frozenResult,
    recommendedOption,
    lineage,
    projectionConflict,
    whatRemainsOpen,
  };
}

/** Convenience: read nodes as a provenance chain (EVI->FND->PRED->PRESC->DEC->ACT->EXEC->FROZEN). */
export function buildProvenanceNodes(p: CognitiveProjectionDTO): ProvenanceNodeDTO[] {
  const nodes: ProvenanceNodeDTO[] = [];
  const push = (kind: string, sourceRef: string | null, status: string, authority: Authority, provenance: string[], label: string) => {
    const ref = sourceRef || 'NOT_AVAILABLE';
    nodes.push({ id: `${kind}:${ref}`, kind, sourceRef: ref, status, authority, provenance, label });
  };
  p.evidence.forEach((e) => push('EVIDENCE', e.id, e.grounded ? 'grounded' : 'UNSUPPORTED', e.grounded ? 'VALIDATED' : 'UNSUPPORTED', [], 'Evidence'));
  p.findings.forEach((f) => push('FINDING', f.id, f.status, f.authority, f.provenance, f.statement.slice(0, 40)));
  p.predictions.forEach((pr) => push('PREDICTION', pr.id, pr.status, pr.authority, pr.provenance, `${pr.modelType} · ${pr.status}`));
  if (p.prescription) push('PRESCRIPTION', p.prescription.id, 'SELECTED', p.prescription.authority, [], 'Prescription');
  if (p.humanDecision.decisionId) push('DECISION', p.humanDecision.decisionId, str(p.humanDecision.status), 'HUMAN_AUTHORIZED', [], `Human: ${p.humanDecision.selectedAlternativeId}`);
  if (p.actionPlan) push('ACTION', p.actionPlan.id, p.actionPlan.status, p.actionPlan.authority, [], 'Action Plan');
  if (p.execution) push('EXECUTION', p.execution.id, p.execution.status, 'SIMULATED', [], 'Execution');
  if (p.result) push('RESULT', p.result.id, p.result.status, 'PUBLISHED', [], 'Result');
  if (p.frozenResult) push('FROZEN', p.frozenResult.id, p.frozenResult.status, 'FROZEN', [], 'Frozen Result');
  return nodes;
}
