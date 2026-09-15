"""EUREKA 5.1 — LOOP 5: AGENT NECESSITY TEST (evaluation ONLY — it never creates an agent).

MISSION
-------
Decide, deterministically and fail-closed, whether the candidates produced by LOOP 4's
``ProblemCompiler`` justify the existence of an EMERGENT cognitive unit.

    NECESSARY      = there is enough evidence to justify that this work COULD require an emergent
                     agent unit — subject to later loops (design, genome, registration,
                     execution, validation). It does NOT create, register, activate, authorize,
                     execute, route or persist anything.
    NOT_NECESSARY  = an EXISTING structure already satisfies the need (reuse-first).
    BLOCKED        = the need cannot be demonstrated with the available evidence.

HARD INVARIANTS (asserted by tests and enforced by validators)
--------------------------------------------------------------
  * no agent is created/registered/authorized/executed (no agent-layer import, no execution API);
  * no second TaskNetwork and no TaskNetwork mutation;
  * no new persistence authority (the report lives INSIDE CanonicalWorkState, persisted by the
    existing WorkStore);
  * no canonical identity change (the report is outside ``canonical_identity._payload`` and
    ``EMPublisher._freeze_signature``, exactly like ``agent_network`` and ``execution_plan``);
  * no routing, no self-validation, no authority escalation, no model call (deterministic Python);
  * F4 (agent_network outside the fingerprint) is NOT resolved here — not incidentally either.

REUSE-FIRST (the eight checks the mission mandates, in this order)
-----------------------------------------------------------------
  1. existing capability   -> ``CapabilityRegistry.resolve`` (registered capability ids)
  2. existing EM           -> ``CONSTITUTIONAL_EM`` + ``FAMILY_OWNER``
  3. existing family       -> ``CognitiveFamily`` / ``FAMILY_OWNER`` (1:1 with the nucleus)
  4. existing task         -> the ONE TaskNetwork (``CognitiveTask``)
  5. existing capability contract -> ``CapabilityContract.canonical_em``/``produces``
  6. existing TaskNetwork  -> read-only, never modified
  7. existing agent genome -> ``canonical.agent_network`` records (``AgentGenome``, LOOP 1)
  8. current pipeline      -> the existing ExecutionPlan the Orchestrator already built

Only when an existing structure cannot satisfy the need may a candidate reach NECESSARY — and it
must then satisfy ALL of N1..N14 with a fully populated evidence record.
"""
from __future__ import annotations

import datetime
import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_genome import (CONSTITUTIONAL_EM, FAMILY_OWNER, HARD_BUDGET, CognitiveFamily,
                           ModelRequirement, ResourceBudget)
from .capability_fabric import CapabilityRegistry
from .problem_compiler import CandidateKind, ProblemCandidate, ProblemCompilation

NECESSITY_VERSION = "1.0"

#: Declared authority of this module. A CONSTANT: nothing can promote it.
NECESSITY_AUTHORITY = "EVALUATION_ONLY"


class NecessityDecision(str, Enum):
    NOT_NECESSARY = "NOT_NECESSARY"
    NECESSARY = "NECESSARY"
    BLOCKED = "BLOCKED"


# ----------------------------------------------------------------------------------------------- #
# Reason codes (the 19 mandated codes + explicitly declared additions; never a generic exception
# where a specific code is possible).
# ----------------------------------------------------------------------------------------------- #
NECESSITY_EXISTING_CAPABILITY_SUFFICIENT = "NECESSITY_EXISTING_CAPABILITY_SUFFICIENT"
NECESSITY_EXISTING_EM_SUFFICIENT = "NECESSITY_EXISTING_EM_SUFFICIENT"
NECESSITY_DUPLICATES_TASK = "NECESSITY_DUPLICATES_TASK"
NECESSITY_DUPLICATES_AGENT = "NECESSITY_DUPLICATES_AGENT"
NECESSITY_DUPLICATES_CAPABILITY = "NECESSITY_DUPLICATES_CAPABILITY"
NECESSITY_BOUNDARY_UNCLEAR = "NECESSITY_BOUNDARY_UNCLEAR"
NECESSITY_OWNER_MISSING = "NECESSITY_OWNER_MISSING"
NECESSITY_INPUT_CONTRACT_MISSING = "NECESSITY_INPUT_CONTRACT_MISSING"
NECESSITY_OUTPUT_CONTRACT_MISSING = "NECESSITY_OUTPUT_CONTRACT_MISSING"
NECESSITY_EVIDENCE_MISSING = "NECESSITY_EVIDENCE_MISSING"
NECESSITY_CROSS_WORK = "NECESSITY_CROSS_WORK"
NECESSITY_CROSS_PROBLEM = "NECESSITY_CROSS_PROBLEM"
NECESSITY_AUTHORITY_ESCALATION = "NECESSITY_AUTHORITY_ESCALATION"
NECESSITY_ROUTING_ESCALATION = "NECESSITY_ROUTING_ESCALATION"
NECESSITY_SELF_VALIDATION = "NECESSITY_SELF_VALIDATION"
NECESSITY_RESOURCE_INFEASIBLE = "NECESSITY_RESOURCE_INFEASIBLE"
NECESSITY_GOVERNANCE_INCOMPATIBLE = "NECESSITY_GOVERNANCE_INCOMPATIBLE"
NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION = "NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION"
NECESSARY_EMERGENT_UNIT_JUSTIFIED = "NECESSARY_EMERGENT_UNIT_JUSTIFIED"
#: Declared additions (the mission allows more than the minimum):
NECESSITY_CAPABILITY_UNKNOWN = "NECESSITY_CAPABILITY_UNKNOWN"          # depends on an unknown capability
NECESSITY_TASK_NOT_IN_NETWORK = "NECESSITY_TASK_NOT_IN_NETWORK"        # claim not grounded in the network
NECESSITY_EVIDENCE_UNVERIFIABLE = "NECESSITY_EVIDENCE_UNVERIFIABLE"    # declared evidence cannot be checked

