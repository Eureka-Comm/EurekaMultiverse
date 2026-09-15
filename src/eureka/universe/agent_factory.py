"""EUREKA 5.1 — LOOP 7: AGENT FACTORY PREREQUISITES — RegistrationRequest preparation.

THE BOUNDARY THIS LOOP PROVES (and nothing beyond it):

    ACCEPTED CANDIDATE -> AGENT GENOME PROPOSAL -> ACCEPTANCE / GOVERNANCE ->
    REGISTRATION REQUEST -> HARD STOP

The operation ``RegistrationRequest -> AgentRegistry.register()`` belongs to a FUTURE loop. LOOP 7
never registers, activates or executes anything, never selects a provider, never calls a model and
never mutates any state.

WHAT THE FACTORY IS
-------------------
A PREPARER / VALIDATOR of a ``RegistrationRequest``: it can build one, validate one, reject one and
produce validation evidence. It is NOT a registry, NOT a runtime, NOT a model provider and NOT an
execution authority:

  * no ``AgentRegistry.register/activate/...`` (the registry remains the ONE registration authority);
  * no ``AgentRuntime`` invocation;
  * no model/provider call (no vendor selection, no network);
  * no TaskNetwork mutation and no CanonicalWorkState mutation (verified by a fingerprint guard);
  * no new store: a request is a DOMAIN OBJECT; when the pipeline keeps it, it lives inside
    ``CanonicalWorkState`` and is persisted by the EXISTING WorkStore (no AgentStore /
    RegistrationStore / FactoryStore).

REUSE (no second authority, no duplicated validator)
----------------------------------------------------
  * ``AgentGenome`` / ``AgentIdentity`` / ``TaskEnvelope`` / ``ResourceBudget`` / ``AgentDependency``
    (LOOP 1) — the ONE canonical agent contract, embedded by reference;
  * ``validate_dependencies`` + ``detect_cycle`` (LOOP 1) for the dependency gate;
  * ``FAMILY_OWNER`` + ``CONSTITUTIONAL_EM`` for ownership/role validation;
  * ``ReturnPackage``'s CANDIDATE-only rule (LOOP 1) for the output contract;
  * ``AgentGenomeProposal`` (LOOP 6) as the input — a proposal is NOT a request;
  * LOOP 5's necessity verdict is READ, never recomputed (no second Necessity Engine);
  * a verdict that is not NECESSARY (NOT_NECESSARY / BLOCKED) can never become a request.

F11 INTERACTION (declared, not repaired)
----------------------------------------
The request identity is a CONTENT reference computed over the proposal/genome with volatile metadata
(``created_at``, ``frozen``) recursively excluded, so LOOP 7 does NOT depend on the (unrepaired)
``AgentGenome.hash()`` semantics for its own determinism. There IS one fail-closed interaction: the
canonical ``TaskEnvelope.assert_matches`` compares the envelope's stored ``genome_hash`` with
``AgentGenome.hash()``, which includes ``created_at``; a genome reconstructed with identical content
but a new timestamp is therefore treated as STALE and REJECTED (it can never be silently accepted).
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_genome import (CONSTITUTIONAL_EM, FAMILY_OWNER, HARD_BUDGET, AgentContractError,
                           AgentDependency, AgentGenome, AgentIdentity, NetworkRole, ResourceBudget,
                           TaskEnvelope, detect_cycle, validate_dependencies)
from .agent_genome_proposal import (PROVIDER_SELECTION_DEFERRED, AgentGenomeProposal,
                                    GenomeProposalStatus, existing_responsibility_coverage)
from .agent_necessity import NecessityDecision, detect_escalation_intent
from .capability_fabric import CapabilityRegistry
from .canonical_identity import canonical_state_fingerprint
from .problem_compiler import CandidateKind, ProblemCandidate, ProblemCompilation

REQUEST_VERSION = "1.0"

#: Declared authority of this module. A CONSTANT — the factory concedes no authority.
FACTORY_AUTHORITY = "REGISTRATION_REQUEST_ONLY"
#: The canonical genome authority, unchanged.
GENOME_AUTHORITY = "PROPOSER"
#: The only admissible agent output status.
OUTPUT_STATUS_CANDIDATE = "CANDIDATE"
#: Request status: a VALIDATED request is still only a REQUEST (never a registration).
STATUS_VALIDATED = "VALIDATED"
STATUS_REJECTED = "REJECTED"

#: Keys an attacker would use to smuggle an operation into the factory call surface.
_REGISTRY_KEYS = ("register", "registration", "activate", "activation", "supersede", "retire",
                  "agent_registry")
_RUNTIME_KEYS = ("execute", "execution", "runtime", "invoke", "run", "agent_runtime")
_TASKNETWORK_KEYS = ("task_network", "tasks", "execution_plan", "next_owner", "routing")
_CANONICAL_KEYS = ("canonical_state", "replace_state", "work_state", "agent_network")
_AUTHORITY_KEYS = ("authority", "authority_scope", "owner", "validator", "publisher", "router",
                   "promote", "bypass_governance", "policy")
_PROVIDER_KEYS = ("provider", "model", "vendor", "api_key", "endpoint", "base_url", "url",
                  "allow_fallback")
#: Vendor-specific keys that must never appear in a DECLARED requirement (allow_fallback and
#: capability_class are legitimate fields of the canonical ModelRequirement contract).
_VENDOR_KEYS = ("provider", "model", "vendor", "api_key", "endpoint", "base_url", "url")
_VOLATILE_KEYS = frozenset({"created_at", "frozen"})
#: Matches a DECLARED authority scope wherever it appears (JSON or plain text).
_AUTHORITY_SCOPE_RE = re.compile(r'authority_scope["\s:=]+([A-Za-z_]+)')
#: Matches the LEGITIMATE contract statement (authority_scope = PROPOSER) for neutralisation.
_NEUTRAL_AUTHORITY_SCOPE_RE = re.compile(r'authority_scope["\s:=]+PROPOSER', re.IGNORECASE)

# ----------------------------------------------------------------------------------------------- #
# Reason codes (specific; never a generic exception where a specific code is possible)
# ----------------------------------------------------------------------------------------------- #
REQUEST_FROM_VALID_PROPOSAL = "REQUEST_FROM_VALID_PROPOSAL"
REQUEST_PROPOSAL_MISSING = "REQUEST_PROPOSAL_MISSING"
REQUEST_PROPOSAL_NOT_PROPOSED = "REQUEST_PROPOSAL_NOT_PROPOSED"
REQUEST_CANDIDATE_MISSING = "REQUEST_CANDIDATE_MISSING"
REQUEST_CANDIDATE_NOT_NECESSARY = "REQUEST_CANDIDATE_NOT_NECESSARY"
REQUEST_CANDIDATE_BLOCKED = "REQUEST_CANDIDATE_BLOCKED"
REQUEST_CANDIDATE_MISMATCH = "REQUEST_CANDIDATE_MISMATCH"
REQUEST_CROSS_WORK = "REQUEST_CROSS_WORK"
REQUEST_CROSS_PROBLEM = "REQUEST_CROSS_PROBLEM"
REQUEST_IDENTITY_MISMATCH = "REQUEST_IDENTITY_MISMATCH"
REQUEST_IDENTITY_DUPLICATE = "REQUEST_IDENTITY_DUPLICATE"
REQUEST_RESPONSIBILITY_DUPLICATE = "REQUEST_RESPONSIBILITY_DUPLICATE"
REQUEST_FAMILY_MISMATCH = "REQUEST_FAMILY_MISMATCH"
REQUEST_NETWORK_ROLE_INVALID = "REQUEST_NETWORK_ROLE_INVALID"
REQUEST_AUTHORITY_ESCALATION = "REQUEST_AUTHORITY_ESCALATION"
REQUEST_HIDDEN_AUTHORITY = "REQUEST_HIDDEN_AUTHORITY"
REQUEST_OUTPUT_NOT_CANDIDATE = "REQUEST_OUTPUT_NOT_CANDIDATE"
REQUEST_PROVIDER_PIN = "REQUEST_PROVIDER_PIN"
REQUEST_PROVIDER_SELECTION_NOT_DEFERRED = "REQUEST_PROVIDER_SELECTION_NOT_DEFERRED"
REQUEST_PROVIDER_FALLBACK_ESCALATION = "REQUEST_PROVIDER_FALLBACK_ESCALATION"
REQUEST_INPUT_WILDCARD = "REQUEST_INPUT_WILDCARD"
REQUEST_INPUT_UNEXPLICIT = "REQUEST_INPUT_UNEXPLICIT"
REQUEST_TOOL_WILDCARD = "REQUEST_TOOL_WILDCARD"
REQUEST_TOOL_UNEXPLICIT = "REQUEST_TOOL_UNEXPLICIT"
REQUEST_BUDGET_ESCALATION = "REQUEST_BUDGET_ESCALATION"
REQUEST_BUDGET_INVALID = "REQUEST_BUDGET_INVALID"
REQUEST_DEPENDENCY_INVALID = "REQUEST_DEPENDENCY_INVALID"
REQUEST_DEPENDENCY_MISSING = "REQUEST_DEPENDENCY_MISSING"
REQUEST_DEPENDENCY_CROSS_WORK = "REQUEST_DEPENDENCY_CROSS_WORK"
REQUEST_DEPENDENCY_CROSS_PROBLEM = "REQUEST_DEPENDENCY_CROSS_PROBLEM"
REQUEST_DEPENDENCY_CYCLE = "REQUEST_DEPENDENCY_CYCLE"
REQUEST_DEPENDENCY_RETIRED = "REQUEST_DEPENDENCY_RETIRED"
REQUEST_PROVENANCE_MISSING = "REQUEST_PROVENANCE_MISSING"
REQUEST_EVIDENCE_FABRICATED = "REQUEST_EVIDENCE_FABRICATED"
REQUEST_STALE_PROPOSAL = "REQUEST_STALE_PROPOSAL"
REQUEST_STALE_GENOME = "REQUEST_STALE_GENOME"
REQUEST_NONDETERMINISTIC = "REQUEST_NONDETERMINISTIC"
REQUEST_MALFORMED_GENOME = "REQUEST_MALFORMED_GENOME"
REQUEST_REGISTRY_REQUESTED = "REQUEST_REGISTRY_REQUESTED"
REQUEST_RUNTIME_REQUESTED = "REQUEST_RUNTIME_REQUESTED"
REQUEST_TASKNETWORK_MUTATION = "REQUEST_TASKNETWORK_MUTATION"
REQUEST_CANONICAL_REPLACEMENT = "REQUEST_CANONICAL_REPLACEMENT"
REQUEST_UNKNOWN_OPTION = "REQUEST_UNKNOWN_OPTION"
REQUEST_DUPLICATE_INCOMPATIBLE = "REQUEST_DUPLICATE_INCOMPATIBLE"
REQUEST_MUTATION_DETECTED = "REQUEST_MUTATION_DETECTED"

REASON_CODES: Tuple[str, ...] = (
    REQUEST_FROM_VALID_PROPOSAL, REQUEST_PROPOSAL_MISSING, REQUEST_PROPOSAL_NOT_PROPOSED,
    REQUEST_CANDIDATE_MISSING, REQUEST_CANDIDATE_NOT_NECESSARY, REQUEST_CANDIDATE_BLOCKED,
    REQUEST_CANDIDATE_MISMATCH, REQUEST_CROSS_WORK, REQUEST_CROSS_PROBLEM,
    REQUEST_IDENTITY_MISMATCH, REQUEST_IDENTITY_DUPLICATE, REQUEST_RESPONSIBILITY_DUPLICATE,
    REQUEST_FAMILY_MISMATCH, REQUEST_NETWORK_ROLE_INVALID, REQUEST_AUTHORITY_ESCALATION,
    REQUEST_HIDDEN_AUTHORITY, REQUEST_OUTPUT_NOT_CANDIDATE, REQUEST_PROVIDER_PIN,
    REQUEST_PROVIDER_SELECTION_NOT_DEFERRED, REQUEST_PROVIDER_FALLBACK_ESCALATION,
    REQUEST_INPUT_WILDCARD, REQUEST_INPUT_UNEXPLICIT, REQUEST_TOOL_WILDCARD,
    REQUEST_TOOL_UNEXPLICIT, REQUEST_BUDGET_ESCALATION, REQUEST_BUDGET_INVALID,
    REQUEST_DEPENDENCY_INVALID, REQUEST_DEPENDENCY_MISSING, REQUEST_DEPENDENCY_CROSS_WORK,
    REQUEST_DEPENDENCY_CROSS_PROBLEM, REQUEST_DEPENDENCY_CYCLE, REQUEST_DEPENDENCY_RETIRED,
    REQUEST_PROVENANCE_MISSING, REQUEST_EVIDENCE_FABRICATED, REQUEST_STALE_PROPOSAL,
    REQUEST_STALE_GENOME, REQUEST_NONDETERMINISTIC, REQUEST_MALFORMED_GENOME,
    REQUEST_REGISTRY_REQUESTED, REQUEST_RUNTIME_REQUESTED, REQUEST_TASKNETWORK_MUTATION,
    REQUEST_CANONICAL_REPLACEMENT, REQUEST_UNKNOWN_OPTION, REQUEST_DUPLICATE_INCOMPATIBLE,
    REQUEST_MUTATION_DETECTED,
)


class FactoryError(Exception):
    """Fail-closed contract violation of the factory API itself (misuse, not a verdict)."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}" if message else reason_code)


