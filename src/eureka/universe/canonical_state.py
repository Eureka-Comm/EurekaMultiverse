from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from .work_model import EurekaWork
from .problem_model import ProblemModel
from .agent_definition import AgentDefinition
import uuid
import datetime

class StateCondition(BaseModel):
    status: str # "GAP", "ERROR", "BLOCKED", "PARTIAL"
    reason_code: str # "CAPABILITY_UNAVAILABLE", "EVIDENCE_MISSING", "SEMANTIC_UNRESOLVED", "EXECUTION_UNAVAILABLE", "GOVERNANCE_RESTRICTION", "SYSTEM_ERROR"
    message: str
    target: Optional[str] = None

class VisualizationBinding(BaseModel):
    id: str
    status: str = "AVAILABLE"  # AVAILABLE or GAP
    data_source: Optional[str] = None
    dimensions: List[str] = Field(default_factory=list)
    interactions: List[str] = Field(default_factory=list)
    reason: Optional[str] = None
    selection_bindings: List[str] = Field(default_factory=list)

class ExecutionStep(BaseModel):
    step_id: str
    capability_id: str
    target: str # e.g. "EM[RANKING]" or "SUBSYSTEM[StoryEngine]"
    canonical_em: Optional[str] = None # The explicitly resolved 8-EM target
    required_inputs: List[str] = Field(default_factory=list)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    status: str = "READY" # READY, RUNNING, COMPLETED, PARTIAL, GAP, BLOCKED, FAILED, WAITING_FOR_EVIDENCE, WAITING_FOR_HUMAN_INPUT
    waiting_reason: str = ""
    
    # Task Network Extensions (Structurer Contract)
    dependencies: List[str] = Field(default_factory=list) # List of step_ids
    expected_outputs: List[str] = Field(default_factory=list)
    execution_level: str = "COGNITIVE" # COGNITIVE, SYSTEM, HUMAN
    return_to_core: bool = True
    
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    revision: int = 1
    provenance: List[str] = Field(default_factory=list)
    produces_result: bool = False

class EMStatus(BaseModel):
    canonical_em: str
    status: str = "NOT_REQUIRED" # NOT_REQUIRED, READY, RUNNING, COMPLETED, PARTIAL, GAP, BLOCKED, FAILED
    step_ids: List[str] = Field(default_factory=list)

class ExecutionPlan(BaseModel):
    steps: List[ExecutionStep] = Field(default_factory=list)


class HumanInteractionRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: "REQ-" + str(uuid.uuid4())[:6])
    type: str
    question: str
    reason: str
    required_information: List[str] = Field(default_factory=list)
    current_context: str = ""
    available_options: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    evidence_required: bool = False
    decision_required: bool = False
    blocking: bool = True
    created_at: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    status: str = "PENDING"
    response_data: Optional[Dict[str, Any]] = None

class HumanDecisionPoint(BaseModel):
    decision_id: str = Field(default_factory=lambda: "DEC-" + str(uuid.uuid4())[:6])
    originating_em: str = ""
    problem_id: str = ""
    task_id: str = ""
    question: str
    context: str = ""
    options: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_option: Optional[str] = None
    recommendation_reason: Optional[str] = None
    uncertainty: str = ""
    required_parameters: List[str] = Field(default_factory=list)
    human_authority: bool = True
    status: str = "PENDING"
    human_selection: Optional[str] = None

class HumanKnowledgeContribution(BaseModel):
    contribution_id: str = Field(default_factory=lambda: "HKC-" + str(uuid.uuid4())[:6])
    type: str
    value: Any
    affected_component: str
    affected_variable: Optional[str] = None
    affected_decision: Optional[str] = None
    rationale: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())

class WorkResult(BaseModel):
    result_id: str
    work_id: str
    summary: Optional[str] = None
    findings: List[str] = Field(default_factory=list)
    calculations: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    scores: Dict[str, Any] = Field(default_factory=dict)
    evidence_ids: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    status: str = "UNAVAILABLE" # AVAILABLE, UNAVAILABLE
    limitations: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)