REASON_CODES: Tuple[str, ...] = (
    NECESSITY_EXISTING_CAPABILITY_SUFFICIENT, NECESSITY_EXISTING_EM_SUFFICIENT,
    NECESSITY_DUPLICATES_TASK, NECESSITY_DUPLICATES_AGENT, NECESSITY_DUPLICATES_CAPABILITY,
    NECESSITY_BOUNDARY_UNCLEAR, NECESSITY_OWNER_MISSING, NECESSITY_INPUT_CONTRACT_MISSING,
    NECESSITY_OUTPUT_CONTRACT_MISSING, NECESSITY_EVIDENCE_MISSING, NECESSITY_CROSS_WORK,
    NECESSITY_CROSS_PROBLEM, NECESSITY_AUTHORITY_ESCALATION, NECESSITY_ROUTING_ESCALATION,
    NECESSITY_SELF_VALIDATION, NECESSITY_RESOURCE_INFEASIBLE, NECESSITY_GOVERNANCE_INCOMPATIBLE,
    NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION, NECESSARY_EMERGENT_UNIT_JUSTIFIED,
    NECESSITY_CAPABILITY_UNKNOWN, NECESSITY_TASK_NOT_IN_NETWORK, NECESSITY_EVIDENCE_UNVERIFIABLE,
)

#: Escalation detectors. A candidate cannot TALK its way into authority: prohibited intent in the
#: payload is a BLOCKED verdict, never a NECESSARY one.
_AUTHORITY_ESCALATION_RE = re.compile(
    r"(authority[_ ]?scope|scope[ =:]*owner|self[- ]?authoriz|authorize (myself|itself|the agent)|"
    r"escalat\w* (authority|autoridad)|autoridad propia|become (the )?authority|"
    r"promote to (owner|authority)|bypass (governance|the gate)|PROPOSER\s*(->|→|to)\s*OWNER)",
    re.IGNORECASE)
_ROUTING_ESCALATION_RE = re.compile(
    # NOTE: a bare mention of "routing" is NOT an escalation — the LOOP 4 capability candidates
    # legitimately say "routing stays with EM Core". Only an INTENT to route/own the routing is one.
    r"(route\s+(the\s+|a\s+|next|siguiente|pipeline|task|em\b|owner)|"
    r"(will|would|should|must|shall|can|may|needs? to|is to|debe|deber[ií]a|puede|va a)\s+"
    r"(route|re-?route|reordenar|enrutar)|"
    r"(own|owns|owning|own's|take over|takes over|assume|assumes|assuming|asumir|asume|tomar)\s+"
    r"(the\s+)?(routing|route|next[- ]owner|siguiente\s+owner|siguiente\s+em)|"
    r"routing\s+(authority|ownership|control|decision|decisions)|"
    r"autoridad\s+de\s+routing|"
    r"become\s+(the\s+)?router|(is|as)\s+(the\s+)?router|\brouter\b|"
    r"(decide|decides|deciding|decidir|decide)\s+(the\s+)?(next[- ]owner|siguiente\s+em|"
    r"siguiente\s+owner|routing)|"
    r"(re-?order|reordenar)\s+(the\s+)?(pipeline|plan|task\s*network)|"
    r"(add|adds|adding|a[nñ]adir)\s+(a\s+)?task\s+to\s+the\s+network|"
    r"task\s*network\s+(mutation|change|modification)|"
    r"(modify|modifies|modifying|modificar)\s+(the\s+)?(execution\s+)?(plan|task\s*network))",
    re.IGNORECASE)
_SELF_VALIDATION_RE = re.compile(
    r"(self[- ]?validat|validate (myself|itself|the agent)|mark (it )?validated|"
    r"auto[- ]?approv|aprobarse a s[ií] mismo|freeze (the )?(result|knowledge)|publish (the )?result)",
    re.IGNORECASE)

#: Declared vocabularies for the mandated check fields (prose-free, machine-checkable).
BOUNDARY_DIFFERENTIATED = "DIFFERENTIATED"
BOUNDARY_GENERIC = "GENERIC"
BOUNDARY_UNKNOWN = "UNKNOWN"
DUPLICATION_NONE = "NO_DUPLICATION"
DUPLICATION_TASK = "DUPLICATES_TASK"
DUPLICATION_AGENT = "DUPLICATES_AGENT"
DUPLICATION_CAPABILITY = "DUPLICATES_CAPABILITY"
DUPLICATION_EM = "DUPLICATES_EM"
AUTHORITY_PROPOSER_ONLY = "PROPOSER_ONLY"
AUTHORITY_ESCALATION_REQUESTED = "ESCALATION_REQUESTED"
ROUTING_NONE = "NO_ROUTING"
ROUTING_REQUESTED = "ROUTING_REQUESTED"
VALIDATION_EXTERNAL = "EXTERNAL_VALIDATION_AVAILABLE"
VALIDATION_SELF = "SELF_VALIDATION_REQUESTED"
CHECK_UNKNOWN = "UNKNOWN"
RESOURCE_FEASIBLE = "FEASIBLE"
RESOURCE_INFEASIBLE = "INFEASIBLE"

