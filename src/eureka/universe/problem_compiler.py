"""EUREKA 5.1 — LOOP 4: ProblemCompiler — compilation ENRICHMENT, never an authority.

AUTHORITY CHAIN (UNCHANGED by this module — asserted by tests and by construction):

    ProblemModel -> [EM Core: orchestration/routing] -> Structurer (cognitive ownership of the
    problem representation) -> Existing Orchestrator -> TaskNetwork (ONE authority: EMStructurer)

``ProblemCompiler`` is a *capability of that compilation*. It READS the governed ProblemModel and
the Structurer's TaskNetwork/ExecutionPlan and emits TRACEABLE CANDIDATES for downstream stages
(Agent Necessity Test -> AgentFactory -> AgentRuntime, later loops). It is enrichment only:

  * NEVER creates or authorizes agents;
  * NEVER routes (Core keeps orchestration/routing);
  * NEVER builds a second TaskNetwork (the network is READ-ONLY here; a mutation attempt fails closed);
  * NEVER mutates canonical state and NEVER persists (no store, no file I/O);
  * NEVER validates, freezes or publishes (those remain Descriptor/Predictor/Publisher authority);
  * NEVER calls a model (deterministic Python derivation only).

REUSE-FIRST MAP (forensic result — no second data model was introduced):

    enrichment item        | existing structure reused                                    | new class?
    -----------------------|--------------------------------------------------------------|-----------
    task_candidates        | ``CognitiveTask`` (TaskNetwork) referenced by ``task_ref``     | no
    required_capabilities  | ``CapabilityContract.capability_id``/``canonical_em`` (registry)| no
    predicates             | compile-time SPEC grounded in declared relationships/variables  | no
    knowledge_gaps         | the declared ``unknowns`` / ``evidence_requirements``          | no
    dependencies           | the existing ``List[str]`` id convention (task/step/candidate) | no
    uncertainties          | the ``ReturnPackage.uncertainty`` vocabulary (LOOP 1)          | no
    segregation_candidates | ``SubproblemDiscovery`` (agent_genome, LOOP 1)                 | no
    cognitive ownership    | ``CONSTITUTIONAL_EM`` (8) + ``FAMILY_OWNER``                   | no
    candidate traceability | — (nothing existing carries {source, reason, expected_value,   | YES: minimal
                           |    coordination_cost, owner, uncertainty} for compile-time     | ``ProblemCandidate``
                           |    candidates; ``CandidateFinding``/``CandidatePrediction`` are |
                           |    EM *content* candidates, a different stage)                 |
    rejections             | — (no existing structure records a rejected candidate)         | YES: minimal
                           |                                                                | ``CandidateRejection``

``ProblemCandidate`` therefore carries NO payload of its own for kinds that already have one: it
references the existing representation (``task_ref`` -> CognitiveTask, ``reference`` ->
capability_id / declared text / family, ``discovery`` -> SubproblemDiscovery) and adds only the
traceability that the harness mandates. Predicates are SPECS (text + declared grounding), never
``PredictivePredicate`` objects: an AST/``mse``/VALIDATED status belongs to the Predictor and
fabricating one here would create a second predicate authority.

FINGERPRINT NOTE (declared decision, not a silent change): the compilation is attached to
``CanonicalWorkState.problem_compilation``, which is NOT part of ``canonical_state_fingerprint``'s
payload (``canonical_identity._payload``) nor of ``EMPublisher._freeze_signature`` — exactly like
``execution_plan`` and ``agent_network``. Compile-time planning artifacts therefore do not alter the
canonical content identity of existing works, and the pre-change fingerprints stay identical
(proven by ``test_problem_compiler.py`` against ``_scratch/loop4/PRE_CHANGE_FINGERPRINTS.json``).
"""
from __future__ import annotations

import datetime
import hashlib
import re
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_genome import CONSTITUTIONAL_EM, FAMILY_OWNER, CognitiveFamily, SubproblemDiscovery
from .capability_fabric import CapabilityRegistry
from .problem_model import ProblemModel, StructuredProblem

COMPILER_VERSION = "1.0"