class ACFLState(BaseModel):
    weights: Dict[str, float] = Field(default_factory=lambda: {"cost": 50.0, "risk": 50.0})
    criteria: List[str] = Field(default_factory=list)
    alternatives: List[str] = Field(default_factory=list)
    normalized_scores: Dict[str, Any] = Field(default_factory=dict)
    frontier: List[str] = Field(default_factory=list)
    sensitivity: Dict[str, Any] = Field(default_factory=dict)

class Evidence(BaseModel):
    evidence_id: str
    filename: str
    media_type: str
    extension: str = ""
    size: int
    sha256: str = ""
    source: str
    ingestion_status: str # UPLOADING, INGESTED, REJECTED, FAILED
    extraction_status: str = "NOT_STARTED" # NOT_STARTED, PARSING, EXTRACTED, PARTIAL, GAP, FAILED
    parser_id: Optional[str] = None
    parser_version: Optional[str] = None
    content_reference: Optional[str] = None
    created_at: str = ""
    provenance: List[str] = Field(default_factory=list)
    extraction_error: Optional[str] = None
    extraction_reason_code: Optional[str] = None

class ExtractedEvidence(BaseModel):
    extracted_evidence_id: str
    evidence_id: str
    content_type: str
    text_blocks: List[Any] = Field(default_factory=list)
    tables: List[Any] = Field(default_factory=list)
    structured_data: Optional[Dict[str, Any]] = None
    pages: List[Any] = Field(default_factory=list)
    slides: List[Any] = Field(default_factory=list)
    sheets: List[Any] = Field(default_factory=list)
    source_locations: List[str] = Field(default_factory=list)
    extraction_method: str
    parser_id: str
    parser_version: str
    extraction_timestamp: str
    warnings: List[str] = Field(default_factory=list)

class StructuredFinding(BaseModel):
    finding_id: str
    statement: str
    finding_type: str = "DESCRIPTIVE" # DESCRIPTIVE, RELATIONAL
    evidence_refs: List[str] = Field(default_factory=list) # List of extracted_evidence_id
    method: Optional[str] = None
    status: str = "VALIDATED" # VALIDATED, UNSUPPORTED, CONTRADICTION, REJECTED
    provenance: List[str] = Field(default_factory=list)
    # Gap 4 — Descriptor contract (additive & truthful).
    uncertainty: Optional[str] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    patterns: List[str] = Field(default_factory=list)
    
class KnowledgeStateModel(BaseModel):
    findings: List[StructuredFinding] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    contradictions: List[str] = Field(default_factory=list)
    version: int = 1
    # Gap 4 — Descriptor contract (additive & truthful). Derived from real data when possible.
    predicates: List[Dict[str, Any]] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    uncertainty: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    dependencies_for_predictor: List[str] = Field(default_factory=list)

from .math_ir import AnyMathematicalExpression

class PredictivePredicate(BaseModel):
    predicate_id: str
    condition_variables: List[str] = Field(default_factory=list)
    target: str
    logical_structure: AnyMathematicalExpression # ACFL AST or MathematicalFormulaIR representation
    mse: Optional[float] = None
    status: str = "VALIDATED" # VALIDATED, REJECTED
    provenance: List[str] = Field(default_factory=list)

class PredictionScenario(BaseModel):
    scenario_id: str
    name: str
    assumptions: List[str] = Field(default_factory=list)
    perturbed_variables: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[str] = Field(default_factory=list)

class PredictiveUncertainty(BaseModel):
    status: str = "NOT_AVAILABLE" # QUANTIFIED, NOT_AVAILABLE, INVALID
    confidence_interval: Optional[Dict[str, float]] = None
    variance: Optional[float] = None
    limitations: List[str] = Field(default_factory=list)
    invalidation_conditions: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)

class PredictionKnowledge(BaseModel):
    prediction_id: str
    target_variable: str
    predictor_variables: List[str] = Field(default_factory=list)
    input_requirements: Dict[str, str] = Field(default_factory=dict)
    units: Optional[str] = None
    data_period: Optional[str] = None
    sample_size: Optional[int] = None
    model_type: str = "FORMULA"
    model_definition: str = ""
    model_parameters: Dict[str, float] = Field(default_factory=dict)
    formula: str = ""
    baseline: Optional[float] = None
    predicted_value: Optional[float] = None
    uncertainty: PredictiveUncertainty = Field(default_factory=PredictiveUncertainty)
    confidence_or_interval: Optional[str] = None
    assumptions: List[str] = Field(default_factory=list)
    validity_conditions: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    computation_trace: List[str] = Field(default_factory=list)
    validation_status: str = "NOT_EVALUATED"
    reproducibility: bool = False
    provenance: List[str] = Field(default_factory=list)

