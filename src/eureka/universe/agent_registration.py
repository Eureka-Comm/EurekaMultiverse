"""EUREKA 5.1 — LOOP 8: AGENT REGISTRATION BOUNDARY (the first intentional registration).

    VALIDATED RegistrationRequest -> AgentRegistry.register() -> registered (CREATED) agent

This is the FIRST loop in which agent registration is intentionally permitted; it is also the ONLY
operation this module performs. It adds NO authority:

  * ``AgentRegistry`` remains the SOLE registration authority — the registrar CONSUMES a validated
    request and delegates the write to ``AgentRegistry.register`` (actor = EM Core);
  * registration is WORK/PROBLEM-scoped, idempotent for identical content and fail-closed for
    incompatible duplicates (the registry's own guards are reused, not re-implemented);
  * the request is RE-VALIDATED (LOOP 7's ``AgentFactory.validate_registration_request``) before any
    write, so a stale/mutated proposal can never be registered;
  * the genome hash uses the REPAIRED F11 semantics (LOOP 6R semantic hash + version);
  * NO activation (the record is created in CREATED), NO runtime execution, NO model/provider call,
    NO publication, NO new store, NO canonical-state mutation beyond the new agent record itself;
  * durable traceability needs no new field: the lifecycle event and the record provenance carry the
    ``request_id`` (the existing canonical container is the audit trail).
"""
from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_factory import (AgentFactory, PROVIDER_SELECTION_DEFERRED, RegistrationRequest,
                            RegistrationRequestStatus, _content_hash)
from .agent_genome import AgentGenome
from .agent_genome_proposal import AgentGenomeProposal
from .agent_registry import CORE_ACTOR, AgentRegistry

REGISTRATION_VERSION = "1.0"
#: Declared authority: this module registers and NOTHING else.
REGISTRAR_AUTHORITY = "REGISTRATION_ONLY"

REGISTRATION_FROM_VALIDATED_REQUEST = "REGISTRATION_FROM_VALIDATED_REQUEST"
REGISTRATION_REQUEST_MISSING = "REGISTRATION_REQUEST_MISSING"
REGISTRATION_REQUEST_NOT_VALIDATED = "REGISTRATION_REQUEST_NOT_VALIDATED"
REGISTRATION_PROPOSAL_MISSING = "REGISTRATION_PROPOSAL_MISSING"
REGISTRATION_STALE_REQUEST = "REGISTRATION_STALE_REQUEST"
REGISTRATION_CONTENT_MISMATCH = "REGISTRATION_CONTENT_MISMATCH"
REGISTRATION_IDENTITY_MISMATCH = "REGISTRATION_IDENTITY_MISMATCH"
REGISTRATION_SCOPE_MISMATCH = "REGISTRATION_SCOPE_MISMATCH"
REGISTRATION_DUPLICATE_INCOMPATIBLE = "REGISTRATION_DUPLICATE_INCOMPATIBLE"
REGISTRATION_ACTOR_UNAUTHORIZED = "REGISTRATION_ACTOR_UNAUTHORIZED"
REGISTRATION_REGISTRY_REFUSED = "REGISTRATION_REGISTRY_REFUSED"
REGISTRATION_REQUEST_TAMPERED = "REGISTRATION_REQUEST_TAMPERED"

#: The canonical values the request must still declare (altering them invalidates the request).
PROPOSER_SCOPE = "PROPOSER"
CANDIDATE_STATUS = "CANDIDATE"

REASON_CODES = (REGISTRATION_FROM_VALIDATED_REQUEST, REGISTRATION_REQUEST_MISSING,
                REGISTRATION_REQUEST_NOT_VALIDATED, REGISTRATION_PROPOSAL_MISSING,
                REGISTRATION_STALE_REQUEST, REGISTRATION_CONTENT_MISMATCH,
                REGISTRATION_IDENTITY_MISMATCH, REGISTRATION_SCOPE_MISMATCH,
                REGISTRATION_DUPLICATE_INCOMPATIBLE, REGISTRATION_ACTOR_UNAUTHORIZED,
                REGISTRATION_REGISTRY_REFUSED, REGISTRATION_REQUEST_TAMPERED)


