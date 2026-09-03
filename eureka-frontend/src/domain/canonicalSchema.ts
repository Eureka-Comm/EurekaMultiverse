import { z } from 'zod';

export const StateConditionSchema = z.object({
  status: z.string(),
  reason_code: z.string(),
  message: z.string(),
  target: z.string().nullable().optional(),
});

export const VisualizationBindingSchema = z.object({
  id: z.string(),
  status: z.string(),
  data_source: z.string().nullable().optional(),
  dimensions: z.array(z.string()),
  interactions: z.array(z.string()),
  reason: z.string().nullable().optional(),
  selection_bindings: z.array(z.string()),
});

export const ExecutionStepSchema = z.object({
  step_id: z.string(),
  capability_id: z.string(),
  target: z.string(),
  canonical_em: z.string().nullable().optional(),
  inputs: z.record(z.string(), z.any()),
  outputs: z.record(z.string(), z.any()),
  status: z.string(),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  revision: z.number(),
  provenance: z.array(z.string()),
});

export const ExecutionPlanSchema = z.object({
  steps: z.array(ExecutionStepSchema),
});

export const EMStatusSchema = z.object({
  canonical_em: z.string(),
  status: z.string(),
  step_ids: z.array(z.string()),
});

export const WorkResultSchema = z.object({
  result_id: z.string(),
  work_id: z.string(),
  summary: z.string().nullable().optional(),
  findings: z.array(z.string()),
  calculations: z.record(z.string(), z.any()),
  recommendations: z.array(z.string()),
  alternatives: z.array(z.string()),
  scores: z.record(z.string(), z.any()),
  evidence_ids: z.array(z.string()),
  provenance: z.array(z.string()),
  confidence: z.number().nullable().optional(),
  status: z.string(),
  limitations: z.array(z.string()),
  gaps: z.array(z.string()),
});

export const ACFLStateSchema = z.object({
  weights: z.record(z.string(), z.number()),
  criteria: z.array(z.string()),
  alternatives: z.array(z.string()),
  normalized_scores: z.record(z.string(), z.any()),
  frontier: z.array(z.string()),
  sensitivity: z.record(z.string(), z.any()),
});

export const WorkInfoSchema = z.object({
  workId: z.string(),
  taskCategory: z.string().nullable().optional(),
  status: z.string(),
  userIntent: z.string(),
  // L-1: preserve the provenance log from the backend projection.
  provenance_log: z.array(z.any()).optional().default([]),
});

export const StateDataSchema = z.object({
  acfl: ACFLStateSchema,
  feasible_only: z.boolean(),
  result: WorkResultSchema.nullable().optional(),
});

export const EvidenceSchema = z.object({
  evidence_id: z.string(),
  filename: z.string(),
  media_type: z.string(),
  extension: z.string().optional().default(""),
  size: z.number(),
  sha256: z.string().optional().default(""),
  source: z.string(),
  ingestion_status: z.string(),
  extraction_status: z.string().optional().default("NOT_STARTED"),
  parser_id: z.string().nullable().optional(),
  parser_version: z.string().nullable().optional(),
  content_reference: z.string().nullable().optional(),
  created_at: z.string().optional().default(""),
  provenance: z.array(z.string()).optional().default([]),
  extraction_error: z.string().nullable().optional(),
  extraction_reason_code: z.string().nullable().optional(),
});

export const ExtractedEvidenceSchema = z.object({
  extracted_evidence_id: z.string(),
  evidence_id: z.string(),
  content_type: z.string(),
  text_blocks: z.array(z.any()).optional().default([]),
  tables: z.array(z.any()).optional().default([]),
  structured_data: z.record(z.string(), z.any()).nullable().optional(),
  pages: z.array(z.any()).optional().default([]),
  slides: z.array(z.any()).optional().default([]),
  sheets: z.array(z.any()).optional().default([]),
  source_locations: z.array(z.string()).optional().default([]),
  extraction_method: z.string(),
  parser_id: z.string(),
  parser_version: z.string(),
  extraction_timestamp: z.string(),
  warnings: z.array(z.string()).optional().default([]),
});