class PredictiveKnowledgeState(BaseModel):
    predictions: List[PredictionKnowledge] = Field(default_factory=list)
    predicates: List[PredictivePredicate] = Field(default_factory=list)
    status: str = "UNAVAILABLE" # UNAVAILABLE, IN_PROGRESS, FROZEN
    version: int = 1

class ExecutionEvent(BaseModel):
    timestamp: str
    step_id: str
    canonical_em: str
    capability_id: str
    event: str
    status: str
    message: Optional[str] = None
    provenance: List[str] = Field(default_factory=list)

from .prescription_model import ValidatedPrescription, PrescriptiveKnowledgeState
from .action_model import ValidatedActionPlan
from .installation_model import ExecutionState
from .publication_model import PublicationState, FrozenResult
class ApplicabilityAssessment(BaseModel):
    assessment_status: str = "NOT_EVALUATED" # APPLICABLE, PARTIALLY_APPLICABLE, NOT_APPLICABLE, INSUFFICIENT_INFORMATION
    matched_conditions: List[str] = Field(default_factory=list)
    mismatched_conditions: List[str] = Field(default_factory=list)
    unknown_conditions: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    reason: Optional[str] = None
    human_review_required: bool = False
    required_human_input: List[Dict[str, Any]] = Field(default_factory=list)

class DeltaItem(BaseModel):
    delta_type: str # VARIABLE_CHANGED, VALUE_CHANGED, DISTRIBUTION_CHANGED, CONSTRAINT_CHANGED, ASSUMPTION_CHANGED, OBJECTIVE_CHANGED, BUDGET_CHANGED, SEGMENT_CHANGED, EVIDENCE_CHANGED, VALIDITY_CONDITION_CHANGED, UNKNOWN
    historical_reference: str
    current_reference: str
    historical_value: Optional[str] = None
    current_value: Optional[str] = None
    evidence_ref: Optional[str] = None
    materiality: str = "UNKNOWN" # NO_MATERIAL_DELTA, MINOR_DELTA, MATERIAL_DELTA, CRITICAL_DELTA, UNKNOWN
    explanation: str

class DeltaAssessment(BaseModel):
    status: str = "NOT_EVALUATED"
    frozen_solution_id: str
    frozen_version: str
    current_problem_id: str
    items: List[DeltaItem] = Field(default_factory=list)
    confidence: Optional[float] = None

class MathematicalRevalidationResult(BaseModel):
    prediction_id: str
    target: str
    status: str = "NOT_REVALIDATABLE" # VALID, INVALIDATED, CHANGED, INSUFFICIENT_DATA, NOT_REVALIDATABLE
    required_data: List[str] = Field(default_factory=list)
    uncertainty: Optional[PredictiveUncertainty] = None

class MathematicalRevalidationAssessment(BaseModel):
    status: str = "NOT_EVALUATED"
    validated_predictions: List[MathematicalRevalidationResult] = Field(default_factory=list)
    invalidated_predictions: List[MathematicalRevalidationResult] = Field(default_factory=list)
    insufficient_data_predictions: List[MathematicalRevalidationResult] = Field(default_factory=list)
    required_data: List[str] = Field(default_factory=list)


class RequiredDataRequirement(BaseModel):
    variable: str
    reason_required: str
    source_expected: str
    impact_if_missing: str

class CognitiveReevaluationAssessment(BaseModel):
    status: str = "NOT_EVALUATED"
    knowledge_status: str = "REQUIRES_HUMAN_REVIEW"
    prediction_status: str = "REQUIRES_HUMAN_REVIEW"
    prescription_status: str = "REQUIRES_HUMAN_REVIEW"
    decision_status: str = "REQUIRES_HUMAN_REVIEW"
    rationale: str
    previous_prescription_id: Optional[str] = None
    previous_prediction_ids: List[str] = Field(default_factory=list)
    current_prediction_ids: List[str] = Field(default_factory=list)
    delta_ids: List[str] = Field(default_factory=list)
    revalidation_status: Optional[str] = None
    new_alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    uncertainty: List[Dict[str, Any]] = Field(default_factory=list)
    validity_conditions: List[str] = Field(default_factory=list)
    human_decision_required: bool = True
    required_data: List[RequiredDataRequirement] = Field(default_factory=list)
    invalidated_reason: Optional[str] = None
    invalidated_predictions: List[str] = Field(default_factory=list)
    dependent_prescriptions: List[str] = Field(default_factory=list)