#: Declared authority of this module. It is a CONSTANT, never a variable: nothing can promote it.
COMPILER_AUTHORITY = "ENRICHMENT_ONLY"
#: The ONE TaskNetwork authority. Declared here as a statement of fact, not as a claim.
TASK_NETWORK_AUTHORITY = "EMStructurer"

#: Rejection reason codes (fail-closed per candidate: never silently dropped).
CANDIDATE_WITHOUT_SOURCE = "CANDIDATE_WITHOUT_SOURCE"
UNGROUNDED_SOURCE = "UNGROUNDED_SOURCE"
CANDIDATE_WITHOUT_OWNER = "CANDIDATE_WITHOUT_OWNER"
UNAUTHORIZED_OWNER = "UNAUTHORIZED_OWNER"
TASK_REF_NOT_IN_NETWORK = "TASK_REF_NOT_IN_NETWORK"
UNKNOWN_DEPENDENCY_TARGET = "UNKNOWN_DEPENDENCY_TARGET"
UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
CAPABILITY_WITHOUT_COGNITIVE_OWNER = "CAPABILITY_WITHOUT_COGNITIVE_OWNER"
INVALID_PREDICATE = "INVALID_PREDICATE"
PREDICATE_UNGROUNDED = "PREDICATE_UNGROUNDED"
SEGREGATION_WITHOUT_DISCOVERY = "SEGREGATION_WITHOUT_DISCOVERY"
SEGREGATION_WITHOUT_FAMILY = "SEGREGATION_WITHOUT_FAMILY"
DISCOVERY_PAYLOAD_MISUSE = "DISCOVERY_PAYLOAD_MISUSE"
DUPLICATE_CANDIDATE = "DUPLICATE_CANDIDATE"

REJECTION_CODES: Tuple[str, ...] = (
    CANDIDATE_WITHOUT_SOURCE, UNGROUNDED_SOURCE, CANDIDATE_WITHOUT_OWNER, UNAUTHORIZED_OWNER,
    TASK_REF_NOT_IN_NETWORK, UNKNOWN_DEPENDENCY_TARGET, UNKNOWN_CAPABILITY,
    CAPABILITY_WITHOUT_COGNITIVE_OWNER, INVALID_PREDICATE, PREDICATE_UNGROUNDED,
    SEGREGATION_WITHOUT_DISCOVERY, SEGREGATION_WITHOUT_FAMILY, DISCOVERY_PAYLOAD_MISUSE,
    DUPLICATE_CANDIDATE,
)

#: id placeholder used while deriving; the fail-closed gate stamps the final deterministic id.
PENDING_ID = "PENDING"

#: grounded provenance pointer shape: ``root.path[i]`` (root ∈ problem | structured_problem | plan).
_SOURCE_RE = re.compile(r"^(problem|structured_problem|execution_plan)((?:\.\w+)*)\[(\d+)\]")

#: exact (non-fuzzy) rule: a candidate may carry an evidence id ONLY if that id is supplied by the
#: caller as really available. Absence of evidence is NEVER converted into evidence.
_UNCERTAINTY_PATTERN = "^(UNKNOWN|LOW|MEDIUM|HIGH)$"  # reused vocabulary (ReturnPackage, LOOP 1)