class RegistrationRequestStatus(str, Enum):
    VALIDATED = STATUS_VALIDATED
    REJECTED = STATUS_REJECTED


class RegistrationRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(..., min_length=1)
    detail: str = ""


class RegistrationRequest(BaseModel):
    """A FORMAL REQUEST to register a proposed emergent unit. NOT a registration.

    Distinct from ``AgentGenomeProposal`` (which expresses a proposal) and from a registered agent
    (which belongs to the AgentRegistry and does not exist at this point in the pipeline).
    """

    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., min_length=1)
    request_version: str = REQUEST_VERSION
    authority: str = FACTORY_AUTHORITY
    #: Declared invariants (validated below — a request cannot claim otherwise).
    request_only: bool = True
    registers_agents: bool = False
    activates_agents: bool = False
    executes_agents: bool = False
    selects_provider: bool = False
    mutates_task_network: bool = False
    mutates_canonical_state: bool = False
    persists_itself: bool = False
    provider_selection: str = PROVIDER_SELECTION_DEFERRED

    status: RegistrationRequestStatus = RegistrationRequestStatus.REJECTED

    # ---- traceability (proposal -> request, candidate -> request) ------------------------------ #
    proposal_id: str = ""
    candidate_id: str = ""
    candidate_kind: Optional[CandidateKind] = None
    agent_id: str = ""
    work_id: str = ""
    problem_id: str = ""
    evaluation_id: str = ""
    necessity_decision: str = ""
    necessity_reason_code: str = ""
    cognitive_owner: str = ""
    cognitive_family: str = ""
    network_role: str = ""
    authority_scope: str = ""
    source_reference: str = ""

    # ---- content references (deterministic; volatile metadata excluded) ------------------------ #
    genome_content_reference: str = ""
    proposal_content_reference: str = ""
    genome_envelope_hash: str = ""

    # ---- the contracts carried forward (by reference to the canonical objects) ----------------- #
    input_contract: Optional[TaskEnvelope] = None
    output_contract: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[AgentDependency] = Field(default_factory=list)
    resource_budget: Optional[ResourceBudget] = None
    model_requirement: Dict[str, Any] = Field(default_factory=dict)
    evidence_refs: List[str] = Field(default_factory=list)

    validation_checks: List[str] = Field(default_factory=list)
    rejections: List[RegistrationRejection] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _request_invariants(self) -> "RegistrationRequest":
        if self.authority != FACTORY_AUTHORITY:
            raise FactoryError("REQUEST_AUTHORITY_CANNOT_BE_ESCALATED", self.authority)
        for flag in ("request_only", "registers_agents", "activates_agents", "executes_agents",
                     "selects_provider", "mutates_task_network", "mutates_canonical_state",
                     "persists_itself"):
            expected = True if flag == "request_only" else False
            if getattr(self, flag) is not expected:
                raise FactoryError("REQUEST_CANNOT_" + flag.upper(), str(getattr(self, flag)))
        if self.provider_selection != PROVIDER_SELECTION_DEFERRED:
            raise FactoryError(REQUEST_PROVIDER_SELECTION_NOT_DEFERRED, self.provider_selection)

        if self.status is RegistrationRequestStatus.VALIDATED:
            if self.rejections:
                raise FactoryError("VALIDATED_REQUEST_WITH_REJECTIONS", self.request_id)
            missing = [name for name in ("proposal_id", "candidate_id", "agent_id", "work_id",
                                         "problem_id", "genome_content_reference",
                                         "proposal_content_reference", "genome_envelope_hash")
                       if not getattr(self, name)]
            if missing:
                raise FactoryError("VALIDATED_REQUEST_WITHOUT_TRACEABILITY", ",".join(missing))
            if self.authority_scope != GENOME_AUTHORITY:
                raise FactoryError(REQUEST_AUTHORITY_ESCALATION, self.authority_scope)
            if self.output_contract.get("properties", {}).get("validation_status", {}).get("const") \
                    != OUTPUT_STATUS_CANDIDATE:
                raise FactoryError(REQUEST_OUTPUT_NOT_CANDIDATE, "validation_status")
            if self.input_contract is None:
                raise FactoryError("VALIDATED_REQUEST_WITHOUT_INPUT_CONTRACT", self.request_id)
            if not self.validation_checks:
                raise FactoryError("VALIDATED_REQUEST_WITHOUT_CHECKS", self.request_id)
        else:
            if not self.rejections:
                raise FactoryError("REJECTED_REQUEST_WITHOUT_REASON", self.request_id)
        return self

    # ---- read-only helpers -------------------------------------------------------------------- #
    def is_validated(self) -> bool:
        return self.status is RegistrationRequestStatus.VALIDATED

    def rejection_codes(self) -> List[str]:
        return [r.reason_code for r in self.rejections]

    def traceability(self) -> Dict[str, str]:
        """Everything needed to reconstruct WHERE this request came from (never fabricated)."""
        return {
            "proposal_id": self.proposal_id, "candidate_id": self.candidate_id,
            "agent_id": self.agent_id, "work_id": self.work_id, "problem_id": self.problem_id,
            "evaluation_id": self.evaluation_id, "necessity_decision": self.necessity_decision,
            "necessity_reason_code": self.necessity_reason_code, "source_reference": self.source_reference,
            "genome_content_reference": self.genome_content_reference,
            "proposal_content_reference": self.proposal_content_reference,
        }


