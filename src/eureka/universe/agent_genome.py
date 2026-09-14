"""EUREKA 5.1 — EMERGENT COGNITIVE CLOUD · LOOP 1: AGENT CONTRACT FOUNDATION.

SINGLE CONTRACTUAL AUTHORITY for the identity and configuration of an agent.

Decision recorded (human authorization, 2026-09-12): `AgentGenome` is the ONE canonical contract.
The two pre-existing `AgentDefinition` classes (`universe/agent_definition.py` — used by the EM
Installer artifact and the provider-backed engine — and `universe/cognitive_provider.py` — a minimal
provider-contract stub) remain as INTERNAL compatibility surfaces with one-way adapters defined here.
Neither is an independent authority any more; nothing new may be modelled on them.

Constitutional constraints honoured by this module:

- LLM != Authority: the genome declares REQUIREMENTS (model capabilities, tools, evidence); it never
  grants authority, and it carries no field a model could use to escalate. `AgentGenome.authority_scope`
  is a fixed literal, and authority-ish fields are REJECTED at validation time.
- DeepSeek != Agent / model-agnostic: the genome never pins a vendor model as authority; it states
  `model_requirements`, and the (future) ModelRouter chooses the concrete provider/model.
- No role creep: `CognitiveFamily` maps 1:1 to the constitutional EM owner; an emergent agent can never
  declare a cognitive family it does not own.
- No duplicate store: the genome is a VALUE OBJECT. It is persisted inside the Work/canonical state
  (see LOOP 2/12), never in a new store.
- Fail closed: every validation raises `AgentContractError` instead of guessing.
- Evidence/Provenance/Freeze/Human Authority are REUSED by reference (`evidence_refs`,
  `provenance`, `freeze_requirement`, `human_escalation_rules`); no new evidence/provenance model.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AgentContractError(Exception):
    """Fail-closed contract violation. Never caught-and-ignored inside the agent layer."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}" if message else reason_code)


# --------------------------------------------------------------------------------------------- #
# Declared policy constants (no implicit budget anywhere)
# --------------------------------------------------------------------------------------------- #
MAX_AGENTS_PER_WORK = 24          # absolute ceiling for one Work (LOOP 13 budget enforcement)
MAX_DEPTH = 2                     # recursive emergence depth ceiling (LOOP 13)
HARD_BUDGET = {
    "max_runtime_seconds": 1800,
    "max_model_calls": 16,
    "max_tokens": 200_000,
    "max_cost_units": 100,
    "max_depth": MAX_DEPTH,
    "max_children": 8,
}


class CognitiveFamily(str, Enum):
    """Cognitive ownership. Maps 1:1 onto the constitutional EM nucleus (no role creep)."""

    STRUCT = "STRUCT"
    DESCRIPTOR = "DESCRIPTOR"
    PREDICTOR = "PREDICTOR"
    PRESCRIPTOR = "PRESCRIPTOR"
    ACTION = "ACTION"
    INSTALL = "INSTALL"
    PUBLISH = "PUBLISH"


#: The ONE mapping family -> constitutional EM owner. An emergent agent may only act under the
#: family it declares, and that family has exactly one constitutional owner.
FAMILY_OWNER: Dict[CognitiveFamily, str] = {
    CognitiveFamily.STRUCT: "EM Structurer",
    CognitiveFamily.DESCRIPTOR: "EM Descriptor",
    CognitiveFamily.PREDICTOR: "EM Predictor",
    CognitiveFamily.PRESCRIPTOR: "EM Prescriptor",
    CognitiveFamily.ACTION: "EM Actioner",
    CognitiveFamily.INSTALL: "EM Installer",
    CognitiveFamily.PUBLISH: "EM Publisher",
}


class NetworkRole(str, Enum):
    """Position of the agent in the cognitive network. CONSTITUTIONAL = the permanent nucleus."""

    CONSTITUTIONAL = "CONSTITUTIONAL"
    SEGREGATOR = "SEGREGATOR"
    INTEGRATOR = "INTEGRATOR"


class AgentStatus(str, Enum):
    """Canonical agent lifecycle (LOOP 2 operations run on top of these states)."""

    PROPOSED = "PROPOSED"
    CREATED = "CREATED"
    READY = "READY"
    RUNNING = "RUNNING"
    RETURNED = "RETURNED"
    VALIDATION_REQUIRED = "VALIDATION_REQUIRED"
    VALIDATED = "VALIDATED"
    FROZEN = "FROZEN"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    RETIRED = "RETIRED"


