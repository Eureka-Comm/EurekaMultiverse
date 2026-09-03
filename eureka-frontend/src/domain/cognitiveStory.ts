import type { CanonicalWorkState } from './canonicalSchema';
import type { CognitionChapter, CognitiveObject, CognitiveView, CognitiveViewKey } from './cognitiveView';
import {
  makeCognitiveObject,
  getProblem,
  getKnowledge,
  getPredictive,
  getPrescriptive,
  getActionPlan,
  getExecutionState,
  getPublication,
  getFrozen,
  getDecisionPoints,
  getHumanRequests,
  getHumanDecision,
  getExecutionEvents,
  getConditions,
  getStateResult,
  getSelectedAlternativeId,
  getAcfl,
  getEvaluatedScores,
  getRankings,
  getScientificMetrics,
  getApplicableCriteria,
  getPrescriptionConstraints,
  getHistoricalContext,
  unique,
} from './cognitiveView';
import { buildNarrativeStages } from './narrative';

/**
 * EUREKA Cognitive Storytelling engine.
 *
 * Takes the real canonical state and produces ONE coherent 13-chapter story,
 * where every chapter is driven by a QUESTION and backed by a Cognitive View.
 * The stage rail (from narrative.ts) becomes the chapter navigation; each
 * chapter's cognitive state is inherited from the narrative stage so the story
 * never claims data that the backend did not produce.
 */

const viewKeyForStage: Record<string, CognitiveViewKey> = {
  QUESTION: 'QUESTION',
  CONTEXT: 'CONTEXT',
  DATA: 'DATA',
  DISCOVERY: 'DISCOVERY',
  PREDICTION: 'WHAT_IS_UNCERTAIN',
  EVALUATION: 'EVALUATION',
  ALTERNATIVES: 'ALTERNATIVE_LANDSCAPE',
  DECISION: 'HUMAN_AUTHORITY',
  PRESCRIPTION: 'WHY_SELECTED',
  FREEZE: 'WHAT_CHANGED',
  ACTION: 'ACTION_DAG',
  RESULT: 'OUTCOME_STORY',
  LEARNING: 'LEARNING',
};

const questionForStage: Record<string, (state: CanonicalWorkState) => string> = {
  QUESTION: () => 'WHAT ARE WE SOLVING?',
  CONTEXT: () => 'WHAT IS THE CONTEXT?',
  DATA: () => 'WHAT DATA INFORMED THIS?',
  DISCOVERY: () => 'WHAT WAS DISCOVERED?',
  PREDICTION: () => 'WHAT IS UNCERTAIN?',
  EVALUATION: () => 'HOW WERE THE OPTIONS SCORED?',
  ALTERNATIVES: () => 'WHAT ARE THE ALTERNATIVES?',
  DECISION: () => 'HUMAN AUTHORITY',
  PRESCRIPTION: (s) => {
    const id = getSelectedAlternativeId(s);
    return id ? `WHY ${id}?` : 'WHY SELECTED?';
  },
  FREEZE: () => 'WHAT CHANGED AFTER THE PRESCRIPTION?',
  ACTION: () => 'WHAT WILL BE DONE?',
  RESULT: () => 'WHAT HAPPENED? (OUTCOME)',
  LEARNING: () => 'WHAT HAPPENED? (TRACE)',
};

/**
 * Build the ordered 13-chapter Cognitive Story.
 */
export function buildCognitiveStory(state: CanonicalWorkState | null): CognitionChapter[] {
  const stages = buildNarrativeStages(state);
  // When there is no work, buildNarrativeStages returns [].
  if (stages.length === 0) return [];
  return stages.map((stage) => {
    const question = (questionForStage[stage.id] || (() => '?'))(state!);
    return {
      stage: stage.id,
      order: stage.order,
      title: stage.title,
      shortTitle: stage.shortTitle,
      question,
      viewKey: viewKeyForStage[stage.id] || 'LEARNING',
      cognitiveState: stage.cognitiveState,
      hasData: stage.hasData,
      dataPendingReason: stage.pendingReason,
    };
  });
}

/** Convenience: get a chapter by narrative stage id / view key. */
export function chapterByStage(state: CanonicalWorkState | null, stage: string): CognitionChapter | undefined {
  return buildCognitiveStory(state).find((c) => c.stage === stage);
}

/* ------------------------------------------------------------------ *
 * Cognitive View builders per question (pure, truth-preserving).
 * ------------------------------------------------------------------ */

export function buildQuestionView(state: CanonicalWorkState | null): CognitiveView {
  const problem = getProblem(state);
  const structured = problem?.structured_problem || {};
  const questions: string[] = structured.questions || [];
  const objective = str(problem?.objective) || state?.work?.userIntent || '';
  const ko = makeCognitiveObject({
    whatItRepresents: 'The governing question that initiated the work.',
    dataSource: 'problem.objective + problem.structured_problem.questions',
    transformation: 'Direct projection of the user intent / structured question.',
    producingEM: 'EM Core',
    predicatesVariables: structured.variables || [],
    evidence: (problem?.evidence_requirements || []).concat(problem?.structured_problem?.evidence_requirements || []),
    uncertainty: (structured.unknowns || []).length
      ? `Open unknowns: ${structured.unknowns.join('; ')}`
      : 'None recorded.',
    relationshipSet: ['work.userIntent', 'problem.objective'],
    supportsDecision: `Objective: ${objective}`,
    provenance: ['EM Core → problem.objective', 'Intake → work.userIntent'],
    confidence: problem?.semantic_confidence,
  });
  return {
    id: 'QUESTION',
    question: 'WHAT ARE WE SOLVING?',
    whatItShows: objective
      ? `The problem EUREKA is tasked with: "${objective}".`
      : 'No objective recorded yet.',
    primaryObject: ko,
    relationships: [{ from: 'work.userIntent', to: 'problem.objective', label: 'frames' }],
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: questions.length || objective ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No structured question was formulated for this work.',
  };
}

