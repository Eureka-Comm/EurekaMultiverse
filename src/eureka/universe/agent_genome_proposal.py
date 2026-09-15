"""EUREKA 5.1 — LOOP 6: EMERGENT AGENT GENOME PROPOSAL (designs a genome; registers/executes nothing).

PURPOSE
-------
Transform a **VERIFIED NECESSARY verdict** (LOOP 5) into a formally valid **AgentGenome PROPOSAL**.

    ProblemModel -> ProblemCompiler -> Agent Necessity Test -> NECESSARY -> Genome Proposal ->
    validation -> CANDIDATE GENOME                                              (STOPS HERE)

It is explicitly NOT a registration, creation, activation, execution, authorization or routing
decision, and it never reaches AgentRegistry / AgentRuntime / any model or provider.

CONSTITUTIONAL RULES HONOURED BY CONSTRUCTION
---------------------------------------------
  * ``AgentGenome`` remains the ONE canonical agent contract: this module EMBEDS an existing
    ``AgentGenome`` object inside a thin provenance wrapper — it does NOT redefine, subclass or
    clone its fields (no AgentGenomeV2 / EmergentAgentGenome / parallel candidate schema).
  * ``authority_scope`` stays ``PROPOSER``: the field is ``frozen=True`` in the contract and the
    proposal validators refuse any other value. VALIDATOR / AUTHORIZER / ROUTER / PUBLISHER /
    FREEZER / SYSTEM_ADMIN are unreachable.
  * the output contract is CANDIDATE-only: the declared ``output_schema`` pins
    ``validation_status = "CANDIDATE"`` and any attempt to declare VALIDATED / FROZEN / PUBLISHED /
    AUTHORIZED is rejected.
  * the genome DECLARES a ``ModelRequirement`` and never selects a provider: the contract's
    ``extra="forbid"`` makes a vendor pin (provider/model/url/api_key) impossible to express.
  * the budget is derived with the EXISTING no-escalation contract (``ResourceBudget.child``), so a
    request above the parent (or above ``HARD_BUDGET``) fails closed.
  * the input contract is the narrowest valid ``TaskEnvelope``: explicit grants only (no wildcard,
    never the whole CanonicalWorkState), and it must satisfy ``TaskEnvelope.assert_matches(genome)``.
  * the cognitive family is NOT requestable: it is derived from the NECESSARY verdict's
    constitutional owner (role creep is impossible by design), and the narrowest existing
    ``NetworkRole`` (SEGREGATOR) is selected by default — the constitutional nucleus can never be
    impersonated.
  * source reference != evidence: provenance pointers are never turned into evidence, and no
    evidence id is ever invented (declared evidence must already exist in the canonical registry).
  * the proposal is persisted (when the caller chooses to) through the EXISTING ``WorkStore`` as a
    field of ``CanonicalWorkState`` — there is no GenomeStore/AgentProposalStore, and the field stays
    OUTSIDE ``canonical_identity._payload`` (F4 deliberately untouched).
"""
from __future__ import annotations

import datetime
import hashlib
import re
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_genome import (CONSTITUTIONAL_EM, FAMILY_OWNER, HARD_BUDGET, AgentContractError,
                           AgentDependency, AgentDependencyKind, AgentGenome, AgentIdentity,
                           CognitiveFamily, ModelRequirement, NetworkRole, ResourceBudget,
                           TaskEnvelope, detect_cycle, validate_dependencies)
from .agent_necessity import NECESSARY_EMERGENT_UNIT_JUSTIFIED, NecessityDecision, NecessityEvaluation
from .capability_fabric import CapabilityRegistry
from .problem_compiler import CandidateKind, ProblemCandidate

PROPOSAL_VERSION = "1.0"

#: Declared authority of this module. A CONSTANT — nothing can promote it.
PROPOSAL_AUTHORITY = "GENOME_PROPOSAL_ONLY"
#: The canonical genome authority. A proposal never changes it.
GENOME_AUTHORITY = "PROPOSER"
#: The only admissible output status of a proposal (a proposal is never validated by its author).
OUTPUT_STATUS_CANDIDATE = "CANDIDATE"
#: Provider selection is DEFERRED to the ModelRouter (LOOP 10). The genome declares requirements only.
PROVIDER_SELECTION_DEFERRED = "DEFERRED_TO_MODEL_ROUTER"

