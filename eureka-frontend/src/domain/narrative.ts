import type { CanonicalWorkState } from './canonicalSchema';

/**
 * EUREKA "Dark Intelligence" Cognitive Console — Narrative Stage model.
 *
 * This module is the single place that maps the REAL CanonicalWorkState to the
 * 13-stage cognitive narrative (Question → Context → Data → Discovery →
 * Prediction → Evaluation → Alternatives → Decision → Prescription → Freeze →
 * Action → Result → Learning). It never invents numbers: when the backend state
 * has no data for a stage, the stage is flagged `hasData:false` with a truthful
 * `pendingReason`, and the UI renders a "DATA PENDING" state instead of a chart.
 */

export type CognitiveState = 'LIVE' | 'RESOLVED' | 'PENDING' | 'REQUIRES_HUMAN';

export interface KnowledgeObject {
  /** What this object represents (semantic definition). */
  whatItRepresents: string;
  /** Backend field(s) this object projects (e.g. "knowledge.findings[]"). */
  dataSource: string;
  /** Transformation applied to get the object from the data source. */
  transformation: string;
  /** The 8-EM that produced this object. */
  producingEM: string;
  /** Predicates / variables used by the object. */
  predicatesVariables: string[];
  /** Supporting evidence references (evidence_ids / finding refs). */
  supportingEvidence: string[];
  /** Uncertainty statement (truthful; may be "Not quantified"). */
  uncertainty: string;
  /** The decision / recommendation this object supports. */
  supports: string;
  /** Provenance chain for the object. */
  provenance: string[];
}

export interface NarrativeStage {
  id: string;
  order: number;
  title: string;
  /** Short label for the node rail. */
  shortTitle: string;
  cognitiveState: CognitiveState;
  hasData: boolean;
  pendingReason: string;
  /** Human-facing explanation of what this stage does. */
  explanation: string;
  knowledgeObject: KnowledgeObject;
  /** Active when the backend active_em maps to this stage. */
  active: boolean;
}

const str = (v: unknown): string =>
  typeof v === 'string' ? v : v == null ? '' : String(v);

/** Non-empty string list from a value that may be an array of strings. */
const strList = (v: unknown): string[] =>
  Array.isArray(v) ? v.map(str).filter(Boolean) : [];

/** Map a backend active_em to its narrative stage id (for the "active" pulse). */
export function stageIdForActiveEM(activeEM: string | null | undefined): string | null {
  switch (activeEM) {
    case 'EM Core':
    case 'EM Structurer':
      return 'CONTEXT';
    case 'EM Descriptor':
      return 'DISCOVERY';
    case 'EM Predictor':
      return 'PREDICTION';
    case 'EM Prescriptor':
      return 'EVALUATION';
    case 'EM Actioner':
      return 'ACTION';
    case 'EM Installer':
      return 'FREEZE';
    case 'EM Publisher':
      return 'RESULT';
    default:
      return null;
  }
}

interface Cum {
  supports: string[];
  evidence: string[];
  provenance: string[];
  vars: string[];
  uncertainty: string[];
}
function cum(): Cum {
  return { supports: [], evidence: [], provenance: [], vars: [], uncertainty: [] };
}

/**
 * Build the ordered narrative stages for a canonical state. Pure & side-effect free.
 */