class ProblemCompilerError(Exception):
    """Fail-closed violation of the compiler's contract (authority, cross-work, mutation)."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}" if message else reason_code)


class CandidateKind(str, Enum):
    """The seven enrichment families mandated for LOOP 4."""

    PREDICATE = "PREDICATE"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"
    REQUIRED_CAPABILITY = "REQUIRED_CAPABILITY"
    TASK = "TASK"
    SEGREGATION = "SEGREGATION"
    DEPENDENCY = "DEPENDENCY"
    UNCERTAINTY = "UNCERTAINTY"


def _slug(text: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", (text or "").strip()).strip("-").upper()
    return (cleaned[:limit] or "EMPTY")


class ProblemCandidate(BaseModel):
    """A traceable compile-time candidate. It proposes; it never authorizes.

    ``source`` is a POINTER into an existing structure (e.g.
    ``structured_problem.task_network.tasks[2].owner``) — it is provenance, not evidence.
    ``reference``/``task_ref``/``discovery`` point AT the existing representation instead of
    re-modelling it (reuse-first).
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1)
    kind: CandidateKind
    #: provenance pointer into an EXISTING structure. Empty is allowed at construction so the
    #: fail-closed GATE can reject it observably (a candidate without provenance is never accepted).
    source: str = ""
    reason: str = Field(..., min_length=1)          # REQUIRED: why the candidate exists
    reference: str = ""
    task_ref: Optional[str] = None                  # REUSE: CognitiveTask.task_id (network stays authority)
    discovery: Optional[SubproblemDiscovery] = None  # REUSE (LOOP 1) for SEGREGATION candidates
    evidence_refs: List[str] = Field(default_factory=list)   # only really-available ids (never invented)
    expected_value: str = ""                        # "" = NOT_DECLARED (never fabricated)
    coordination_cost: str = "NOT_ESTIMATED"        # never a fabricated number
    cognitive_owner: str = ""                       # must be one of CONSTITUTIONAL_EM to be accepted
    dependencies: List[str] = Field(default_factory=list)    # existing id-list convention
    uncertainty: str = Field("UNKNOWN", pattern=_UNCERTAINTY_PATTERN)


class CandidateRejection(BaseModel):
    """A candidate the compiler refused to accept (fail-closed, always recorded)."""

    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(..., min_length=1)
    detail: str = ""
    kind: Optional[CandidateKind] = None
    source: str = ""


class ProblemCompilation(BaseModel):
    """The enrichment artifact: candidates + rejections. Never an authority, never a TaskNetwork."""

    model_config = ConfigDict(extra="forbid")

    compilation_id: str = Field(..., min_length=1)
    work_id: str = ""
    problem_id: str = ""
    compiler: str = "ProblemCompiler"
    compiler_version: str = COMPILER_VERSION
    authority: str = COMPILER_AUTHORITY
    task_network_authority: str = TASK_NETWORK_AUTHORITY
    enrichment_only: bool = True
    candidates: List[ProblemCandidate] = Field(default_factory=list)
    rejections: List[CandidateRejection] = Field(default_factory=list)
    #: READ-ONLY proof of what the compiler saw (never a task proposal of its own).
    task_network_snapshot: List[str] = Field(default_factory=list)
    available_evidence_ids: List[str] = Field(default_factory=list)
    created_at: str = ""
    provenance: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _enrichment_only_is_not_negotiable(self) -> "ProblemCompilation":
        """Authority escalation is impossible by construction (fail-closed, not by convention)."""
        if self.authority != COMPILER_AUTHORITY:
            raise ProblemCompilerError("COMPILER_AUTHORITY_CANNOT_BE_ESCALATED", self.authority)
        if self.task_network_authority != TASK_NETWORK_AUTHORITY:
            raise ProblemCompilerError("TASK_NETWORK_AUTHORITY_CANNOT_BE_REASSIGNED",
                                       self.task_network_authority)
        if self.enrichment_only is not True:
            raise ProblemCompilerError("COMPILER_MUST_STAY_ENRICHMENT_ONLY",
                                       str(self.enrichment_only))
        return self

    def by_kind(self, kind: CandidateKind) -> List[ProblemCandidate]:
        return [c for c in self.candidates if c.kind == kind]

    def counts(self) -> Dict[str, int]:
        """Deterministic count per kind (every kind present, even at 0)."""
        return {kind.value: sum(1 for c in self.candidates if c.kind == kind)
                for kind in CandidateKind}

    def candidate_ids(self) -> List[str]:
        return [c.candidate_id for c in self.candidates]

    def owners(self) -> List[str]:
        return sorted({c.cognitive_owner for c in self.candidates if c.cognitive_owner})

    def is_empty(self) -> bool:
        return not self.candidates