class ReusableKnowledgeContext(BaseModel):
    frozen_solution_id: str
    version: str
    original_problem: Optional[Dict[str, Any]] = None
    historical_knowledge: List[Dict[str, Any]] = Field(default_factory=list)
    historical_predictions: List[Dict[str, Any]] = Field(default_factory=list)
    historical_prescriptions: List[Dict[str, Any]] = Field(default_factory=list)
    historical_action_plan: Optional[Dict[str, Any]] = None
    historical_decision: Optional[Dict[str, Any]] = None
    provenance: List[str] = Field(default_factory=list)
    applicability_status: str = "NOT_EVALUATED" # NOT_EVALUATED, APPLICABLE, PARTIALLY_APPLICABLE, NOT_APPLICABLE
    applicability_assessment: Optional[ApplicabilityAssessment] = None
    delta_assessment: Optional[DeltaAssessment] = None
    mathematical_revalidation: Optional[MathematicalRevalidationAssessment] = None
    cognitive_reevaluation: Optional[CognitiveReevaluationAssessment] = None


class HumanDecision(BaseModel):
    decision_id: str
    work_id: str
    decision_type: str
    selected_alternative_id: Optional[str] = None
    selected_prescription_id: Optional[str] = None
    parameters_modified: Dict[str, Any] = Field(default_factory=dict)
    human_knowledge: str = ""
    rationale: str = ""
    timestamp: str
    decision_authority: str = "HUMAN_OPERATOR"

class RuntimeCallMetadata(BaseModel):
    """EM ↔ Runtime governance header (per cognitive-engine invocation).

    Preserves, for every EM → engine call, the provenance/observability fields that
    the EM↔Agent contract v1.0 requires: which model/version served the call, the
    runtime/prompt version, the context it ran under, the inference parameters, the
    token usage and latency, the output schema, and the validation status. It is the
    audit trail that lets a consumer prove WHY an EM produced what it produced.
    """
    call_id: str
    em: str
    capability_id: str
    model: str = ""
    model_version: str = ""
    runtime_version: str = ""
    context_id: str = ""
    prompt_version: str = ""
    inference_parameters: Dict[str, Any] = Field(default_factory=dict)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    output_schema: str = ""
    validation_status: str = ""
    timestamp: str = ""
    status: str = "COMPLETED"


class CoreTask(BaseModel):
    task_id: str
    classification: str  # D, PRED, PRES, DEF, ACT, INS, PUB, ?
    owner: str
    capability: str
    dependencies: List[str] = Field(default_factory=list)

class CoreAnalysis(BaseModel):
    """EM Core `core_analysis` — a READ-ONLY projection of the existing orchestration.

    It catalogs the classification (derived from the real canonical_em), the routing
    (task -> owner/capability), the integration (final EM + result source) and the current
    status. It is a view of `execution_plan`/`em_pipeline`/`status` and NEVER drives
    execution (the runtime `advance` is the only execution path).
    """
    analysis_id: str
    problem_type: str = "UNKNOWN"
    tasks: List[CoreTask] = Field(default_factory=list)
    routing: List[str] = Field(default_factory=list)
    integration: Dict[str, Any] = Field(default_factory=dict)
    status: str = ""


# Stable classification derived from the REAL canonical_em (authority-approved: no intent_category).
_CORE_CLASS = {
    "EM Descriptor": "D",
    "EM Predictor": "PRED",
    "EM Prescriptor": "PRES",
    "EM Structurer": "DEF",
    "EM Actioner": "ACT",
    "EM Installer": "INS",
    "EM Publisher": "PUB",
}