class AgentFactory:
    """PREPARER / VALIDATOR of ``RegistrationRequest`` objects. Stateless, mutation-free.

    Public surface: ``prepare_registration_request`` and ``validate_registration_request``. There is
    deliberately NO ``register``/``create_agent``/``execute``/``activate`` method: registration is a
    future loop's operation.
    """

    AUTHORITY = FACTORY_AUTHORITY
    GENOME_AUTHORITY = GENOME_AUTHORITY

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self.cap_registry = capability_registry

    # ------------------------------------------------------------------ public API ------------- #
    def prepare_registration_request(
        self,
        proposal: Optional[AgentGenomeProposal],
        *,
        candidate: Optional[ProblemCandidate] = None,
        compilation: Optional[ProblemCompilation] = None,
        canonical_state: Any = None,
        parent_budget: Optional[ResourceBudget] = None,
        options: Optional[Any] = None,
        now: Optional[str] = None,
    ) -> RegistrationRequest:
        """Build (and validate) a RegistrationRequest from a LOOP 6 proposal. Mutates nothing.

        Raises ``FactoryError`` only on API misuse (an operation-smuggling ``options`` payload).
        Every candidate-level refusal is returned as a REJECTED request with a specific code.
        """
        _assert_no_smuggled_options(options)
        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        return _evaluate(proposal, candidate, compilation, canonical_state, parent_budget, created)

    def validate_registration_request(
        self,
        request: RegistrationRequest,
        *,
        proposal: Optional[AgentGenomeProposal],
        candidate: Optional[ProblemCandidate] = None,
        compilation: Optional[ProblemCompilation] = None,
        canonical_state: Any = None,
        parent_budget: Optional[ResourceBudget] = None,
        options: Optional[Any] = None,
        now: Optional[str] = None,
    ) -> RegistrationRequest:
        """Re-validate an existing request against the CURRENT proposal/state (staleness, mutation).

        A re-validated request keeps its identity ONLY if the content is unchanged; otherwise it is
        returned as REJECTED (STALE / NONDETERMINISTIC) — never silently accepted.
        """
        _assert_no_smuggled_options(options)
        if not isinstance(request, RegistrationRequest):
            raise FactoryError("INVALID_REGISTRATION_REQUEST", type(request).__name__)
        created = now or request.created_at or datetime.datetime.now(
            datetime.timezone.utc).isoformat()
        fresh = _evaluate(proposal, candidate, compilation, canonical_state, parent_budget, created)
        if fresh.status is RegistrationRequestStatus.REJECTED:
            return fresh
        if fresh.genome_content_reference != request.genome_content_reference:
            return _reject(dict(fresh.model_dump(), request_id=fresh.request_id), REQUEST_STALE_GENOME,
                           "the genome content changed since the request was prepared")
        if fresh.proposal_content_reference != request.proposal_content_reference:
            return _reject(dict(fresh.model_dump(), request_id=fresh.request_id),
                           REQUEST_STALE_PROPOSAL,
                           "the proposal content changed since the request was prepared")
        for field in ("proposal_id", "candidate_id", "agent_id", "work_id", "problem_id"):
            if getattr(fresh, field) != getattr(request, field):
                return _reject(dict(fresh.model_dump(), request_id=fresh.request_id),
                               REQUEST_NONDETERMINISTIC,
                               f"the request declares {field}={getattr(request, field)!r} but the "
                               f"proposal/state says {getattr(fresh, field)!r}")
        if fresh.request_id != request.request_id:
            return _reject(dict(fresh.model_dump(), request_id=fresh.request_id),
                           REQUEST_NONDETERMINISTIC,
                           f"recomputed request id {fresh.request_id} != {request.request_id}")
        return fresh