#: The ONLY legal transitions. Anything else raises (illegal lifecycle transition).
ALLOWED_TRANSITIONS: Dict[AgentStatus, Tuple[AgentStatus, ...]] = {
    AgentStatus.PROPOSED: (AgentStatus.CREATED, AgentStatus.BLOCKED, AgentStatus.RETIRED),
    AgentStatus.CREATED: (AgentStatus.READY, AgentStatus.BLOCKED, AgentStatus.REVISION_REQUIRED,
                          AgentStatus.RETIRED),
    AgentStatus.READY: (AgentStatus.RUNNING, AgentStatus.BLOCKED, AgentStatus.RETIRED),
    AgentStatus.RUNNING: (AgentStatus.RETURNED, AgentStatus.FAILED, AgentStatus.BLOCKED),
    AgentStatus.RETURNED: (AgentStatus.VALIDATION_REQUIRED, AgentStatus.FAILED),
    AgentStatus.VALIDATION_REQUIRED: (AgentStatus.VALIDATED, AgentStatus.REVISION_REQUIRED,
                                      AgentStatus.FAILED),
    AgentStatus.VALIDATED: (AgentStatus.FROZEN, AgentStatus.COMPLETED, AgentStatus.RETIRED),
    AgentStatus.FROZEN: (AgentStatus.COMPLETED, AgentStatus.RETIRED),
    AgentStatus.COMPLETED: (AgentStatus.RETIRED,),
    AgentStatus.BLOCKED: (AgentStatus.READY, AgentStatus.REVISION_REQUIRED, AgentStatus.RETIRED),
    AgentStatus.FAILED: (AgentStatus.REVISION_REQUIRED, AgentStatus.RETIRED),
    AgentStatus.REVISION_REQUIRED: (AgentStatus.PROPOSED, AgentStatus.CREATED, AgentStatus.RETIRED),
    AgentStatus.RETIRED: (),
}

#: Legacy EM Installer deployment lifecycle (canonical_state.AgentDeployment) -> canonical AgentStatus.
#: Declared so the repository keeps ONE lifecycle semantics instead of two competing ones.
DEPLOYMENT_STATE_TO_AGENT_STATUS: Dict[str, AgentStatus] = {
    "PROPOSED": AgentStatus.PROPOSED,
    "DESIGNED": AgentStatus.CREATED,
    "VALIDATED": AgentStatus.VALIDATED,
    "FROZEN": AgentStatus.FROZEN,
    "REGISTERED": AgentStatus.READY,
    "ACTIVE": AgentStatus.RUNNING,
}


def agent_status_from_deployment_state(state: str) -> AgentStatus:
    """Map the legacy EMI deployment lifecycle onto the canonical agent lifecycle (fail closed)."""
    mapped = DEPLOYMENT_STATE_TO_AGENT_STATUS.get((state or "").strip().upper())
    if mapped is None:
        raise AgentContractError("UNKNOWN_DEPLOYMENT_STATE", f"'{state}' is not an EMI deployment state")
    return mapped


def transition(current: AgentStatus, new: AgentStatus) -> AgentStatus:
    """Validate a lifecycle transition (fail closed on anything not explicitly allowed)."""
    if new not in ALLOWED_TRANSITIONS.get(current, ()):
        raise AgentContractError(
            "ILLEGAL_LIFECYCLE_TRANSITION", f"{current.value} -> {new.value} is not allowed")
    return new


# --------------------------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------------------------- #
_SLUG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_]{0,63}$")

_FAMILY_PREFIX: Dict[CognitiveFamily, str] = {
    CognitiveFamily.STRUCT: "STRUCT",
    CognitiveFamily.DESCRIPTOR: "DESC",
    CognitiveFamily.PREDICTOR: "PRED",
    CognitiveFamily.PRESCRIPTOR: "PRESC",
    CognitiveFamily.ACTION: "ACT",
    CognitiveFamily.INSTALL: "INST",
    CognitiveFamily.PUBLISH: "PUB",
}