# ----------------------------------------------------------------------------------------------- #
# Reason codes (specific, never a generic exception where a specific code is possible)
# ----------------------------------------------------------------------------------------------- #
PROPOSAL_FROM_NECESSARY_VERDICT = "PROPOSAL_FROM_NECESSARY_VERDICT"
GENOME_VERDICT_NOT_NECESSARY = "GENOME_VERDICT_NOT_NECESSARY"
GENOME_CANDIDATE_MISMATCH = "GENOME_CANDIDATE_MISMATCH"
GENOME_CROSS_WORK = "GENOME_CROSS_WORK"
GENOME_CROSS_PROBLEM = "GENOME_CROSS_PROBLEM"
GENOME_OWNER_MISSING = "GENOME_OWNER_MISSING"
GENOME_FAMILY_MISMATCH = "GENOME_FAMILY_MISMATCH"
GENOME_NETWORK_ROLE_REFUSED = "GENOME_NETWORK_ROLE_REFUSED"
GENOME_IDENTITY_UNPARSEABLE = "GENOME_IDENTITY_UNPARSEABLE"
GENOME_IDENTITY_COLLISION = "GENOME_IDENTITY_COLLISION"
GENOME_PROVIDER_PIN = "GENOME_PROVIDER_PIN"
GENOME_BUDGET_ESCALATION = "GENOME_BUDGET_ESCALATION"
GENOME_EVIDENCE_FABRICATED = "GENOME_EVIDENCE_FABRICATED"
GENOME_EVIDENCE_MISSING = "GENOME_EVIDENCE_MISSING"
GENOME_DEPENDENCY_UNRESOLVABLE = "GENOME_DEPENDENCY_UNRESOLVABLE"
GENOME_DEPENDENCY_CYCLE = "GENOME_DEPENDENCY_CYCLE"
GENOME_INPUT_CONTRACT_TOO_BROAD = "GENOME_INPUT_CONTRACT_TOO_BROAD"
GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE = "GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE"
GENOME_AUTHORITY_ESCALATION = "GENOME_AUTHORITY_ESCALATION"
GENOME_POLICY_MUTATION = "GENOME_POLICY_MUTATION"
GENOME_REGISTRY_REQUESTED = "GENOME_REGISTRY_REQUESTED"
GENOME_RUNTIME_REQUESTED = "GENOME_RUNTIME_REQUESTED"
GENOME_TASKNETWORK_MUTATION_REQUESTED = "GENOME_TASKNETWORK_MUTATION_REQUESTED"
GENOME_PREDICATE_INVALID = "GENOME_PREDICATE_INVALID"
GENOME_DUPLICATES_EXISTING = "GENOME_DUPLICATES_EXISTING"

REASON_CODES: Tuple[str, ...] = (
    PROPOSAL_FROM_NECESSARY_VERDICT, GENOME_VERDICT_NOT_NECESSARY, GENOME_CANDIDATE_MISMATCH,
    GENOME_CROSS_WORK, GENOME_CROSS_PROBLEM, GENOME_OWNER_MISSING, GENOME_FAMILY_MISMATCH,
    GENOME_NETWORK_ROLE_REFUSED, GENOME_IDENTITY_UNPARSEABLE, GENOME_IDENTITY_COLLISION,
    GENOME_PROVIDER_PIN, GENOME_BUDGET_ESCALATION, GENOME_EVIDENCE_FABRICATED,
    GENOME_EVIDENCE_MISSING, GENOME_DEPENDENCY_UNRESOLVABLE, GENOME_DEPENDENCY_CYCLE,
    GENOME_INPUT_CONTRACT_TOO_BROAD, GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE,
    GENOME_AUTHORITY_ESCALATION, GENOME_POLICY_MUTATION, GENOME_REGISTRY_REQUESTED,
    GENOME_RUNTIME_REQUESTED, GENOME_TASKNETWORK_MUTATION_REQUESTED, GENOME_PREDICATE_INVALID,
    GENOME_DUPLICATES_EXISTING,
)

#: Request-mapping keys categorised by the escalation they attempt, so every adversarial path gets
#: its OWN specific code instead of a generic validation error.
_PROVIDER_REQUEST_KEYS = ("provider", "model", "vendor", "api_key", "endpoint", "base_url", "url",
                          "capability_class", "reasoning", "model_requirements")
_AUTHORITY_REQUEST_KEYS = ("authority", "authority_scope", "owner", "cognitive_family", "family",
                           "identity", "agent_id", "canonical_owner", "validator", "publisher",
                           "network_role", "work_id", "problem_id")
_POLICY_REQUEST_KEYS = ("policy", "canonical_status", "execution_mode", "bypass_governance",
                        "promote", "approved", "release", "is_admin", "freeze", "validate")
_REGISTRY_REQUEST_KEYS = ("register", "registration", "activate", "activation", "supersede",
                          "retire", "agent_registry")
_RUNTIME_REQUEST_KEYS = ("execute", "execution", "runtime", "invoke", "run", "agent_runtime")
_TASKNETWORK_REQUEST_KEYS = ("task_network", "tasks", "execution_plan", "next_owner", "routing")

#: Every operation a proposed emergent unit is FOREVER forbidden to perform (declared in the genome,
#: not merely documented here). This is the anti-role-creep statement of the proposal.
FORBIDDEN_OPERATIONS: Tuple[str, ...] = (
    "validate_own_output", "freeze_any_artifact", "publish_any_artifact", "authorize_any_agent",
    "register_any_agent", "create_child_agent", "route_next_owner", "modify_task_network",
    "mutate_canonical_state", "change_policy", "select_model_provider", "change_model_requirement",
    "write_persistence", "bypass_effect_boundary",
)