_ARROW_SPLIT_RE = re.compile(r"\s*(?:->|→|=>)\s*")


class NecessityError(Exception):
    """Fail-closed contract violation of the necessity test itself."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}" if message else reason_code)


# ----------------------------------------------------------------------------------------------- #
# Evidence record (the mandated model). A NECESSARY verdict that is missing ANY required check is
# rejected by the validator below — it cannot be constructed by accident.
# ----------------------------------------------------------------------------------------------- #
class NecessityEvaluation(BaseModel):
    """One candidate's necessity evaluation, with its full evidence record."""

    model_config = ConfigDict(extra="forbid")

    evaluation_id: str = Field(..., min_length=1)
    candidate_id: str = Field(..., min_length=1)
    work_id: str = ""
    problem_id: str = ""
    candidate_kind: CandidateKind
    decision: NecessityDecision
    reason_code: str = Field(..., min_length=1)

    # --- mandated evidence record ------------------------------------------------------------- #
    evidence_refs: List[str] = Field(default_factory=list)
    existing_capabilities_checked: List[str] = Field(default_factory=list)
    existing_agents_checked: List[str] = Field(default_factory=list)
    existing_tasks_checked: List[str] = Field(default_factory=list)
    existing_families_checked: List[str] = Field(default_factory=list)
    responsibility_boundary: str = BOUNDARY_UNKNOWN
    input_contract: str = ""
    output_contract: str = ""
    owner: str = ""
    duplication_check: str = CHECK_UNKNOWN
    authority_check: str = CHECK_UNKNOWN
    routing_check: str = CHECK_UNKNOWN
    validation_check: str = CHECK_UNKNOWN
    resource_check: str = CHECK_UNKNOWN

    # --- declared additions (evidence the mission requires but does not name) ------------------ #
    existing_em: str = ""
    capability_gap_evidence: str = ""
    source: str = ""
    detail: str = ""
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _necessary_requires_full_evidence(self) -> "NecessityEvaluation":
        """NECESSARY is only constructible with every required check positively evidenced."""
        if self.decision != NecessityDecision.NECESSARY:
            return self
        problems = []
        if self.reason_code != NECESSARY_EMERGENT_UNIT_JUSTIFIED:
            problems.append("reason_code")
        if self.responsibility_boundary != BOUNDARY_DIFFERENTIATED:
            problems.append("responsibility_boundary")
        if self.duplication_check != DUPLICATION_NONE:
            problems.append("duplication_check")
        if self.authority_check != AUTHORITY_PROPOSER_ONLY:
            problems.append("authority_check")
        if self.routing_check != ROUTING_NONE:
            problems.append("routing_check")
        if self.validation_check != VALIDATION_EXTERNAL:
            problems.append("validation_check")
        if self.resource_check != RESOURCE_FEASIBLE:
            problems.append("resource_check")
        if not self.input_contract:
            problems.append("input_contract")
        if not self.output_contract:
            problems.append("output_contract")
        if self.owner not in CONSTITUTIONAL_EM:
            problems.append("owner")
        if not self.capability_gap_evidence:
            problems.append("capability_gap_evidence")
        if problems:
            raise NecessityError("NECESSARY_WITHOUT_FULL_EVIDENCE", ",".join(problems))
        return self


class AgentNecessityReport(BaseModel):
    """The evaluation artifact. It DECLARES — and is validated to honour — that it creates nothing."""

    model_config = ConfigDict(extra="forbid")

    report_id: str = Field(..., min_length=1)
    work_id: str = ""
    problem_id: str = ""
    test: str = "AgentNecessityTest"
    test_version: str = NECESSITY_VERSION
    authority: str = NECESSITY_AUTHORITY
    evaluation_only: bool = True
    creates_agents: bool = False
    creates_task_network: bool = False
    persists: bool = False
    carries_routing: bool = False
    evaluations: List[NecessityEvaluation] = Field(default_factory=list)
    created_at: str = ""
    provenance: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _evaluation_only_is_not_negotiable(self) -> "AgentNecessityReport":
        if self.authority != NECESSITY_AUTHORITY:
            raise NecessityError("NECESSITY_AUTHORITY_CANNOT_BE_ESCALATED", self.authority)
        if self.evaluation_only is not True:
            raise NecessityError("NECESSITY_TEST_MUST_STAY_EVALUATION_ONLY", str(self.evaluation_only))
        for flag in ("creates_agents", "creates_task_network", "persists", "carries_routing"):
            if getattr(self, flag) is not False:
                raise NecessityError("NECESSITY_TEST_CANNOT_" + flag.upper(), str(getattr(self, flag)))
        return self

    def by_decision(self, decision: NecessityDecision) -> List[NecessityEvaluation]:
        return [e for e in self.evaluations if e.decision == decision]

    def necessary(self) -> List[NecessityEvaluation]:
        return self.by_decision(NecessityDecision.NECESSARY)

    def not_necessary(self) -> List[NecessityEvaluation]:
        return self.by_decision(NecessityDecision.NOT_NECESSARY)

    def blocked(self) -> List[NecessityEvaluation]:
        return self.by_decision(NecessityDecision.BLOCKED)

    def counts(self) -> Dict[str, int]:
        return {decision.value: len(self.by_decision(decision)) for decision in NecessityDecision}

    def reason_codes(self) -> List[str]:
        return [e.reason_code for e in self.evaluations]


