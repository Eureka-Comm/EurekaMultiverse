from typing import List, Dict, Optional, Any, Set
from pydantic import BaseModel, Field

class CognitiveTask(BaseModel):
    """
    A unit of cognitive work required by the problem. 
    Not an execution capability, but a semantic task to be fulfilled.
    """
    task_id: str
    description: str
    owner: str # e.g. "EM Descriptor", "EM Predictor"
    expected_outputs: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)

class TaskNetwork(BaseModel):
    """
    A directed acyclic graph of CognitiveTasks required to solve the problem.
    """
    tasks: List[CognitiveTask] = Field(default_factory=list)

class StructuredProblem(BaseModel):
    """
    The structural breakdown of the problem, produced by EM Structurer.
    """
    questions: List[str] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    relationships: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    unknowns: List[str] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    success_criteria: List[str] = Field(default_factory=list)
    task_network: TaskNetwork = Field(default_factory=TaskNetwork)

class ProblemModel(BaseModel):
    # =========================================================
    # DOCUMENTED EM 5.1 CONCEPTS (Problem Formulation)
    # =========================================================
    intent: str = Field(..., description="The original raw input from the user")
    problem_id: str = Field("", description="Stable identity of the problem instance (F-2 governance id).")
    problem_understanding: Optional[str] = Field(None, description="The core problem statement synthesized by EM Core")
    context: Optional[str] = Field(None, description="The context in which the problem exists")
    objective: str = Field(..., description="The main objective to accomplish")
    evidence_requirements: List[str] = Field(default_factory=list, description="Information or data needed to resolve the problem")
    constraints: List[str] = Field(default_factory=list, description="Any hard constraints specified by the user")
    horizon: Optional[str] = Field(None, description="Time horizon for the problem (e.g., short-term, long-term)")
    risk: Optional[str] = Field(None, description="Risk considerations or appetite")
    success_criteria: List[str] = Field(default_factory=list, description="Criteria that define when the problem is solved")
    authority: Optional[str] = Field(None, description="Explicit human authority/approvals required")

    # =========================================================
    # RUNTIME EXTENSIONS & EXISTING METADATA
    # =========================================================
    structured_problem: Optional[StructuredProblem] = None
    
    questions: List[str] = Field(default_factory=list, description="RUNTIME EXTENSION: Unanswered questions that must be resolved")
    assumptions: List[str] = Field(default_factory=list, description="RUNTIME EXTENSION: Assumptions made during formulation")
    unknowns: List[str] = Field(default_factory=list, description="RUNTIME EXTENSION: Elements identified as missing or unknown")
    
    entities: List[str] = Field(default_factory=list, description="Key entities involved in the problem")
    alternatives: List[str] = Field(default_factory=list, description="Explicit or implicit alternatives to consider")
    criteria: List[str] = Field(default_factory=list, description="Evaluation criteria for decision making")
    requested_outputs: List[str] = Field(default_factory=list, description="What the user wants to get out (e.g. recommendation, explanation, PDF)")
    # =========================================================
    # LS92 — GOVERNED OPERATION MODE (Python-derived routing authority)
    # The LLM SemanticProposal.intent_category is a CANDIDATE. Python decides the
    # operation_mode (KNOWLEDGE_ANSWER | DECISION) using the LLM candidate PLUS a
    # deterministic decision-verb detector — the LLM never decides routing/authority.
    # =========================================================
    intent_category: str = Field("UNKNOWN", description="LS92: LLM candidate intent kind (QUESTION/SUMMARY/REPORT/PROBLEM_SOLVING/COMMAND) — CANDIDATE, not authority.")
    operation_mode: str = Field("KNOWLEDGE_ANSWER", description="LS92: Python-derived routing mode. KNOWLEDGE_ANSWER = publish a governed LLM answer (no forced decision); DECISION = human decides among alternatives (HITL preserved).")
    domain_context: Optional[str] = Field(None, description="The general domain (e.g., BUSINESS, EDUCATION), used strictly as metadata, not for routing")
    temporal_context: Optional[str] = Field(None, description="Any temporal context")
    required_capabilities: List[str] = Field(default_factory=list, description="Capabilities identified as required by semantic parsing (DEPRECATED: routing will use TaskNetwork)")
    semantic_confidence: float = Field(1.0, description="Confidence in the extracted semantics")
    status: str = Field("STRUCTURED", description="Status of the problem model")

    # =========================================================
    # LS77.1 — EM CORE AUTHORITY GOVERNANCE (additive, non-breaking)
    # The LLM SemanticProposal is a CANDIDATE. These fields make the
    # LLM -> Python governance boundary explicit: the LLM never silently
    # becomes the authority of the governed ProblemModel.
    # =========================================================
    provenance: List[str] = Field(default_factory=list, description="LS77.1: EM Core provenance — how this ProblemModel was governed (LLM candidate + Python governance).")
    governance_status: str = Field("GOVERNED", description="LS77.1: CANDIDATE | GOVERNED | NOT_EVALUATED — governance state of the model (Python-derived, never LLM).")
    authority_status: str = Field("UNDETERMINED", description="LS77.1: HUMAN_REQUIRED | NONE | UNDETERMINED — deterministic authority governance (Python-derived, never LLM).")
    governance_fields: Dict[str, str] = Field(default_factory=dict, description="LS77.1: per-field source classification (LLM_CANDIDATE | PYTHON | HUMAN_AUTHORIZED | UNKNOWN).")