export const ExecutionEventSchema = z.object({
  timestamp: z.string(),
  step_id: z.string(),
  canonical_em: z.string(),
  capability_id: z.string(),
  event: z.string(),
  status: z.string(),
  message: z.string().nullable().optional(),
  provenance: z.array(z.string()),
});

export const CanonicalWorkStateSchema = z.object({
  schema_version: z.literal("EUREKA_CANONICAL_WORK_STATE_V2"),
  work: WorkInfoSchema,
  execution_plan: ExecutionPlanSchema,
  em_pipeline: z.array(EMStatusSchema).optional().default([]),
  state: StateDataSchema,
  evidence: z.array(EvidenceSchema).optional().default([]),
  extracted_evidence: z.record(z.string(), ExtractedEvidenceSchema).optional().default({}),
  visualizations: z.array(VisualizationBindingSchema),
  available_capabilities: z.array(z.string()),
  gaps: z.array(z.string()),
  conditions: z.array(StateConditionSchema),
  tool_call_id: z.string().nullable().optional(),
  revision: z.number(),
  extracted_entities: z.record(z.string(), z.any()),

  active_em: z.string().nullable().optional(),
  active_step_id: z.string().nullable().optional(),
  active_capability: z.string().nullable().optional(),
  execution_progress: z.number().optional().default(0.0),
  execution_events: z.array(ExecutionEventSchema).optional().default([]),
  decision_points: z.array(z.any()).optional().default([]),
  human_requests: z.array(z.any()).optional().default([]),
  publication_state: z.any().optional().nullable(),

  // =========================================================
  // EUREKA Cognitive Console (narrative) projections.
  // These are REAL backend fields emitted by server._process_state from the
  // CanonicalWorkState. They must be RETAINED (not stripped) so the narrative
  // layer can read the full reasoning chain. They are optional/tolerant so the
  // contract never hard-fails on a missing or partially-built field.
  // =========================================================
  problem: z.any().optional().nullable(),
  historical_context: z.any().optional().nullable(),
  knowledge: z.any().optional(),
  predictive_knowledge: z.any().optional(),
  prescriptive_knowledge: z.any().optional(),
  action_plan: z.any().optional().nullable(),
  execution_state: z.any().optional().nullable(),
  frozen_result: z.any().optional().nullable(),
  human_decision: z.any().optional().nullable(),
  // LS90 — the governed "what remains open" projection (open_research). Must be
  // RETAINED (not stripped) so the CognitiveProjectionDTO can read the leading
  // edge of an OPEN cognitive operation. Tolerant/optional so the contract never
  // hard-fails on its absence.
  open_research: z.any().optional().nullable(),
  human_contributions: z.array(z.any()).optional().default([]),
  scientific_metrics: z.record(z.string(), z.any()).optional(),
  evaluated_scores: z.record(z.string(), z.any()).optional(),
  rankings: z.record(z.string(), z.any()).optional(),
  information_request: z.any().optional().nullable(),
  execution_phase: z.string().nullable().optional(),
  waiting_reason: z.string().nullable().optional(),
  waiting_for_evidence_ids: z.array(z.string()).optional().default([]),
  resolved_pipeline: z.array(z.string()).optional().default([]),
  problem_state: z.string().nullable().optional(),
  knowledge_state: z.string().nullable().optional(),
  decision_state: z.string().nullable().optional(),
  narrative_state: z.string().nullable().optional(),

  // If `resolved_pipeline` is present but `execution_plan` is missing, it will fail because execution_plan is required.
});

export type CanonicalWorkState = z.infer<typeof CanonicalWorkStateSchema>;
export type Evidence = z.infer<typeof EvidenceSchema>;
export type ExtractedEvidence = z.infer<typeof ExtractedEvidenceSchema>;
export type VisualizationBinding = z.infer<typeof VisualizationBindingSchema>;
export type StateCondition = z.infer<typeof StateConditionSchema>;
export type ExecutionStep = z.infer<typeof ExecutionStepSchema>;
export type ExecutionEvent = z.infer<typeof ExecutionEventSchema>;
export type EMStatus = z.infer<typeof EMStatusSchema>;
