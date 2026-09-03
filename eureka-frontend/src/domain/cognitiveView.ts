import type { CanonicalWorkState } from './canonicalSchema';
import type { CognitiveState } from './narrative';

/**
 * EUREKA "Dark Intelligence" Cognitive Visualization + Storytelling contracts.
 *
 * A CognitiveView is NOT a chart. It is the atomic unit that ANSWERS A QUESTION
 * out of the REAL CanonicalWorkState. Every view carries:
 *   - the question it answers (e.g. "WHY ALT-002?"),
 *   - what it shows,
 *   - the primary CognitiveObject (semantic definition of what it projects),
 *   - its relationships, uncertainty, decision support and provenance.
 *
 * Nothing here invents numbers. If the backend state has no data for a
 * question, the view reports a truthful "DATA PENDING" state via
 * `cognitiveState === 'PENDING'` and `dataPendingReason`.
 */

/** The set of question-driven Cognitive Views that the story engine can mount. */
export type CognitiveViewKey =
  | 'QUESTION'
  | 'CONTEXT'
  | 'DATA'
  | 'DISCOVERY'
  | 'WHAT_IS_UNCERTAIN'
  | 'EVALUATION'
  | 'ALTERNATIVE_LANDSCAPE'
  | 'HUMAN_AUTHORITY'
  | 'WHY_SELECTED'
  | 'WHAT_CHANGED'
  | 'ACTION_DAG'
  | 'OUTCOME_STORY'
  | 'WHAT_HAPPENED'
  | 'LEARNING';

/**
 * The contract for a single Cognitive Object: the semantic "thing a view knows".
 * Mirrors the real backend projections (proof of origin, not invention).
 */
export interface CognitiveObject {
  /** What this object represents (semantic definition). */
  whatItRepresents: string;
  /** Backend field(s) this object projects (e.g. "prescriptive_knowledge.prescriptions[].selected_alternative"). */
  dataSource: string;
  /** Transformation applied to get the object from the data source. */
  transformation: string;
  /** The 8-EM that produced this object. */
  producingEM: string;
  /** Predicates / variables used by the object. */
  predicatesVariables: string[];
  /** Supporting evidence references (evidence_ids / finding refs). */
  evidence: string[];
  /** Uncertainty statement (truthful; may be "Not quantified"). */
  uncertainty: string;
  /** Related objects / relationships referenced by this object. */
  relationshipSet: string[];
  /** The decision / recommendation this object supports. */
  supportsDecision: string;
  /** Provenance chain for the object. */
  provenance: string[];
  /** Confidence (truthful; "Not quantified" when absent). */
  confidence: string;
}

/** A relationship edge between two cognitive objects/concepts. */
export interface CognitiveRelationship {
  from: string;
  to: string;
  label: string;
}

/**
 * A Cognitive View = a unit that ANSWERS A QUESTION. Not a chart.
 */
export interface CognitiveView {
  id: CognitiveViewKey;
  /** The question this view answers (e.g. "WHY ALT-002?"). */
  question: string;
  /** Human-facing description of what this view shows. */
  whatItShows: string;
  /** The primary cognitive object that anchors the view. */
  primaryObject: CognitiveObject;
  /** Semantic relationship edges relevant to the question. */
  relationships: CognitiveRelationship[];
  /** Uncertainty statement for the view. */
  uncertainty: string;
  /** What decision this view supports. */
  decisionSupport: string;
  /** Provenance chain for the view. */
  provenance: string[];
  cognitiveState: CognitiveState;
  /** Truthful reason when cognitiveState === 'PENDING'. */
  dataPendingReason: string;
}

/**
 * A chapter of the Cognitive Story: maps one narrative stage to the question it
 * answers and the Cognitive View that renders it.
 */
export interface CognitionChapter {
  stage: string;
  order: number;
  title: string;
  shortTitle: string;
  question: string;
  viewKey: CognitiveViewKey;
  cognitiveState: CognitiveState;
  hasData: boolean;
  dataPendingReason: string;
}

/* ------------------------------------------------------------------ *
 * Small truth-preserving helpers
 * ------------------------------------------------------------------ */

const str = (v: unknown): string =>
  typeof v === 'string' ? v : v == null ? '' : String(v);

const strList = (v: unknown): string[] =>
  Array.isArray(v) ? v.map(str).filter(Boolean) : [];

export const unique = (list: string[]): string[] => [...new Set(list)];