class AgentNecessityTest:
    """Deterministic, fail-closed necessity evaluation. Stateless (only the registry it reads).

    Public surface: ``evaluate_compilation`` and ``evaluate_candidate``. There is deliberately NO
    API to create/register/authorize/execute an agent, to route, to mutate a TaskNetwork or to
    persist: ``test_agent_necessity.py`` asserts that by introspection.
    """

    AUTHORITY = NECESSITY_AUTHORITY

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self.cap_registry = capability_registry

    # ---------------------------------------------------------------- public API (evaluation) -- #
    def evaluate_compilation(
        self,
        compilation: ProblemCompilation,
        *,
        canonical_state: Any = None,
        expected_work_id: Optional[str] = None,
        expected_problem_id: Optional[str] = None,
        requested_budget: Optional[Dict[str, int]] = None,
        requested_model: Optional[Dict[str, Any]] = None,
        now: Optional[str] = None,
    ) -> AgentNecessityReport:
        """Evaluate EVERY candidate of a compilation. Never mutates anything."""
        work_id = compilation.work_id
        problem_id = compilation.problem_id
        evaluations = [
            self.evaluate_candidate(
                candidate, work_id=work_id, problem_id=problem_id,
                compilation=compilation, canonical_state=canonical_state,
                expected_work_id=expected_work_id, expected_problem_id=expected_problem_id,
                requested_budget=requested_budget, requested_model=requested_model, now=now,
            )
            for candidate in compilation.candidates
        ]
        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        report = AgentNecessityReport(
            report_id=_report_id(work_id, problem_id, [e.candidate_id for e in evaluations]),
            work_id=work_id, problem_id=problem_id, evaluations=evaluations, created_at=created,
            provenance=[
                f"AgentNecessityTest v{NECESSITY_VERSION} — {NECESSITY_AUTHORITY}; "
                "evaluates LOOP 4 candidates, creates nothing",
                f"evaluated {len(evaluations)} candidate(s) from compilation "
                f"{compilation.compilation_id}",
                "reuse-first: existing capability/EM/family/task/capability-contract/TaskNetwork/"
                "AgentGenome/pipeline were checked before any NECESSARY verdict",
                "deterministic Python (no model call, no routing, no persistence, no agent creation)",
            ],
        )
        return report

    def evaluate_candidate(
        self,
        candidate: ProblemCandidate,
        *,
        work_id: str = "",
        problem_id: str = "",
        compilation: Optional[ProblemCompilation] = None,
        canonical_state: Any = None,
        expected_work_id: Optional[str] = None,
        expected_problem_id: Optional[str] = None,
        requested_budget: Optional[Dict[str, int]] = None,
        requested_model: Optional[Dict[str, Any]] = None,
        now: Optional[str] = None,
    ) -> NecessityEvaluation:
        """Evaluate ONE candidate. Pure read-only derivation over existing structures.

        The candidate's own ``kind`` is authoritative here — there is deliberately NO way to
        relabel a candidate to steer it into the differentiated (NECESSARY) path.
        """
        ctx = _Context(
            kind=candidate.kind,
            work_id=work_id, problem_id=problem_id, compilation=compilation,
            canonical_state=canonical_state, cap_registry=self.cap_registry,
            requested_budget=requested_budget, requested_model=requested_model,
            expected_work_id=expected_work_id, expected_problem_id=expected_problem_id,
        )
        evaluation = _evaluate(candidate, ctx)
        evaluation.created_at = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        return evaluation


def _report_id(work_id: str, problem_id: str, candidate_ids: Sequence[str]) -> str:
    blob = f"{NECESSITY_VERSION}|{work_id}|{problem_id}|{'|'.join(candidate_ids)}"
    return "NEC-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12].upper()