#: Tokens that would imply authority/validation in an output contract.
_FORBIDDEN_OUTPUT_VALUES = ("VALIDATED", "FROZEN", "PUBLISHED", "AUTHORIZED", "APPROVED")
#: Keys an attacker would use to smuggle authority/policy/provider/registry/runtime into a design
#: request. They are refused BY NAME (with their own specific code) before any construction.
_FORBIDDEN_REQUEST_KEYS = tuple(dict.fromkeys(
    _PROVIDER_REQUEST_KEYS + _AUTHORITY_REQUEST_KEYS + _POLICY_REQUEST_KEYS
    + _REGISTRY_REQUEST_KEYS + _RUNTIME_REQUEST_KEYS + _TASKNETWORK_REQUEST_KEYS
    + ("canonical_state", "publish", "authorize"))
)
_ARROW_SPLIT_RE = re.compile(r"\s*(?:->|→|=>)\s*")
_SLUG_STRIP_RE = re.compile(r"[^A-Za-z0-9]+")


class GenomeProposalError(Exception):
    """Fail-closed contract violation of the proposal API itself (misuse, not a candidate verdict)."""

    def __init__(self, reason_code: str, message: str = "") -> None:
        self.reason_code = reason_code
        super().__init__(f"{reason_code}: {message}" if message else reason_code)


class GenomeDesignRequest(BaseModel):
    """Caller-supplied design options. ``extra="forbid"`` makes authority smuggling impossible.

    There is deliberately NO field for cognitive family, authority scope, provider, policy or
    registry/runtime action: those cannot be requested at all.
    """

    model_config = ConfigDict(extra="forbid")

    requested_network_role: Optional[NetworkRole] = None
    requested_dependencies: List[str] = Field(default_factory=list)
    requested_budget: Dict[str, int] = Field(default_factory=dict)
    requested_inputs: List[str] = Field(default_factory=list)


class GenomeProposalStatus(str, Enum):
    """A proposal is either formally valid (PROPOSED) or refused (REJECTED). Never "validated"."""

    PROPOSED = "PROPOSED"
    REJECTED = "REJECTED"


class GenomeProposalRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(..., min_length=1)
    detail: str = ""


class AgentGenomeProposal(BaseModel):
    """Thin PROVENANCE WRAPPER around an EXISTING ``AgentGenome`` (which is the real contract)."""

    model_config = ConfigDict(extra="forbid")

    proposal_id: str = Field(..., min_length=1)
    proposal_version: str = PROPOSAL_VERSION
    authority: str = PROPOSAL_AUTHORITY
    #: Declared invariants (validated below — a proposal cannot claim otherwise).
    proposal_only: bool = True
    registers_agents: bool = False
    activates_agents: bool = False
    executes_agents: bool = False
    selects_provider: bool = False
    mutates_task_network: bool = False
    mutates_canonical_state: bool = False
    persists_itself: bool = False
    provider_selection: str = PROVIDER_SELECTION_DEFERRED

    status: GenomeProposalStatus = GenomeProposalStatus.PROPOSED
    genome: Optional[AgentGenome] = None                 # THE canonical contract (embedded as-is)
    input_contract: Optional[TaskEnvelope] = None
    output_contract: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[AgentDependency] = Field(default_factory=list)

    # ---- mandatory traceability (LOOP 6) ------------------------------------------------------ #
    work_id: str = ""
    problem_id: str = ""
    candidate_id: str = ""
    candidate_kind: Optional[CandidateKind] = None
    necessity_decision: str = ""
    necessity_reason_code: str = ""
    source_reference: str = ""
    cognitive_owner: str = ""
    boundary: str = ""
    capability_gap_evidence: str = ""

    rejections: List[GenomeProposalRejection] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _proposal_invariants(self) -> "AgentGenomeProposal":
        if self.authority != PROPOSAL_AUTHORITY:
            raise GenomeProposalError("PROPOSAL_AUTHORITY_CANNOT_BE_ESCALATED", self.authority)
        for flag in ("proposal_only", "registers_agents", "activates_agents", "executes_agents",
                     "selects_provider", "mutates_task_network", "mutates_canonical_state",
                     "persists_itself"):
            expected = True if flag == "proposal_only" else False
            if getattr(self, flag) is not expected:
                raise GenomeProposalError("PROPOSAL_CANNOT_" + flag.upper(), str(getattr(self, flag)))
        if self.provider_selection != PROVIDER_SELECTION_DEFERRED:
            raise GenomeProposalError("PROVIDER_SELECTION_MUST_BE_DEFERRED", self.provider_selection)

        if self.status is GenomeProposalStatus.PROPOSED:
            if self.genome is None:
                raise GenomeProposalError("PROPOSED_WITHOUT_GENOME", self.proposal_id)
            if self.rejections:
                raise GenomeProposalError("PROPOSED_WITH_REJECTIONS", self.proposal_id)
            if self.genome.authority_scope != GENOME_AUTHORITY:
                raise GenomeProposalError(GENOME_AUTHORITY_ESCALATION, self.genome.authority_scope)
            if self.output_contract.get("properties", {}).get("validation_status", {}).get("const") \
                    != OUTPUT_STATUS_CANDIDATE:
                raise GenomeProposalError(GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE, "validation_status")
            if self.input_contract is None:
                raise GenomeProposalError("PROPOSED_WITHOUT_INPUT_CONTRACT", self.proposal_id)
            self.input_contract.assert_matches(self.genome)      # reused canonical check
        else:
            if self.genome is not None:
                raise GenomeProposalError("REJECTED_PROPOSAL_CANNOT_CARRY_A_GENOME", self.proposal_id)
            if not self.rejections:
                raise GenomeProposalError("REJECTED_WITHOUT_REASON", self.proposal_id)
        return self

    # ---- read-only helpers -------------------------------------------------------------------- #
    def is_valid_proposal(self) -> bool:
        return self.status is GenomeProposalStatus.PROPOSED and self.genome is not None

    def agent_id(self) -> Optional[str]:
        return self.genome.agent_id if self.genome else None

    def semantic_identity(self) -> Optional[Dict[str, Any]]:
        """The semantic identity of the proposal (NOT its volatile creation metadata)."""
        if self.genome is None:
            return None
        identity = self.genome.identity
        return {
            "cognitive_family": identity.cognitive_family.value,
            "network_role": identity.network_role.value,
            "predicate": identity.predicate,
            "context": identity.context,
            "cognitive_owner": identity.cognitive_owner,
            "work_id": self.genome.work_id,
            "problem_id": self.genome.problem_id,
            "task_id": self.genome.task_id,
            "objective": self.genome.objective,
            "predicates": list(self.genome.predicates),
        }


