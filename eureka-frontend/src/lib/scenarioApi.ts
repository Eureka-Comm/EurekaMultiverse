// Scenario WHAT-IF API client. Thin, contract-accurate.
// This client ONLY represents the backend's already-verified domain contract. It never computes
// gclv/m, never implements authority/governance, never promotes/executes. The UI is a window into
// the domain authority, not a new authority.

import { getApiBase } from './apiBase';

const BASE = `${getApiBase()}/api/scenario`;
// Work observability + cognitive trace live under the Work authority, NOT the Scenario API.
// CONSTELACIÓN must read the real canonical work through this dedicated read-only base.
const WORK_BASE = `${getApiBase()}/api/work`;

export interface JsonDict { [k: string]: unknown; }

export interface ProjectedArtifact {
  artifact_id: string;
  artifact_kind: string;
  source_state_identity: string;
  scope: string;
  authority: string;
  canonical_status: string;
  provenance: string[];
  payload: JsonDict;
}

export interface WhatIfResponse {
  scenario_id: string;
  source_state_identity: string;
  scope: string;
  authority: string;
  canonical_status: string;
  status: string;
  provenance: string[];
  assumptions: JsonDict[];
  governance: JsonDict;
  projected_artifacts: ProjectedArtifact[];
}

export interface ScenarioSummary {
  scenario_id: string;
  source_state_identity: string;
  scope: string;
  status: string;
  assumptions: JsonDict[];
  provenance: string[];
  governance: JsonDict;
}

export interface CompareResponse {
  comparison_id: string;
  scenario_ids: string[];
  source_state_identity: string;
  scope: string;
  authority: string;
  canonical_status: string;
  scenarios: {
    scenario_id: string;
    metrics: JsonDict;
    assumptions: JsonDict[];
    authority: string;
    scope: string;
    canonical_status: string;
    provenance: string[];
  }[];
  metric_comparisons: { metric: string; scenario_id: string; value?: number; baseline_value?: number; absolute_delta?: number; relative_delta?: number }[];
  provenance: string[];
}

export interface DecisionInput {
  // the HUMAN's own inputs only. authority/scope/canonical_status are SERVER-derived.
  decision_type: 'CONFIRM' | 'REJECT' | 'ESCALATE';
  rationale: string;
  human_actor: string;
  selected_artifact_id?: string | null;
}

export interface DecisionResponse {
  decision_id: string;
  scenario_id: string;
  lifecycle_state: string;
  decision_type: string;
  selected_artifact_id?: string | null;
  rationale: string;
  human_actor: string;
  scope: string;
  authority: string;
  canonical_status: string;
  source_state_identity: string;
  provenance: string[];
  created_at: string;
  status: string;
}

export interface ExecutionResponse {
  execution_id: string;
  scenario_id: string;
  decision_id: string;
  action_id: string;
  source_state_identity: string;
  status: 'SUCCEEDED' | 'REJECTED' | 'FAILED';
  scope: string;
  authority: string;
  canonical_status: string;
  governance: { mode?: string; effect_class?: string; decision?: string; reason_code?: string; message?: string };
  effect: { artifact_id?: string; artifact_kind?: string; artifact_path?: string; bytes?: number; exists?: boolean };
  provenance: string[];
  created_at: string;
}