export function buildNarrativeStages(state: CanonicalWorkState | null): NarrativeStage[] {
  if (!state) return [];
  const activeId = stageIdForActiveEM(state.active_em);
  const isHITL = state.work?.status === 'WAITING_FOR_HUMAN_INPUT';

  const problem = (state as any).problem;
  const problemStructured = problem?.structured_problem || {};

  // QUESTION
  const questions = strList(problemStructured?.questions);
  const objective = str(problem?.objective) || state.work?.userIntent || '';
  const questionKO: KnowledgeObject = {
    whatItRepresents: 'The governing question that initiated the work.',
    dataSource: 'problem.structured_problem.questions + work.userIntent',
    transformation: 'Direct projection of the user intent / structured question.',
    producingEM: 'EM Core',
    predicatesVariables: strList(problemStructured?.variables),
    supportingEvidence: strList(problem?.evidence_requirements).length
      ? strList(problem?.evidence_requirements)
      : [],
    uncertainty: problemStructured?.unknowns?.length
      ? `Open unknowns: ${strList(problemStructured?.unknowns).join('; ')}`
      : 'None recorded.',
    supports: `Objective: ${objective}`,
    provenance: ['EM Core → problem.objective', 'Intake → work.userIntent'],
  };
  const questionStage: NarrativeStage = {
    id: 'QUESTION',
    order: 1,
    title: 'Question',
    shortTitle: 'QUESTION',
    cognitiveState: activeId === 'QUESTION' ? 'LIVE' : 'RESOLVED',
    hasData: questions.length > 0 || objective.length > 0,
    pendingReason: 'No structured question was formulated for this work.',
    explanation: 'The cognitive question that frames everything downstream.',
    knowledgeObject: questionKO,
    active: activeId === 'QUESTION',
  };

  // CONTEXT
  const entities = strList(problemStructured?.entities);
  const variables = strList(problemStructured?.variables);
  const relationships = strList(problemStructured?.relationships);
  const assumptions = strList(problemStructured?.assumptions);
  const constraints = [
    ...strList(problemStructured?.constraints),
    ...strList(problem?.constraints),
  ];
  const contextKO: KnowledgeObject = {
    whatItRepresents: 'The situational envelope: entities, variables, assumptions, constraints.',
    dataSource: 'problem + problem.structured_problem',
    transformation: 'Structured problem model projection.',
    producingEM: 'EM Structurer',
    predicatesVariables: variables,
    supportingEvidence: strList(problemStructured?.evidence_requirements),
    uncertainty: problemStructured?.unknowns?.length
      ? `Unknowns: ${strList(problemStructured?.unknowns).join('; ')}`
      : 'None recorded.',
    supports: 'Frames the search space for the 8-EM pipeline.',
    provenance: ['EM Structurer → problem.structured_problem'],
  };
  const contextStage: NarrativeStage = {
    id: 'CONTEXT',
    order: 2,
    title: 'Context',
    shortTitle: 'CONTEXT',
    cognitiveState: activeId === 'CONTEXT' ? 'LIVE' : 'RESOLVED',
    hasData: entities.length + variables.length + relationships.length + constraints.length > 0,
    pendingReason: 'No structured context was extracted.',
    explanation: 'The envelope of entities, variables, assumptions and constraints.',
    knowledgeObject: contextKO,
    active: activeId === 'CONTEXT',
  };

  // DATA
  const evidence = state.evidence || [];
  const extracted = (state as any).extracted_evidence || {};
  const extractedIds = Object.keys(extracted);
  const textBlockCount = extractedIds.reduce(
    (acc, eid) => acc + ((extracted[eid]?.text_blocks || []).length || 0),
    0,
  );
  const tableCount = extractedIds.reduce(
    (acc, eid) => acc + ((extracted[eid]?.tables || []).length || 0),
    0,
  );
  const dataKO: KnowledgeObject = {
    whatItRepresents: 'The ingested evidence corpus and its extracted content.',
    dataSource: 'evidence[] + extracted_evidence{}',
    transformation: 'Parsing + structured extraction of text/tables.',
    producingEM: 'EM Structurer',
    predicatesVariables: [],
    supportingEvidence: evidence.map((e) => e.evidence_id),
    uncertainty: 'Extraction completeness varies by source.',
    supports: 'Grounds findings, predictions and prescriptions in real sources.',
    provenance: [
      ...new Set(evidence.map((e) => e.provenance?.[0] || `Evidence[${e.evidence_id}]`)),
    ],
  };
  const dataStage: NarrativeStage = {
    id: 'DATA',
    order: 3,
    title: 'Data',
    shortTitle: 'DATA',
    cognitiveState: evidence.length > 0 ? 'RESOLVED' : 'PENDING',
    hasData: evidence.length > 0,
    pendingReason: 'No evidence has been attached to this work.',
    explanation: 'The real, attached evidence and what was extracted from it.',
    knowledgeObject: dataKO,
    active: activeId === 'DATA',
  };

  // DISCOVERY
  const knowledge = (state as any).knowledge || {};
  const findings: any[] = knowledge.findings || [];
  const discoveryKO: KnowledgeObject = {
    whatItRepresents: 'Structured findings/statements derived from the evidence.',
    dataSource: 'knowledge.findings[]',
    transformation: 'Descriptor analysis → StructuredFinding',
    producingEM: 'EM Descriptor',
    predicatesVariables: [],
    supportingEvidence: [
      ...new Set(findings.flatMap((f) => f.evidence_refs || []).filter(Boolean)),
    ],
    uncertainty: strList(knowledge.unknowns).length
      ? `Unknowns: ${strList(knowledge.unknowns).join('; ')}`
      : 'None recorded.',
    supports: 'The evidence-based interpretation that feeds prediction.',
    provenance: [
      ...new Set(findings.flatMap((f) => f.provenance || []).filter(Boolean)),
    ],
  };
  const discoveryStage: NarrativeStage = {
    id: 'DISCOVERY',
    order: 4,
    title: 'Discovery',
    shortTitle: 'DISCOVERY',
    cognitiveState: activeId === 'DISCOVERY' ? 'LIVE' : findings.length > 0 ? 'RESOLVED' : 'PENDING',
    hasData: findings.length > 0,
    pendingReason: 'No structured findings produced yet.',
    explanation: 'The facts and observations discovered from the evidence.',
    knowledgeObject: discoveryKO,
    active: activeId === 'DISCOVERY',
  };

  // PREDICTION
  const predictive = (state as any).predictive_knowledge || {};
  const predictions: any[] = predictive.predictions || [];
  const predKO: KnowledgeObject = {
    whatItRepresents: 'Forward-looking predictions of target variables.',
    dataSource: 'predictive_knowledge.predictions[] / .predicates[]',
    transformation: 'Predictor analysis → PredictionKnowledge / PredictivePredicate',
    producingEM: 'EM Predictor',
    predicatesVariables: [
      ...new Set([
        ...predictions.flatMap((p: any) => p.predictor_variables || []),
        ...(predictive.predicates || []).flatMap((p: any) => p.condition_variables || []),
      ].filter(Boolean)),
    ],
    supportingEvidence: [
      ...new Set(predictions.flatMap((p: any) => p.evidence_refs || []).filter(Boolean)),
    ],
    uncertainty: predictions[0]?.uncertainty?.status
      ? `Uncertainty: ${predictions[0].uncertainty.status}`
      : predictive.status === 'UNAVAILABLE'
        ? 'Not quantified — prediction stage returned UNAVAILABLE.'
        : 'Not quantified.',
    supports: predictions[0]
      ? `Prediction of ${predictions[0].target_variable} → feeds prescription.`
      : 'No predictions to support a recommendation yet.',
    provenance: [
      ...new Set(predictions.flatMap((p) => p.provenance || []).filter(Boolean)),
    ],
  };
  const predictionStage: NarrativeStage = {
    id: 'PREDICTION',
    order: 5,
    title: 'Prediction',
    shortTitle: 'PREDICTION',
    cognitiveState:
      activeId === 'PREDICTION' ? 'LIVE' : predictions.length > 0 ? 'RESOLVED' : 'PENDING',
    hasData: predictions.length > 0 || (predictive.predicates || []).length > 0,
    pendingReason:
      predictive.status === 'UNAVAILABLE'
        ? 'Predictor returned UNAVAILABLE (no quantitative prediction produced).'
        : 'No predictions produced yet.',
    explanation: 'The forward projections the system derives from discovery.',
    knowledgeObject: predKO,
    active: activeId === 'PREDICTION',
  };

  // EVALUATION
  const acfl = (state as any).state?.acfl || {};
  const weights = acfl.weights || {};
  const prescriptive = (state as any).prescriptive_knowledge || {};
  const prescriptions: any[] = prescriptive.prescriptions || [];
  const criteria =
    prescriptions.flatMap((p) => p.applicable_criteria || p.criteria || []) || [];
  const acflFrontier = acfl.frontier || [];
  const hasAcflData = Object.keys(weights).length > 0 || acflFrontier.length > 0;
  const evalKO: KnowledgeObject = {
    whatItRepresents: 'The criteria weighting & trade-off surface used to score alternatives.',
    dataSource: 'state.acfl.weights + prescriptive_knowledge.prescriptions[].criteria',
    transformation: 'ACFL weighting / criterion projection.',
    producingEM: 'EM Prescriptor',
    predicatesVariables: [...Object.keys(weights), ...criteria.map((c: any) => c.target || '')].filter(
      Boolean,
    ),
    supportingEvidence: [
      ...new Set(criteria.flatMap((c: any) => c.provenance || []).filter(Boolean)),
    ],
    uncertainty: hasAcflData
      ? 'Frontier & sensitivity not populated; evaluation from weights/criteria only.'
      : 'Not quantified — no ACFL weights or criteria present.',
    supports: 'Scores the alternatives that feed the decision.',
    provenance: [
      ...new Set(criteria.flatMap((c: any) => c.provenance || []).filter(Boolean)),
    ],
  };
  const evaluationStage: NarrativeStage = {
    id: 'EVALUATION',
    order: 6,
    title: 'Evaluation',
    shortTitle: 'EVALUATION',
    cognitiveState: hasAcflData ? 'RESOLVED' : 'PENDING',
    hasData: hasAcflData,
    pendingReason:
      acflFrontier.length === 0 && Object.keys(weights).length === 0
        ? 'ACFL frontier is not populated for this work.'
        : 'ACFL frontier is empty (weights only).',
    explanation: 'The criteria and trade-off surface that scores options.',
    knowledgeObject: evalKO,
    active: activeId === 'EVALUATION',
  };

  // ALTERNATIVES
  const alternatives: any[] = prescriptions.flatMap((p) => p.alternatives || []);
  const altKO: KnowledgeObject = {
    whatItRepresents: 'The distinct candidate strategies considered for the decision.',
    dataSource: 'prescriptive_knowledge.prescriptions[].alternatives[]',
    transformation: 'Prescriptor enumeration of alternative rollout strategies.',
    producingEM: 'EM Prescriptor',
    predicatesVariables: [],
    supportingEvidence: [
      ...new Set(alternatives.flatMap((a) => a.provenance || []).filter(Boolean)),
    ],
    uncertainty: 'Trade-offs among alternatives are qualitative; no numeric scores.',
    supports: 'Provides the choice set surfaced to the human decision.',
    provenance: [
      ...new Set(alternatives.flatMap((a) => a.provenance || []).filter(Boolean)),
    ],
  };
  const alternativesStage: NarrativeStage = {
    id: 'ALTERNATIVES',
    order: 7,
    title: 'Alternatives',
    shortTitle: 'ALTERNATIVES',
    cognitiveState: alternatives.length > 0 ? 'RESOLVED' : 'PENDING',
    hasData: alternatives.length > 0,
    pendingReason: 'No alternatives were proposed.',
    explanation: 'The candidate strategies the system evaluated.',
    knowledgeObject: altKO,
    active: false,
  };

  // DECISION
  const decisionPoints: any[] = (state as any).decision_points || [];
  const humanRequests: any[] = (state as any).human_requests || [];
  const decisionHasData = decisionPoints.length > 0 || humanRequests.length > 0;
  const decisionKO: KnowledgeObject = {
    whatItRepresents: 'The human-in-the-loop decision points & information requests.',
    dataSource: 'decision_points[] + human_requests[]',
    transformation: 'Direct projection of pending/answered decision gates.',
    producingEM: 'EM Prescriptor / EM Installer',
    predicatesVariables: [],
    supportingEvidence: [
      ...new Set(decisionPoints.flatMap((d) => [d.question].concat(d.options?.map((o: any) => o.id || '') || []))),
    ],
    uncertainty: decisionPoints[0]?.uncertainty || 'Not quantified.',
    supports: decisionPoints[0]
      ? `Decision: ${decisionPoints[0].question}`
      : 'No decision is currently gated on human input.',
    provenance: [
      ...new Set(decisionPoints.flatMap((d) => [d.originating_em, d.task_id].filter(Boolean))),
    ],
  };
  const decisionStage: NarrativeStage = {
    id: 'DECISION',
    order: 8,
    title: 'Decision',
    shortTitle: 'DECISION',
    cognitiveState:
      decisionHasData && decisionPoints.some((d) => d.status === 'PENDING')
        ? 'REQUIRES_HUMAN'
        : decisionHasData
          ? 'RESOLVED'
          : 'PENDING',
    hasData: decisionHasData,
    pendingReason: 'No decision point or information request present.',
    explanation: 'The human-in-the-loop gates where authority is exercised.',
    knowledgeObject: decisionKO,
    active: isHITL || decisionPoints.some((d) => d.status === 'PENDING'),
  };

  // PRESCRIPTION
  const prescriptionKO: KnowledgeObject = {
    whatItRepresents: 'The validated prescription tying evidence to a recommended strategy.',
    dataSource: 'prescriptive_knowledge.prescriptions[] (rationale / selected_alternative / criteria)',
    transformation: 'Prescriptor synthesis of evidence + predictions into a recommendation.',
    producingEM: 'EM Prescriptor',
    predicatesVariables: prescriptions.flatMap((p) =>
      (p.supporting_predictions || []).concat(p.supporting_knowledge || []),
    ),
    supportingEvidence: prescriptions.flatMap((p) => p.evidence_refs || []),
    uncertainty: prescriptions[0]?.decision_rule?.status
      ? `Decision rule: ${prescriptions[0].decision_rule.status}`
      : 'Not quantified.',
    supports: prescriptions[0]
      ? `Recommended: ${prescriptions[0].selected_alternative?.alternative_id || 'none selected yet'}`
      : 'No prescription produced.',
    provenance: [
      ...new Set(prescriptions.flatMap((p) => p.provenance || []).filter(Boolean)),
    ],
  };
  const prescriptionStage: NarrativeStage = {
    id: 'PRESCRIPTION',
    order: 9,
    title: 'Prescription',
    shortTitle: 'PRESCRIPTION',
    cognitiveState:
      prescriptions.length > 0
        ? prescriptions.some((p) => p.selected_alternative)
          ? 'RESOLVED'
          : 'REQUIRES_HUMAN'
        : 'PENDING',
    hasData: prescriptions.length > 0,
    pendingReason: 'No validated prescription produced yet.',
    explanation: 'The concrete recommendation derived from evidence.',
    knowledgeObject: prescriptionKO,
    active: activeId === 'PRESCRIPTION',
  };

  // FREEZE
  const frozen = (state as any).frozen_result;
  const publication = (state as any).publication_state || {};
  const humanDecision = (state as any).human_decision;
  const freezeHasData =
    frozen != null || publication.status === 'FROZEN' || publication.status === 'PUBLISHED';
  const freezeKO: KnowledgeObject = {
    whatItRepresents: 'The freeze/assembly authorization that turns the solution into an asset.',
    dataSource: 'frozen_result + publication_state.status + human_decision',
    transformation: 'Installer assembly & human freeze approval.',
    producingEM: 'EM Installer',
    predicatesVariables: [],
    supportingEvidence: [],
    uncertainty: freezeHasData ? 'Frozen asset governs reuse.' : 'Not quantified.',
    supports:
      humanDecision?.decision_type === 'SELECT_ALTERNATIVE'
        ? `Freeze authorization: ${humanDecision.selected_alternative_id}`
        : 'No freeze decision recorded.',
    provenance: [...(frozen?.provenance || []), publication.state_id].filter(Boolean),
  };
  const freezeStage: NarrativeStage = {
    id: 'FREEZE',
    order: 10,
    title: 'Freeze',
    shortTitle: 'FREEZE',
    cognitiveState: freezeHasData ? 'RESOLVED' : 'PENDING',
    hasData: freezeHasData,
    pendingReason: 'No frozen result and the publication is not frozen/published.',
    explanation: 'The authorization gate that freezes the solution as a reusable asset.',
    knowledgeObject: freezeKO,
    active: activeId === 'FREEZE',
  };

  // ACTION
  const actionPlan = (state as any).action_plan;
  const actions: any[] = actionPlan?.actions || [];
  const executionState = (state as any).execution_state;
  const actKO: KnowledgeObject = {
    whatItRepresents: 'The validated action plan and its execution authorization/result.',
    dataSource: 'action_plan.actions[] + execution_state',
    transformation: 'Actioner synthesis + Installer authorization/execution.',
    producingEM: 'EM Actioner / EM Installer',
    predicatesVariables: [],
    supportingEvidence: (executionState?.evidence || []).map((e: any) => e.evidence_id),
    uncertainty:
      executionState?.result?.status
        ? `Execution result: ${executionState.result.status}`
        : 'Not executed yet.',
    supports: 'The step-by-step actions to realise the prescription.',
    provenance: [
      ...new Set(
        [...(actionPlan?.provenance || []), ...(executionState?.authorization?.authorized_by ? [`Authority: ${executionState.authorization.authorized_by}`] : [])],
      ),
    ],
  };
  const actionStage: NarrativeStage = {
    id: 'ACTION',
    order: 11,
    title: 'Action',
    shortTitle: 'ACTION',
    cognitiveState:
      executionState?.result?.status === 'SUCCEEDED'
        ? 'RESOLVED'
        : actions.length > 0
          ? 'RESOLVED'
          : 'PENDING',
    hasData: actions.length > 0,
    pendingReason: 'No validated action plan produced yet.',
    explanation: 'The ordered actions that carry the prescription into execution.',
    knowledgeObject: actKO,
    active: activeId === 'ACTION',
  };

  // RESULT
  const result = (state as any).state?.result;
  const pubSections =
    (publication.publications || []).flatMap((pub: any) => pub.sections || []) || [];
  const resultHasData = result?.status === 'AVAILABLE' || pubSections.length > 0;
  const resultKO: KnowledgeObject = {
    whatItRepresents: 'The final outcome summary + published sections.',
    dataSource: 'state.result + publication_state.publications[].sections',
    transformation: 'Publisher assembly of the final result.',
    producingEM: 'EM Publisher',
    predicatesVariables: [],
    supportingEvidence: result?.evidence_ids || pubSections.flatMap((s: any) => s.source_refs || []),
    uncertainty: result?.confidence != null ? `Confidence: ${result.confidence}` : 'Not quantified.',
    supports: 'The authoritative final answer to the question.',
    provenance: [...(result?.provenance || []), ...pubSections.flatMap((s: any) => s.provenance || [])],
  };
  const resultStage: NarrativeStage = {
    id: 'RESULT',
    order: 12,
    title: 'Result',
    shortTitle: 'RESULT',
    cognitiveState: resultHasData ? 'RESOLVED' : 'PENDING',
    hasData: resultHasData,
    pendingReason: 'No final result produced yet.',
    explanation: 'The delivered outcome and its published sections.',
    knowledgeObject: resultKO,
    active: activeId === 'RESULT',
  };

  // LEARNING
  const contradictions = strList(knowledge.contradictions);
  const unknowns = strList(knowledge.unknowns);
  const gaps = strList((state as any).gaps);
  const conditions = (state as any).conditions || [];
  const events = (state as any).execution_events || [];
  const learningKO: KnowledgeObject = {
    whatItRepresents: 'The meta-learning: gaps, conditions, contradictions, unknowns, execution trace.',
    dataSource: 'knowledge.{unknowns,contradictions} + gaps + conditions + execution_events',
    transformation: 'Reflection over execution traces & state conditions.',
    producingEM: 'All 8-EM (cross-cutting)',
    predicatesVariables: [],
    supportingEvidence: [],
    uncertainty: 'Learning is bounded by what the runtime surfaced.',
    supports: 'Informs future runs & documents limitations.',
    provenance: [...conditions.map((c: any) => c.reason_code), ...events.map((e: any) => e.event)],
  };
  const learningStage: NarrativeStage = {
    id: 'LEARNING',
    order: 13,
    title: 'Learning',
    shortTitle: 'LEARNING',
    cognitiveState:
      contradictions.length + unknowns.length + gaps.length + conditions.length > 0
        ? 'RESOLVED'
        : state.work?.status === 'COMPLETED'
          ? 'RESOLVED'
          : 'PENDING',
    hasData:
      contradictions.length + unknowns.length + gaps.length + conditions.length + events.length > 0,
    pendingReason: 'No learning signals (gaps/conditions/contradictions) recorded.',
    explanation: 'What the execution taught, its gaps and its constraints.',
    knowledgeObject: learningKO,
    active: false,
  };

  return [
    questionStage,
    contextStage,
    dataStage,
    discoveryStage,
    predictionStage,
    evaluationStage,
    alternativesStage,
    decisionStage,
    prescriptionStage,
    freezeStage,
    actionStage,
    resultStage,
    learningStage,
  ];
}

/** Convenience: find the stage currently requiring human input, if any. */
export function findActiveHITLStage(stages: NarrativeStage[]): NarrativeStage | undefined {
  return stages.find((s) => s.cognitiveState === 'REQUIRES_HUMAN');
}