class AgentGenomeDesigner:
    """Deterministic genome designer. Stateless (only the capability registry it reads).

    Public surface: ``propose``. There is deliberately NO method to register, activate, execute,
    route, persist or mutate anything, and none that reaches a provider/model.
    """

    AUTHORITY = PROPOSAL_AUTHORITY
    GENOME_AUTHORITY = GENOME_AUTHORITY

    def __init__(self, capability_registry: CapabilityRegistry) -> None:
        self.cap_registry = capability_registry

    # ------------------------------------------------------------------ public API ------------- #
    def propose(
        self,
        evaluation: NecessityEvaluation,
        *,
        candidate: Optional[ProblemCandidate] = None,
        canonical_state: Any = None,
        request: Optional[Any] = None,
        parent_budget: Optional[ResourceBudget] = None,
        now: Optional[str] = None,
    ) -> AgentGenomeProposal:
        """Design a genome PROPOSAL from a LOOP 5 NECESSARY verdict. Registers/executes nothing.

        Raises ``GenomeProposalError`` only on API misuse (a foreign payload, or a design request that
        names the forbidden authority/policy/provider/registry/runtime surface). Every candidate-level
        refusal is returned as a REJECTED proposal with a specific reason code — observable, never
        silent.
        """
        if not isinstance(evaluation, NecessityEvaluation):
            raise GenomeProposalError("INVALID_NECESSITY_EVALUATION", type(evaluation).__name__)
        request = _coerce_request(request)
        _assert_no_forbidden_request_fields(request)
        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        base = _base_data(evaluation, candidate, created)

        def _reject(code: str, detail: str, **overrides: Any) -> AgentGenomeProposal:
            data = dict(base)
            data.update({
                "status": GenomeProposalStatus.REJECTED,
                "genome": None, "input_contract": None,
                "rejections": [GenomeProposalRejection(reason_code=code, detail=detail)],
            })
            data.update(overrides)
            return AgentGenomeProposal(**data)

        # ---- the verdict must be NECESSARY ---------------------------------------------------- #
        if evaluation.decision is not NecessityDecision.NECESSARY:
            return _reject(GENOME_VERDICT_NOT_NECESSARY,
                           f"the necessity verdict is {evaluation.decision.value}; only a NECESSARY "
                           "verdict may produce a genome proposal")
        if evaluation.reason_code != NECESSARY_EMERGENT_UNIT_JUSTIFIED:
            return _reject(GENOME_VERDICT_NOT_NECESSARY,
                           f"unexpected necessity reason_code {evaluation.reason_code}")

        # ---- candidate identity must match the judged candidate -------------------------------- #
        if candidate is not None and candidate.candidate_id != evaluation.candidate_id:
            return _reject(GENOME_CANDIDATE_MISMATCH,
                           f"candidate {candidate.candidate_id} != evaluated {evaluation.candidate_id}")

        # ---- work / problem scoping ------------------------------------------------------------ #
        if canonical_state is not None:
            work_id = getattr(getattr(canonical_state, "work", None), "work_id", "")
            problem_id = getattr(getattr(canonical_state, "problem", None), "problem_id", "")
            if work_id and work_id != evaluation.work_id:
                return _reject(GENOME_CROSS_WORK,
                               f"candidate work {evaluation.work_id} != state work {work_id}")
            if problem_id and problem_id != evaluation.problem_id:
                return _reject(GENOME_CROSS_PROBLEM,
                               f"candidate problem {evaluation.problem_id} != state problem {problem_id}")

        # ---- owner -> cognitive family (NOT requestable: anti-role-creep by construction) ------- #
        owner = (evaluation.owner or "").strip()
        if not owner:
            return _reject(GENOME_OWNER_MISSING, "the NECESSARY verdict declares no constitutional owner")
        if owner not in CONSTITUTIONAL_EM:
            return _reject(GENOME_FAMILY_MISMATCH,
                           f"'{owner}' is not one of the 8 constitutional EMs")
        family = _family_of(owner)
        if family is None:
            return _reject(GENOME_FAMILY_MISMATCH,
                           f"'{owner}' has no CognitiveFamily; an emergent unit must map 1:1 onto it")

        # ---- boundary (condition -> target) ----------------------------------------------------- #
        boundary = (getattr(candidate, "reference", "") or "").strip() or _boundary_from(evaluation)
        parts = _ARROW_SPLIT_RE.split(boundary, maxsplit=1)
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            return _reject(GENOME_PREDICATE_INVALID,
                           f"'{boundary}' is not a well-formed condition->target boundary")
        condition_text, target_text = parts[0].strip(), parts[1].strip()

        # ---- network role: narrowest compatible (constitutional impersonation refused) ---------- #
        role, role_rejection = _select_role(request)
        if role_rejection:
            return _reject(*role_rejection)

        # ---- identity (deterministic; parseable; collision-checked) ------------------------------ #
        context = _context_slug(canonical_state)
        identity = AgentIdentity(cognitive_family=family, network_role=role,
                                 predicate=_slug(target_text), context=context)
        if AgentIdentity.parse(identity.agent_id).agent_id != identity.agent_id:
            return _reject(GENOME_IDENTITY_UNPARSEABLE, identity.agent_id)
        collision = _identity_collision(identity, canonical_state)
        if collision is not None:
            return _reject(GENOME_IDENTITY_COLLISION, collision)

        # ---- budget: derived through the EXISTING no-escalation contract ------------------------- #
        parent = parent_budget or ResourceBudget()
        budget, budget_rejection = _derive_budget(parent, request)
        if budget_rejection:
            return _reject(*budget_rejection)

        # ---- evidence: never invented, never converted from the source reference ----------------- #
        real_evidence = [str(e) for e in (getattr(canonical_state, "evidence_ids", None) or [])]
        evidence_refs = [e for e in evaluation.evidence_refs if e]
        fabricated = [e for e in evidence_refs if e not in real_evidence]
        if fabricated:
            return _reject(GENOME_EVIDENCE_FABRICATED,
                           f"declared evidence {fabricated} does not exist in the canonical registry")
        source_reference = base["source_reference"]
        if source_reference and source_reference in (evidence_refs + real_evidence):
            return _reject(GENOME_EVIDENCE_FABRICATED,
                           "the provenance source reference must not be used as evidence")

        # ---- N8-at-design-time: the responsibility must not already be covered ------------------ #
        coverage = _existing_coverage(canonical_state, target_text)
        if coverage is not None:
            return _reject(GENOME_DUPLICATES_EXISTING,
                           f"the target '{target_text}' is already covered by {coverage}: a "
                           "NECESSARY verdict must not be turned into a duplicate unit")

        # ---- dependencies: only EXISTING, same-work, resolvable, acyclic, non-duplicated -------- #
        dependencies, dep_rejection = _derive_dependencies(identity.agent_id, request, canonical_state)
        if dep_rejection:
            return _reject(*dep_rejection)

        # ---- input contract: the narrowest valid TaskEnvelope ----------------------------------- #
        condition_inputs = _declared_symbols(canonical_state, condition_text)
        if not condition_inputs:
            return _reject(GENOME_INPUT_CONTRACT_TOO_BROAD,
                           f"no declared symbol grounds the condition '{condition_text}'")
        requested_inputs = [i for i in request.requested_inputs if i]
        declared = set(_all_declared_symbols(canonical_state))
        foreign = [i for i in requested_inputs if i not in declared]
        if foreign:
            return _reject(GENOME_INPUT_CONTRACT_TOO_BROAD,
                           f"requested inputs {foreign} are not declared symbols of this work")
        narrow_inputs = list(dict.fromkeys(condition_inputs + [target_text])) + requested_inputs
        if any(_is_broad_input(i) for i in narrow_inputs):
            return _reject(GENOME_INPUT_CONTRACT_TOO_BROAD,
                           "the input contract must not grant the whole canonical state")

        # ---- tools: ONLY the family's own registered capabilities -------------------------------- #
        tools = sorted(cap.capability_id for cap in _family_capabilities(self.cap_registry, owner))

        # ---- output contract: strict, CANDIDATE-only --------------------------------------------- #
        output_schema = _output_schema(boundary, condition_inputs, target_text)
        escalation = _output_escalation(output_schema)
        if escalation:
            return _reject(GENOME_OUTPUT_CONTRACT_NOT_CANDIDATE, escalation)

        # ---- the ONE canonical genome ------------------------------------------------------------ #
        genome = AgentGenome(
            identity=identity,
            work_id=evaluation.work_id, problem_id=evaluation.problem_id,
            task_id=f"TASK-{identity.agent_id}",
            objective=(f"Propose a CANDIDATE for the differentiated condition->target "
                       f"'{boundary}' inside {family.value}; validation stays with {owner}"),
            questions=[f"Is the relationship '{boundary}' supported by the authorized evidence?"],
            predicates=[boundary],
            constraints=list(condition_inputs),
            authoritative_inputs=list(narrow_inputs),
            knowledge_sources=[source_reference or "structured_problem.relationships"],
            tools=tools,
            forbidden_operations=list(FORBIDDEN_OPERATIONS),
            model_requirements=ModelRequirement(min_context_tokens=2048, cost_class="LOW",
                                                latency_class="NORMAL", allow_fallback=False),
            dependencies=dependencies,
            output_schema=output_schema,
            evidence_requirements=[f"series:{s}" for s in (condition_inputs + [target_text])],
            uncertainty="UNKNOWN",
            execution_level="COGNITIVE",
            resource_budget=budget,
            validation_rules=[
                f"returns are validated by {owner} (external validation; never by this unit)",
                f"evidence must exist in the canonical registry ({len(real_evidence)} id(s) available)",
                "the unit returns a CANDIDATE (ReturnPackage); it can never validate, freeze or publish",
            ],
            freeze_requirement=False,
            human_escalation_rules=["escalate to EM Core when authorized evidence is missing"],
            return_to=owner,
            provenance=[
                f"LOOP 6 genome proposal from necessity verdict {evaluation.reason_code}",
                f"source: {source_reference or 'n/a'} | candidate {evaluation.candidate_id}",
                f"capability gap evidence: {evaluation.capability_gap_evidence}",
                "no provider selected (ModelRouter owns selection in LOOP 10)",
                "not authorized: created_by marks the genome as an UNAUTHORIZED PROPOSAL",
            ],
            created_by="PROPOSAL_NOT_AUTHORIZED",
            created_at=created,          # deterministic provenance (never the wall clock)
        )

        envelope = TaskEnvelope(
            envelope_id=f"ENV-{identity.agent_id}",
            work_id=genome.work_id, problem_id=genome.problem_id, task_id=genome.task_id,
            agent_id=genome.agent_id, genome_hash=genome.hash(),
            authorized_inputs=list(narrow_inputs),
            authorized_evidence_ids=list(evidence_refs),
            allowed_tools=list(tools),
            context={"boundary": boundary, "condition_inputs": list(condition_inputs),
                     "target": target_text, "cognitive_family": family.value},
            budget=budget,
            created_at=created,          # deterministic provenance (never the wall clock)
        )

        data = dict(base)
        data.update({
            "status": GenomeProposalStatus.PROPOSED,
            "genome": genome, "input_contract": envelope, "output_contract": output_schema,
            "dependencies": dependencies,
            "cognitive_owner": owner, "boundary": boundary,
            "evidence_refs": evidence_refs,
            "provenance": [
                *base["provenance"],
                f"{PROPOSAL_FROM_NECESSARY_VERDICT}: NECESSARY({evaluation.reason_code}) -> genome "
                f"proposal for '{boundary}'",
                f"family {family.value} owned by {owner}; network role {role.value} (narrowest)",
                f"budget {budget.model_dump()} derived from parent {parent.model_dump()} (no escalation)",
                "genome embedded unmodified; authority_scope=PROPOSER; output=CANDIDATE only",
                "no registration, no execution, no model call, no provider selection",
            ],
        })
        return AgentGenomeProposal(**data)


