export type EMStage = 'OBJECTIVE' | 'SEMANTICS' | 'PREDICTION' | 'SCIENCE' | 'EVALUATION' | 'RANKING' | 'SELECTION' | 'PRESCRIPTION' | 'FREEZE' | 'AUTHORITY' | 'ACTION';
export type GovernanceState = 'PENDING' | 'FROZEN' | 'BLOCKED' | 'AUTHORIZATION_REQUIRED' | 'AUTHORIZED' | 'EXECUTED';

export interface DecisionContext {
  id: string;
  caseId: string;
  title: string;
  workspace: string;
  agent: string;
  emStage: EMStage;
  governanceState: GovernanceState;
  createdAt: string;
  updatedAt: string;
}

export interface NodeBase {
  id: string;
  type: string;
  title: string;
  description?: string;
  provenance?: string;
}

export interface Evidence extends NodeBase {
  type: 'EVIDENCE';
  confidence: number;
  source: string;
  timestamp: string;
}

export interface Constraint extends NodeBase {
  type: 'CONSTRAINT';
  operator: string;
  threshold: number;
  isHard: boolean;
}

export interface Alternative extends NodeBase {
  type: 'ALTERNATIVE';
  utility: number;
  risk: number;
  cost: number;
  confidence: number;
  feasibility: number;
  isDominated: boolean;
  rank: number;
  status: 'REJECTED' | 'FEASIBLE' | 'SELECTED';
  scientificMetrics: Record<string, number>;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  stage: EMStage;
  title: string;
  description: string;
  relatedEntityIds: string[];
}

export interface GraphEdge {
  source: string;
  target: string;
  type: 'SUPPORTS' | 'CONSTRAINS' | 'EVALUATES' | 'RESULTS_IN' | 'TRANSFORMS_TO';
  weight?: number;
}