async function req<T>(method: string, path: string, body?: unknown, base: string = BASE): Promise<T> {
  const res = await fetch(`${base}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const j = await res.json();
      detail = typeof j?.detail === 'string' ? j.detail : JSON.stringify(j?.detail ?? '');
    } catch { /* ignore */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export function runWhatIf(scenarioId: string, delta: number, workId?: string, work?: JsonDict): Promise<WhatIfResponse> {
  return req<WhatIfResponse>('POST', '/whatif', {
    scenario_id: scenarioId,
    assumptions: [{ delta }],
    // When a real work_id is available, the backend resolves the REAL canonical work server-side.
    // The client never supplies authoritative canonical state.
    ...(workId ? { work_id: workId } : { work: work ?? { work_id: 'W1', title: 'what-if', user_intent: 'what-if', task_category: 'WHATIF', problem_statement: '', acfl_weights: { cost: 50, risk: 50 } } }),
  });
}

export function getScenario(scenarioId: string): Promise<ScenarioSummary> {
  return req<ScenarioSummary>('GET', `/${scenarioId}`);
}

export function getResult(scenarioId: string): Promise<WhatIfResponse> {
  return req<WhatIfResponse>('GET', `/${scenarioId}/result`);
}

export function compareScenario(scenarioIds: string[], baseline?: string): Promise<CompareResponse> {
  return req<CompareResponse>('POST', '/compare', { scenario_ids: scenarioIds, baseline_scenario_id: baseline ?? null });
}

// ---- governed HUMAN decision (record-only; never promotes/executes/canonicalizes) ------------ //
export function authorizeScenario(scenarioId: string, workId: string, decision: DecisionInput): Promise<DecisionResponse> {
  return req<DecisionResponse>('POST', `/${scenarioId}/authorize`, { work_id: workId, ...decision });
}

export function discardScenario(scenarioId: string, workId: string, decision: DecisionInput): Promise<DecisionResponse> {
  return req<DecisionResponse>('POST', `/${scenarioId}/discard`, { work_id: workId, ...decision });
}

export function getDecision(scenarioId: string): Promise<DecisionResponse> {
  return req<DecisionResponse>('GET', `/${scenarioId}/decision`);
}

export function listDecisions(): Promise<DecisionResponse[]> {
  return req<DecisionResponse[]>('GET', '/decisions');
}

export function executeScenario(scenarioId: string, workId: string): Promise<ExecutionResponse> {
  return req<ExecutionResponse>('POST', `/${scenarioId}/execute`, { work_id: workId });
}

export function getExecution(scenarioId: string): Promise<ExecutionResponse> {
  return req<ExecutionResponse>('GET', `/${scenarioId}/execution`);
}

export function listExecutions(): Promise<ExecutionResponse[]> {
  return req<ExecutionResponse[]>('GET', '/executions');
}

export interface AuditStage {
  stage: string;
  status: 'RECORDED' | 'DERIVED' | 'NOT_RECORDED';
  entity_id: string;
  authority: string;
  canonical_status: string;
  scope: string;
  timestamp?: string | null;
  provenance: string[];
  details: JsonDict;
}

export interface WorkAuditView {
  work_id: string;
  source_state_identity: string;
  revision?: number | null;
  status?: string | null;
  linked_to_scenario: boolean;
  provenance: string[];
}

export interface AuditResponse {
  scenario_id: string;
  source_state_identity: string;
  work: WorkAuditView | null;
  stages: AuditStage[];
  projected_artifacts: ProjectedArtifact[];
  decision: DecisionResponse | null;
  execution: ExecutionResponse | null;
  provenance: string[];
}

export function getAudit(scenarioId: string, workId?: string): Promise<AuditResponse> {
  const qs = workId ? `?work_id=${encodeURIComponent(workId)}` : '';
  return req<AuditResponse>('GET', `/${scenarioId}/audit${qs}`);
}

export interface WorkAuditStage {
  stage: string;
  status: 'RECORDED' | 'DERIVED' | 'NOT_RECORDED';
  authority: string;
  details: JsonDict;
  provenance: string[];
}

export interface WorkConsumptionVerification {
  integrity?: string;
  schema_valid?: boolean;
  signature_match?: boolean;
  currentness?: string;
  revision?: number | null;
}

export interface EmPipelineEntry { canonical_em: string; status: string; step_ids?: string[]; }
export interface CognitiveTraceEntry {
  em: string; capability_id: string; model: string; status: string;
  latency_ms?: number; output_schema?: string; call_id?: string; model_version?: string;
}

export interface WorkAuditResponse {
  work_id: string;
  canonical_state_identity: string;
  revision?: number | null;
  status?: string | null;
  stages: WorkAuditStage[];
  execution: JsonDict | null;
  result: JsonDict | null;
  publication: JsonDict | null;
  consumption: { verification: WorkConsumptionVerification; candidate_artifacts: string[] } | null;
  contractual_pipeline: string[];
  em_pipeline: EmPipelineEntry[];
  cognitive_trace: CognitiveTraceEntry[];
  provenance: string[];
}

export function getWorkAudit(workId: string): Promise<WorkAuditResponse> {
  return req<WorkAuditResponse>('GET', `/${encodeURIComponent(workId)}/audit`, undefined, WORK_BASE);
}

export interface WorkPublicationResponse {
  work_id: string;
  publication: JsonDict | null;
  verification: WorkConsumptionVerification;
  candidate_artifacts: string[];
}

export function getWorkPublication(workId: string): Promise<WorkPublicationResponse> {
  return req<WorkPublicationResponse>('GET', `/${encodeURIComponent(workId)}/publication`, undefined, WORK_BASE);
}