def build_core_analysis(canonical: "CanonicalWorkState") -> Optional[CoreAnalysis]:
    """READ-ONLY projection of the orchestration into a `CoreAnalysis`.

    Never mutates the canonical state; only reads execution_plan/em_pipeline/status to
    catalog classification / routing / integration / status. No second router.
    """
    if not canonical or not canonical.execution_plan:
        return None
    steps = list(canonical.execution_plan.steps or [])
    tasks = []
    for s in steps:
        owner = getattr(s, "canonical_em", None) or "?"
        tasks.append(CoreTask(
            task_id=getattr(s, "step_id", ""),
            classification=_CORE_CLASS.get(owner, "?"),
            owner=owner,
            capability=getattr(s, "capability_id", ""),
            dependencies=list(getattr(s, "dependencies", None) or []),
        ))
    routing = [f"{getattr(s,'step_id','')} -> {getattr(s,'canonical_em',None) or '?'}" for s in steps]
    final_em = next((getattr(s, "canonical_em", None) for s in reversed(steps) if getattr(s, "canonical_em", None)), "EM Publisher")
    result_ok = bool(canonical.result) and getattr(canonical.result, "status", None) == "AVAILABLE"
    problem_type = "UNKNOWN"
    if canonical.problem:
        problem_type = getattr(canonical.problem, "domain_context", None) or "UNKNOWN"
    import uuid
    return CoreAnalysis(
        analysis_id=f"CORE-{uuid.uuid4().hex[:6].upper()}",
        problem_type=problem_type,
        tasks=tasks,
        routing=routing,
        integration={"final_em": final_em, "result_source": "state.result" if result_ok else "state.result (pending)"},
        status=getattr(canonical, "status", "") or "",
    )


class AgentDeployment(BaseModel):
    """EM Installer `agent_definition` + deployment/lifecycle (single EM, internal capabilities).

    Reuses the existing `AgentDefinition` (agent_definition.py). `lifecycle_state` follows
    PROPOSED -> DESIGNED -> VALIDATED -> FROZEN -> REGISTERED -> ACTIVE; ACTIVE is NEVER a
    consequence of producing an AgentDefinition (requires explicit registration/confirmation).
    """
    deployment_id: str
    agent_definition: AgentDefinition
    lifecycle_state: str = "PROPOSED"
    provenance: List[str] = Field(default_factory=list)
    deployment_state: str = ""