class RegistrationOutcome(str, Enum):
    REGISTERED = "REGISTERED"          # a new record was created
    REUSED = "REUSED"                  # identical content was already registered (idempotent)
    REJECTED = "REJECTED"              # nothing was written (fail closed)


class RegistrationReceipt(BaseModel):
    """The result of one registration attempt. It records FACTS, and grants nothing."""

    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(..., min_length=1)
    registration_version: str = REGISTRATION_VERSION
    authority: str = REGISTRAR_AUTHORITY
    registration_only: bool = True
    activates_agents: bool = False
    executes_agents: bool = False
    calls_model: bool = False
    selects_provider: bool = False
    publishes: bool = False
    mutates_task_network: bool = False
    provider_selection: str = PROVIDER_SELECTION_DEFERRED

    outcome: RegistrationOutcome = RegistrationOutcome.REJECTED
    reason_code: str = ""
    request_id: str = ""
    proposal_id: str = ""
    agent_id: str = ""
    work_id: str = ""
    problem_id: str = ""
    genome_hash: str = ""
    genome_hash_version: str = ""
    record_status: str = ""
    idempotent: bool = False
    registry_count_before: int = 0
    registry_count_after: int = 0
    lifecycle_reason: str = ""
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _receipt_invariants(self) -> "RegistrationReceipt":
        if self.authority != REGISTRAR_AUTHORITY:
            raise ValueError("RECEIPT_AUTHORITY_CANNOT_BE_ESCALATED")
        for flag in ("registration_only", "activates_agents", "executes_agents", "calls_model",
                     "selects_provider", "publishes", "mutates_task_network"):
            expected = True if flag == "registration_only" else False
            if getattr(self, flag) is not expected:
                raise ValueError("RECEIPT_CANNOT_" + flag.upper())
        if self.provider_selection != PROVIDER_SELECTION_DEFERRED:
            raise ValueError("RECEIPT_PROVIDER_SELECTION_MUST_BE_DEFERRED")
        if self.outcome is not RegistrationOutcome.REJECTED:
            missing = [name for name in ("request_id", "agent_id", "work_id", "problem_id",
                                         "genome_hash", "genome_hash_version", "record_status")
                       if not getattr(self, name)]
            if missing:
                raise ValueError("RECEIPT_WITHOUT_TRACEABILITY:" + ",".join(missing))
            if self.reason_code != REGISTRATION_FROM_VALIDATED_REQUEST:
                raise ValueError("RECEIPT_WITHOUT_REGISTRATION_REASON")
        elif not self.reason_code:
            raise ValueError("REJECTED_RECEIPT_WITHOUT_REASON")
        return self

    def is_registered(self) -> bool:
        return self.outcome in (RegistrationOutcome.REGISTERED, RegistrationOutcome.REUSED)