# ----------------------------------------------------------------------------------------------- #
# Internals: the fail-closed validation gate (pure reads; nothing is mutated)
# ----------------------------------------------------------------------------------------------- #
def _assert_no_smuggled_options(options: Optional[Any]) -> None:
    """The factory takes NO operational options: an operation-smuggling payload is REFUSED by name.

    Registration / activation / execution / TaskNetwork mutation / canonical replacement / provider
    selection / authority escalation cannot be requested here at all — each attempt gets its OWN code.
    """
    if options is None:
        return
    if not isinstance(options, dict):
        raise FactoryError("INVALID_FACTORY_OPTIONS", type(options).__name__)
    for keys, code in ((_REGISTRY_KEYS, REQUEST_REGISTRY_REQUESTED),
                       (_RUNTIME_KEYS, REQUEST_RUNTIME_REQUESTED),
                       (_TASKNETWORK_KEYS, REQUEST_TASKNETWORK_MUTATION),
                       (_CANONICAL_KEYS, REQUEST_CANONICAL_REPLACEMENT),
                       (_AUTHORITY_KEYS, REQUEST_HIDDEN_AUTHORITY),
                       (("allow_fallback",), REQUEST_PROVIDER_FALLBACK_ESCALATION),
                       (_PROVIDER_KEYS, REQUEST_PROVIDER_PIN)):
        offending = [k for k in options.keys() if k in keys]
        if offending:
            raise FactoryError(code, f"factory option(s) {offending} are not requestable")
    raise FactoryError(REQUEST_UNKNOWN_OPTION, f"{sorted(options.keys())}")


def _strip_volatile(node: Any) -> Any:
    """Remove volatile metadata RECURSIVELY (created_at/frozen are not content — see F11)."""
    if isinstance(node, dict):
        return {k: _strip_volatile(v) for k, v in node.items() if k not in _VOLATILE_KEYS}
    if isinstance(node, list):
        return [_strip_volatile(x) for x in node]
    return node