# ----------------------------------------------------------------------------------------------- #
# Internals
# ----------------------------------------------------------------------------------------------- #
class _Context:
    """Everything the evaluation may READ (no writer, no store, no model, no agent layer)."""

    def __init__(self, *, kind: CandidateKind, work_id: str, problem_id: str,
                 compilation: Optional[ProblemCompilation], canonical_state: Any,
                 cap_registry: CapabilityRegistry, requested_budget: Optional[Dict[str, int]],
                 requested_model: Optional[Dict[str, Any]], expected_work_id: Optional[str],
                 expected_problem_id: Optional[str]) -> None:
        self.kind = kind
        self.work_id = work_id
        self.problem_id = problem_id
        self.compilation = compilation
        self.canonical = canonical_state
        self.cap_registry = cap_registry
        self.requested_budget = requested_budget or {}
        self.requested_model = requested_model or {}
        self.expected_work_id = expected_work_id
        self.expected_problem_id = expected_problem_id

    # ---- read-only views over EXISTING structures --------------------------------------------- #
    @property
    def problem(self) -> Any:
        return getattr(self.canonical, "problem", None)

    @property
    def structured(self) -> Any:
        problem = self.problem
        return getattr(problem, "structured_problem", None)

    @property
    def network_tasks(self) -> List[Any]:
        structured = self.structured
        network = getattr(structured, "task_network", None)
        return list(getattr(network, "tasks", None) or [])

    @property
    def task_ids(self) -> List[str]:
        return [t.task_id for t in self.network_tasks]

    @property
    def plan(self) -> Any:
        return getattr(self.canonical, "execution_plan", None)

    @property
    def plan_steps(self) -> List[Any]:
        return list(getattr(self.plan, "steps", None) or [])

    @property
    def evidence_ids(self) -> List[str]:
        return [str(e) for e in (getattr(self.canonical, "evidence_ids", None) or [])]

    @property
    def agent_ids(self) -> List[str]:
        network = getattr(self.canonical, "agent_network", None)
        records = getattr(network, "records", None) or []
        return [getattr(getattr(r, "genome", None), "agent_id", "") for r in records]

    @property
    def agent_identities(self) -> List[Any]:
        network = getattr(self.canonical, "agent_network", None)
        records = getattr(network, "records", None) or []
        return [getattr(r, "genome", None) for r in records]

    def declared_symbols(self) -> List[str]:
        structured = self.structured
        problem = self.problem
        values: List[str] = []
        for source in (getattr(structured, "variables", None), getattr(structured, "entities", None),
                       getattr(problem, "entities", None)):
            values += [str(v).strip() for v in (source or []) if str(v).strip()]
        return list(dict.fromkeys(values))

    def family_capabilities(self, owner: str) -> List[Any]:
        if not self.cap_registry:
            return []
        return [cap for cap in self.cap_registry._capabilities.values()
                if getattr(cap, "canonical_em", None) == owner]


def detect_escalation_intent(text: str) -> Optional[str]:
    """Public wrapper over the SAME escalation detectors the necessity test uses (one implementation).

    Returns the necessity reason code for the escalation the text attempts, or None. Used by later
    loops (LOOP 7 factory) so the rule is never duplicated.
    """
    text = text or ""
    if _SELF_VALIDATION_RE.search(text):
        return NECESSITY_SELF_VALIDATION
    if _AUTHORITY_ESCALATION_RE.search(text):
        return NECESSITY_AUTHORITY_ESCALATION
    if _ROUTING_ESCALATION_RE.search(text):
        return NECESSITY_ROUTING_ESCALATION
    return None


def _common(candidate: ProblemCandidate, ctx: _Context, decision: NecessityDecision,
            reason_code: str, **overrides: Any) -> NecessityEvaluation:
    data: Dict[str, Any] = dict(
        evaluation_id="EVAL-" + hashlib.sha256(
            f"{ctx.work_id}|{ctx.problem_id}|{candidate.candidate_id}|{reason_code}".encode("utf-8")
        ).hexdigest()[:12].upper(),
        candidate_id=candidate.candidate_id or "UNKNOWN",
        work_id=ctx.work_id, problem_id=ctx.problem_id, candidate_kind=ctx.kind,
        decision=decision, reason_code=reason_code,
        existing_capabilities_checked=sorted(
            cap.capability_id for cap in ctx.family_capabilities(candidate.cognitive_owner)
        ) if candidate.cognitive_owner else [],
        existing_agents_checked=list(ctx.agent_ids),
        existing_tasks_checked=list(ctx.task_ids),
        existing_families_checked=sorted(f.value for f in CognitiveFamily),
        owner=candidate.cognitive_owner,
        existing_em=candidate.cognitive_owner if candidate.cognitive_owner in CONSTITUTIONAL_EM else "",
        source=candidate.source,
        provenance=[f"candidate {candidate.candidate_id} of kind {ctx.kind.value} "
                    f"(source {candidate.source or 'n/a'})"],
    )
    data.update(overrides)
    evaluation = NecessityEvaluation(**data)
    return evaluation


def _escalation(candidate: ProblemCandidate) -> Optional[Tuple[str, str, Dict[str, Any]]]:
    """Deterministic escalation detection over the candidate's textual payload (fail closed)."""
    text = " ".join(str(x) for x in (candidate.reference, candidate.reason, candidate.expected_value,
                                     candidate.candidate_id) if x)
    discovery = candidate.discovery
    if discovery is not None:
        text += f" {discovery.statement} {discovery.reason} {discovery.proposed_predicate}"
    if _SELF_VALIDATION_RE.search(text):
        return (NECESSITY_SELF_VALIDATION, VALIDATION_SELF,
                {"validation_check": VALIDATION_SELF})
    if _AUTHORITY_ESCALATION_RE.search(text):
        return (NECESSITY_AUTHORITY_ESCALATION, AUTHORITY_ESCALATION_REQUESTED,
                {"authority_check": AUTHORITY_ESCALATION_REQUESTED})
    if _ROUTING_ESCALATION_RE.search(text):
        return (NECESSITY_ROUTING_ESCALATION, ROUTING_REQUESTED,
                {"routing_check": ROUTING_REQUESTED})
    return None


def _evidence_check(candidate: ProblemCandidate, ctx: _Context) -> Optional[NecessityEvaluation]:
    """Self-created evidence cannot satisfy an external evidence requirement (fail closed)."""
    declared = [str(e) for e in candidate.evidence_refs]
    if not declared:
        return None
    if ctx.canonical is None:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_EVIDENCE_UNVERIFIABLE,
                       detail=("evidence_refs declared but no canonical state was supplied: the "
                               "existence of the evidence cannot be verified"),
                       evidence_refs=declared)
    available = set(ctx.evidence_ids)
    fake = [e for e in declared if e not in available]
    if fake:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_EVIDENCE_MISSING,
                       detail=(f"declared evidence {fake} does not exist in the canonical evidence "
                               "registry: self-created evidence never satisfies a requirement"),
                       evidence_refs=declared)
    return None