class AgentRegistrar:
    """Consumes a VALIDATED RegistrationRequest and delegates the write to the AgentRegistry.

    Public surface: ``register``. There is deliberately NO method that activates, executes, routes,
    publishes, selects a provider or mutates the TaskNetwork.
    """

    AUTHORITY = REGISTRAR_AUTHORITY

    def __init__(self, capability_registry: Any) -> None:
        self.cap_registry = capability_registry
        self._factory = AgentFactory(capability_registry)     # reused validator (no second gate)

    # ------------------------------------------------------------------ public API ------------- #
    def register(
        self,
        request: Optional[RegistrationRequest],
        proposal: Optional[AgentGenomeProposal],
        *,
        canonical_state: Any,
        actor: str = CORE_ACTOR,
        now: Optional[str] = None,
    ) -> RegistrationReceipt:
        """Register the genome a VALIDATED request refers to. Writes ONLY through the registry.

        ``actor`` may only be EM Core: no agent (and no other caller) can register itself, and the
        registry re-checks the actor as defence in depth.
        """
        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
        registry = AgentRegistry.rebuild_from(canonical_state)
        base = dict(
            receipt_id="RCP-" + (request.request_id[4:] if request is not None else "MISSING"),
            request_id=request.request_id if request is not None else "",
            proposal_id=request.proposal_id if request is not None else "",
            agent_id=request.agent_id if request is not None else "",
            work_id=request.work_id if request is not None else "",
            problem_id=request.problem_id if request is not None else "",
            registry_count_before=registry.count(),
            registry_count_after=registry.count(),
            created_at=created,
            provenance=[f"LOOP 8 registration boundary v{REGISTRATION_VERSION} — {REGISTRAR_AUTHORITY}",
                        "the AgentRegistry remains the SOLE registration authority"],
        )

        def _reject(code: str, detail: str) -> RegistrationReceipt:
            data = dict(base)
            data.update({"outcome": RegistrationOutcome.REJECTED, "reason_code": code})
            data["provenance"] = [*base["provenance"], detail]
            return RegistrationReceipt(**data)

        # ---- 1/2/3. presence, actor and request status ---------------------------------------- #
        if not isinstance(request, RegistrationRequest):
            return _reject(REGISTRATION_REQUEST_MISSING, "no RegistrationRequest was supplied")
        if actor != CORE_ACTOR:
            return _reject(REGISTRATION_ACTOR_UNAUTHORIZED,
                           f"actor '{actor}' may not register agents (only EM Core creates agents)")
        status_value = getattr(request.status, "value", request.status)
        if status_value != RegistrationRequestStatus.VALIDATED.value:
            return _reject(REGISTRATION_REQUEST_NOT_VALIDATED,
                           f"the request status is {status_value}; only VALIDATED requests may be "
                           "registered")
        if proposal is None or proposal.genome is None:
            return _reject(REGISTRATION_PROPOSAL_MISSING,
                           "the proposal that produced the request is required (the request carries "
                           "references, never the genome itself)")
        genome: AgentGenome = proposal.genome

        # ---- 4/5/6. identity, scope and content (specific codes before the broad staleness gate) - #
        if genome.agent_id != request.agent_id:
            return _reject(REGISTRATION_IDENTITY_MISMATCH,
                           f"genome {genome.agent_id} != request {request.agent_id}")
        work_id = getattr(getattr(canonical_state, "work", None), "work_id", "")
        problem_id = getattr(getattr(canonical_state, "problem", None), "problem_id", "")
        if (work_id and work_id != request.work_id) or (problem_id and problem_id != request.problem_id):
            return _reject(REGISTRATION_SCOPE_MISMATCH,
                           f"request scope {request.work_id}/{request.problem_id} != state "
                           f"{work_id}/{problem_id}")
        if _content_hash(genome) != request.genome_content_reference:
            return _reject(REGISTRATION_CONTENT_MISMATCH,
                           "the genome does not match the content the request was validated for")
        if (request.provider_selection != PROVIDER_SELECTION_DEFERRED
                or request.authority_scope != PROPOSER_SCOPE
                or request.output_contract.get("properties", {})
                    .get("validation_status", {}).get("const") != CANDIDATE_STATUS):
            return _reject(REGISTRATION_REQUEST_TAMPERED,
                           "the request's authority/provider/output invariants were altered after "
                           "validation")

        # ---- 7. idempotency is decided BEFORE the LOOP 7 re-validation: an already-registered
        #         IDENTICAL agent is a legitimate REUSE, while LOOP 7's gate (correctly) refuses to
        #         PREPARE a request for an identity that already exists ------------------------- #
        try:                                     # resolve() fails closed when the agent is unknown
            existing = registry.resolve(genome.agent_id)
        except Exception:
            existing = None
        if existing is not None:
            if existing.genome.hash() != genome.hash():
                return _reject(REGISTRATION_DUPLICATE_INCOMPATIBLE,
                               f"a DIFFERENT genome is already registered as {genome.agent_id}")
            return self._receipt(base, registry, request, genome, existing,
                                 RegistrationOutcome.REUSED, idempotent=True, created=created)

        # ---- re-validate (REUSE of the LOOP 7 gate): staleness / proposal mutation -------------- #
        fresh = self._factory.validate_registration_request(
            request, proposal=proposal,
            compilation=getattr(canonical_state, "problem_compilation", None),
            canonical_state=canonical_state, now=created)
        if fresh.status is not RegistrationRequestStatus.VALIDATED:
            return _reject(REGISTRATION_STALE_REQUEST,
                           f"re-validation refused the request: {fresh.rejection_codes()}")
        if fresh.genome_content_reference != request.genome_content_reference:
            return _reject(REGISTRATION_CONTENT_MISMATCH, "genome content reference changed")

        # ---- 8. the ONE write: delegated to the registry (actor = EM Core) --------------------- #
        lifecycle_reason = f"RegistrationRequest {request.request_id} (VALIDATED, LOOP 7 gate)"
        try:
            record = registry.register(genome, actor=actor, reason=lifecycle_reason)
        except Exception as exc:                                  # fail closed, nothing written
            code = getattr(exc, "reason_code", "REGISTRY_REFUSED")
            if code == "DUPLICATE_AGENT":
                return _reject(REGISTRATION_DUPLICATE_INCOMPATIBLE,
                               f"an incompatible genome is already registered as {genome.agent_id}")
            if code == "UNAUTHORIZED_ACTOR":
                return _reject(REGISTRATION_ACTOR_UNAUTHORIZED, str(exc))
            if code in ("CROSS_WORK_CONTAMINATION", "CROSS_PROBLEM_CONTAMINATION",
                        "CONSTITUTIONAL_IMPERSONATION", "CROSS_WORK_REFERENCE"):
                return _reject(REGISTRATION_SCOPE_MISMATCH, f"{code}: {exc}")
            return _reject(REGISTRATION_REGISTRY_REFUSED, f"{code}: {exc}")

        idempotent = existing is not None and existing is record
        return self._receipt(base, registry, request, genome, record,
                             RegistrationOutcome.REUSED if idempotent
                             else RegistrationOutcome.REGISTERED,
                             idempotent=idempotent, created=created)

    # ------------------------------------------------------------------ internals -------------- #
    def _receipt(self, base: dict, registry: AgentRegistry, request: RegistrationRequest,
                 genome: AgentGenome, record: Any, outcome: RegistrationOutcome, *,
                 idempotent: bool, created: str) -> RegistrationReceipt:
        """Build the success/reuse receipt for a record that the REGISTRY owns."""
        lifecycle_reason = f"RegistrationRequest {request.request_id} (VALIDATED, LOOP 7 gate)"
        data = dict(base)
        data.update({
            "outcome": outcome,
            "reason_code": REGISTRATION_FROM_VALIDATED_REQUEST,
            "genome_hash": record.genome.hash(),
            "genome_hash_version": record.genome.hash_version(),
            "record_status": record.status.value,
            "idempotent": idempotent,
            "registry_count_after": registry.count(),
            "lifecycle_reason": lifecycle_reason,
            "provenance": [
                *base["provenance"],
                f"{REGISTRATION_FROM_VALIDATED_REQUEST}: request {request.request_id} -> "
                f"{genome.agent_id} ({record.status.value})",
                "the request_id is recorded in the record's lifecycle event (durable traceability)",
                "no activation, no execution, no model call, no publication",
            ],
        })
        return RegistrationReceipt(**data)