class AgentIdentity(BaseModel):
    """CognitiveRole + NetworkRole + ProblemPredicate + Context  (e.g. PRED-SEG-LeadTime-Europe)."""

    model_config = ConfigDict(extra="forbid")

    cognitive_family: CognitiveFamily
    network_role: NetworkRole
    predicate: str = Field(..., min_length=1, max_length=64)
    context: str = Field(..., min_length=1, max_length=64)

    @field_validator("predicate", "context")
    @classmethod
    def _slug(cls, v: str) -> str:
        # No dashes: the identity string is '-'-delimited, so parts must be unambiguous to parse.
        v = (v or "").strip()
        if not _SLUG_RE.match(v):
            raise ValueError(f"'{v}' must be a slug ([A-Za-z0-9_], 1..64 chars, no dashes)")
        return v

    @property
    def agent_id(self) -> str:
        """Deterministic identity string. Same identity -> same id (collision is detectable)."""
        return f"{_FAMILY_PREFIX[self.cognitive_family]}-{self.network_role.value[:3]}-{self.predicate}-{self.context}"

    @property
    def cognitive_owner(self) -> str:
        """The constitutional EM that owns this family. Role creep is impossible by construction."""
        return FAMILY_OWNER[self.cognitive_family]

    @staticmethod
    def parse(agent_id: str) -> "AgentIdentity":
        """Parse an identity string back into its parts (fail closed on a malformed id)."""
        parts = (agent_id or "").split("-")
        if len(parts) < 4:
            raise AgentContractError("MALFORMED_AGENT_ID", agent_id)
        prefix, role_code, predicate, context = parts[0], parts[1], parts[2], "-".join(parts[3:])
        family = next((f for f, p in _FAMILY_PREFIX.items() if p == prefix), None)
        if family is None:
            raise AgentContractError("UNKNOWN_FAMILY_PREFIX", prefix)
        role = next((r for r in NetworkRole if r.value[:3] == role_code), None)
        if role is None:
            raise AgentContractError("UNKNOWN_NETWORK_ROLE", role_code)
        return AgentIdentity(cognitive_family=family, network_role=role,
                             predicate=predicate, context=context)


class AgentReference(BaseModel):
    """Lightweight reference to another agent (upstream/downstream), always Work-scoped."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    network_role: NetworkRole
    work_id: str


class AgentDependencyKind(str, Enum):
    DATA = "DATA"
    EVIDENCE = "EVIDENCE"
    VALIDATION = "VALIDATION"


class AgentDependency(BaseModel):
    """A declared dependency on another agent's output. Never a self-dependency, never a cycle."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    kind: AgentDependencyKind = AgentDependencyKind.DATA
    required: bool = True


def validate_dependencies(agent_id: str, dependencies: List[AgentDependency]) -> None:
    """Fail closed on self-dependency or duplicated dependency ids."""
    seen = set()
    for dep in dependencies or []:
        if dep.agent_id == agent_id:
            raise AgentContractError("SELF_DEPENDENCY", agent_id)
        if dep.agent_id in seen:
            raise AgentContractError("DUPLICATE_DEPENDENCY", dep.agent_id)
        seen.add(dep.agent_id)


def detect_identity_collision(genomes: List["AgentGenome"]) -> List[str]:
    """Return the agent_ids that appear MORE THAN ONCE with different content (identity collision).

    One identity must mean one agent: reusing an id with a different genome is a collision, and the
    caller (Agent Necessity / Registry, LOOP 2/5) must REUSE or MERGE instead of creating it.
    """
    by_id: Dict[str, set] = {}
    for genome in genomes or []:
        by_id.setdefault(genome.agent_id, set()).add(genome.hash())
    return sorted(aid for aid, hashes in by_id.items() if len(hashes) > 1)


