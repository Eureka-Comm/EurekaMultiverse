export type AuthorityType = "NONE" | "HUMAN_EXTERNAL" | "LLM_INTERNAL" | "DOCUMENTED_RULE" | "EUREKA_CORE";
export type DecisionStage = "DRAFT" | "ANALYZING" | "RANKED" | "AWAITING_SELECTION" | "PRESCRIBED" | "FROZEN" | "AUTHORIZED" | "EXECUTED" | "BLOCKED";

export interface AgentOutputViewModel {
  id: string;
  provider: string; // e.g. "DeepSeek", "Mock"
  runtime: "LOCAL" | "API";
  trust: "UNTRUSTED" | "VERIFIED";
  authority: AuthorityType;
  content: string;
  proposedInterpretation?: string;
  questions?: string[];
  timestamp: string;
}

export interface VariableViewModel {
  id: string;
  name: string;
  type: string;
  value?: any;
}

export interface PredicateViewModel {
  id: string;
  expression: string;
  variables: VariableViewModel[];
  sourceAuthority: string;
  provenance: string;
  semanticAuthorityStatus: "VALIDATED" | "PENDING" | "REJECTED";
}

export interface AlternativeViewModel {
  id: string;
  name: string;
  description: string;
  data: Record<string, any>;
}

export interface EvaluationViewModel {
  alternativeId: string;
  truthValue: number; // 0 to 1
  utility: number;
  evidence: string[];
}

export interface RankingViewModel {
  id: string;
  predicateId: string;
  sortedEvaluations: EvaluationViewModel[];
  generatedAt: string;
}

export interface AuthorityViewModel {
  type: AuthorityType;
  status: "AUTHORIZED" | "NOT_AUTHORIZED" | "PENDING";
  provenance: string;
  timestamp?: string;
  actor?: string;
}

export interface PrescriptionViewModel {
  id: string;
  decisionId: string;
  proposedAction: string;
  target: string;
  expectedEffect: string;
  authorityStatus: AuthorityViewModel;
}

export interface FrozenArtifactViewModel {
  id: string;
  prescriptionId: string;
  snapshot: any;
  frozenAt: string;
  status: "FROZEN" | "UNFROZEN";
  waitingFor: AuthorityType;
}

export interface ExecutionAuthorityViewModel {
  status: "AUTHORIZED" | "BLOCKED";
  gateReason: string;
  authorizedBy?: string;
  authorizedAt?: string;
}

export interface TimelineEventViewModel {
  id: string;
  timestamp: string;
  stage: string;
  actor: string;
  description: string;
  state: "SUCCESS" | "WARNING" | "DANGER" | "INFO";
}

export interface DecisionViewModel {
  id: string;
  title: string;
  status: DecisionStage;
  createdAt: string;
  updatedAt: string;
  agentOutputs: AgentOutputViewModel[];
  objective?: PredicateViewModel;
  alternatives: AlternativeViewModel[];
  ranking?: RankingViewModel;
  prescription?: PrescriptionViewModel;
  frozenArtifact?: FrozenArtifactViewModel;
  executionAuthority?: ExecutionAuthorityViewModel;
  timeline: TimelineEventViewModel[];
}