def _resource_check(ctx: _Context) -> Optional[NecessityEvaluation]:
    """The unit must be expressible within the EXISTING budget/model contracts (no vendor pin)."""
    for key, value in (ctx.requested_budget or {}).items():
        if key not in HARD_BUDGET:
            return (NECESSITY_GOVERNANCE_INCOMPATIBLE,
                    {"resource_check": CHECK_UNKNOWN,
                     "detail": f"requested_budget declares unknown field '{key}'"})
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            return (NECESSITY_GOVERNANCE_INCOMPATIBLE,
                    {"resource_check": CHECK_UNKNOWN,
                     "detail": f"requested_budget['{key}'] is not an integer: {value!r}"})
        if numeric > int(HARD_BUDGET[key]):
            return (NECESSITY_RESOURCE_INFEASIBLE,
                    {"resource_check": RESOURCE_INFEASIBLE,
                     "detail": f"requested {key}={numeric} exceeds the declared ceiling "
                               f"{HARD_BUDGET[key]}"})
    if ctx.requested_model:
        try:
            ModelRequirement(**ctx.requested_model)
        except Exception as exc:                                # unknown field / bad value
            return (NECESSITY_GOVERNANCE_INCOMPATIBLE,
                    {"resource_check": CHECK_UNKNOWN,
                     "detail": f"requested_model is not expressible as an existing ModelRequirement: {exc}"})
    return None


def _target_coverage(target: str, ctx: _Context) -> Tuple[List[str], List[str]]:
    """Is the target already covered by an existing task / capability? (reuse-first)"""
    token = target.strip().lower()
    if not token:
        return [], []
    covered_tasks = [t.task_id for t in ctx.network_tasks
                     if token in f"{t.description} {' '.join(t.expected_outputs or [])}".lower()]
    covered_caps = [cap.capability_id for cap in (ctx.cap_registry._capabilities.values()
                                                  if ctx.cap_registry else [])
                    if token in f"{cap.description} {' '.join(cap.produces or [])}".lower()]
    return covered_tasks, covered_caps