def detect_cycle(edges: Dict[str, List[str]]) -> Optional[List[str]]:
    """Return a cycle path when the dependency graph has one, else None (used by LOOP 13)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {n: WHITE for n in edges}
    stack: List[str] = []

    def visit(node: str) -> Optional[List[str]]:
        color[node] = GRAY
        stack.append(node)
        for nxt in edges.get(node, []):
            if nxt not in color:
                color[nxt] = WHITE
            if color[nxt] == GRAY:
                return stack[stack.index(nxt):] + [nxt]
            if color[nxt] == WHITE:
                found = visit(nxt)
                if found:
                    return found
        stack.pop()
        color[node] = BLACK
        return None

    for node in list(edges.keys()):
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


# --------------------------------------------------------------------------------------------- #
# Model requirements (the agent DECLARES; the ModelRouter decides) — LOOP 10 contract
# --------------------------------------------------------------------------------------------- #
class ModelCapabilityClass(str, Enum):
    REMOTE_API = "REMOTE_API"
    LOCAL_RUNTIME = "LOCAL_RUNTIME"


class ReasoningClass(str, Enum):
    FAST = "FAST"
    BALANCED = "BALANCED"
    DEEP = "DEEP"


class ModelRequirement(BaseModel):
    """Provider-agnostic requirement. NEVER a vendor pin: no `model=` authority field exists."""

    model_config = ConfigDict(extra="forbid")

    capability_class: ModelCapabilityClass = ModelCapabilityClass.REMOTE_API
    min_context_tokens: int = Field(8000, ge=256, le=2_000_000)
    reasoning: ReasoningClass = ReasoningClass.BALANCED
    latency_class: str = Field("NORMAL", pattern="^(FAST|NORMAL|RELAXED)$")
    cost_class: str = Field("STANDARD", pattern="^(LOW|STANDARD|HIGH)$")
    allow_fallback: bool = False   # fallback only when explicitly authorized


# --------------------------------------------------------------------------------------------- #
# Resource budget (no escalation: a child budget can only be <= the parent's)
# --------------------------------------------------------------------------------------------- #
class ResourceBudget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_runtime_seconds: int = Field(300, ge=0, le=HARD_BUDGET["max_runtime_seconds"])
    max_model_calls: int = Field(4, ge=0, le=HARD_BUDGET["max_model_calls"])
    max_tokens: int = Field(20_000, ge=0, le=HARD_BUDGET["max_tokens"])
    max_cost_units: int = Field(10, ge=0, le=HARD_BUDGET["max_cost_units"])
    max_depth: int = Field(0, ge=0, le=HARD_BUDGET["max_depth"])   # REMAINING depth allowance: a
    # child receives at most the parent's value (usually parent.max_depth - 1), never more.
    max_children: int = Field(0, ge=0, le=HARD_BUDGET["max_children"])

    def child(self, **overrides: int) -> "ResourceBudget":
        """Derive a child budget. Any escalation attempt raises (fail closed)."""
        data = self.model_dump()
        for key, value in overrides.items():
            if key not in data:
                raise AgentContractError("UNKNOWN_BUDGET_FIELD", key)
            if int(value) > int(data[key]):
                raise AgentContractError("BUDGET_ESCALATION", f"{key}: {value} > {data[key]}")
            data[key] = int(value)
        if data["max_depth"] > HARD_BUDGET["max_depth"]:
            raise AgentContractError("DEPTH_CEILING_EXCEEDED", str(data["max_depth"]))
        return ResourceBudget(**data)

    def exhausted(self, *, elapsed_seconds: float = 0.0, model_calls: int = 0,
                  tokens: int = 0, cost_units: int = 0) -> Optional[str]:
        """Return the reason the budget is exhausted, or None."""
        if elapsed_seconds > self.max_runtime_seconds:
            return "BUDGET_RUNTIME_EXHAUSTED"
        if model_calls > self.max_model_calls:
            return "BUDGET_MODEL_CALLS_EXHAUSTED"
        if tokens > self.max_tokens:
            return "BUDGET_TOKENS_EXHAUSTED"
        if cost_units > self.max_cost_units:
            return "BUDGET_COST_EXHAUSTED"
        return None


# --------------------------------------------------------------------------------------------- #
# AgentGenome — the ONE canonical contract
# --------------------------------------------------------------------------------------------- #
class AgentGenome(BaseModel):
    """Canonical identity + configuration of an agent. NOT centred on a prompt or an LLM."""

    model_config = ConfigDict(extra="forbid")

    # identity & scope
    identity: AgentIdentity
    work_id: str = Field(..., min_length=1)
    problem_id: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    version: str = Field("1.0", min_length=1, max_length=32)

    # cognitive contract
    objective: str = Field(..., min_length=1)
    questions: List[str] = Field(default_factory=list)
    predicates: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    authoritative_inputs: List[str] = Field(default_factory=list)
    knowledge_sources: List[str] = Field(default_factory=list)
    tools: List[str] = Field(default_factory=list)              # capabilities the agent MAY use
    forbidden_operations: List[str] = Field(default_factory=list)

    # model + execution requirements (the router decides the concrete model — LOOP 10)
    model_requirements: ModelRequirement = Field(default_factory=ModelRequirement)

    # network position
    dependencies: List[AgentDependency] = Field(default_factory=list)
    upstream_agents: List[AgentReference] = Field(default_factory=list)
    downstream_agents: List[AgentReference] = Field(default_factory=list)

    # output contract
    output_schema: Dict[str, Any] = Field(default_factory=dict)
    evidence_requirements: List[str] = Field(default_factory=list)
    uncertainty: str = Field("UNKNOWN", pattern="^(UNKNOWN|LOW|MEDIUM|HIGH)$")

    # governance
    execution_level: str = Field("COGNITIVE", pattern="^(COGNITIVE|SYSTEM|HUMAN)$")
    resource_budget: ResourceBudget = Field(default_factory=ResourceBudget)
    validation_rules: List[str] = Field(default_factory=list)
    freeze_requirement: bool = False
    human_escalation_rules: List[str] = Field(default_factory=list)
    return_to: str = Field("EM Core", min_length=1)

    # provenance of the genome itself
    provenance: List[str] = Field(default_factory=list)
    created_by: str = Field("EM Core", min_length=1)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(
        datetime.timezone.utc).isoformat())
    frozen: bool = False

    #: FIXED: an agent is a proposer. There is no field that can grant authority.
    authority_scope: str = Field("PROPOSER", frozen=True)

    # ---- validation ------------------------------------------------------------------------ #
    @field_validator("created_by")
    @classmethod
    def _no_agent_creates_itself(cls, v: str) -> str:
        if (v or "").strip() == "":
            raise ValueError("created_by is mandatory (Core authorizes creation)")
        return v

    @model_validator(mode="after")
    def _validate_genome(self) -> "AgentGenome":
        # An emergent agent returns to the constitutional owner of its family (or to Core).
        if self.return_to not in ("EM Core", self.identity.cognitive_owner):
            raise ValueError(f"return_to must be 'EM Core' or '{self.identity.cognitive_owner}'")
        validate_dependencies(self.identity.agent_id, self.dependencies)
        refs = [r.agent_id for r in (self.upstream_agents or []) + (self.downstream_agents or [])]
        if self.identity.agent_id in refs:
            raise AgentContractError("SELF_REFERENCE", self.identity.agent_id)
        for ref in (self.upstream_agents or []) + (self.downstream_agents or []):
            if ref.work_id != self.work_id:
                raise AgentContractError("CROSS_WORK_REFERENCE", ref.agent_id)
        return self

    # ---- identity helpers ------------------------------------------------------------------ #
    @property
    def agent_id(self) -> str:
        return self.identity.agent_id

    @property
    def cognitive_owner(self) -> str:
        return self.identity.cognitive_owner

    def requires_evidence(self) -> bool:
        return bool(self.evidence_requirements)

    def assert_same_work(self, work_id: str, problem_id: Optional[str] = None) -> None:
        """Cross-work / cross-problem contamination guard (fail closed)."""
        if work_id != self.work_id:
            raise AgentContractError("CROSS_WORK_CONTAMINATION",
                                     f"genome {self.work_id} != {work_id}")
        if problem_id is not None and problem_id != self.problem_id:
            raise AgentContractError("CROSS_PROBLEM_CONTAMINATION",
                                     f"genome {self.problem_id} != {problem_id}")

    def assert_model_allowed(self, allowed_models: List[str], chosen_model: str) -> None:
        """The agent may not silently substitute a model outside the authorized set (LOOP 10)."""
        if chosen_model not in (allowed_models or []):
            raise AgentContractError("UNAUTHORIZED_MODEL", f"{chosen_model} not in authorized set")

    def hash(self) -> str:
        """Canonical content hash of the genome (frozen-genome tamper evidence)."""
        payload = self.model_dump(mode="json")
        payload.pop("frozen", None)   # freezing is metadata, not content identity
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()

    def freeze(self) -> "AgentGenome":
        """Freeze the genome. A frozen genome is content-immutable (see `assert_compatible_with`)."""
        self.frozen = True
        return self

    def assert_compatible_with(self, other: "AgentGenome") -> None:
        """A frozen genome can never be silently mutated: the content hash must be unchanged."""
        if self.frozen and self.hash() != other.hash():
            raise AgentContractError("FROZEN_GENOME_MUTATION", self.agent_id)

    def assert_no_authority_escalation(self, candidate: Dict[str, Any]) -> None:
        """Reject any payload that tries to change authority/ownership/identity/policy.

        Scope fields (work_id/problem_id) are NOT listed here: they are validated by the caller with
        the more specific CROSS_WORK_CONTAMINATION / CROSS_PROBLEM_CONTAMINATION codes.
        """
        immutable = ("authority_scope", "cognitive_family", "network_role", "identity",
                     "created_by", "return_to")
        for key in immutable:
            if key in candidate and candidate[key] != self.model_dump(mode="json").get(key):
                raise AgentContractError("AUTHORITY_ESCALATION_ATTEMPT", key)
        for forbidden in ("authority", "canonical_status", "execution_mode", "bypass_governance",
                          "promote", "release", "approved", "is_admin", "owner"):
            if forbidden in candidate:
                raise AgentContractError("FORBIDDEN_FIELD", forbidden)


# --------------------------------------------------------------------------------------------- #
# TaskEnvelope — everything an agent is AUTHORIZED to see for one task
# --------------------------------------------------------------------------------------------- #
class TaskEnvelope(BaseModel):
    """Authorized context for one agent-task execution. Authorization is explicit, never a wildcard."""

    model_config = ConfigDict(extra="forbid")

    envelope_id: str = Field(..., min_length=1)
    work_id: str = Field(..., min_length=1)
    problem_id: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    genome_hash: str = Field(..., min_length=8)
    authorized_inputs: List[str] = Field(default_factory=list)
    authorized_evidence_ids: List[str] = Field(default_factory=list)
    allowed_tools: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    budget: ResourceBudget = Field(default_factory=ResourceBudget)
    attempt: int = Field(1, ge=1)
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(
        datetime.timezone.utc).isoformat())

    @model_validator(mode="after")
    def _no_wildcard(self) -> "TaskEnvelope":
        if "*" in self.authorized_inputs or "*" in self.authorized_evidence_ids or "*" in self.allowed_tools:
            raise ValueError("wildcard authorization is not allowed (explicit grants only)")
        return self

    def assert_matches(self, genome: AgentGenome) -> None:
        """The envelope must target the genome's work/problem/task and its frozen content hash."""
        genome.assert_same_work(self.work_id, self.problem_id)
        if self.agent_id != genome.agent_id:
            raise AgentContractError("ENVELOPE_AGENT_MISMATCH", self.agent_id)
        if self.task_id != genome.task_id:
            raise AgentContractError("ENVELOPE_TASK_MISMATCH", self.task_id)
        if self.genome_hash != genome.hash():
            raise AgentContractError("ENVELOPE_GENOME_MISMATCH", "stale genome hash")

    def authorizes_evidence(self, evidence_id: str) -> bool:
        return evidence_id in self.authorized_evidence_ids

    def authorizes_tool(self, tool: str) -> bool:
        return tool in self.allowed_tools