# ----------------------------------------------------------------------------------------------- #
# Internals (pure helpers; no I/O, no mutation, no provider)
# ----------------------------------------------------------------------------------------------- #
def _coerce_request(request: Optional[Any]) -> GenomeDesignRequest:
    """Turn a caller payload into a design request, refusing escalations with THEIR OWN code.

    An untrusted mapping is categorised BEFORE construction, so the refusal reason is specific
    (provider substitution, authority escalation, policy mutation, registry/runtime request,
    TaskNetwork mutation) instead of a generic validation error. Unknown fields also fail closed.
    """
    if request is None:
        return GenomeDesignRequest()
    if isinstance(request, GenomeDesignRequest):
        return request
    if not isinstance(request, dict):
        raise GenomeProposalError("INVALID_DESIGN_REQUEST", type(request).__name__)
    categories = (
        (_PROVIDER_REQUEST_KEYS, GENOME_PROVIDER_PIN),
        (_AUTHORITY_REQUEST_KEYS, GENOME_AUTHORITY_ESCALATION),
        (_POLICY_REQUEST_KEYS, GENOME_POLICY_MUTATION),
        (_REGISTRY_REQUEST_KEYS, GENOME_REGISTRY_REQUESTED),
        (_RUNTIME_REQUEST_KEYS, GENOME_RUNTIME_REQUESTED),
        (_TASKNETWORK_REQUEST_KEYS, GENOME_TASKNETWORK_MUTATION_REQUESTED),
    )
    for keys, code in categories:
        offending = [k for k in request.keys() if k in keys]
        if offending:
            raise GenomeProposalError(code, f"design request field(s) {offending} are not requestable")
    unknown = [k for k in request.keys() if k not in GenomeDesignRequest.model_fields]
    if unknown:
        raise GenomeProposalError("UNKNOWN_DESIGN_REQUEST_FIELD", f"{unknown}")
    return GenomeDesignRequest(**request)