class ProblemCompiler:
    """Deterministic compilation enrichment. Stateless: the ONLY attribute is the registry it reads.

    NOTE (forensic guard): the public surface exposes exactly one operation, ``compile``. There is
    deliberately NO API to create/authorize an agent, to route, to add a task, to persist or to
    mutate canonical state — ``test_problem_compiler.py`` asserts that by introspection.
    """

    AUTHORITY = COMPILER_AUTHORITY
    TASK_NETWORK_AUTHORITY = TASK_NETWORK_AUTHORITY

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self.cap_registry = capability_registry

    # ------------------------------------------------------------------ public API (enrichment) #
    def compile(
        self,
        problem: ProblemModel,
        structured_problem: StructuredProblem,
        *,
        work_id: str = "",
        execution_plan: Any = None,
        available_evidence_ids: Iterable[str] = (),
        expected_work_id: Optional[str] = None,
        expected_problem_id: Optional[str] = None,
        now: Optional[str] = None,
    ) -> ProblemCompilation:
        """Enrich an ALREADY-COMPILED problem. Read-only; deterministic; fail-closed.

        Raises ``ProblemCompilerError`` on cross-work/cross-problem contamination, on a TaskNetwork
        mutation attempt, or on an unsupported task-network shape. Per-candidate contract
        violations do NOT raise: they are REJECTED and recorded (never silently dropped).
        """
        network = getattr(structured_problem, "task_network", None)
        if network is None or not hasattr(network, "tasks"):
            raise ProblemCompilerError("TASK_NETWORK_UNAVAILABLE",
                                       "the compiler enriches a TaskNetwork; none was supplied")

        problem_id = getattr(problem, "problem_id", "") or ""
        if expected_work_id and work_id and expected_work_id != work_id:
            raise ProblemCompilerError("CROSS_WORK_CONTAMINATION",
                                       f"{work_id} != {expected_work_id}")
        if expected_problem_id and problem_id and expected_problem_id != problem_id:
            raise ProblemCompilerError("CROSS_PROBLEM_CONTAMINATION",
                                       f"{problem_id} != {expected_problem_id}")

        evidence_ids = tuple(dict.fromkeys(str(e) for e in (available_evidence_ids or ()) if str(e)))
        tasks = list(network.tasks or [])
        network_before = network.model_dump(mode="json")

        judge = _Judge(problem, structured_problem, tasks, execution_plan, evidence_ids,
                       self.cap_registry)
        raw: List[Any] = []
        raw += judge.predicates()
        raw += judge.knowledge_gaps()
        raw += judge.required_capabilities()
        raw += judge.task_candidates()
        raw += judge.dependencies()
        raw += judge.segregations()
        raw += judge.uncertainties()

        accepted, rejections = judge.gate(raw)

        # HIDDEN-MUTATION GUARD: the network must be byte-identical after enrichment.
        if network.model_dump(mode="json") != network_before:
            raise ProblemCompilerError("TASK_NETWORK_MUTATION_ATTEMPT",
                                       "ProblemCompiler must never modify the TaskNetwork")

        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        compilation = ProblemCompilation(
            compilation_id=_compilation_id(work_id, problem_id, [t.task_id for t in tasks]),
            work_id=work_id,
            problem_id=problem_id,
            candidates=accepted,
            rejections=rejections,
            task_network_snapshot=[t.task_id for t in tasks],
            available_evidence_ids=list(evidence_ids),
            created_at=created,
            provenance=[
                f"ProblemCompiler v{COMPILER_VERSION} — {COMPILER_AUTHORITY}; "
                f"TaskNetwork authority remains {TASK_NETWORK_AUTHORITY}",
                f"read-only derivation over {len(tasks)} task(s); "
                f"{len(accepted)} candidate(s) accepted, {len(rejections)} rejected",
                "deterministic Python derivation (no model call, no new authority, no persistence)",
            ],
        )
        return compilation


def _compilation_id(work_id: str, problem_id: str, task_ids: Sequence[str]) -> str:
    """Deterministic identity (no uuid): same input -> same id (reproducibility)."""
    blob = f"{COMPILER_VERSION}|{work_id}|{problem_id}|{'|'.join(task_ids)}"
    return "COMP-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12].upper()