export function buildContextView(state: CanonicalWorkState | null): CognitiveView {
  const problem = getProblem(state);
  const structured = problem?.structured_problem || {};
  const entities = unique((structured.entities || []).concat(problem?.entities || []));
  const variables = unique((structured.variables || []).concat(problem?.variables || []));
  const relationships = unique((structured.relationships || []).concat(problem?.relationships || []));
  const constraints = unique((structured.constraints || []).concat(problem?.constraints || []));
  const assumptions = unique((structured.assumptions || []).concat(problem?.assumptions || []));
  const unknowns = unique((structured.unknowns || []).concat(problem?.unknowns || []));
  const hasData = entities.length + variables.length + relationships.length + constraints.length + assumptions.length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The situational envelope: entities, variables, relationships, assumptions, constraints.',
    dataSource: 'problem + problem.structured_problem',
    transformation: 'Structured problem model projection.',
    producingEM: 'EM Structurer',
    predicatesVariables: variables,
    evidence: (problem?.evidence_requirements || []).concat(structured.evidence_requirements || []),
    uncertainty: unknowns.length ? `Unknowns: ${unknowns.join('; ')}` : 'None recorded.',
    relationshipSet: relationships,
    supportsDecision: 'Frames the search space for the 8-EM pipeline.',
    provenance: ['EM Structurer → problem.structured_problem'],
  });
  return {
    id: 'CONTEXT',
    question: 'WHAT IS THE CONTEXT?',
    whatItShows: `The envelope is described by ${entities.length} entities, ${variables.length} variables, ${constraints.length} constraints and ${assumptions.length} assumptions.`,
    primaryObject: ko,
    relationships: [
      ...entities.map((e) => ({ from: 'entity', to: e, label: 'in-scope' })),
      ...variables.map((v) => ({ from: 'variable', to: v, label: 'observed' })),
      ...constraints.map((c) => ({ from: 'constraint', to: c, label: 'binds' })),
    ],
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No structured context was extracted.',
  };
}