/** Build a CognitiveObject from raw real state. Confidence is truthful or "Not quantified". */
export function makeCognitiveObject(partial: {
  whatItRepresents: string;
  dataSource: string;
  transformation: string;
  producingEM: string;
  predicatesVariables?: string[];
  evidence?: string[];
  uncertainty?: string;
  relationshipSet?: string[];
  supportsDecision?: string;
  provenance?: string[];
  confidence?: string | number | null;
}): CognitiveObject {
  const conf = partial.confidence;
  return {
    whatItRepresents: partial.whatItRepresents,
    dataSource: partial.dataSource,
    transformation: partial.transformation,
    producingEM: partial.producingEM,
    predicatesVariables: partial.predicatesVariables ?? [],
    evidence: partial.evidence ?? [],
    uncertainty: partial.uncertainty ?? 'Not quantified.',
    relationshipSet: partial.relationshipSet ?? [],
    supportsDecision: partial.supportsDecision ?? '',
    provenance: partial.provenance ?? [],
    confidence:
      typeof conf === 'number' && Number.isFinite(conf)
        ? String(conf)
        : str(conf) || 'Not quantified',
  };
}

/** Safe numeric extraction that never returns a fabricated number. */
export const finiteNum = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v) ? v : null;

/* ------------------------------------------------------------------ *
 * Real-data selectors (no invention, always tolerant)
 * ------------------------------------------------------------------ */

export const getProblem = (state: CanonicalWorkState | null): any =>
  (state as any)?.problem || null;

export const getKnowledge = (state: CanonicalWorkState | null): any =>
  (state as any)?.knowledge || {};

export const getPredictive = (state: CanonicalWorkState | null): any =>
  (state as any)?.predictive_knowledge || {};

export const getPrescriptive = (state: CanonicalWorkState | null): any =>
  (state as any)?.prescriptive_knowledge || {};

export const getActionPlan = (state: CanonicalWorkState | null): any =>
  (state as any)?.action_plan || null;

export const getExecutionState = (state: CanonicalWorkState | null): any =>
  (state as any)?.execution_state || null;

export const getPublication = (state: CanonicalWorkState | null): any =>
  (state as any)?.publication_state || null;

export const getFrozen = (state: CanonicalWorkState | null): any =>
  (state as any)?.frozen_result || null;

export const getDecisionPoints = (state: CanonicalWorkState | null): any[] =>
  (state as any)?.decision_points || [];

export const getHumanRequests = (state: CanonicalWorkState | null): any[] =>
  (state as any)?.human_requests || [];

export const getHumanDecision = (state: CanonicalWorkState | null): any =>
  (state as any)?.human_decision || null;

export const getExecutionEvents = (state: CanonicalWorkState | null): any[] =>
  (state as any)?.execution_events || [];

export const getConditions = (state: CanonicalWorkState | null): any[] =>
  (state as any)?.conditions || [];

export const getStateResult = (state: CanonicalWorkState | null): any =>
  (state as any)?.state?.result || null;

export const getResult = (state: CanonicalWorkState | null): any =>
  getStateResult(state);

/** The ACFL evaluation surface. Backend may emit it top-level OR under state.acfl. */
export const getAcfl = (state: CanonicalWorkState | null): any => {
  const top = (state as any)?.acfl;
  const nested = (state as any)?.state?.acfl;
  if (top && typeof top === 'object' && Object.keys(top).length) return top;
  return nested || {};
};

/** Real per-classification evaluation scores (may be {} when the backend emits none). */
export const getEvaluatedScores = (state: CanonicalWorkState | null): any =>
  (state as any)?.evaluated_scores || {};

export const getRankings = (state: CanonicalWorkState | null): any =>
  (state as any)?.rankings || {};

export const getScientificMetrics = (state: CanonicalWorkState | null): any =>
  (state as any)?.scientific_metrics || {};

export const getHistoricalContext = (state: CanonicalWorkState | null): any =>
  (state as any)?.historical_context || null;

/** The real applicable criteria (criterion_id / target / direction / threshold / weight / authority). */
export function getApplicableCriteria(state: CanonicalWorkState | null): any[] {
  const presc = getPrescriptive(state);
  const prescriptions: any[] = presc.prescriptions || [];
  return prescriptions.flatMap((p) => p.applicable_criteria || p.criteria || p.criterion || []).filter(Boolean);
}

/** The real prescription-level hard constraints (e.g. availability 99.9%, budget, change mgmt). */
export function getPrescriptionConstraints(state: CanonicalWorkState | null): string[] {
  const presc = getPrescriptive(state);
  const prescriptions: any[] = presc.prescriptions || [];
  return prescriptions.flatMap((p) => {
    const c = (p as any).constraints;
    return Array.isArray(c) ? (c as string[]) : [];
  }).filter(Boolean);
}

/** The currently/canonically selected alternative id, from the validated prescription. */
export function getSelectedAlternativeId(state: CanonicalWorkState | null): string | null {
  const presc = getPrescriptive(state).prescriptions?.[0];
  return presc?.selected_alternative?.alternative_id || null;
}