class CanonicalWorkState(BaseModel):
    """
    The Single Source of Truth for a running task.
    No surface (Analytics, Story, Inspector) can invent data.
    Everything is read from this state.
    """
    schema_version: str = "EUREKA_CANONICAL_WORK_STATE_V2"
    work: EurekaWork
    problem: Optional[ProblemModel] = None
    historical_context: Optional[ReusableKnowledgeContext] = None
    
    # Processed outcomes
    evidence_ids: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    extracted_evidence: Dict[str, ExtractedEvidence] = Field(default_factory=dict)
    extracted_entities: Dict[str, Any] = {}
    evaluated_scores: Dict[str, Any] = {}
    rankings: Dict[str, Any] = {}
    scientific_metrics: Dict[str, Any] = {}
    
    # Execution representation
    knowledge: KnowledgeStateModel = Field(default_factory=KnowledgeStateModel)
    predictive_knowledge: PredictiveKnowledgeState = Field(default_factory=PredictiveKnowledgeState)
    prescriptive_knowledge: PrescriptiveKnowledgeState = Field(default_factory=PrescriptiveKnowledgeState)
    action_plan: Optional[ValidatedActionPlan] = None
    execution_state: Optional[ExecutionState] = None
    publication_state: Optional[PublicationState] = None
    frozen_result: Optional[FrozenResult] = None
    execution_plan: ExecutionPlan = Field(default_factory=ExecutionPlan)
    em_pipeline: List[EMStatus] = Field(default_factory=list)
    acfl: ACFLState = Field(default_factory=ACFLState)
    result: Optional[WorkResult] = None
    
    # Execution Pointer
    active_em: Optional[str] = None
    active_step_id: Optional[str] = None
    active_capability: Optional[str] = None
    execution_phase: str = "INITIALIZING" # e.g. RUNNING, WAITING_FOR_EVIDENCE
    waiting_reason: Optional[str] = None
    waiting_for_evidence_ids: List[str] = Field(default_factory=list)
    execution_progress: float = 0.0
    execution_events: List[ExecutionEvent] = Field(default_factory=list)
    # EM ↔ Runtime governance: per-invocation cognitive-engine metadata (model/version/tokens/latency/schema).
    runtime_metadata: List[RuntimeCallMetadata] = Field(default_factory=list)
    # Loop 83: EM Core `core_analysis` — READ-ONLY projection of the orchestration.
    core_analysis: Optional[CoreAnalysis] = None
    # Loop 84: EM Installer `agent_definition` + deployment/lifecycle (single EM).
    agent_deployment: Optional[AgentDeployment] = None

    # Deprecated flat pipeline, kept for immediate backward compatibility but should use execution_plan
    resolved_pipeline: list[str] = []
    gaps: list[str] = []
    
    # Granular condition tracking (Errors, Warnings, Gaps, Blocks)
    conditions: List[StateCondition] = Field(default_factory=list)
    
    status: str = "OPEN" # OPEN, READY, RUNNING, COMPLETED, PARTIAL, GAP, BLOCKED, FAILED, WAITING_FOR_EVIDENCE, WAITING_FOR_HUMAN_INPUT
    waiting_reason: str = ""
    
    information_request: Optional[Dict[str, Any]] = None
    human_requests: List[HumanInteractionRequest] = Field(default_factory=list)
    decision_points: List[HumanDecisionPoint] = Field(default_factory=list)
    human_contributions: List[HumanKnowledgeContribution] = Field(default_factory=list)
    human_decision: Optional[HumanDecision] = None

    
    # State tracking
    revision: int = 1
    feasible_only: bool = False
    
    # =========================================================
    # CONCEPTUAL 5.1 STATE PROJECTIONS (Runtime Extensions)
    # =========================================================
    problem_state: str = "FORMULATING" # FORMULATING, STRUCTURED, WAITING, RESOLVED
    knowledge_state: str = "INCOMPLETE"
    decision_state: str = "PENDING"
    narrative_state: str = "INITIALIZING" # RUNTIME EXTENSION
    
    # UI projection hints governed by backend
    visualizations: List[VisualizationBinding] = Field(default_factory=list)

    def get_provenance_for(self, entity_id: str):
        for rec in self.work.provenance_log:
            if rec.source_id == entity_id:
                return rec
        return None


# ===========================================================================
# LS90 — OPEN RESEARCH COGNITIVE OPERATION (Decision Intelligence)
# ===========================================================================
# A read-only, Python-derived projection of "what remains open" — the leading
# edge of an OPEN cognitive operation (a research question that has NOT yet
# reached a decision). It aggregates the REAL canonical fields (unknowns,
# unanswered questions, uncertainty, limitations, contradictions, not-evaluated
# predictions, insufficient information, data-not-available, a pending human
# decision / pending human input) WITHOUT inventing a decision, a ranking, an
# optimizer, a utility, or a preference — and WITHOUT converting any LLM output
# into authority. It is the governed counterpart to build_core_analysis (LS83)
# and the story_arc (LS85): a derived VIEW, never an authority, never a re-router
# of execution, never a decision. Python computes it; the LLM never does.
#
# `operation_kind` is a truthful descriptor of the CURRENT completion state
# ("OPEN_RESEARCH" when no human decision has been reached, "DECISION" when one
# has). It does NOT classify intent, it does NOT re-route the pipeline, and it is
# NOT an authority judgement.

OPEN_ITEM_KINDS = frozenset({
    "UNRESOLVED_QUESTION",
    "INSUFFICIENT_INFORMATION",
    "INSUFFICIENT_DATA",
    "MISSING_EVIDENCE",
    "UNCERTAINTY",
    "LIMITATION",
    "CONTRADICTION",
    "PENDING_HUMAN_DECISION",
    "PENDING_HUMAN_INPUT",
    "NOT_EVALUATED",
    "DATA_NOT_AVAILABLE",
})


class OpenResearchItem(BaseModel):
    """A single honest "still open" item, provenance-tagged to its source field."""
    kind: str
    label: str
    source_ref: str       # e.g. "problem.unknowns[0]", "knowledge.uncertainty[0]", "human_decision"
    provenance: List[str] = Field(default_factory=list)