def _assert_no_forbidden_request_fields(request: GenomeDesignRequest) -> None:
    assert isinstance(request, GenomeDesignRequest)
    for key in request.model_dump().keys():
        if key in _FORBIDDEN_REQUEST_KEYS:
            raise GenomeProposalError("FORBIDDEN_REQUEST_FIELD", key)
    for dep in request.requested_dependencies:
        lowered = (dep or "").lower()
        for token in ("register", "activate", "execute", "runtime", "publish", "freeze"):
            if token in lowered:
                raise GenomeProposalError("FORBIDDEN_REQUEST_VALUE", f"{dep} (contains '{token}')")


def _base_data(evaluation: NecessityEvaluation, candidate: Optional[ProblemCandidate],
               created: str) -> Dict[str, Any]:
    """The provenance/traceability base shared by proposals and rejections."""
    proposal_id = "PROP-" + hashlib.sha256(
        f"{PROPOSAL_VERSION}|{evaluation.work_id}|{evaluation.problem_id}|"
        f"{evaluation.candidate_id}|{evaluation.evaluation_id}".encode("utf-8")
    ).hexdigest()[:12].upper()
    return dict(
        proposal_id=proposal_id,
        work_id=evaluation.work_id, problem_id=evaluation.problem_id,
        candidate_id=evaluation.candidate_id, candidate_kind=evaluation.candidate_kind,
        necessity_decision=evaluation.decision.value,
        necessity_reason_code=evaluation.reason_code,
        source_reference=(candidate.source if candidate is not None else evaluation.source),
        cognitive_owner=evaluation.owner,
        boundary=(getattr(candidate, "reference", "") or "").strip(),
        capability_gap_evidence=evaluation.capability_gap_evidence,
        created_at=created,
        provenance=[
            f"LOOP 6 genome designer v{PROPOSAL_VERSION} — {PROPOSAL_AUTHORITY}",
            f"derived from necessity evaluation {evaluation.evaluation_id} of work "
            f"{evaluation.work_id} / problem {evaluation.problem_id}",
            "PROPOSAL ONLY: no registration, no activation, no execution, no model/provider call",
        ],
    )