def _content_hash(value: Any) -> str:
    dumped = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    blob = json.dumps(_strip_volatile(dumped), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _request_id(work_id: str, problem_id: str, candidate_id: str, proposal_id: str,
                genome_ref: str, proposal_ref: str) -> str:
    blob = f"{REQUEST_VERSION}|{work_id}|{problem_id}|{candidate_id}|{proposal_id}|" \
           f"{genome_ref}|{proposal_ref}"
    return "REQ-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12].upper()


def _base_request(proposal: Optional[AgentGenomeProposal], created: str,
                  candidate: Optional[ProblemCandidate] = None) -> Dict[str, Any]:
    genome = proposal.genome if proposal is not None else None
    return dict(
        request_id="PENDING",
        work_id=proposal.work_id if proposal is not None else "",
        problem_id=proposal.problem_id if proposal is not None else "",
        proposal_id=proposal.proposal_id if proposal is not None else "",
        candidate_id=proposal.candidate_id if proposal is not None else (
            candidate.candidate_id if candidate is not None else ""),
        candidate_kind=proposal.candidate_kind if proposal is not None else (
            candidate.kind if candidate is not None else None),
        agent_id=genome.agent_id if genome is not None else "",
        evaluation_id="",
        necessity_decision=proposal.necessity_decision if proposal is not None else "",
        necessity_reason_code=proposal.necessity_reason_code if proposal is not None else "",
        cognitive_owner=proposal.cognitive_owner if proposal is not None else "",
        cognitive_family=(genome.identity.cognitive_family.value if genome is not None else ""),
        network_role=(genome.identity.network_role.value if genome is not None else ""),
        authority_scope=(genome.authority_scope if genome is not None else ""),
        source_reference=proposal.source_reference if proposal is not None else "",
        created_at=created,
        provenance=[
            f"LOOP 7 AgentFactory v{REQUEST_VERSION} — {FACTORY_AUTHORITY}",
            "PREPARED ONLY: no registration, no activation, no execution, no model/provider call",
        ],
    )


def _reject(data: Dict[str, Any], code: str, detail: str) -> RegistrationRequest:
    payload = dict(data)
    payload.update({
        "status": RegistrationRequestStatus.REJECTED,
        "rejections": [RegistrationRejection(reason_code=code, detail=detail)],
    })
    return RegistrationRequest(**payload)


def _evaluate(proposal: Optional[AgentGenomeProposal], candidate: Optional[ProblemCandidate],
              compilation: Optional[ProblemCompilation], canonical_state: Any,
              parent_budget: Optional[ResourceBudget],
              created: str) -> RegistrationRequest:
    """The ordered fail-closed gate. It performs pure reads and NEVER mutates anything."""
    if proposal is not None and not isinstance(proposal, AgentGenomeProposal):
        raise FactoryError("INVALID_PROPOSAL", type(proposal).__name__)
    data = _base_request(proposal, created, candidate)

    # ---- capture the state BEFORE any read-heavy validation (mutation firewall) --------------- #
    fingerprint_before = None
    if canonical_state is not None:
        try:
            fingerprint_before = canonical_state_fingerprint(canonical_state)
        except Exception:                                        # pragma: no cover - defensive
            fingerprint_before = None

    if proposal is None:
        return _reject(data, REQUEST_PROPOSAL_MISSING, "no proposal was supplied")
    if proposal.status is not GenomeProposalStatus.PROPOSED or proposal.genome is None:
        return _reject(data, REQUEST_PROPOSAL_NOT_PROPOSED,
                       "the proposal is not a formally valid PROPOSED genome proposal")
    genome = proposal.genome
    envelope = proposal.input_contract
    if envelope is None:
        return _reject(data, REQUEST_MALFORMED_GENOME, "the proposal carries no input contract")

    # ---- 1/2/3. the candidate must exist and be the one the proposal was built from ----------- #
    known_ids = [c.candidate_id for c in (compilation.candidates if compilation else [])]
    if candidate is None and compilation is not None:
        candidate = next((c for c in compilation.candidates
                          if c.candidate_id == proposal.candidate_id), None)
    if candidate is None:
        return _reject(data, REQUEST_CANDIDATE_MISSING, "the candidate does not exist")
    if candidate.candidate_id != proposal.candidate_id:
        return _reject(data, REQUEST_CANDIDATE_MISMATCH,
                       f"candidate {candidate.candidate_id} != proposal {proposal.candidate_id}")
    if compilation is not None and candidate.candidate_id not in known_ids:
        return _reject(data, REQUEST_CANDIDATE_MISSING,
                       f"candidate {candidate.candidate_id} is not part of this compilation")

    # ---- 4. the LOOP 5 necessity verdict is READ (never recomputed) --------------------------- #
    evaluation = None
    necessity = getattr(canonical_state, "agent_necessity", None) if canonical_state else None
    if necessity is not None:
        evaluation = next((e for e in necessity.evaluations
                           if e.candidate_id == proposal.candidate_id), None)
        if evaluation is None:
            return _reject(data, REQUEST_CANDIDATE_MISSING,
                           "no necessity evaluation exists for this candidate")
        data["evaluation_id"] = evaluation.evaluation_id
        data["necessity_decision"] = _decision_value(evaluation.decision)
        data["necessity_reason_code"] = evaluation.reason_code
        if _decision_value(evaluation.decision) == NecessityDecision.BLOCKED.value:
            return _reject(data, REQUEST_CANDIDATE_BLOCKED,
                           f"the necessity verdict is BLOCKED ({evaluation.reason_code})")
        if _decision_value(evaluation.decision) != NecessityDecision.NECESSARY.value:
            return _reject(data, REQUEST_CANDIDATE_NOT_NECESSARY,
                           f"the necessity verdict is {_decision_value(evaluation.decision)}")
    if proposal.necessity_decision != NecessityDecision.NECESSARY.value:
        return _reject(data, REQUEST_CANDIDATE_NOT_NECESSARY,
                       f"the proposal was not built from a NECESSARY verdict "
                       f"({proposal.necessity_decision or 'UNKNOWN'})")
    # ---- 5. scope: exactly one Work and exactly one Problem ----------------------------------- #
    if canonical_state is not None:
        work_id = getattr(getattr(canonical_state, "work", None), "work_id", "")
        problem_id = getattr(getattr(canonical_state, "problem", None), "problem_id", "")
        if work_id and work_id != proposal.work_id:
            return _reject(data, REQUEST_CROSS_WORK,
                           f"proposal work {proposal.work_id} != state work {work_id}")
        if problem_id and problem_id != proposal.problem_id:
            return _reject(data, REQUEST_CROSS_PROBLEM,
                           f"proposal problem {proposal.problem_id} != state problem {problem_id}")
    if compilation is not None:
        if compilation.work_id and compilation.work_id != proposal.work_id:
            return _reject(data, REQUEST_CROSS_WORK, "compilation/work mismatch")
        if compilation.problem_id and compilation.problem_id != proposal.problem_id:
            return _reject(data, REQUEST_CROSS_PROBLEM, "compilation/problem mismatch")
    if not proposal.work_id or not proposal.problem_id or "*" in (proposal.work_id, proposal.problem_id):
        return _reject(data, REQUEST_CROSS_WORK,
                       "a request must be bound to exactly one work and one problem (no wildcard)")

    # ---- 6. identity is deterministic, parseable and PRESERVED -------------------------------- #
    try:
        parsed = AgentIdentity.parse(genome.agent_id)
    except AgentContractError as exc:
        return _reject(data, REQUEST_IDENTITY_MISMATCH, f"{exc.reason_code}: {exc}")
    if parsed != genome.identity:
        return _reject(data, REQUEST_IDENTITY_MISMATCH,
                       f"agent_id {genome.agent_id} does not round-trip to its own identity")

    # ---- 7. the family must belong to the owner the proposal CLAIMS (checked before the identity
    #         owner equality so a spoofed owner receives its OWN specific code) ------------------ #
    claimed_owner = proposal.cognitive_owner or genome.identity.cognitive_owner
    if FAMILY_OWNER[genome.identity.cognitive_family] != claimed_owner:
        return _reject(data, REQUEST_FAMILY_MISMATCH,
                       f"family {genome.identity.cognitive_family.value} is owned by "
                       f"{FAMILY_OWNER[genome.identity.cognitive_family]}, not by the claimed "
                       f"owner {claimed_owner}")
    if proposal.cognitive_owner and proposal.cognitive_owner != genome.identity.cognitive_owner:
        return _reject(data, REQUEST_IDENTITY_MISMATCH,
                       f"proposal owner {proposal.cognitive_owner} != genome owner "
                       f"{genome.identity.cognitive_owner}")

    # ---- 9/12. authority stays PROPOSER, no escalation intent in the declarations ------------- #
    # Checked BEFORE the envelope match so an escalation attempt receives its OWN specific code
    # instead of being masked by a staleness rejection.
    if genome.authority_scope != GENOME_AUTHORITY:
        return _reject(data, REQUEST_AUTHORITY_ESCALATION,
                       f"authority_scope is {genome.authority_scope}, not {GENOME_AUTHORITY}")
    attempt = _authority_scope_attempt(genome, proposal)
    if attempt is not None:
        return _reject(data, REQUEST_AUTHORITY_ESCALATION,
                       f"the payload declares authority_scope={attempt} (only PROPOSER is admissible)")
    intent = detect_escalation_intent(_declaration_text(genome, proposal))
    if intent is not None:
        code = {"NECESSITY_AUTHORITY_ESCALATION": REQUEST_AUTHORITY_ESCALATION,
                "NECESSITY_ROUTING_ESCALATION": REQUEST_TASKNETWORK_MUTATION,
                "NECESSITY_SELF_VALIDATION": REQUEST_HIDDEN_AUTHORITY}.get(intent,
                                                                          REQUEST_HIDDEN_AUTHORITY)
        return _reject(data, code, f"the genome/declaration text requests {intent}")

    # ---- 6b. the canonical envelope must still describe THIS genome (stale/malformed) --------- #
    try:
        envelope.assert_matches(genome)
    except AgentContractError as exc:
        if exc.reason_code == "ENVELOPE_GENOME_MISMATCH":
            return _reject(data, REQUEST_STALE_GENOME,
                           "the input contract was issued for a different genome content "
                           "(F11 note: AgentGenome.hash includes created_at, so a genome "
                           "reconstructed with a new timestamp is STALE here)")
        return _reject(data, REQUEST_MALFORMED_GENOME, f"{exc.reason_code}: {exc}")

    # ---- 7/8. family <-> owner, and a valid non-constitutional network role -------------------- #
    if FAMILY_OWNER[genome.identity.cognitive_family] != genome.identity.cognitive_owner \
            or genome.identity.cognitive_owner not in CONSTITUTIONAL_EM:
        return _reject(data, REQUEST_FAMILY_MISMATCH,
                       f"family {genome.identity.cognitive_family.value} is not owned by "
                       f"{genome.identity.cognitive_owner}")
    if genome.identity.network_role is NetworkRole.CONSTITUTIONAL:
        return _reject(data, REQUEST_NETWORK_ROLE_INVALID,
                       "an emergent unit can never hold the CONSTITUTIONAL network role")

    # ---- 10/11. the agent output contract is CANDIDATE-only ----------------------------------- #
    schema = proposal.output_contract or {}
    if schema.get("properties", {}).get("validation_status", {}).get("const") \
            != OUTPUT_STATUS_CANDIDATE:
        return _reject(data, REQUEST_OUTPUT_NOT_CANDIDATE,
                       "the output contract does not pin validation_status=CANDIDATE")
    for value in _walk(schema):
        if isinstance(value, str) and value.strip().upper() in ("VALIDATED", "FROZEN", "PUBLISHED",
                                                                "AUTHORIZED", "APPROVED"):
            return _reject(data, REQUEST_OUTPUT_NOT_CANDIDATE,
                           f"the output contract declares '{value}'")

    # ---- 12b. (routing / self-validation intent already handled above) ------------------------ #
    # ---- 13. provider: selection deferred, no vendor, no fallback escalation ------------------- #
    if proposal.provider_selection != PROVIDER_SELECTION_DEFERRED:
        return _reject(data, REQUEST_PROVIDER_SELECTION_NOT_DEFERRED, proposal.provider_selection)
    requirement = genome.model_requirements
    if requirement.allow_fallback:
        return _reject(data, REQUEST_PROVIDER_FALLBACK_ESCALATION,
                       "allow_fallback must stay False (fallback is never implicit)")
    dumped_requirement = requirement.model_dump(mode="json")
    for key in dumped_requirement:
        if key in _VENDOR_KEYS:
            return _reject(data, REQUEST_PROVIDER_PIN, f"model requirement exposes '{key}'")
    # a vendor token hidden ANYWHERE in the payload (declarations, provenance, contracts) is a pin
    vendor = _vendor_token(genome, proposal)
    if vendor is not None:
        return _reject(data, REQUEST_PROVIDER_PIN, f"vendor-specific value/token '{vendor}'")

    # ---- 14/15. explicit inputs and tools, no wildcards --------------------------------------- #
    if any(_is_wildcard(i) for i in envelope.authorized_inputs) or \
            any(_is_wildcard(i) for i in envelope.authorized_evidence_ids):
        return _reject(data, REQUEST_INPUT_WILDCARD, "wildcard authorization is not allowed")
    if not envelope.authorized_inputs:
        return _reject(data, REQUEST_INPUT_UNEXPLICIT, "the input contract grants nothing explicit")
    if any(_is_broad(i) for i in envelope.authorized_inputs):
        return _reject(data, REQUEST_INPUT_UNEXPLICIT,
                       "the input contract must not grant the whole canonical state")
    if any(_is_wildcard(t) for t in envelope.allowed_tools) or \
            any(_is_wildcard(t) for t in genome.tools):
        return _reject(data, REQUEST_TOOL_WILDCARD, "wildcard tools are not allowed")
    if not envelope.allowed_tools:
        return _reject(data, REQUEST_TOOL_UNEXPLICIT, "the request must declare its tools explicitly")

    # ---- 16. budget: child <= parent and <= HARD_BUDGET --------------------------------------- #
    budget = genome.resource_budget
    budget_dump = budget.model_dump(mode="json")
    if set(budget_dump) != set(HARD_BUDGET):
        return _reject(data, REQUEST_BUDGET_INVALID, f"unexpected budget shape {sorted(budget_dump)}")
    for key, ceiling in HARD_BUDGET.items():
        value = budget_dump[key]
        if not isinstance(value, int) or value < 0:
            return _reject(data, REQUEST_BUDGET_INVALID, f"{key}={value!r} is not a valid budget")
        if value > ceiling:
            return _reject(data, REQUEST_BUDGET_ESCALATION, f"{key}={value} > ceiling {ceiling}")
        if parent_budget is not None and value > getattr(parent_budget, key):
            return _reject(data, REQUEST_BUDGET_ESCALATION,
                           f"{key}={value} > parent {getattr(parent_budget, key)}")

    # ---- 17. dependencies: valid, existing, same work/problem, not retired, acyclic ----------- #
    dep_verdict = _validate_dependencies(genome, canonical_state)
    if dep_verdict is not None:
        code, detail = dep_verdict
        return _reject(data, code, detail)

    # ---- 18/19. no duplicate identity, no duplicate responsibility ---------------------------- #
    existing = _existing_agent(canonical_state, genome.agent_id)
    if existing is not None:
        return _reject(data, REQUEST_IDENTITY_DUPLICATE,
                       f"agent {genome.agent_id} already exists in this work (one identity = one agent)")
    target = (proposal.boundary or "").split("->")[-1].strip()
    coverage = existing_responsibility_coverage(canonical_state, target)
    if coverage is not None:
        return _reject(data, REQUEST_RESPONSIBILITY_DUPLICATE,
                       f"the responsibility '{target}' is already covered by {coverage}")

    # ---- 20. no incompatible duplicate request for the same agent ----------------------------- #
    genome_ref = _content_hash(genome)
    proposal_ref = _content_hash(proposal)
    for prior in (getattr(canonical_state, "agent_registration_requests", None) or []):
        if prior.agent_id == genome.agent_id and prior.is_validated() \
                and prior.genome_content_reference != genome_ref:
            return _reject(data, REQUEST_DUPLICATE_INCOMPATIBLE,
                           f"a validated request for {genome.agent_id} exists with different content")

    # ---- 21. provenance is mandatory --------------------------------------------------------- #
    if not proposal.provenance or not genome.provenance or not proposal.source_reference:
        return _reject(data, REQUEST_PROVENANCE_MISSING,
                       "proposal/genome provenance and the source reference are mandatory")

    # ---- 22. evidence must be real (never fabricated, never the source reference) ------------- #
    real_evidence = [str(e) for e in (getattr(canonical_state, "evidence_ids", None) or [])]
    evidence_refs = list(evaluation.evidence_refs) if evaluation is not None else \
        list(proposal.evidence_refs)
    fabricated = [e for e in evidence_refs if e not in real_evidence]
    if fabricated:
        return _reject(data, REQUEST_EVIDENCE_FABRICATED,
                       f"declared evidence {fabricated} does not exist in the canonical registry")
    if proposal.source_reference in evidence_refs:
        return _reject(data, REQUEST_EVIDENCE_FABRICATED,
                       "the provenance source reference must not be used as evidence")

    # ---- 23. mutation firewall: validation must not have changed the canonical state ---------- #
    if fingerprint_before is not None:
        if canonical_state_fingerprint(canonical_state) != fingerprint_before:
            return _reject(data, REQUEST_MUTATION_DETECTED,
                           "validation changed the canonical state (forbidden)")

    # ---- VALIDATED ---------------------------------------------------------------------------- #
    checks = [
        "proposal_exists", "proposal_is_proposed", "candidate_exists", "candidate_matches_proposal",
        "candidate_in_compilation", "necessity_is_necessary", "work_scope", "problem_scope",
        "identity_deterministic", "identity_preserved", "family_owner_consistent",
        "network_role_valid", "authority_is_proposer", "output_is_candidate",
        "no_hidden_authority", "provider_selection_deferred", "no_vendor_pin",
        "no_fallback_escalation", "inputs_explicit", "no_wildcard_inputs", "tools_explicit",
        "no_wildcard_tools", "budget_within_parent", "budget_within_hard_ceiling",
        "dependencies_valid", "no_dependency_cycle", "no_duplicate_identity",
        "no_duplicate_responsibility", "provenance_present", "evidence_real", "no_mutation",
    ]
    payload = dict(data)
    payload.update({
        "request_id": _request_id(proposal.work_id, proposal.problem_id, proposal.candidate_id,
                                  proposal.proposal_id, genome_ref, proposal_ref),
        "status": RegistrationRequestStatus.VALIDATED,
        "genome_content_reference": genome_ref,
        "proposal_content_reference": proposal_ref,
        "genome_envelope_hash": envelope.genome_hash,
        "input_contract": envelope,
        "output_contract": schema,
        "dependencies": list(genome.dependencies),
        "resource_budget": budget,
        "model_requirement": dumped_requirement,
        "evidence_refs": evidence_refs,
        "validation_checks": checks,
        "provenance": [
            *data["provenance"],
            f"{REQUEST_FROM_VALID_PROPOSAL}: proposal {proposal.proposal_id} of candidate "
            f"{proposal.candidate_id} ({proposal.necessity_reason_code})",
            f"traceability: work {proposal.work_id} / problem {proposal.problem_id} / "
            f"evaluation {data['evaluation_id'] or 'n/a'}",
            "the request is a DOMAIN OBJECT: it registers nothing and mutates nothing",
            "registration itself belongs to a FUTURE loop (RegistrationRequest -> AgentRegistry)",
        ],
    })
    return RegistrationRequest(**payload)


def _validate_dependencies(genome: AgentGenome,
                           canonical_state: Any) -> Optional[Tuple[str, str]]:
    """Reuse the canonical dependency validators; add existence/work/status/cycle checks."""
    try:
        validate_dependencies(genome.agent_id, list(genome.dependencies or []))
    except AgentContractError as exc:
        return REQUEST_DEPENDENCY_INVALID, f"{exc.reason_code}: {exc}"
    if not genome.dependencies:
        return None
    network = getattr(canonical_state, "agent_network", None)
    records = list(getattr(network, "records", None) or [])
    existing = {}
    for record in records:
        dep_genome = getattr(record, "genome", None)
        if dep_genome is not None:
            existing[dep_genome.agent_id] = record
    edges: Dict[str, List[str]] = {genome.agent_id: [d.agent_id for d in genome.dependencies]}
    for dep in genome.dependencies:
        record = existing.get(dep.agent_id)
        if record is None:
            return (REQUEST_DEPENDENCY_MISSING,
                    f"dependency {dep.agent_id} does not exist in this work "
                    "(no registry entry is ever invented)")
        dep_genome = record.genome
        if dep_genome.work_id != genome.work_id:
            return REQUEST_DEPENDENCY_CROSS_WORK, f"dependency {dep.agent_id} belongs to another work"
        if dep_genome.problem_id != genome.problem_id:
            return (REQUEST_DEPENDENCY_CROSS_PROBLEM,
                    f"dependency {dep.agent_id} belongs to another problem")
        if getattr(record, "status", None) is not None and \
                getattr(record.status, "value", record.status) == "RETIRED":
            return (REQUEST_DEPENDENCY_RETIRED,
                    f"dependency {dep.agent_id} is RETIRED (a terminal lifecycle state)")
        edges.setdefault(dep.agent_id, [d.agent_id for d in (dep_genome.dependencies or [])])
    cycle = detect_cycle(edges)
    if cycle:
        return REQUEST_DEPENDENCY_CYCLE, f"dependency cycle detected: {' -> '.join(cycle)}"
    return None


def _existing_agent(canonical_state: Any, agent_id: str) -> Optional[Any]:
    network = getattr(canonical_state, "agent_network", None)
    for record in (getattr(network, "records", None) or []):
        genome = getattr(record, "genome", None)
        if genome is not None and genome.agent_id == agent_id:
            return record
    return None


def _decision_value(decision: Any) -> str:
    """Tolerant decision accessor: a malformed/foreign verdict can never crash the gate."""
    return str(getattr(decision, "value", decision) or "")


def _vendor_token(genome: AgentGenome, proposal: AgentGenomeProposal) -> Optional[str]:
    """A vendor/provider token hidden anywhere in the payload is a provider pin."""
    dumped = json.dumps({"genome": genome.model_dump(mode="json"),
                         "proposal": proposal.model_dump(mode="json")}, ensure_ascii=False).lower()
    for token in ("deepseek", "ollama", "openai", "anthropic", "gpt-", "claude", "http://",
                  "https://", "api_key", "bearer ", "localhost:", ":11434"):
        if token in dumped:
            return token
    return None


def _declaration_text(genome: AgentGenome, proposal: AgentGenomeProposal) -> str:
    """Every textual declaration (INCLUDING provenance) is scanned for escalation intent.

    The legitimate contract statement ``authority_scope=PROPOSER`` is neutralised first, because it
    is an audit-trail DESCRIPTION of the contract rather than an escalation attempt (scanning it
    verbatim produced a false positive). Any OTHER scope value is caught by
    ``_authority_scope_attempt``, which reads the whole payload.
    """
    parts: List[str] = [genome.objective, *genome.questions, *genome.predicates,
                        *genome.validation_rules, *genome.human_escalation_rules,
                        *genome.provenance, *proposal.provenance]
    text = " ".join(str(p) for p in parts if p)
    # NOTE: the replacement text deliberately avoids the words the detectors look for, otherwise the
    # neutralised statement would itself re-trigger them.
    return _NEUTRAL_AUTHORITY_SCOPE_RE.sub("the declared proposer-only scope statement", text)


def _authority_scope_attempt(genome: AgentGenome, proposal: AgentGenomeProposal) -> Optional[str]:
    """Any declared authority scope OTHER than PROPOSER, anywhere in the payload, is an attempt."""
    dumped = json.dumps({"genome": genome.model_dump(mode="json"),
                         "proposal": proposal.model_dump(mode="json")}, ensure_ascii=False)
    for match in _AUTHORITY_SCOPE_RE.finditer(dumped):
        value = match.group(1).strip().strip('"').upper()
        if value and value != GENOME_AUTHORITY:
            return value
    return None


def _walk(node: Any) -> List[Any]:
    if isinstance(node, dict):
        out: List[Any] = []
        for value in node.values():
            out += _walk(value)
        return out
    if isinstance(node, list):
        out = []
        for item in node:
            out += _walk(item)
        return out
    return [node]


def _is_wildcard(token: str) -> bool:
    return "*" in str(token)


def _is_broad(token: str) -> bool:
    lowered = str(token).strip().lower()
    return lowered in ("canonical_state", "canonicalworkstate", "whole_state", "everything",
                       "all_inputs", "all", "all_evidence")