# --------------------------------------------------------------------------------------------- #
# ReturnPackage — what an agent is allowed to RETURN (a CANDIDATE, never a validated truth)
# --------------------------------------------------------------------------------------------- #
class ReturnStatus(str, Enum):
    RESULT = "RESULT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    SUBPROBLEM_DISCOVERED = "SUBPROBLEM_DISCOVERED"
    NEW_AGENT_REQUIRED = "NEW_AGENT_REQUIRED"
    BLOCKED = "BLOCKED"
    FAILED = "FAILED"


class SubproblemDiscovery(BaseModel):
    """An agent may DISCOVER a subproblem; it may never create a child agent itself (LOOP 13)."""

    model_config = ConfigDict(extra="forbid")

    statement: str = Field(..., min_length=1)
    proposed_predicate: str = Field("", max_length=64)
    proposed_family: Optional[CognitiveFamily] = None
    reason: str = Field(..., min_length=1)


class ReturnPackage(BaseModel):
    """Structured return from one agent execution. `validation_status` starts as CANDIDATE always."""

    model_config = ConfigDict(extra="forbid")

    return_id: str = Field(..., min_length=1)
    work_id: str = Field(..., min_length=1)
    problem_id: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    execution_id: str = Field(..., min_length=1)
    status: ReturnStatus = ReturnStatus.RESULT
    result: Dict[str, Any] = Field(default_factory=dict)
    predicates: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    uncertainty: str = Field("UNKNOWN", pattern="^(UNKNOWN|LOW|MEDIUM|HIGH)$")
    provenance: List[str] = Field(default_factory=list)
    validation_status: str = Field("CANDIDATE", pattern="^(CANDIDATE|REJECTED|VALIDATED)$")
    subproblem_discoveries: List[SubproblemDiscovery] = Field(default_factory=list)
    recommended_agents: List[str] = Field(default_factory=list)   # CANDIDATES for the necessity test
    model_used: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(
        datetime.timezone.utc).isoformat())

    @model_validator(mode="after")
    def _candidate_only(self) -> "ReturnPackage":
        # An agent can never return something already VALIDATED (validation is Python/Core's job).
        if self.validation_status == "VALIDATED":
            raise AgentContractError("AGENT_CANNOT_SELF_VALIDATE", self.agent_id)
        return self

    def validate_against(self, genome: AgentGenome) -> None:
        """Contract check against the genome that produced this return (fail closed)."""
        genome.assert_same_work(self.work_id, self.problem_id)
        if self.agent_id != genome.agent_id:
            raise AgentContractError("RETURN_AGENT_MISMATCH", self.agent_id)
        if self.task_id != genome.task_id:
            raise AgentContractError("RETURN_TASK_MISMATCH", self.task_id)
        if genome.requires_evidence() and self.status == ReturnStatus.RESULT and not self.evidence_refs:
            raise AgentContractError("EVIDENCE_REQUIRED_MISSING",
                                     f"{genome.agent_id} requires evidence for a RESULT return")
        if not self.provenance:
            raise AgentContractError("PROVENANCE_REQUIRED", self.return_id)