def _family_of(owner: str) -> Optional[CognitiveFamily]:
    for family, mapped in FAMILY_OWNER.items():
        if mapped == owner:
            return family
    return None


def _select_role(request: GenomeDesignRequest) -> Tuple[Optional[NetworkRole], Optional[Tuple[str, str]]]:
    """Narrowest compatible network role. The constitutional nucleus can never be impersonated."""
    requested = request.requested_network_role
    if requested is None:
        return NetworkRole.SEGREGATOR, None            # narrowest default (bounded sub-unit)
    if requested is NetworkRole.CONSTITUTIONAL:
        return None, (GENOME_NETWORK_ROLE_REFUSED,
                      "an emergent unit can never claim the CONSTITUTIONAL nucleus")
    return requested, None


def _derive_budget(parent: ResourceBudget, request: GenomeDesignRequest
                   ) -> Tuple[Optional[ResourceBudget], Optional[Tuple[str, str]]]:
    """Derive the unit's budget as a CHILD of the parent (the existing no-escalation contract).

    The DEFAULT is deliberately narrower than the parent (an emergent unit is a bounded sub-unit);
    every override still has to pass ``ResourceBudget.child``, which fails closed on any increase.
    """
    overrides: Dict[str, int] = {
        "max_runtime_seconds": min(parent.max_runtime_seconds, 120),
        "max_model_calls": min(parent.max_model_calls, 2),
        "max_tokens": min(parent.max_tokens, 8000),
        "max_cost_units": min(parent.max_cost_units, 5),
    }
    for key, value in (request.requested_budget or {}).items():
        if key not in HARD_BUDGET:
            return None, (GENOME_BUDGET_ESCALATION, f"unknown budget field '{key}'")
        try:
            overrides[key] = int(value)
        except (TypeError, ValueError):
            return None, (GENOME_BUDGET_ESCALATION, f"budget field '{key}' is not an integer")
    try:
        budget = parent.child(**overrides)
    except AgentContractError as exc:
        return None, (GENOME_BUDGET_ESCALATION, f"{exc.reason_code}: {exc}")
    if budget.max_cost_units > HARD_BUDGET["max_cost_units"] or \
            budget.max_model_calls > HARD_BUDGET["max_model_calls"]:
        return None, (GENOME_BUDGET_ESCALATION, "budget exceeds the declared hard ceiling")
    return budget, None


def _derive_dependencies(agent_id: str, request: GenomeDesignRequest, canonical_state: Any
                         ) -> Tuple[List[AgentDependency], Optional[Tuple[str, str]]]:
    """Dependencies must be EXPLICIT, resolvable (existing agents), work-scoped and acyclic."""
    requested = [d for d in (request.requested_dependencies or []) if d]
    if not requested:
        return [], None                                  # nothing exists -> no dependency invented
    network = getattr(canonical_state, "agent_network", None)
    records = getattr(network, "records", None) or []
    existing: Dict[str, Any] = {}
    for record in records:
        genome = getattr(record, "genome", None)
        if genome is not None:
            existing[genome.agent_id] = genome
    unknown = [d for d in requested if d not in existing]
    if unknown:
        return None, (GENOME_DEPENDENCY_UNRESOLVABLE,
                      f"dependency(ies) {unknown} do not exist in this work (a dependency on a "
                      "non-existent agent is never invented, and no registry entry is created)")
    dependencies = [AgentDependency(agent_id=d, kind=AgentDependencyKind.DATA, required=True)
                    for d in requested]
    try:
        validate_dependencies(agent_id, dependencies)             # reused canonical check
    except AgentContractError as exc:
        return None, (GENOME_DEPENDENCY_UNRESOLVABLE, f"{exc.reason_code}: {exc}")
    edges: Dict[str, List[str]] = {agent_id: [d.agent_id for d in dependencies]}
    for existing_id, genome in existing.items():
        edges.setdefault(existing_id, [dep.agent_id for dep in (genome.dependencies or [])])
    cycle = detect_cycle(edges)                                   # reused canonical check
    if cycle:
        return None, (GENOME_DEPENDENCY_CYCLE, f"dependency cycle detected: {' -> '.join(cycle)}")
    return dependencies, None