def _evaluate(candidate: ProblemCandidate, ctx: _Context) -> NecessityEvaluation:
    """The deterministic decision procedure. Order matters and is fixed (auditable)."""
    # ---- N1 PROBLEM_SCOPED (cross-work / cross-problem contamination) -------------------------- #
    if ctx.expected_work_id and ctx.work_id and ctx.expected_work_id != ctx.work_id:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_CROSS_WORK,
                       detail=f"candidate belongs to work {ctx.work_id}, expected {ctx.expected_work_id}")
    if ctx.expected_problem_id and ctx.problem_id and ctx.expected_problem_id != ctx.problem_id:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_CROSS_PROBLEM,
                       detail=(f"candidate belongs to problem {ctx.problem_id}, "
                               f"expected {ctx.expected_problem_id}"))

    # ---- ESCALATION DETECTION (kind-independent, fail closed) ---------------------------------- #
    # A candidate can never TALK its way past the nucleus: an escalation request in ANY kind's
    # payload is a BLOCKED verdict with the specific code — never a benign NOT_NECESSARY.
    escalation = _escalation(candidate)
    if escalation is not None:
        code, _, overrides = escalation
        extras = dict(duplication_check=DUPLICATION_NONE, responsibility_boundary=BOUNDARY_UNKNOWN,
                      authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                      validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
        extras.update(overrides)
        return _common(candidate, ctx, NecessityDecision.BLOCKED, code,
                       detail="the candidate payload requests an escalation the unit can never hold",
                       **extras)

    # ---- REUSE-FIRST: kinds whose need is already satisfied by existing structures ------------- #
    if ctx.kind == CandidateKind.REQUIRED_CAPABILITY:
        cap = ctx.cap_registry.resolve(candidate.reference) if ctx.cap_registry else None
        if cap is None:
            return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_CAPABILITY_UNKNOWN,
                           detail=(f"'{candidate.reference}' is not a registered capability: an "
                                   "unknown capability can never justify a new unit"),
                           duplication_check=DUPLICATION_NONE,
                           responsibility_boundary=BOUNDARY_UNKNOWN,
                           authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                           validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_EXISTING_CAPABILITY_SUFFICIENT,
                       detail=(f"capability '{cap.capability_id}' already exists and is owned by "
                               f"{cap.canonical_em}"),
                       duplication_check=DUPLICATION_CAPABILITY,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="capability input_schema (existing)",
                       output_contract="capability output_schema (existing)",
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    if ctx.kind == CandidateKind.TASK:
        if candidate.task_ref not in ctx.task_ids:
            return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_TASK_NOT_IN_NETWORK,
                           detail=f"task '{candidate.task_ref}' is not in the ONE TaskNetwork",
                           duplication_check=DUPLICATION_NONE,
                           responsibility_boundary=BOUNDARY_UNKNOWN,
                           authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                           validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
        task = next(t for t in ctx.network_tasks if t.task_id == candidate.task_ref)
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_EXISTING_EM_SUFFICIENT,
                       detail=(f"the TaskNetwork already assigns '{task.task_id}' to {task.owner}"),
                       duplication_check=DUPLICATION_TASK,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="; ".join(task.dependencies or []) or "network entry task",
                       output_contract="; ".join(task.expected_outputs or []),
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    if ctx.kind == CandidateKind.SEGREGATION:
        members = [m for m in (candidate.dependencies or [])]
        missing = [m for m in members if m not in ctx.task_ids]
        if missing or not members:
            return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_TASK_NOT_IN_NETWORK,
                           detail=(f"segregation members {missing or 'none'} are not all in the ONE "
                                   "TaskNetwork: the input/output contract cannot be demonstrated"),
                           duplication_check=DUPLICATION_NONE,
                           responsibility_boundary=BOUNDARY_UNKNOWN,
                           authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                           validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
        owners = {t.owner for t in ctx.network_tasks if t.task_id in members}
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_EXISTING_EM_SUFFICIENT,
                       detail=(f"the cluster's tasks are already owned by {sorted(owners)}; the "
                               "existing EMs cover the responsibility"),
                       duplication_check=DUPLICATION_TASK,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="; ".join(members),
                       output_contract="; ".join(
                           o for t in ctx.network_tasks if t.task_id in members
                           for o in (t.expected_outputs or [])),
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    if ctx.kind == CandidateKind.DEPENDENCY:
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION,
                       detail="an ordering edge is not a differentiated cognitive responsibility",
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    if ctx.kind in (CandidateKind.KNOWLEDGE_GAP, CandidateKind.UNCERTAINTY):
        owner = candidate.cognitive_owner
        family = _owner_family(owner)
        caps = sorted(cap.capability_id for cap in ctx.family_capabilities(owner))
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_EXISTING_CAPABILITY_SUFFICIENT,
                       detail=(f"{ctx.kind.value} is covered by the existing {owner} capabilities "
                               f"{caps or ['(EM contract)']}"),
                       duplication_check=DUPLICATION_CAPABILITY,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="declared problem/structured input",
                       output_contract=candidate.reference or "declared knowledge/uncertainty output",
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_families_checked=sorted(
                           f.value for f in CognitiveFamily) if family else [])

    # ---- PREDICATE: the only kind that can carry a DIFFERENTIATED responsibility --------------- #
    if ctx.canonical is None:
        # Fail closed: without the canonical state the reuse-first checks (tasks/agents/evidence)
        # cannot be performed, so nothing may be declared NECESSARY by inference.
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_EVIDENCE_UNVERIFIABLE,
                       detail=("no canonical state was supplied: the reuse-first checks against the "
                               "TaskNetwork, the agent network and the evidence registry cannot be "
                               "performed"),
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    owner = candidate.cognitive_owner
    if not owner:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_OWNER_MISSING,
                       detail="the candidate declares no constitutional owner",
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
    family = _owner_family(owner)
    if family is None:
        return _common(candidate, ctx, NecessityDecision.BLOCKED,
                       NECESSITY_GOVERNANCE_INCOMPATIBLE,
                       detail=(f"'{owner}' has no CognitiveFamily; an emergent unit must map 1:1 "
                               "onto the constitutional nucleus"),
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)

    # ---- N5/N6 boundary + input/output contracts ---------------------------------------------- #
    boundary_text = (candidate.reference or "").strip()
    if not boundary_text:
        return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_BOUNDARY_UNCLEAR,
                       detail="the candidate declares no responsibility boundary",
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE)
    parts = _ARROW_SPLIT_RE.split(boundary_text, maxsplit=1)
    if len(parts) != 2:
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION,
                       detail=(f"'{boundary_text}' is not a condition->target responsibility, so it "
                               "carries no differentiated cognitive unit"),
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)

    condition_text, target_text = parts[0].strip(), parts[1].strip()
    symbols = ctx.declared_symbols()
    condition_symbols = [s for s in symbols if s.lower() in condition_text.lower()]
    target_symbols = [s for s in symbols if s.lower() in target_text.lower()]
    # reuse-first coverage of the target by EXISTING structures (computed once, used for N6 and N8)
    covered_tasks, covered_caps = _target_coverage(target_text, ctx)
    if not condition_symbols:
        return _common(candidate, ctx, NecessityDecision.BLOCKED,
                       NECESSITY_INPUT_CONTRACT_MISSING,
                       detail=(f"no declared variable/entity appears as the condition of "
                               f"'{boundary_text}' (declared: {symbols})"),
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       input_contract=condition_text,
                       output_contract=target_text,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)
    if not target_text:
        return _common(candidate, ctx, NecessityDecision.BLOCKED,
                       NECESSITY_OUTPUT_CONTRACT_MISSING,
                       detail=f"'{boundary_text}' declares no target result",
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       input_contract="; ".join(condition_symbols),
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)
    if not target_symbols:
        # N6: the output contract must be IDENTIFIABLE — either as a declared symbol OR as something
        # an existing structure already produces (a task output / a capability product). If neither
        # holds, the responsibility is ambiguous and the candidate is BLOCKED (never NECESSARY).
        if not covered_tasks and not covered_caps:
            return _common(candidate, ctx, NecessityDecision.BLOCKED, NECESSITY_BOUNDARY_UNCLEAR,
                           detail=(f"the target '{target_text}' is traceable neither to a declared "
                                   "symbol nor to any existing task/capability product: the output "
                                   "contract cannot be identified"),
                           duplication_check=DUPLICATION_NONE,
                           responsibility_boundary=BOUNDARY_UNKNOWN,
                           input_contract="; ".join(condition_symbols),
                           output_contract=target_text,
                           authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                           validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                           existing_em=owner)

    # ---- evidence (self-created evidence never satisfies) ------------------------------------- #
    evidence_verdict = _evidence_check(candidate, ctx)
    if evidence_verdict is not None:
        evidence_verdict.input_contract = "; ".join(condition_symbols)
        evidence_verdict.output_contract = target_text
        evidence_verdict.existing_em = owner
        return evidence_verdict

    # ---- resource / governance feasibility (existing contracts only) -------------------------- #
    resource_verdict = _resource_check(ctx)
    if resource_verdict is not None:
        code, overrides = resource_verdict
        extras = dict(duplication_check=DUPLICATION_NONE,
                      responsibility_boundary=BOUNDARY_DIFFERENTIATED,
                      input_contract="; ".join(condition_symbols),
                      output_contract=target_text,
                      authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                      validation_check=VALIDATION_EXTERNAL, existing_em=owner)
        extras.update(overrides)
        return _common(candidate, ctx, NecessityDecision.BLOCKED, code, **extras)

    # ---- N8 NO_DUPLICATION (task / agent / capability / EM) ----------------------------------- #
    if covered_tasks:
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY, NECESSITY_DUPLICATES_TASK,
                       detail=(f"the target '{target_text}' is already produced by task(s) "
                               f"{covered_tasks}"),
                       duplication_check=DUPLICATION_TASK,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="; ".join(condition_symbols), output_contract=target_text,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)
    for genome in ctx.agent_identities:
        identity = getattr(genome, "identity", None)
        if identity is None:
            continue
        same_family = getattr(identity, "cognitive_family", None) == family
        same_predicate = str(getattr(identity, "predicate", "")).lower() == target_text.lower()
        if same_family and same_predicate:
            return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                           NECESSITY_DUPLICATES_AGENT,
                           detail=(f"an agent with the same family/predicate already exists: "
                                   f"{genome.agent_id}"),
                           duplication_check=DUPLICATION_AGENT,
                           responsibility_boundary=BOUNDARY_DIFFERENTIATED,
                           input_contract="; ".join(condition_symbols), output_contract=target_text,
                           authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                           validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                           existing_em=owner)
    if covered_caps:
        return _common(candidate, ctx, NecessityDecision.NOT_NECESSARY,
                       NECESSITY_EXISTING_CAPABILITY_SUFFICIENT,
                       detail=f"capability(ies) {covered_caps} already cover '{target_text}'",
                       duplication_check=DUPLICATION_CAPABILITY,
                       responsibility_boundary=BOUNDARY_GENERIC,
                       input_contract="; ".join(condition_symbols), output_contract=target_text,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)

    # ---- N3 EXISTING_CAPABILITY_GAP + N14 COGNITIVE_VALUE ------------------------------------- #
    family_caps = ctx.family_capabilities(owner)
    family_cap_ids = sorted(cap.capability_id for cap in family_caps)
    if not family_caps:
        return _common(candidate, ctx, NecessityDecision.BLOCKED,
                       NECESSITY_INSUFFICIENT_COGNITIVE_DIFFERENTIATION,
                       detail=(f"the owning EM {owner} declares no capability at all: the gap cannot "
                               "be demonstrated against an existing capability"),
                       duplication_check=DUPLICATION_NONE,
                       responsibility_boundary=BOUNDARY_UNKNOWN,
                       input_contract="; ".join(condition_symbols), output_contract=target_text,
                       authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                       validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                       existing_em=owner)
    gap = (f"family {family.value} owner {owner} exposes only generic capabilities "
           f"{family_cap_ids}; none covers the specific condition->target '{boundary_text}'")

    # ---- NECESSARY: every mandatory criterion holds, with the full evidence record ------------- #
    return _common(candidate, ctx, NecessityDecision.NECESSARY,
                   NECESSARY_EMERGENT_UNIT_JUSTIFIED,
                   detail=(f"differentiated {family.value} responsibility '{boundary_text}' is not "
                           "covered by any existing task/capability/agent; the unit stays a PROPOSER "
                           "whose returns are validated externally by " + owner),
                   duplication_check=DUPLICATION_NONE,
                   responsibility_boundary=BOUNDARY_DIFFERENTIATED,
                   input_contract="; ".join(condition_symbols),
                   output_contract=target_text,
                   authority_check=AUTHORITY_PROPOSER_ONLY, routing_check=ROUTING_NONE,
                   validation_check=VALIDATION_EXTERNAL, resource_check=RESOURCE_FEASIBLE,
                   capability_gap_evidence=gap,
                   existing_em=owner,
                   evidence_refs=list(candidate.evidence_refs),
                   provenance=[f"candidate {candidate.candidate_id} of kind {ctx.kind.value} "
                               f"(source {candidate.source or 'n/a'})",
                               "reuse-first: no existing task/agent/capability covers the target",
                               f"gap evidence: {gap}"])


def _owner_family(owner: str) -> Optional[CognitiveFamily]:
    for family, mapped_owner in FAMILY_OWNER.items():
        if mapped_owner == owner:
            return family
    return None