# --------------------------------------------------------------------------------------------- #
# AgentExecutionRecord — the persisted execution record (LOOP 12 observability/persistence)
# --------------------------------------------------------------------------------------------- #
class AgentExecutionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_id: str = Field(..., min_length=1)
    work_id: str = Field(..., min_length=1)
    problem_id: str = Field(..., min_length=1)
    task_id: str = Field(..., min_length=1)
    agent_id: str = Field(..., min_length=1)
    genome_hash: str = Field("", max_length=128)
    provider: str = Field("", max_length=64)
    model: str = Field("", max_length=128)
    status: AgentStatus = AgentStatus.CREATED
    attempt: int = Field(1, ge=1)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    latency_ms: Optional[float] = None
    tokens: int = Field(0, ge=0)
    cost_units: float = Field(0.0, ge=0)
    evidence_ids: List[str] = Field(default_factory=list)
    return_package: Optional[ReturnPackage] = None
    failure_reason: Optional[str] = None
    provenance: List[str] = Field(default_factory=list)

    def advance(self, new: AgentStatus) -> "AgentExecutionRecord":
        self.status = transition(self.status, new)
        return self


# --------------------------------------------------------------------------------------------- #
# LOOP 2 — persisted agent-network shapes (canonical, Work-scoped). NO new store: these live
# inside CanonicalWorkState.agent_network and are persisted by the existing WorkStore authority.
# --------------------------------------------------------------------------------------------- #