class OpenResearchState(BaseModel):
    """The governed leading edge of an OPEN cognitive operation (read-only view)."""
    status: str = "OPEN"                    # OPEN | OPEN_INSUFFICIENT_INFORMATION | CLOSED
    operation_kind: str = "OPEN_RESEARCH"   # OPEN_RESEARCH (no decision yet) | DECISION (decision made)
    is_open: bool = True                    # == NOT decision_reached
    decision_reached: bool = False
    decision_pending: bool = True
    items: List[OpenResearchItem] = Field(default_factory=list)
    decision_relevant_knowledge: List[str] = Field(default_factory=list)  # real artifact ids that inform a future decision
    summary: str = ""
    provenance: List[str] = Field(default_factory=list)
    built: str = ""


def build_open_research_state(canonical: Optional["CanonicalWorkState"]) -> Optional["OpenResearchState"]:
    """LS90 — deterministic, read-only projection of an OPEN cognitive operation.

    Aggregates the REAL canonical fields that describe "what remains open". Pure
    (no mutation, no LLM, no side effects) so it is safe to compute inside the
    read-only `_project_state` (F-1: GET /state is a pure read).
    """
    if canonical is None:
        return None
    import datetime as _dt
    now = _dt.datetime.now().isoformat()
    provenance = [
        "LS90 Python-derived open-research projection",
        "governed read-only view; no LLM output, no decision authority, no re-router of execution",
    ]
    items: List[OpenResearchItem] = []

    def add_item(kind: str, label: str, source_ref: str, src_prov: str = "") -> None:
        items.append(OpenResearchItem(
            kind=kind if kind in OPEN_ITEM_KINDS else "INSUFFICIENT_INFORMATION",
            label=label,
            source_ref=source_ref,
            provenance=[src_prov] if src_prov else [],
        ))

    # --- Decision reached? (the single OPEN/CLOSED signal) ---
    hd = getattr(canonical, "human_decision", None)
    decision_reached = bool(hd and getattr(hd, "selected_alternative_id", None))

    # --- Unresolved / unknown questions (problem + knowledge) ---
    prob = getattr(canonical, "problem", None)
    if prob is not None:
        for i, u in enumerate(getattr(prob, "unknowns", None) or []):
            if u:
                add_item("UNRESOLVED_QUESTION", str(u), f"problem.unknowns[{i}]", "problem.unknowns")
        for i, q in enumerate(getattr(prob, "questions", None) or []):
            if q:
                add_item("UNRESOLVED_QUESTION", str(q), f"problem.questions[{i}]", "problem.questions")
    knowledge = getattr(canonical, "knowledge", None)
    if knowledge is not None:
        for i, u in enumerate(getattr(knowledge, "unknowns", None) or []):
            if u:
                add_item("UNRESOLVED_QUESTION", str(u), f"knowledge.unknowns[{i}]", "knowledge.unknowns")
        for i, u in enumerate(getattr(knowledge, "uncertainty", None) or []):
            if u:
                add_item("UNCERTAINTY", str(u), f"knowledge.uncertainty[{i}]", "knowledge.uncertainty")
        for i, l in enumerate(getattr(knowledge, "limitations", None) or []):
            if l:
                add_item("LIMITATION", str(l), f"knowledge.limitations[{i}]", "knowledge.limitations")
        for i, c in enumerate(getattr(knowledge, "contradictions", None) or []):
            if c:
                add_item("CONTRADICTION", str(c), f"knowledge.contradictions[{i}]", "knowledge.contradictions")

    # --- Knowledge completeness (canonical-level, not per-finding) ---
    if getattr(canonical, "knowledge_state", None) == "INCOMPLETE" and not decision_reached:
        add_item("INSUFFICIENT_INFORMATION", "Knowledge state is INCOMPLETE — not enough to conclude.", "knowledge_state")

    # --- Predictive knowledge status / not-evaluated predictions ---
    pk = getattr(canonical, "predictive_knowledge", None)
    if pk is not None:
        if getattr(pk, "status", None) == "UNAVAILABLE":
            add_item("DATA_NOT_AVAILABLE", "No predictive knowledge was produced.", "predictive_knowledge.status")
        for i, p in enumerate(getattr(pk, "predictions", None) or []):
            pid = getattr(p, "prediction_id", None) or f"[{i}]"
            if getattr(p, "mse", None) is None and getattr(p, "predicted_value", None) is None:
                add_item("NOT_EVALUATED", f"Prediction {pid} was NOT_EVALUATED (no numeric value).",
                         f"predictive_knowledge.predictions[{i}]", "predictive_knowledge.predictions[].validation_status")
            elif getattr(p, "validation_status", None) == "NOT_EVALUATED":
                add_item("NOT_EVALUATED", f"Prediction {pid} was NOT_EVALUATED.", f"predictive_knowledge.predictions[{i}]")
            unc = getattr(p, "uncertainty", None)
            if unc is not None and getattr(unc, "status", None) == "NOT_AVAILABLE":
                add_item("INSUFFICIENT_INFORMATION", f"Uncertainty for prediction {pid} is NOT_AVAILABLE.",
                         f"predictive_knowledge.predictions[{i}].uncertainty", "predictive_knowledge.predictions[].uncertainty")

    # --- Missing / waiting evidence ---
    if getattr(canonical, "execution_phase", None) == "WAITING_FOR_EVIDENCE" \
            or any(getattr(s, "status", None) == "WAITING_FOR_EVIDENCE" for s in getattr(canonical, "execution_plan", None).steps):
        add_item("MISSING_EVIDENCE", "The pipeline is waiting for evidence ingestion/extraction.", "execution_phase")
    if getattr(canonical, "waiting_for_evidence_ids", None):
        add_item("MISSING_EVIDENCE", "Evidence required: " + ", ".join(getattr(canonical, "waiting_for_evidence_ids", [])),
                 "waiting_for_evidence_ids")

    # --- Pending human decision / pending human input ---
    if not decision_reached:
        add_item("PENDING_HUMAN_DECISION", "No human decision yet — this operation is still OPEN.", "human_decision")
    for i, hr in enumerate(getattr(canonical, "human_requests", None) or []):
        if getattr(hr, "status", None) == "PENDING":
            add_item("PENDING_HUMAN_INPUT", getattr(hr, "question", "") or "Human input required.",
                     f"human_requests[{i}]", "human_requests[].status")

    # --- Result status ---
    res = getattr(canonical, "result", None)
    if res is not None and getattr(res, "status", None) == "PARTIAL":
        add_item("INSUFFICIENT_INFORMATION", "Result is PARTIAL — no validated analysis produced (no-sustitución).", "state.result.status")
    elif res is not None and getattr(res, "status", None) == "UNAVAILABLE":
        add_item("DATA_NOT_AVAILABLE", "Result is UNAVAILABLE.", "state.result.status")

    # --- Existing decision-relevant knowledge (real artifact ids, never invented) ---
    drk: List[str] = []
    for f in (getattr(knowledge, "findings", None) or []):
        if getattr(f, "finding_id", None):
            drk.append(str(getattr(f, "finding_id", None)))
    for p in (getattr(pk, "predictions", None) or []):
        if getattr(p, "prediction_id", None):
            drk.append(str(getattr(p, "prediction_id", None)))
    for pr in (getattr(getattr(canonical, "prescriptive_knowledge", None), "prescriptions", None) or []):
        if getattr(pr, "prescription_id", None):
            drk.append(str(getattr(pr, "prescription_id", None)))

    # --- Derived descriptors (Python, not LLM) ---
    operation_kind = "OPEN_RESEARCH" if not decision_reached else "DECISION"
    is_open = not decision_reached
    has_insufficient = any(
        i.kind in ("INSUFFICIENT_INFORMATION", "INSUFFICIENT_DATA", "DATA_NOT_AVAILABLE",
                   "MISSING_EVIDENCE", "NOT_EVALUATED") for i in items
    )
    if decision_reached:
        status = "CLOSED"
    elif has_insufficient:
        status = "OPEN_INSUFFICIENT_INFORMATION"
    else:
        status = "OPEN"

    summary = (
        "Operation is open - no human decision has been reached." if not decision_reached
        else "Operation reached a human decision."
    ) + (f" {len(items)} open item(s) remain." if items else " No open items.")

    return OpenResearchState(
        status=status,
        operation_kind=operation_kind,
        is_open=is_open,
        decision_reached=decision_reached,
        decision_pending=not decision_reached,
        items=items,
        decision_relevant_knowledge=drk,
        summary=summary,
        provenance=provenance,
        built=now,
    )