// THE SINGLE DEMO DECISION DATASET (Rich Analytical Model)
export const MOCK_DECISION_GRAPH = {
  context: {
    id: "DEC-001",
    caseId: "CASE-Q4-EXP",
    title: "European Q4 Expansion Strategy",
    workspace: "Strategic Planning",
    agent: "DeepSeek-Local",
    emStage: "AUTHORITY" as EMStage,
    governanceState: "AUTHORIZATION_REQUIRED" as GovernanceState,
    createdAt: "2035-11-20T09:42:00Z",
    updatedAt: "2035-11-20T10:39:00Z"
  } as DecisionContext,

  evidence: [
    { id: "EV-01", type: 'EVIDENCE', title: "Q3 Market Cap Analysis", source: "DataLake-Alpha", confidence: 0.94, timestamp: "2035-11-20T10:01:00Z", provenance: "System Indexer" },
    { id: "EV-02", type: 'EVIDENCE', title: "Competitor Logistics Report", source: "External-Intel", confidence: 0.76, timestamp: "2035-11-20T10:02:00Z", provenance: "Semantic Parser" },
    { id: "EV-03", type: 'EVIDENCE', title: "Regulatory Compliance (EU)", source: "Gov-Node-2", confidence: 0.99, timestamp: "2035-11-20T10:03:00Z", provenance: "Constraint Engine" },
  ] as Evidence[],

  constraints: [
    { id: "CN-01", type: 'CONSTRAINT', title: "Maximum Capital Risk", operator: "<", threshold: 0.30, isHard: true, description: "Capital risk cannot exceed 30% of total allocation." },
    { id: "CN-02", type: 'CONSTRAINT', title: "Deployment Speed", operator: "<", threshold: 45, isHard: false, description: "Preferred deployment within 45 days." },
  ] as Constraint[],

  alternatives: [
    { id: "ALT-A", type: 'ALTERNATIVE', title: "Aggressive DACH Entry", utility: 0.88, risk: 0.45, cost: 0.7, confidence: 0.82, feasibility: 0.4, isDominated: true, rank: 4, status: 'REJECTED', scientificMetrics: { pValue: 0.04, variance: 0.12 } },
    { id: "ALT-B", type: 'ALTERNATIVE', title: "Phased Nordic Expansion", utility: 0.91, risk: 0.20, cost: 0.4, confidence: 0.92, feasibility: 0.9, isDominated: false, rank: 1, status: 'SELECTED', scientificMetrics: { pValue: 0.01, variance: 0.03 } },
    { id: "ALT-C", type: 'ALTERNATIVE', title: "Acquisition of Local Player", utility: 0.95, risk: 0.35, cost: 0.9, confidence: 0.65, feasibility: 0.5, isDominated: false, rank: 2, status: 'FEASIBLE', scientificMetrics: { pValue: 0.08, variance: 0.22 } },
    { id: "ALT-D", type: 'ALTERNATIVE', title: "Status Quo (No Action)", utility: 0.10, risk: 0.05, cost: 0.0, confidence: 0.99, feasibility: 1.0, isDominated: true, rank: 14, status: 'REJECTED', scientificMetrics: { pValue: 0.00, variance: 0.01 } },
  ] as Alternative[],

  timeline: [
    { id: "TL-1", timestamp: "2035-11-20T09:42:00Z", stage: 'OBJECTIVE', title: "Objective Created", description: "Expansion goal established.", relatedEntityIds: [] },
    { id: "TL-2", timestamp: "2035-11-20T10:01:00Z", stage: 'SEMANTICS', title: "Evidence Indexed", description: "3 primary intelligence sources parsed.", relatedEntityIds: ["EV-01", "EV-02", "EV-03"] },
    { id: "TL-3", timestamp: "2035-11-20T10:14:00Z", stage: 'PREDICTION', title: "Predicate Formalized", description: "Constraints translated into logical boundaries.", relatedEntityIds: ["CN-01", "CN-02"] },
    { id: "TL-4", timestamp: "2035-11-20T10:31:00Z", stage: 'SCIENCE', title: "14 Alternatives Generated", description: "Phase space populated.", relatedEntityIds: ["ALT-A", "ALT-B", "ALT-C", "ALT-D"] },
    { id: "TL-5", timestamp: "2035-11-20T10:33:00Z", stage: 'EVALUATION', title: "Scientific Evaluation", description: "Metrics applied and constraints checked.", relatedEntityIds: ["ALT-A", "ALT-B", "ALT-C", "ALT-D"] },
    { id: "TL-6", timestamp: "2035-11-20T10:34:00Z", stage: 'RANKING', title: "Ranking Completed", description: "Dominant alternatives identified.", relatedEntityIds: [] },
    { id: "TL-7", timestamp: "2035-11-20T10:36:00Z", stage: 'SELECTION', title: "Alternative B Selected", description: "Highest utility within feasible risk boundaries.", relatedEntityIds: ["ALT-B"] },
    { id: "TL-8", timestamp: "2035-11-20T10:37:00Z", stage: 'PRESCRIPTION', title: "Prescription Created", description: "Execution graph formulated.", relatedEntityIds: ["ALT-B"] },
    { id: "TL-9", timestamp: "2035-11-20T10:38:00Z", stage: 'FREEZE', title: "Decision Frozen", description: "State captured immutably.", relatedEntityIds: [] },
    { id: "TL-10", timestamp: "2035-11-20T10:39:00Z", stage: 'AUTHORITY', title: "Human Authority Required", description: "Awaiting final sign-off.", relatedEntityIds: [] },
  ] as TimelineEvent[],

  edges: [
    { source: "EV-01", target: "ALT-B", type: "SUPPORTS", weight: 0.9 },
    { source: "EV-02", target: "ALT-C", type: "SUPPORTS", weight: 0.6 },
    { source: "EV-03", target: "CN-01", type: "CONSTRAINS", weight: 1.0 },
    { source: "CN-01", target: "ALT-A", type: "CONSTRAINS", weight: 1.0 }, // ALT-A violates
    { source: "ALT-B", target: "DEC-001", type: "RESULTS_IN", weight: 1.0 },
  ] as GraphEdge[]
};