#: The permanent constitutional nucleus. Read-only references: the registry never owns them and
#: never creates them — it only guarantees the EMERGENT layer stays distinct from them.
CONSTITUTIONAL_EM: Tuple[str, ...] = ("EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
                                      "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher")


class LifecycleEvent(BaseModel):
    """One governed lifecycle transition (append-only history: the audit trail of an agent)."""

    model_config = ConfigDict(extra="forbid")

    at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    from_status: Optional[AgentStatus] = None
    to_status: AgentStatus
    actor: str = Field(..., min_length=1)
    reason: str = ""


class EmergentAgentRecord(BaseModel):
    """A registered EMERGENT agent: its genome + canonical lifecycle state + audit history.

    Persisted inside the Work's canonical state (`CanonicalWorkState.agent_network`). The registry is
    a DERIVED index over these records; it is never a second persistence authority.
    """

    model_config = ConfigDict(extra="forbid")

    genome: AgentGenome
    status: AgentStatus = AgentStatus.CREATED
    history: List[LifecycleEvent] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    frozen_genome_hash: str = ""
    registered_at: str = Field(default_factory=lambda: datetime.datetime.now(
        datetime.timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.datetime.now(
        datetime.timezone.utc).isoformat())

    @property
    def agent_id(self) -> str:
        return self.genome.agent_id

    @property
    def work_id(self) -> str:
        return self.genome.work_id

    @property
    def problem_id(self) -> str:
        return self.genome.problem_id

    @property
    def cognitive_owner(self) -> str:
        return self.genome.cognitive_owner

    def assert_frozen_integrity(self) -> None:
        """A FROZEN agent's genome can never change (tamper evidence)."""
        if self.status is AgentStatus.FROZEN:
            if not self.frozen_genome_hash:
                raise AgentContractError("FROZEN_AGENT_WITHOUT_HASH", self.agent_id)
            if self.frozen_genome_hash != self.genome.hash():
                raise AgentContractError("FROZEN_GENOME_MUTATION", self.agent_id)


class AgentNetworkState(BaseModel):
    """Canonical container of a Work's EMERGENT agents (+ their executions). Default empty.

    Both the registered agents and their execution records live HERE, inside the Work's canonical
    state, so the Work/WorkStore remains the single persistence authority (no AgentStore).
    """

    model_config = ConfigDict(extra="forbid")

    records: List[EmergentAgentRecord] = Field(default_factory=list)
    executions: List["AgentExecutionRecord"] = Field(default_factory=list)

    def by_id(self, agent_id: str) -> Optional[EmergentAgentRecord]:
        return next((r for r in self.records if r.agent_id == agent_id), None)

    def ids(self) -> List[str]:
        return [r.agent_id for r in self.records]


# --------------------------------------------------------------------------------------------- #
# Compatibility adapters (AgentDefinition -> AgentGenome). One-way; definitions are NOT authority.
# --------------------------------------------------------------------------------------------- #
def genome_from_agent_definition(ad: Any, *, identity: AgentIdentity, work_id: str, problem_id: str,
                                 task_id: str, objective: str, **overrides: Any) -> AgentGenome:
    """Adapter for `universe.agent_definition.AgentDefinition` (EMI artifact / provider-backed engine).

    Maps the reusable subset: agent_id/version -> identity+version, capabilities -> tools,
    forbidden_operations, knowledge_sources, output_schema, provider_policy.timeout -> budget.
    `system_prompt` is carried as a NON-authoritative provenance note, never as agent identity.
    """
    provider_policy = dict(getattr(ad, "provider_policy", None) or {})
    budget = ResourceBudget(
        max_runtime_seconds=int(provider_policy.get("timeout", 300)) if str(
            provider_policy.get("timeout", 300)).isdigit() else 300,
    )
    data: Dict[str, Any] = {
        "identity": identity,
        "work_id": work_id,
        "problem_id": problem_id,
        "task_id": task_id,
        "version": str(getattr(ad, "version", "1.0")),
        "objective": objective,
        "tools": list(getattr(ad, "capabilities", None) or []),
        "forbidden_operations": list(getattr(ad, "forbidden_operations", None) or []),
        "knowledge_sources": list(getattr(ad, "knowledge_sources", None) or []),
        "output_schema": dict(getattr(ad, "output_schema", None) or {}),
        "resource_budget": budget,
        "provenance": [f"AgentDefinition[{getattr(ad, 'agent_id', '?')}] v{getattr(ad, 'version', '?')} "
                       f"adapted to AgentGenome (system_prompt is non-authoritative)"],
    }
    data.update(overrides)
    return AgentGenome(**data)


def agent_definition_from_genome(genome: AgentGenome) -> Dict[str, Any]:
    """Projection of a genome onto the legacy AgentDefinition field set (compatibility surface)."""
    return {
        "agent_id": genome.agent_id,
        "version": genome.version,
        "system_prompt": ("EUREKA emergent agent. Cognitive family: "
                          f"{genome.identity.cognitive_family.value}; owner: {genome.cognitive_owner}. "
                          "You PROPOSE structured output only; Python/EUREKA governs."),
        "input_schema": {"type": "object", "properties": {"task_envelope": {"type": "object"}}},
        "output_schema": genome.output_schema or {"type": "object"},
        "capabilities": list(genome.tools),
        "forbidden_operations": list(genome.forbidden_operations),
        "knowledge_sources": list(genome.knowledge_sources),
        "provider_policy": {"timeout": genome.resource_budget.max_runtime_seconds,
                            "allow_fallback": genome.model_requirements.allow_fallback},
    }


def genome_from_provider_stub(stub: Any, *, identity: AgentIdentity, work_id: str, problem_id: str,
                              task_id: str, objective: str, **overrides: Any) -> AgentGenome:
    """Adapter for the legacy `cognitive_provider.AgentDefinition` stub (description/system_prompt/
    tools/model). The stub's `model` is carried as a NON-authoritative provenance note: model choice
    belongs to the ModelRouter (LOOP 10), so the genome only records the requested model."""
    requested_model = str(getattr(stub, "model", "") or "")
    provenance = [f"ProviderStub[{getattr(stub, 'description', '?')}] adapted to AgentGenome"]
    if requested_model:
        provenance.append(f"requested_model={requested_model} (routing decided by ModelRouter)")
    data: Dict[str, Any] = {
        "identity": identity,
        "work_id": work_id,
        "problem_id": problem_id,
        "task_id": task_id,
        "objective": objective or str(getattr(stub, "description", "")) or "unspecified",
        "tools": list(getattr(stub, "tools", None) or []),
        "provenance": provenance,
    }
    data.update(overrides)
    return AgentGenome(**data)