def _identity_collision(identity: AgentIdentity, canonical_state: Any) -> Optional[str]:
    """One identity means ONE agent: an existing registered agent with this id is a collision."""
    network = getattr(canonical_state, "agent_network", None)
    for record in (getattr(network, "records", None) or []):
        genome = getattr(record, "genome", None)
        if genome is None or genome.agent_id != identity.agent_id:
            continue
        return (f"identity {identity.agent_id} already exists in this work "
                f"(one identity must mean one agent: REUSE/MERGE, never propose a duplicate)")
    return None


def _existing_coverage(canonical_state: Any, target: str) -> Optional[str]:
    """Is the responsibility already covered by an existing task? (anti-duplication at design time)"""
    token = (target or "").strip().lower()
    if not token or canonical_state is None:
        return None
    structured = getattr(getattr(canonical_state, "problem", None), "structured_problem", None)
    network = getattr(structured, "task_network", None)
    for task in (getattr(network, "tasks", None) or []):
        haystack = f"{task.description} {' '.join(task.expected_outputs or [])}".lower()
        if token in haystack:
            return f"task '{task.task_id}' (owner {task.owner})"
    return None


def _output_schema(boundary: str, condition_inputs: List[str], target: str) -> Dict[str, Any]:
    """The narrowest CANDIDATE output contract. No field can express validation/freeze/publish."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "boundary": {"type": "string", "const": boundary},
            "condition_inputs": {"type": "array",
                                 "items": {"type": "string", "enum": condition_inputs}},
            "target": {"type": "string", "const": target},
            "candidate_findings": {"type": "array", "maxItems": 8},
            "evidence_refs": {"type": "array", "items": {"type": "string"}},
            "uncertainty": {"type": "string", "enum": ["UNKNOWN", "LOW", "MEDIUM", "HIGH"]},
            "validation_status": {"type": "string", "const": OUTPUT_STATUS_CANDIDATE},
        },
        "required": ["boundary", "target", "validation_status"],
    }


def _output_escalation(schema: Dict[str, Any]) -> Optional[str]:
    """Any validation/freeze/publish/authorize value in the schema is an escalation."""
    for value in _walk_values(schema):
        if isinstance(value, str) and value.strip().upper() in _FORBIDDEN_OUTPUT_VALUES:
            return f"the output contract declares '{value}' (a unit may only return CANDIDATE)"
    return None


def _walk_values(node: Any) -> List[Any]:
    if isinstance(node, dict):
        out: List[Any] = []
        for value in node.values():
            out += _walk_values(value)
        return out
    if isinstance(node, list):
        out = []
        for item in node:
            out += _walk_values(item)
        return out
    return [node]


def _family_capabilities(registry: CapabilityRegistry, owner: str) -> List[Any]:
    if not registry:
        return []
    return [cap for cap in registry._capabilities.values()
            if getattr(cap, "canonical_em", None) == owner]


def _boundary_from(evaluation: NecessityEvaluation) -> str:
    if evaluation.input_contract and evaluation.output_contract:
        return f"{evaluation.input_contract} -> {evaluation.output_contract}"
    return ""


def _slug(text: str) -> str:
    cleaned = _SLUG_STRIP_RE.sub("_", (text or "").strip()).strip("_")
    return (cleaned[:64] or "Unknown")


def _context_slug(canonical_state: Any) -> str:
    problem = getattr(canonical_state, "problem", None)
    candidates = [
        getattr(problem, "context", None),
        ((getattr(getattr(problem, "structured_problem", None), "entities", None) or [None])[0]),
        getattr(problem, "domain_context", None),
    ]
    for value in candidates:
        if value and str(value).strip():
            return _slug(str(value))
    return "Work"


def _declared_symbols(canonical_state: Any, text: str) -> List[str]:
    lowered = (text or "").lower()
    return [s for s in _all_declared_symbols(canonical_state) if s.lower() in lowered]


def _all_declared_symbols(canonical_state: Any) -> List[str]:
    problem = getattr(canonical_state, "problem", None)
    structured = getattr(problem, "structured_problem", None)
    values: List[str] = []
    for source in (getattr(structured, "variables", None), getattr(structured, "entities", None),
                   getattr(problem, "entities", None)):
        values += [str(v).strip() for v in (source or []) if str(v).strip()]
    return list(dict.fromkeys(values))


def _is_broad_input(token: str) -> bool:
    lowered = (token or "").strip().lower()
    return lowered in ("*", "canonical_state", "canonicalworkstate", "whole_state", "everything",
                       "all_evidence", "all") or "*" in lowered