# ----------------------------------------------------------------------------------------------- #
# Deterministic derivation + candidate gate (private; NOT part of the compiler's public surface).
# ----------------------------------------------------------------------------------------------- #
class _Judge:
    """Derives candidates from EXISTING structures only and decides accept/reject per candidate."""

    def __init__(self, problem: ProblemModel, structured_problem: StructuredProblem,
                 tasks: List[Any], execution_plan: Any, evidence_ids: Sequence[str],
                 cap_registry: CapabilityRegistry) -> None:
        self.problem = problem
        self.structured = structured_problem
        self.tasks = tasks
        self.plan = execution_plan
        self.evidence_ids = tuple(evidence_ids)
        self.cap_registry = cap_registry
        self._task_ids = [t.task_id for t in tasks]
        self._symbols = {s.strip().lower() for s in
                         list(structured_problem.variables or []) +
                         list(structured_problem.entities or []) if s and s.strip()}

    # ---- kinds (order is the deterministic generation order) ---------------------------------- #
    def predicates(self) -> List[ProblemCandidate]:
        """PREDICATE = a condition->target SPEC grounded in a DECLARED relationship.

        Deliberately NOT a ``PredictivePredicate`` (no AST, no mse, no VALIDATED status): validating
        a predicate is the Predictor's authority. No relationship declared -> no predicate proposed
        (the compiler never invents one).
        """
        out: List[ProblemCandidate] = []
        for i, rel in enumerate(list(self.structured.relationships or [])):
            text = (rel or "").strip()
            source = f"structured_problem.relationships[{i}]"
            if not text:
                out.append(_rejected_placeholder(
                    CandidateKind.PREDICATE, source, INVALID_PREDICATE,
                    detail="empty relationship text cannot yield a predicate SPEC"))
                continue
            grounded = [s for s in self._symbols if s in text.lower()]
            cand = ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.PREDICATE, source=source,
                reason=("declared relationship suitable as a candidate predicate SPEC "
                        "(condition -> target); validation belongs to EM Predictor"),
                reference=text,
                cognitive_owner=FAMILY_OWNER[CognitiveFamily.PREDICTOR],
                evidence_refs=list(self._exact_evidence(text)),
                expected_value="",
                uncertainty="UNKNOWN",
            )
            if not grounded:
                out.append(_rejected_placeholder(
                    CandidateKind.PREDICATE, source, PREDICATE_UNGROUNDED,
                    detail=f"no declared variable/entity appears in '{text}'"))
                continue
            out.append(cand)
        return out

    def knowledge_gaps(self) -> List[ProblemCandidate]:
        """KNOWLEDGE_GAP = a declared unknown or an unmet evidence requirement (never invented)."""
        out: List[ProblemCandidate] = []
        sources: List[Tuple[str, str]] = []
        for i, u in enumerate(list(self.problem.unknowns or [])):
            sources.append((f"problem.unknowns[{i}]", u))
        for i, u in enumerate(list(self.structured.unknowns or [])):
            sources.append((f"structured_problem.unknowns[{i}]", u))
        for i, e in enumerate(list(self.problem.evidence_requirements or [])):
            sources.append((f"problem.evidence_requirements[{i}]", e))
        for i, e in enumerate(list(self.structured.evidence_requirements or [])):
            sources.append((f"structured_problem.evidence_requirements[{i}]", e))
        for source, text in sources:
            if not (text or "").strip():
                continue
            out.append(ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.KNOWLEDGE_GAP, source=source,
                reason=("knowledge declared missing at compile time; grounding is required and no "
                        "evidence is claimed here"),
                reference=text.strip(),
                cognitive_owner=FAMILY_OWNER[CognitiveFamily.DESCRIPTOR],
                evidence_refs=list(self._exact_evidence(text)),   # exact id match only
                expected_value="",
                coordination_cost="NOT_ESTIMATED",
                uncertainty="UNKNOWN",
            ))
        return out

    def required_capabilities(self) -> List[ProblemCandidate]:
        """REQUIRED_CAPABILITY = an EXISTING capability id (declared or already planned by Core).

        A capability that the registry cannot resolve is rejected (never invented); a capability
        without a constitutional cognitive owner is rejected (no orphan ownership).
        """
        out: List[ProblemCandidate] = []
        declared = [(f"problem.required_capabilities[{i}]", c)
                    for i, c in enumerate(list(self.problem.required_capabilities or []))]
        planned: List[Tuple[str, str]] = []
        for i, step in enumerate(list(getattr(self.plan, "steps", None) or [])):
            cap_id = getattr(step, "capability_id", None)
            if cap_id:
                planned.append((f"execution_plan.steps[{i}].capability_id", cap_id))
        for source, cap_id in declared + planned:
            cap_id = (cap_id or "").strip()
            if not cap_id:
                continue
            cap = self.cap_registry.resolve(cap_id) if self.cap_registry else None
            if cap is None:
                out.append(_rejected_placeholder(
                    CandidateKind.REQUIRED_CAPABILITY, source, UNKNOWN_CAPABILITY,
                    detail=f"'{cap_id}' is not a registered capability"))
                continue
            owner = cap.canonical_em or ""
            if owner not in CONSTITUTIONAL_EM:
                out.append(_rejected_placeholder(
                    CandidateKind.REQUIRED_CAPABILITY, source, CAPABILITY_WITHOUT_COGNITIVE_OWNER,
                    detail=f"'{cap_id}' has canonical_em={cap.canonical_em!r}"))
                continue
            out.append(ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.REQUIRED_CAPABILITY, source=source,
                reason=("capability required by the compilation; owner taken from the EXISTING "
                        "CapabilityContract (plan view only — routing stays with EM Core)"),
                reference=cap_id,
                expected_value="; ".join(cap.produces or []),
                cognitive_owner=owner,
                uncertainty="UNKNOWN",
            ))
        return out

    def task_candidates(self) -> List[ProblemCandidate]:
        """TASK = a READ-ONLY traceable view over the Structurer's CognitiveTasks (no new task)."""
        out: List[ProblemCandidate] = []
        for i, task in enumerate(self.tasks):
            out.append(ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.TASK,
                source=f"structured_problem.task_network.tasks[{i}]",
                reason=("task proposed by the Structurer's TaskNetwork (candidate view; the network "
                        "remains the ONE authority)"),
                reference=task.task_id, task_ref=task.task_id,
                cognitive_owner=task.owner or "",
                dependencies=list(task.dependencies or []),
                expected_value="; ".join(task.expected_outputs or []),
                uncertainty="UNKNOWN",
            ))
        return out

    def dependencies(self) -> List[ProblemCandidate]:
        """DEPENDENCY = an existing edge of the TaskNetwork, re-expressed with provenance.

        The ``dependencies`` field reuses the codebase's existing id-list convention (there is no
        second dependency model). An edge pointing outside the network fails closed.
        """
        out: List[ProblemCandidate] = []
        for i, task in enumerate(self.tasks):
            for dep in list(task.dependencies or []):
                source = f"structured_problem.task_network.tasks[{i}].dependencies"
                if dep not in self._task_ids:
                    out.append(_rejected_placeholder(
                        CandidateKind.DEPENDENCY, source, UNKNOWN_DEPENDENCY_TARGET,
                        detail=f"'{dep}' is not in the TaskNetwork (edge {task.task_id}->{dep})"))
                    continue
                owner = next((t.owner for t in self.tasks if t.task_id == dep), "") or ""
                out.append(ProblemCandidate(
                    candidate_id=PENDING_ID, kind=CandidateKind.DEPENDENCY, source=source,
                    reason="existing task-network dependency edge (ordering fact, not a proposal)",
                    reference=f"{task.task_id}->{dep}",
                    dependencies=[task.task_id, dep],
                    cognitive_owner=owner if owner in CONSTITUTIONAL_EM else "",
                    uncertainty="UNKNOWN",
                ))
        return out

    def segregations(self) -> List[ProblemCandidate]:
        """SEGREGATION = a same-family cluster of tasks with NO direct dependency edge between them.

        The payload REUSES ``SubproblemDiscovery`` (LOOP 1), so a compile-time segregation candidate
        and a runtime-discovered subproblem share ONE representation. Still a candidate: it never
        creates an agent (that is a later, separately-gated loop).
        """
        out: List[ProblemCandidate] = []
        for family in CognitiveFamily:                     # enum order -> deterministic
            owner = FAMILY_OWNER[family]
            members = [t.task_id for t in self.tasks if t.owner == owner]
            if len(members) < 2:
                continue
            if self._has_direct_edge(members):
                continue
            discovery = SubproblemDiscovery(
                statement=(f"{len(members)} independent {family.value} task(s) "
                           f"({', '.join(members)}) could be owned by a dedicated agent"),
                proposed_predicate="",
                proposed_family=family,
                reason=("tasks share one cognitive family and have no direct dependency edge "
                        "between them (structural segregation signal)"),
            )
            out.append(ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.SEGREGATION,
                source="structured_problem.task_network.tasks[].owner",
                reason=discovery.reason,
                reference=family.value,
                discovery=discovery,
                dependencies=list(members),
                cognitive_owner=owner,
                coordination_cost="NOT_ESTIMATED",
                uncertainty="UNKNOWN",
            ))
        return out

    def uncertainties(self) -> List[ProblemCandidate]:
        """UNCERTAINTY = declared risk that is NOT quantified at compile time.

        Quantified uncertainty stays ``PredictiveUncertainty`` (EM Predictor). Declared unknowns are
        already carried by KNOWLEDGE_GAP candidates, so this kind reads a DIFFERENT source
        (``problem.risk``) and never double-counts them.
        """
        out: List[ProblemCandidate] = []
        risk = (getattr(self.problem, "risk", None) or "").strip()
        if risk:
            out.append(ProblemCandidate(
                candidate_id=PENDING_ID, kind=CandidateKind.UNCERTAINTY, source="problem.risk",
                reason=("risk declared at compile time but not quantified; quantification is "
                        "EM Predictor's authority (PredictiveUncertainty), never the compiler's"),
                reference=risk,
                cognitive_owner=FAMILY_OWNER[CognitiveFamily.PREDICTOR],
                uncertainty="UNKNOWN",
                coordination_cost="NOT_ESTIMATED",
            ))
        return out

    # ---- helpers ------------------------------------------------------------------------------ #
    def _has_direct_edge(self, members: Sequence[str]) -> bool:
        ids = set(members)
        for task in self.tasks:
            if task.task_id not in ids:
                continue
            if any(dep in ids for dep in (task.dependencies or [])):
                return True
        return False

    def _exact_evidence(self, text: str) -> Tuple[str, ...]:
        """Exact (never fuzzy) evidence binding: the text IS an available evidence id."""
        stripped = (text or "").strip()
        return (stripped,) if stripped and stripped in self.evidence_ids else ()

    # ---- the fail-closed gate ----------------------------------------------------------------- #
    def gate(self, raw: List[Any]) -> Tuple[List[ProblemCandidate], List[CandidateRejection]]:
        """Accept/reject every candidate, deduplicate, and stamp deterministic ids.

        Rejections are never silent. Duplicates keep the FIRST occurrence (the convention already
        used by ``orchestrator._dedup_execution_steps``) and are recorded as rejections.
        """
        accepted: List[ProblemCandidate] = []
        rejections: List[CandidateRejection] = []
        seen: Dict[Tuple[str, str, str], str] = {}

        for cand in raw:
            if isinstance(cand, _Placeholder):
                rejections.append(CandidateRejection(
                    reason_code=cand.reason_code, detail=cand.detail, kind=cand.kind,
                    source=cand.source))
                continue
            problem_code, detail = self._contract_violation(cand)
            if problem_code:
                rejections.append(CandidateRejection(reason_code=problem_code, detail=detail,
                                                     kind=cand.kind, source=cand.source))
                continue

            key = (cand.kind.value, cand.reference, cand.task_ref or "")
            if key in seen:
                rejections.append(CandidateRejection(
                    reason_code=DUPLICATE_CANDIDATE,
                    detail=f"duplicate of {seen[key]} (kind={cand.kind.value}, ref='{cand.reference}')",
                    kind=cand.kind, source=cand.source))
                continue
            if cand.kind == CandidateKind.SEGREGATION and cand.discovery is None:
                rejections.append(CandidateRejection(
                    reason_code=SEGREGATION_WITHOUT_DISCOVERY, kind=cand.kind, source=cand.source,
                    detail="a segregation candidate must reuse SubproblemDiscovery"))
                continue
            if cand.kind != CandidateKind.SEGREGATION and cand.discovery is not None:
                rejections.append(CandidateRejection(
                    reason_code=DISCOVERY_PAYLOAD_MISUSE, kind=cand.kind, source=cand.source,
                    detail="SubproblemDiscovery payload is reserved for SEGREGATION candidates"))
                continue

            cand.candidate_id = f"CAND-{cand.kind.value}-{len(accepted):02d}-{_slug(cand.reference or cand.source)}"
            seen[key] = cand.candidate_id
            accepted.append(cand)

        return accepted, rejections

    def _contract_violation(self, cand: ProblemCandidate) -> Tuple[str, str]:
        source = (cand.source or "").strip()
        if not source:
            return CANDIDATE_WITHOUT_SOURCE, "a candidate must point at the structure it derives from"
        if not self._source_resolves(source):
            return UNGROUNDED_SOURCE, f"'{source}' does not resolve to an existing element"
        if cand.task_ref is not None and cand.task_ref not in self._task_ids:
            return TASK_REF_NOT_IN_NETWORK, f"'{cand.task_ref}' is not in the TaskNetwork"
        if cand.kind == CandidateKind.DEPENDENCY:
            # a dependency is only meaningful if BOTH ends exist in the ONE TaskNetwork.
            ends = [p for p in (cand.reference or "").split("->") if p] or list(cand.dependencies)
            missing = [t for t in ends if t not in self._task_ids]
            if len(ends) != 2 or missing:
                return UNKNOWN_DEPENDENCY_TARGET, (
                    f"dependency '{cand.reference}' does not resolve to two tasks of the "
                    f"TaskNetwork (missing: {missing or 'malformed edge'})")
        owner = (cand.cognitive_owner or "").strip()
        if not owner:
            return CANDIDATE_WITHOUT_OWNER, f"candidate {cand.candidate_id} declares no cognitive owner"
        if owner not in CONSTITUTIONAL_EM:
            return UNAUTHORIZED_OWNER, f"'{owner}' is not one of the 8 constitutional EMs"
        if cand.kind == CandidateKind.SEGREGATION and cand.discovery is not None:
            family = cand.discovery.proposed_family
            if family is None:
                return SEGREGATION_WITHOUT_FAMILY, "segregation candidate declares no cognitive family"
            if FAMILY_OWNER[family] != owner:
                return UNAUTHORIZED_OWNER, f"family {family.value} is owned by {FAMILY_OWNER[family]}"
        return "", ""

    def _source_resolves(self, source: str) -> bool:
        """Ground a ``root.path[i]`` provenance pointer against the REAL objects (never trust it).

        A pointer without an index carries nothing to verify (accepted); an indexed pointer must
        resolve to an existing element, otherwise the candidate is UNGROUNDED (fail closed).
        """
        match = _SOURCE_RE.match(source or "")
        if not match:
            return True
        root, path, index = match.group(1), match.group(2), int(match.group(3))
        obj: Any = {"problem": self.problem, "structured_problem": self.structured,
                    "execution_plan": self.plan}.get(root)
        for part in [p for p in (path or "").split(".") if p]:
            obj = getattr(obj, part, None)
            if obj is None:
                return False
        try:
            return index < len(obj)
        except TypeError:
            return False


class _Placeholder:
    """An already-known rejection (built during derivation, materialised by the gate)."""

    __slots__ = ("kind", "source", "reason_code", "detail")

    def __init__(self, kind: CandidateKind, source: str, reason_code: str,
                 detail: str = "") -> None:
        self.kind = kind
        self.source = source
        self.reason_code = reason_code
        self.detail = detail


def _rejected_placeholder(kind: CandidateKind, source: str, reason_code: str,
                          detail: str = "") -> Any:
    return _Placeholder(kind, source, reason_code, detail)