export function buildDataView(state: CanonicalWorkState | null): CognitiveView {
  const evidence = state?.evidence || [];
  const extracted = (state as any)?.extracted_evidence || {};
  const ids = Object.keys(extracted);
  const textBlocks = ids.reduce((a, e) => a + ((extracted[e]?.text_blocks || []).length || 0), 0);
  const tables = ids.reduce((a, e) => a + ((extracted[e]?.tables || []).length || 0), 0);
  const ko = makeCognitiveObject({
    whatItRepresents: 'The ingested evidence corpus and its extracted content.',
    dataSource: 'evidence[] + extracted_evidence{}',
    transformation: 'Ingestion + structured extraction of text/tables.',
    producingEM: 'EM Structurer',
    evidence: evidence.map((e) => e.evidence_id),
    uncertainty: 'Extraction completeness varies by source.',
    relationshipSet: unique(evidence.map((e) => e.evidence_id)),
    supportsDecision: 'Grounds findings, predictions and prescriptions in real sources.',
    provenance: unique(evidence.map((e) => e.provenance?.[0] || `Evidence[${e.evidence_id}]`)),
  });
  return {
    id: 'DATA',
    question: 'WHAT DATA INFORMED THIS?',
    whatItShows: `${evidence.length} evidence ${evidence.length === 1 ? 'file' : 'files'} attached; ${ids.length} extracted sources yielding ${textBlocks} text blocks and ${tables} tables.`,
    primaryObject: ko,
    relationships: evidence.map((e) => ({ from: 'evidence', to: e.evidence_id, label: e.source || 'source' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: evidence.length > 0 || ids.length > 0 ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No evidence has been attached to this work.',
  };
}

export function buildDiscoveryView(state: CanonicalWorkState | null): CognitiveView {
  const knowledge = getKnowledge(state);
  const findings: any[] = knowledge.findings || [];
  const unknownList: string[] = knowledge.unknowns || [];
  const contradictions: string[] = knowledge.contradictions || [];
  const ko = makeCognitiveObject({
    whatItRepresents: 'Structured findings/statements derived from the evidence.',
    dataSource: 'knowledge.findings[]',
    transformation: 'Descriptor analysis → StructuredFinding',
    producingEM: 'EM Descriptor',
    evidence: unique(findings.flatMap((f) => f.evidence_refs || []).filter(Boolean)),
    uncertainty: unknownList.length ? `Unknowns: ${unknownList.join('; ')}` : contradictions.length ? `Contradictions: ${contradictions.join('; ')}` : 'None recorded.',
    relationshipSet: unique(findings.map((f) => f.finding_id)),
    supportsDecision: 'The evidence-based interpretation that feeds prediction.',
    provenance: unique(findings.flatMap((f) => f.provenance || []).filter(Boolean)),
    confidence: findings.find((f) => f.status !== 'VALIDATED') ? 'Mixed evidence strength' : null,
  });
  return {
    id: 'DISCOVERY',
    question: 'WHAT WAS DISCOVERED?',
    whatItShows: `${findings.length} structured ${findings.length === 1 ? 'finding' : 'findings'} derived from the attached evidence.`,
    primaryObject: ko,
    relationships: findings.map((f) => ({ from: 'finding', to: f.finding_id, label: f.status || 'VALIDATED' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: findings.length > 0 ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No structured findings produced yet.',
  };
}

export function buildUncertainView(state: CanonicalWorkState | null): CognitiveView {
  const predictive = getPredictive(state);
  const predictions: any[] = predictive.predictions || [];
  const hasPredictions = predictions.length > 0;
  const acfl = getAcfl(state);
  const normalizedScores = acfl.normalized_scores || {};
  const evaluatedScores = getEvaluatedScores(state);
  const rankings = getRankings(state);
  const hasAnyQuantified =
    predictions.some((p) => p.uncertainty?.status === 'QUANTIFIED') ||
    Object.keys(normalizedScores).length > 0 ||
    Object.keys(evaluatedScores).length > 0 ||
    Object.keys(rankings).length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'Forward-looking predictions and their quantified uncertainty.',
    dataSource:
      'predictive_knowledge.predictions[] + predictive_knowledge.status + acfl.normalized_scores + evaluated_scores + rankings',
    transformation: 'Predictor analysis → PredictionKnowledge / PredictiveUncertainty',
    producingEM: 'EM Predictor',
    predicatesVariables: unique(predictions.flatMap((p) => p.predictor_variables || []).concat(predictive.predicates || []).flatMap((p: any) => p.condition_variables || [])),
    evidence: unique(predictions.flatMap((p) => p.evidence_refs || []).filter(Boolean)),
    uncertainty: hasAnyQuantified
      ? 'Some quantitative uncertainty/scores are present below.'
      : 'Not quantified — no prediction uncertainty, no ACFL normalized scores, no evaluated scores or rankings were emitted by the backend for this work.',
    relationshipSet: unique(predictions.map((p) => p.prediction_id)),
    supportsDecision: 'Bounds the confidence the system has in its forward projections.',
    provenance: unique(predictions.flatMap((p) => p.provenance || []).filter(Boolean)),
  });
  return {
    id: 'WHAT_IS_UNCERTAIN',
    question: 'WHAT IS UNCERTAIN?',
    whatItShows: hasPredictions
      ? `The system holds ${predictions.length} prediction${predictions.length === 1 ? '' : 's'}. Uncertainty is ${predictions.some((p) => p.uncertainty?.status === 'QUANTIFIED') ? 'quantified where available' : 'not quantified by the predictor'}.`
      : `No quantitative prediction is available (predictive_knowledge.status = ${predictive.status || 'n/a'}), so uncertainty cannot be stated from the backend.${Object.keys(normalizedScores).length || Object.keys(evaluatedScores).length || Object.keys(rankings).length ? '' : ' No ACFL normalized scores, evaluated scores or rankings are emitted either — i.e. no quantitative uncertainty exists in this state.'}`,
    primaryObject: ko,
    relationships: predictions.map((p) => ({ from: 'prediction', to: p.prediction_id, label: p.target_variable || 'target' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasPredictions ? 'RESOLVED' : 'PENDING',
    dataPendingReason: predictive.status === 'UNAVAILABLE' ? 'Predictor returned UNAVAILABLE (no quantitative prediction produced); no uncertainty range/MSE/error exists.' : 'No predictions produced yet.',
  };
}

export function buildEvaluationView(state: CanonicalWorkState | null): CognitiveView {
  const acfl = getAcfl(state);
  const weights: Record<string, number> = acfl.weights || {};
  const frontier: any[] = acfl.frontier || [];
  const normalizedScores = acfl.normalized_scores || {};
  const criteria = getApplicableCriteria(state);
  const criteriaLabels = unique(
    criteria.map((c: any) => {
      const dir = c.direction ? ` (${c.direction})` : '';
      const wt = c.weight != null ? ` w=${c.weight}` : '';
      const th = c.threshold != null ? ` ≤${c.threshold}` : '';
      return `${c.target || c.description}${dir}${wt}${th}`;
    }),
  );
  const hasCriteria = criteria.length > 0;
  const hasWeights = Object.keys(weights).length > 0;
  const hasData = hasCriteria || hasWeights || frontier.length > 0;
  const hasPerAlternativeScores = Object.keys(normalizedScores).length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The criteria weighting & trade-off surface used to score alternatives.',
    dataSource:
      'prescriptive_knowledge.prescriptions[].applicable_criteria + acfl.weights + acfl.normalized_scores',
    transformation: 'ACFL weighting / criterion projection (direction / threshold / weight).',
    producingEM: 'EM Prescriptor',
    predicatesVariables: unique([...Object.keys(weights), ...criteria.map((c: any) => c.target || '')]),
    relationshipSet: frontier,
    uncertainty: hasPerAlternativeScores
      ? 'Per-alternative normalized scores are present below.'
      : 'Per-alternative normalized scores are NOT emitted by the backend for this work — only the criterion weights/thresholds and the alternatives are available.',
    supportsDecision: 'Scores the alternatives that feed the decision.',
    provenance: unique(criteria.flatMap((c: any) => c.provenance || []).filter(Boolean)),
    confidence: hasPerAlternativeScores ? null : 'Not quantified',
  });
  const whatItShows = hasData
    ? `${criteria.length} applicable criteria (${criteriaLabels.length} weighted) and ${Object.keys(weights).length} ACFL weight(s) define the score surface.${hasPerAlternativeScores ? '' : ' Per-alternative numeric scores are not emitted (data pending).'}`
    : 'No criterion weights or criteria are available.';
  return {
    id: 'EVALUATION',
    question: 'HOW WERE THE OPTIONS SCORED?',
    whatItShows,
    primaryObject: ko,
    relationships: criteriaLabels.map((c) => ({ from: 'criterion', to: c, label: 'weighted' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? 'RESOLVED' : 'PENDING',
    dataPendingReason:
      !hasCriteria && !hasWeights
        ? 'ACFL frontier / criteria are not populated for this work.'
        : 'Criteria weights are present, but per-alternative normalized scores were not emitted by the backend.',
  };
}

export function buildAlternativeLandscapeView(state: CanonicalWorkState | null): CognitiveView {
  const presc = getPrescriptive(state);
  const prescriptions: any[] = presc.prescriptions || [];
  const alternatives: any[] = prescriptions.flatMap((p) => p.alternatives || []);
  const selectedId = getSelectedAlternativeId(state);
  const criteria = getApplicableCriteria(state);
  const constraints = getPrescriptionConstraints(state);
  const acfl = getAcfl(state);
  const normalizedScores = acfl.normalized_scores || {};
  const hasPerAlternativeScores = Object.keys(normalizedScores).length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The candidate strategies considered for the decision.',
    dataSource:
      'prescriptive_knowledge.prescriptions[].alternatives[] + prescriptions[].constraints + prescriptions[].applicable_criteria + acfl.normalized_scores',
    transformation: 'Prescriptor enumeration + criteria-gated evaluation (real alternatives / real constraints / real criteria weights).',
    producingEM: 'EM Prescriptor',
    evidence: unique(alternatives.flatMap((a) => a.evidence_refs || a.provenance || []).filter(Boolean)),
    uncertainty: hasPerAlternativeScores
      ? 'Per-alternative scores present; axes below are real normalized scores.'
      : 'The backend emits NO numeric per-alternative scores — the landscape is projected from real attribute counts (expected_effects / constraints) plus real criterion weights.',
    relationshipSet: unique([
      ...alternatives.map((a) => a.alternative_id).filter(Boolean),
      ...criteria.map((c: any) => c.criterion_id || c.target || '').filter(Boolean),
      ...constraints,
    ]),
    supportsDecision: 'Provides the choice set surfaced to the human decision.',
    provenance: unique(alternatives.flatMap((a) => a.provenance || []).filter(Boolean)),
  });
  return {
    id: 'ALTERNATIVE_LANDSCAPE',
    question: 'WHAT ARE THE ALTERNATIVES?',
    whatItShows: `${alternatives.length} alternative${alternatives.length === 1 ? '' : 's'} evaluated; ${selectedId ? `selected: ${selectedId}` : 'none selected yet'}. Scored against ${criteria.length} criterion(ia) (${criteria.map((c: any) => c.target || c.criterion_id).filter(Boolean).join(', ') || 'none'}) subject to ${constraints.length} hard constraint(s).`,
    primaryObject: ko,
    relationships: alternatives.map((a) => ({ from: 'alternative', to: a.alternative_id, label: a.alternative_id === selectedId ? 'SELECTED' : 'candidate' })),
    uncertainty: ko.uncertainty,
    decisionSupport: selectedId ? `Selected: ${selectedId}` : 'Awaiting selection.',
    provenance: ko.provenance,
    cognitiveState: alternatives.length > 0 ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No alternatives were proposed.',
  };
}

export function buildHumanAuthorityView(state: CanonicalWorkState | null): CognitiveView {
  const dps = getDecisionPoints(state);
  const hrs = getHumanRequests(state);
  const humanDecision = getHumanDecision(state);
  const publication = getPublication(state);
  const frozen = getFrozen(state);
  const relevant = dps.find((d) => d.status === 'PENDING') || dps[dps.length - 1];
  const ko = makeCognitiveObject({
    whatItRepresents: 'The EUREKA-recommends → human-authorizes flow.',
    dataSource: 'decision_points[] + human_requests[] + human_decision + publication_state.status + frozen_result',
    transformation: 'Direct projection of pending/answered decision gates and the freeze authorization.',
    producingEM: 'EM Prescriptor / EM Installer',
    relationshipSet: unique([...(relevant?.options || []).map((o: any) => o.id).filter(Boolean), publication?.status, frozen?.result_id].filter(Boolean)),
    uncertainty: relevant?.uncertainty || 'Not quantified.',
    supportsDecision: relevant ? `Decision: ${relevant.question}` : 'No decision is currently gated on human input.',
    provenance: unique([relevant?.originating_em, relevant?.task_id, humanDecision?.decision_id].filter(Boolean)),
  });
  const approved = humanDecision?.decision_type === 'SELECT_ALTERNATIVE' || publication?.status === 'FROZEN' || publication?.status === 'PUBLISHED' || frozen != null;
  const whatItShows = relevant
    ? `EUREKA recommends "${relevant.recommended_option || 'no explicit recommendation'}" and the human ${relevant.status === 'PENDING' ? 'must now authorize it' : `answered "${relevant.human_selection || 'no choice'}"`}.`
    : approved
      ? 'The human authorized a decision and the result is frozen/published.'
      : 'No decision gate is open.';
  return {
    id: 'HUMAN_AUTHORITY',
    question: 'HUMAN AUTHORITY',
    whatItShows,
    primaryObject: ko,
    relationships: [
      ...(relevant ? [{ from: 'eureka', to: relevant.recommended_option || 'recommendation', label: 'recommends' } as any] : []),
      ...(relevant ? [{ from: 'human', to: relevant.human_selection || 'pending', label: relevant.status === 'PENDING' ? 'must authorize' : 'authorized' } as any] : []),
      ...(approved ? [{ from: 'authorization', to: frozen?.result_id || publication?.status || 'FROZEN', label: 'froze' } as any] : []),
    ],
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: relevant || approved ? (relevant?.status === 'PENDING' ? 'REQUIRES_HUMAN' : 'RESOLVED') : 'PENDING',
    dataPendingReason: 'No decision point, information request, or freeze authorization is present.',
  };
}

export function buildWhySelectedView(state: CanonicalWorkState | null): CognitiveView {
  const presc = getPrescriptive(state);
  const prescription = presc.prescriptions?.[0];
  const selected = prescription?.selected_alternative;
  const selectedId = selected?.alternative_id || prescription?.selected_alternative?.alternative_id;
  const selectedPredictionRefs = prescription?.supporting_predictions || [];
  const criteria = getApplicableCriteria(state);
  const criteriaLabels = criteria.map((c: any) =>
    `${c.target || c.description}${c.direction ? ` (${c.direction})` : ''}${c.weight != null ? ` w=${c.weight}` : ''}${c.threshold != null ? ` (thr=${c.threshold})` : ''}`,
  );
  const acfl = getAcfl(state);
  const normalizedScores = acfl.normalized_scores || {};
  const hasPerAlternativeScores = Object.keys(normalizedScores).length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The provenance chain: Evidence → Predictions → Evaluation → selected alternative → Prescription.',
    dataSource:
      'prescriptive_knowledge.prescriptions[] (selected_alternative + supporting_predictions/supporting_knowledge + rationale + evidence_refs + applicable_criteria + constraints) + acfl',
    transformation: 'Prescriptor synthesis of evidence + criteria into a recommendation.',
    producingEM: 'EM Prescriptor',
    predicatesVariables: (prescription?.supporting_predictions || []).concat(prescription?.supporting_knowledge || []).concat(criteria.map((c: any) => c.target || '')),
    evidence: prescription?.evidence_refs || [],
    uncertainty: prescription?.decision_rule?.status
      ? `Decision rule: ${prescription.decision_rule.status}${prescription.decision_rule.rule_type ? ` (${prescription.decision_rule.rule_type})` : ''}${prescription.decision_rule.authority ? ` — ${prescription.decision_rule.authority}` : ''}${prescription.decision_rule.description ? ` — ${prescription.decision_rule.description}` : ''}`
      : `Per-alternative numeric scores: ${hasPerAlternativeScores ? 'present' : 'not emitted (data pending)'}.`,
    relationshipSet: unique([
      ...(prescription?.alternatives || []).map((a: any) => a.alternative_id),
      ...selectedPredictionRefs,
      ...(prescription?.supporting_knowledge || []),
      ...criteria.map((c: any) => c.criterion_id || c.target || ''),
    ]),
    supportsDecision: selectedId ? `Recommended: ${selectedId}` : 'No recommendation produced yet.',
    provenance: prescription?.provenance || [],
    confidence: prescription?.validation_status,
  });
  // Truthful note about the real evaluation gap (not fabricating per-alt scores).
  const scoreNote = hasPerAlternativeScores
    ? ''
    : ` Per-alternative normalized scores are NOT emitted by the backend for this work — the evaluation is carried by ${criteria.length} criterion weight(s)/threshold(s) (${criteria.map((c: any) => c.target || c.criterion_id).filter(Boolean).join(', ') || 'none'}) rather than a numeric score per alternative.`;
  const hasData = !!(prescription && (selectedId || (prescription?.rationale || '')));
  return {
    id: 'WHY_SELECTED',
    question: selectedId ? `WHY ${selectedId}?` : 'WHY SELECTED?',
    whatItShows: hasData
      ? `The rationale for ${selectedId || 'the recommendation'}: ${prescription?.rationale || 'rationale captured below'}.${scoreNote}`
      : 'No validated prescription produced yet.',
    primaryObject: ko,
    relationships: [
      { from: 'evidence', to: `evidence[${(prescription?.evidence_refs || []).join(',')}]`, label: 'supports' },
      { from: 'predictions', to: (selectedPredictionRefs || []).join(',') || 'predictions', label: 'predicts' },
      { from: 'criteria', to: 'selection', label: 'scores' },
      { from: 'alternative', to: selectedId || 'none', label: 'selected' },
      ...criteria.map((c: any) => ({ from: 'criterion', to: c.target || c.criterion_id || '', label: `w=${c.weight ?? '?'} ${c.direction ?? ''}` })),
    ],
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? (prescription?.validation_status === 'HUMAN_DECISION_REQUIRED' ? 'REQUIRES_HUMAN' : 'RESOLVED') : 'PENDING',
    dataPendingReason: 'No validated prescription produced yet.',
  };
}

const EMPTY_DELTA_ITEMS: any[] = [];
export function buildWhatChangedView(state: CanonicalWorkState | null): CognitiveView {
  const presc = getPrescriptive(state);
  const prescription = presc.prescriptions?.[0];
  const selected = prescription?.selected_alternative;
  const effectList: string[] = selected?.expected_effects || [];
  const constraintList: string[] = selected?.constraints || [];
  const hardConstraints = getPrescriptionConstraints(state);
  const acfl = getAcfl(state);
  const weights: Record<string, number> = acfl.weights || {};
  const criteria = getApplicableCriteria(state);
  const histCtx = getHistoricalContext(state);
  const deltaItems: any[] = histCtx?.delta_assessment?.items || [];
  const hasDelta = deltaItems.length > 0;
  const hasData = effectList.length > 0 || constraintList.length > 0 || Object.keys(weights).length > 0 || hardConstraints.length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The before/after prescription risk/cost/impact trade-off.',
    dataSource:
      'prescriptive_knowledge.prescriptions[].selected_alternative.{expected_effects,constraints} + prescriptions[].constraints + acfl.weights + historical_context.delta_assessment.items',
    transformation: 'Projection of the selected alternative expected effects vs. its constraints + hard invariants.',
    producingEM: 'EM Prescriptor',
    predicatesVariables: criteria.map((c: any) => c.target).filter(Boolean),
    uncertainty: hasDelta
      ? `Real material deltas: ${deltaItems.length} item(s) (${deltaItems.map((d: any) => `${d.delta_type || d.field || 'field'} ${d.historical_value ?? ''}→${d.current_value ?? ''}`).filter(Boolean).join('; ') || 'details below'}).`
      : 'The backend records NO numeric before/after delta for this work (delta_assessment absent); the change is expressed directionally via expected_effects/constraints, not numeric deltas.',
    relationshipSet: [...effectList, ...constraintList, ...hardConstraints],
    supportsDecision: 'Explains the expected value of committing to the selected alternative.',
    provenance: selected?.provenance || prescription?.provenance || [],
  });
  return {
    id: 'WHAT_CHANGED',
    question: 'WHAT CHANGED AFTER THE PRESCRIPTION?',
    whatItShows: hasData
      ? `Choosing ${selected?.alternative_id || 'the selected alternative'} yields ${effectList.length} expected effect(s) subject to ${constraintList.length} alternative constraint(s) and ${hardConstraints.length} hard invariant(s).${hasDelta ? '' : ' No numeric before/after delta is emitted by the backend (data pending).'}`
      : 'No before/after delta is recorded in the backend state.',
    primaryObject: ko,
    relationships: [
      ...effectList.map((e) => ({ from: 'expected_effect', to: e, label: 'gain' })),
      ...constraintList.map((c) => ({ from: 'constraint', to: c, label: 'binds' })),
      ...hardConstraints.map((c) => ({ from: 'hard_constraint', to: c, label: 'invariant' })),
    ],
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No expected effects/constraints recorded for the selected alternative.',
  };
}

export function buildOutcomeStoryView(state: CanonicalWorkState | null): CognitiveView {
  const result = getStateResult(state);
  const publication = getPublication(state);
  const pubSections = (publication?.publications || []).flatMap((pub: any) => pub.sections || []);
  const evidenceCount = state?.evidence?.length ?? 0;
  const presc = getPrescriptive(state);
  const prescription = presc.prescriptions?.[0];
  const selectedId = getSelectedAlternativeId(state);
  const hasData = result?.status === 'AVAILABLE' || pubSections.length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The delivered outcome: question, findings, recommendation, execution, published sections.',
    dataSource: 'state.result + publication_state.publications[].sections',
    transformation: 'Publisher assembly of the final result.',
    producingEM: 'EM Publisher',
    evidence: (result?.evidence_ids || []).concat(pubSections.flatMap((s: any) => s.source_refs || [])),
    uncertainty: result?.confidence != null ? `Confidence: ${result.confidence}` : 'Not quantified.',
    relationshipSet: pubSections.map((s: any) => s.section_type),
    supportsDecision: 'The authoritative final answer to the question.',
    provenance: (result?.provenance || []).concat(pubSections.flatMap((s: any) => s.provenance || [])),
    confidence: result?.confidence,
  });
  return {
    id: 'OUTCOME_STORY',
    question: 'WHAT HAPPENED? (OUTCOME)',
    whatItShows: hasData
      ? `Delivered with ${evidenceCount} evidence source(s) and ${pubSections.length} published section(s).`
      : 'No final result produced yet.',
    primaryObject: ko,
    relationships: pubSections.map((s: any) => ({ from: 'published', to: s.section_type, label: 'section' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No final result produced yet.',
  };
}

export function buildWhatHappenedView(state: CanonicalWorkState | null): CognitiveView {
  const events = getExecutionEvents(state);
  const hasData = events.length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The execution trace across the 8-EM pipeline.',
    dataSource: 'execution_events[]',
    transformation: 'Chronological projection of the execution event stream.',
    producingEM: 'All 8-EM (cross-cutting)',
    uncertainty: 'Bounded by what the runtime surfaced.',
    relationshipSet: unique(events.map((e) => e.canonical_em).filter(Boolean)),
    supportsDecision: 'Reconstructs the question → … → published trajectory.',
    provenance: unique(events.map((e) => e.capability_id).filter(Boolean)),
  });
  return {
    id: 'WHAT_HAPPENED',
    question: 'WHAT HAPPENED? (TRACE)',
    whatItShows: hasData ? `${events.length} execution event(s) recorded across the pipeline.` : 'No execution trace recorded yet.',
    primaryObject: ko,
    relationships: events.slice(0, 16).map((e) => ({ from: e.status, to: `${e.canonical_em}: ${e.event}`, label: e.step_id })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No execution trace recorded yet.',
  };
}

export function buildLearningView(state: CanonicalWorkState | null): CognitiveView {
  const knowledge = getKnowledge(state);
  const unknowns: string[] = knowledge.unknowns || [];
  const contradictions: string[] = knowledge.contradictions || [];
  const conditions = getConditions(state);
  const gaps: string[] = (state as any)?.gaps || [];
  const events = getExecutionEvents(state);
  const hasData = unknowns.length + contradictions.length + gaps.length + conditions.length + events.length > 0;
  const ko = makeCognitiveObject({
    whatItRepresents: 'The meta-learning: gaps, conditions, contradictions, unknowns, execution trace.',
    dataSource: 'knowledge.{unknowns,contradictions} + gaps + conditions + execution_events',
    transformation: 'Reflection over execution traces & state conditions.',
    producingEM: 'All 8-EM (cross-cutting)',
    uncertainty: 'Learning is bounded by what the runtime surfaced.',
    relationshipSet: unique(conditions.map((c) => c.reason_code).concat(gaps).filter(Boolean)),
    supportsDecision: 'Informs future runs & documents limitations.',
    provenance: conditions.map((c) => c.reason_code).concat(events.map((e) => e.event)),
  });
  const statements = [
    ...unknowns.map((u) => `Unknown: ${u}`),
    ...contradictions.map((c) => `Contradiction: ${c}`),
    ...gaps.map((g) => `Gap: ${g}`),
    ...conditions.map((c) => `${c.status}: ${c.message}`),
  ];
  return {
    id: 'LEARNING',
    question: 'WHAT HAPPENED? (TRACE)',
    whatItShows: hasData ? `${statements.length} learning signal(s) recorded.` : 'No learning signals recorded.',
    primaryObject: ko,
    relationships: statements.map((s) => ({ from: 'learned', to: s, label: 'signal' })),
    uncertainty: ko.uncertainty,
    decisionSupport: ko.supportsDecision,
    provenance: ko.provenance,
    cognitiveState: hasData || state?.work?.status === 'COMPLETED' ? 'RESOLVED' : 'PENDING',
    dataPendingReason: 'No learning signals (gaps/conditions/contradictions) recorded.',
  };
}

const viewBuilders: Record<CognitiveViewKey, (state: CanonicalWorkState | null) => CognitiveView> = {
  QUESTION: buildQuestionView,
  CONTEXT: buildContextView,
  DATA: buildDataView,
  DISCOVERY: buildDiscoveryView,
  WHAT_IS_UNCERTAIN: buildUncertainView,
  EVALUATION: buildEvaluationView,
  ALTERNATIVE_LANDSCAPE: buildAlternativeLandscapeView,
  HUMAN_AUTHORITY: buildHumanAuthorityView,
  WHY_SELECTED: buildWhySelectedView,
  WHAT_CHANGED: buildWhatChangedView,
  ACTION_DAG: (state: CanonicalWorkState | null) =>
    ({
      id: 'ACTION_DAG',
      question: 'WHAT WILL BE DONE?',
      whatItShows: 'The operational action plan as an explanation DAG.',
      primaryObject: makeCognitiveObject({
        whatItRepresents: 'The validated action plan and its execution authorization/result.',
        dataSource: 'action_plan.actions[] + execution_state',
        transformation: 'Actioner synthesis + Installer authorization/execution.',
        producingEM: 'EM Actioner / EM Installer',
        uncertainty: getExecutionState(state)?.result?.status ? `Execution result: ${getExecutionState(state).result.status}` : 'Not executed yet.',
        supportsDecision: 'The step-by-step actions to realise the prescription.',
        provenance: getActionPlan(state)?.provenance || [],
      }),
      relationships: [],
      uncertainty: 'Not quantified.',
      decisionSupport: 'Carries the prescription into execution.',
      provenance: getActionPlan(state)?.provenance || [],
      cognitiveState: (getActionPlan(state)?.actions || []).length > 0 ? 'RESOLVED' : 'PENDING',
      dataPendingReason: 'No validated action plan produced yet.',
    }) as CognitiveView,
  OUTCOME_STORY: buildOutcomeStoryView,
  WHAT_HAPPENED: buildWhatHappenedView,
  LEARNING: buildLearningView,
};

/**
 * Build a single Cognitive View for a given view key (defaults to a pending view
 * when the key is unknown).
 */
export function buildView(state: CanonicalWorkState | null, key: CognitiveViewKey): CognitiveView {
  const builder = viewBuilders[key];
  return builder ? builder(state) : buildLearningView(state);
}

/**
 * Build a compact, truthful narrative context for the Copilot narrator.
 * It is derived only from real CanonicalWorkState fields so the LLM can answer
 * nested questions ("¿por qué ALT-002?", "¿qué evidencia soporta esto?", "¿qué
 * cambió tras la ejecución?") from the built Cognitive Story, never from generic
 * chat or invented data.
 */
export function buildCopilotNarrativeContext(state: CanonicalWorkState | null): string {
  if (!state) return '';
  const lines: string[] = [];

  const chapters = buildCognitiveStory(state);
  lines.push('*** EUREKA COGNITIVE STORY (chapter -> question -> state) ***');
  chapters.forEach((c) => {
    lines.push(`${c.order}. ${c.shortTitle} [${c.cognitiveState}] — QUESTION: "${c.question}"`);
  });

  const selected = getSelectedAlternativeId(state);
  const prescription = getPrescriptive(state).prescriptions?.[0];
  if (prescription) {
    lines.push('');
    lines.push('*** PRESCRIPTION / WHY ***');
    lines.push(`Prescription: ${prescription.prescription_id}`);
    lines.push(`Selected alternative: ${selected || 'none'}`);
    lines.push(`Rationale: ${prescription.rationale || '—'}`);
    lines.push(`Decision rule: ${prescription.decision_rule?.status || '—'}${prescription.decision_rule?.rule_type ? ` (${prescription.decision_rule.rule_type})` : ''}${prescription.decision_rule?.authority ? ` (${prescription.decision_rule.authority})` : ''}${prescription.decision_rule?.description ? ` — ${prescription.decision_rule.description}` : ''}`);
    lines.push(`Authority: ${prescription.authority || '—'} · Validation: ${prescription.validation_status || '—'}`);
    lines.push(`Evidence refs: ${(prescription.evidence_refs || []).join(', ') || '—'}`);
    lines.push(`Supporting predictions: ${(prescription.supporting_predictions || []).join(', ') || '—'}`);
    lines.push(`Supporting knowledge: ${(prescription.supporting_knowledge || []).join(', ') || '—'}`);
    lines.push(`Hard constraints: ${(prescription.constraints || []).join('; ') || '—'}`);
  }

  // Real criteria evaluation surface (the REAL "how were options scored").
  const criteria = getApplicableCriteria(state);
  if (criteria.length) {
    lines.push('');
    lines.push('*** EVALUATION / CRITERIA (REAL weights, directions, thresholds) ***');
    criteria.forEach((c: any) => {
      lines.push(`Criterion ${c.criterion_id || '?'}: "${c.target || c.description}" direction=${c.direction || 'N/A'} threshold=${c.threshold ?? 'N/A'} weight=${c.weight ?? '?'} authority=${c.authority || 'N/A'} provenance=[${(c.provenance || []).join('; ')}]`);
    });
  }
  const acfl = getAcfl(state);
  const acflW = acfl.weights || {};
  if (Object.keys(acflW).length) {
    lines.push('');
    lines.push('*** ACFL WEIGHTS ***');
    lines.push(`ACFL weights: ${Object.entries(acflW).map(([k, v]) => `${k}=${v}`).join(', ')}`);
  }
  const acflNorm = acfl.normalized_scores || {};
  const evaluatedScores = getEvaluatedScores(state);
  const rankings = getRankings(state);
  if (Object.keys(acflNorm).length || Object.keys(evaluatedScores).length || Object.keys(rankings).length) {
    lines.push('');
    lines.push('*** PER-ALTERNATIVE SCORES ***');
    if (Object.keys(acflNorm).length) lines.push(`ACFL normalized_scores: ${JSON.stringify(acflNorm)}`);
    if (Object.keys(evaluatedScores).length) lines.push(`evaluated_scores: ${JSON.stringify(evaluatedScores)}`);
    if (Object.keys(rankings).length) lines.push(`rankings: ${JSON.stringify(rankings)}`);
  } else {
    lines.push('');
    lines.push('*** PER-ALTERNATIVE SCORES: NOT EMITTED ***');
    lines.push('The backend does NOT emit per-alternative numeric scores for this work (acfl.normalized_scores, evaluated_scores, rankings are empty). Answer "what if" questions using the alternatives\' real description/expected_effects/constraints and the real criterion weights — do NOT invent a numeric score.');
  }

  if (prescription) {
    lines.push('');
    lines.push('*** ALTERNATIVES (for "what if ALT-00x") ***');
    (prescription.alternatives || []).forEach((a: any) => {
      lines.push(`Alternative ${a.alternative_id}${a.alternative_id === selected ? '  <-- SELECTED' : ''}`);
      lines.push(`  description: ${a.description || '—'}`);
      lines.push(`  expected_effects: ${(a.expected_effects || []).join('; ') || '—'}`);
      lines.push(`  constraints: ${(a.constraints || []).join('; ') || '—'}`);
      lines.push(`  provenance: ${(a.provenance || []).join('; ') || '—'}`);
    });
  }

  const predictions = getPredictive(state).predictions || [];
  if (predictions.length) {
    lines.push('');
    lines.push('*** PREDICTIONS / UNCERTAINTY ***');
    predictions.forEach((p: any) => {
      const unc = p.uncertainty || {};
      const ci = unc.confidence_interval || {};
      const lo = ci.low ?? ci.lower ?? '?';
      const hi = ci.high ?? ci.upper ?? '?';
      lines.push(`${p.prediction_id}: target=${p.target_variable} predicted=${p.predicted_value ?? 'n/a'} baseline=${p.baseline ?? 'n/a'} uncertainty=${unc.status ?? 'NOT_AVAILABLE'} range=${lo}..${hi} mse=${p.mse ?? 'n/a'} evidence=[${(p.evidence_refs || []).join(', ')}]`);
    });
  } else {
    lines.push('');
    lines.push('*** PREDICTIONS: NONE ***');
    lines.push(`predictive_knowledge.status = ${getPredictive(state).status || 'n/a'} and predictions list is empty. There is NO quantitative prediction / uncertainty range / MSE / error for this work. Do not invent one.`);
  }

  const plan = getActionPlan(state);
  if (plan?.actions?.length) {
    lines.push('');
    lines.push('*** ACTION PLAN ***');
    lines.push(`Plan: ${plan.plan_id} rationale="${plan.rationale || '—'}"`);
    plan.actions.forEach((a: any) => {
      lines.push(`${a.action_id} [${a.owner}] deps=[${(a.dependencies || []).join(', ')}] inputs=[${(a.inputs || []).join(', ')}] outputs=[${(a.expected_outputs || []).join(', ')}] criteria=[${(a.acceptance_criteria || []).join('; ')}] desc="${a.description || ''}"`);
    });
  }

  const dps = getDecisionPoints(state);
  const hr = (state as any).human_requests || [];
  const humanDecision = getHumanDecision(state);
  const pub = getPublication(state);
  const frozen = getFrozen(state);
  if (dps.length || hr.length || humanDecision || pub || frozen) {
    lines.push('');
    lines.push('*** HUMAN AUTHORITY ***');
    dps.forEach((d) => {
      lines.push(`Decision ${d.decision_id}: "${d.question}" status=${d.status} recommended=${d.recommended_option || '—'} human_selection=${d.human_selection || '—'} reason="${d.recommendation_reason || '—'}"`);
    });
    (hr || []).forEach((h: any) => {
      lines.push(`Info request ${h.request_id}: "${h.question}" status=${h.status}`);
    });
    if (humanDecision) lines.push(`Human decision: type=${humanDecision.decision_type} selected=${humanDecision.selected_alternative_id || '—'}`);
    if (pub) lines.push(`Publication status: ${pub.status}`);
    if (frozen) lines.push(`Frozen result: ${frozen.result_id} (${frozen.status})`);
  }

  const execState = getExecutionState(state);
  if (execState) {
    lines.push('');
    lines.push('*** EXECUTION / WHAT CHANGED AFTER ***');
    const auth = execState.authorization || {};
    lines.push(`Execution status: ${execState.status || '—'}`);
    lines.push(`Authorization: by ${auth.authorized_by || '—'} level=${auth.authorized_execution_level ?? 'n/a'} actions=[${(auth.authorized_actions || []).join(', ')}]`);
    if (execState.result) {
      lines.push(`Execution result status: ${execState.result.status}`);
      lines.push(`Successful actions: ${(execState.result.successful_actions || []).join(', ') || '—'}`);
      lines.push(`Failed actions: ${(execState.result.failed_actions || []).join(', ') || '—'}`);
      lines.push(`Execution evidence: ${(execState.result.evidence_refs || []).join(', ') || '—'}`);
    }
    if (execState.evidence?.length) {
      lines.push(`Observations per executed action:`);
      execState.evidence.forEach((ev: any) => {
        (ev.observations || []).forEach((ob: any) => {
          lines.push(`  ${ev.action_id}: [${ob.observation_type}] ${ob.content}${ob.is_error ? ' (ERROR)' : ''}`);
        });
      });
    }
  }
  const liveResult = getStateResult(state);
  if (liveResult?.status === 'AVAILABLE') {
    lines.push('');
    lines.push('*** FINAL RESULT ***');
    lines.push(`Result status: ${liveResult.status}${liveResult.confidence != null ? ` (confidence=${liveResult.confidence})` : ' (confidence not emitted)'}`);
    lines.push(`Result summary: ${liveResult.summary || '—'}`);
  }

  const events = getExecutionEvents(state);
  if (events.length) {
    lines.push('');
    lines.push('*** WHAT HAPPENED (trace) ***');
    events.forEach((e) => {
      lines.push(`${e.canonical_em} ${e.status} — ${e.event}${e.message ? ` (${e.message})` : ''}`);
    });
  }

  const knowledge = getKnowledge(state);
  const result = getStateResult(state);
  if (knowledge?.findings?.length || result) {
    lines.push('');
    lines.push('*** FINDINGS / OUTCOME ***');
    (knowledge.findings || []).forEach((f: any) => {
      lines.push(`Finding ${f.finding_id} [${f.status}]: ${f.statement}`);
    });
    if (result) {
      lines.push(`Result status: ${result.status}`);
      lines.push(`Result summary: ${result.summary || '—'}`);
    }
  }

  lines.push('');
  lines.push('*** RULE ***');
  lines.push('Answer the operator question using ONLY the facts above. If a value is absent, say so — do not invent data. Answer in the language of the question.');

  return lines.join('\n');
}

const str = (v: unknown): string => (typeof v === 'string' ? v : v == null ? '' : String(v));
