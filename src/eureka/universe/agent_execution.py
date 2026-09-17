"""EUREKA 5.1 — LOOP 11: AGENT EXECUTION BOUNDARY (execute a REGISTERED agent).

    AGENT REGISTERED -> VALIDATED AGENT -> EXECUTION REQUEST -> AgentRuntime -> VALIDATION ->
    DETERMINISTIC LOCAL PROVIDER -> RETURN PACKAGE -> EXECUTION RECORD -> EVIDENCE -> LIFECYCLE

This module ADDS NO EXECUTION AUTHORITY. ``AgentRuntime`` remains the ONE execution boundary (and
``AgentRegistry`` the ONE registration/lifecycle authority): here we only

  * PREPARE and VALIDATE the canonical ``ExecutionRequest`` that binds an execution to the
    REGISTERED agent, its registration request, its genome hash and its Work/Problem;
  * apply the DEPENDENCY GATE (declared dependencies must exist, be in-scope, not retired/failed and
    acyclic) — a gap the runtime did not cover;
  * delegate the actual execution to the EXISTING ``AgentRuntime.execute`` (one call, no retries);
  * OBSERVE and report the side effects (ledger) and the resulting canonical execution record.

Hard rules enforced here:
  * no agent is created (registration is LOOP 8's operation), no registry mutation beyond the
    canonical lifecycle transitions the runtime already performs, no TaskNetwork mutation, no
    canonical-identity mutation (fingerprint observed before/after);
  * the provider is the DETERMINISTIC LOCAL provider for this loop: NO real model call is made and
    the evidence never claims a real LLM;
  * the agent never receives the CanonicalWorkState: only the authorized TaskEnvelope.
"""
from __future__ import annotations

import datetime
import hashlib
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .agent_factory import (PROVIDER_SELECTION_DEFERRED, RegistrationRequest,
                            RegistrationRequestStatus)
from .agent_genome import (HARD_BUDGET, HASH_VERSION_V2, AgentContractError, AgentDependency,
                           AgentGenome, AgentStatus, TaskEnvelope, detect_cycle)
from .agent_genome_proposal import AgentGenomeProposal
from .agent_registry import CORE_ACTOR, AgentRegistry
from .agent_runtime import AgentRuntime
from .canonical_identity import canonical_state_fingerprint

EXECUTION_VERSION = "1.0"
#: Declared authority: prepare/validate/observe ONLY. The runtime executes.
EXECUTION_BOUNDARY_AUTHORITY = "EXECUTION_BOUNDARY_ONLY"

EXEC_READY_TO_EXECUTE = "EXEC_READY_TO_EXECUTE"
EXEC_REGISTRATION_REQUEST_MISSING = "EXEC_REGISTRATION_REQUEST_MISSING"
EXEC_REGISTRATION_NOT_VALIDATED = "EXEC_REGISTRATION_NOT_VALIDATED"
EXEC_PROPOSAL_MISSING = "EXEC_PROPOSAL_MISSING"
EXEC_AGENT_NOT_REGISTERED = "EXEC_AGENT_NOT_REGISTERED"
EXEC_GENOME_MISMATCH = "EXEC_GENOME_MISMATCH"
EXEC_HASH_VERSION_MISMATCH = "EXEC_HASH_VERSION_MISMATCH"
EXEC_ENVELOPE_MISMATCH = "EXEC_ENVELOPE_MISMATCH"
EXEC_SCOPE_MISMATCH = "EXEC_SCOPE_MISMATCH"
EXEC_LIFECYCLE_NOT_READY = "EXEC_LIFECYCLE_NOT_READY"
EXEC_DEPENDENCY_MISSING = "EXEC_DEPENDENCY_MISSING"
EXEC_DEPENDENCY_FAILED = "EXEC_DEPENDENCY_FAILED"
EXEC_DEPENDENCY_RETIRED = "EXEC_DEPENDENCY_RETIRED"
EXEC_DEPENDENCY_CROSS_WORK = "EXEC_DEPENDENCY_CROSS_WORK"
EXEC_DEPENDENCY_CROSS_PROBLEM = "EXEC_DEPENDENCY_CROSS_PROBLEM"
EXEC_DEPENDENCY_CYCLE = "EXEC_DEPENDENCY_CYCLE"
EXEC_BUDGET_INVALID = "EXEC_BUDGET_INVALID"
EXEC_BUDGET_ESCALATION = "EXEC_BUDGET_ESCALATION"
EXEC_REQUEST_TAMPERED = "EXEC_REQUEST_TAMPERED"
EXEC_ACTOR_UNAUTHORIZED = "EXEC_ACTOR_UNAUTHORIZED"
EXEC_RUNTIME_REFUSED = "EXEC_RUNTIME_REFUSED"

REASON_CODES = (EXEC_READY_TO_EXECUTE, EXEC_REGISTRATION_REQUEST_MISSING,
                EXEC_REGISTRATION_NOT_VALIDATED, EXEC_PROPOSAL_MISSING, EXEC_AGENT_NOT_REGISTERED,
                EXEC_GENOME_MISMATCH, EXEC_HASH_VERSION_MISMATCH, EXEC_ENVELOPE_MISMATCH,
                EXEC_SCOPE_MISMATCH, EXEC_LIFECYCLE_NOT_READY, EXEC_DEPENDENCY_MISSING,
                EXEC_DEPENDENCY_FAILED, EXEC_DEPENDENCY_RETIRED, EXEC_DEPENDENCY_CROSS_WORK,
                EXEC_DEPENDENCY_CROSS_PROBLEM, EXEC_DEPENDENCY_CYCLE, EXEC_BUDGET_INVALID,
                EXEC_BUDGET_ESCALATION, EXEC_REQUEST_TAMPERED, EXEC_ACTOR_UNAUTHORIZED,
                EXEC_RUNTIME_REFUSED)

#: The side-effect ledger keys (measured, never declared).
LEDGER_KEYS = ("agent_created", "registry_mutation", "runtime_execution", "model_call",
               "external_call", "tasknetwork_mutation", "canonical_mutation", "work_persistence",
               "evidence_persistence", "lifecycle_mutation")

#: Budget dimensions that PAY for an execution. A grant below 1 on any of them authorizes a call that
#: cannot be paid for, i.e. an IMPOSSIBLE execution. (max_depth/max_children are structural
#: allowances and may legitimately be 0 for a leaf agent, so they are deliberately NOT listed.)
CONSUMPTION_BUDGET = ("max_model_calls", "max_tokens", "max_runtime_seconds", "max_cost_units")


class ExecutionRequestStatus(str, Enum):
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"


class ExecutionOutcome(str, Enum):
    EXECUTED = "EXECUTED"        # the runtime produced a NEW execution record
    REUSED = "REUSED"            # the runtime returned the EXISTING record (canonical idempotency)
    BLOCKED = "BLOCKED"          # the runtime refused (fail closed)
    FAILED = "FAILED"            # the runtime executed but the model/validation failed
    REJECTED = "REJECTED"        # the execution REQUEST was refused (nothing was executed)


class ExecutionRejection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason_code: str = Field(..., min_length=1)
    detail: str = ""


class ExecutionRequest(BaseModel):
    """A FORMAL request to execute ONE registered agent for ONE authorized task.

    It is NOT authority: ``AgentRuntime`` still performs every execution check. This object binds the
    execution to the registration request, the genome hash and the Work/Problem, so a stale or
    manipulated execution is impossible.
    """

    model_config = ConfigDict(extra="forbid")

    execution_request_id: str = Field(..., min_length=1)
    execution_version: str = EXECUTION_VERSION
    authority: str = EXECUTION_BOUNDARY_AUTHORITY
    prepare_only: bool = True
    creates_agents: bool = False
    selects_provider: bool = False
    mutates_task_network: bool = False
    mutates_canonical_identity: bool = False
    provider_selection: str = PROVIDER_SELECTION_DEFERRED

    status: ExecutionRequestStatus = ExecutionRequestStatus.REJECTED
    reason_code: str = ""
    work_id: str = ""
    problem_id: str = ""
    agent_id: str = ""
    task_id: str = ""
    registration_request_id: str = ""
    genome_hash: str = ""
    genome_hash_version: str = ""
    attempt: int = Field(1, ge=1)
    envelope: Optional[TaskEnvelope] = None
    budget: Dict[str, int] = Field(default_factory=dict)
    dependencies: List[AgentDependency] = Field(default_factory=list)
    validation_checks: List[str] = Field(default_factory=list)
    rejections: List[ExecutionRejection] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _request_invariants(self) -> "ExecutionRequest":
        if self.authority != EXECUTION_BOUNDARY_AUTHORITY:
            raise ValueError("EXEC_REQUEST_AUTHORITY_CANNOT_BE_ESCALATED")
        for flag in ("prepare_only", "creates_agents", "selects_provider", "mutates_task_network",
                     "mutates_canonical_identity"):
            expected = True if flag == "prepare_only" else False
            if getattr(self, flag) is not expected:
                raise ValueError("EXEC_REQUEST_CANNOT_" + flag.upper())
        if self.provider_selection != PROVIDER_SELECTION_DEFERRED:
            raise ValueError("EXEC_REQUEST_PROVIDER_SELECTION_MUST_BE_DEFERRED")
        if self.status is ExecutionRequestStatus.VALIDATED:
            if self.rejections:
                raise ValueError("VALIDATED_EXEC_REQUEST_WITH_REJECTIONS")
            missing = [n for n in ("work_id", "problem_id", "agent_id", "task_id",
                                   "registration_request_id", "genome_hash",
                                   "genome_hash_version") if not getattr(self, n)]
            if missing:
                raise ValueError("EXEC_REQUEST_WITHOUT_TRACEABILITY:" + ",".join(missing))
            if self.envelope is None:
                raise ValueError("EXEC_REQUEST_WITHOUT_ENVELOPE")
            if self.genome_hash_version != HASH_VERSION_V2:
                raise ValueError(EXEC_HASH_VERSION_MISMATCH)
            if not self.validation_checks:
                raise ValueError("EXEC_REQUEST_WITHOUT_CHECKS")
        elif not self.rejections:
            raise ValueError("REJECTED_EXEC_REQUEST_WITHOUT_REASON")
        return self

    def is_validated(self) -> bool:
        return self.status is ExecutionRequestStatus.VALIDATED


class ExecutionReceipt(BaseModel):
    """FACTS observed from one execution attempt (granting nothing)."""

    model_config = ConfigDict(extra="forbid")

    receipt_id: str = Field(..., min_length=1)
    execution_request_id: str = ""
    execution_id: str = ""
    outcome: ExecutionOutcome = ExecutionOutcome.REJECTED
    reason_code: str = ""
    agent_id: str = ""
    work_id: str = ""
    problem_id: str = ""
    task_id: str = ""
    genome_hash: str = ""
    provider: str = ""
    model: str = ""
    real_model_call: bool = False
    record_status: str = ""
    return_status: str = ""
    latency_ms: Optional[float] = None
    evidence_refs: List[str] = Field(default_factory=list)
    side_effects: Dict[str, int] = Field(default_factory=dict)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""

    @model_validator(mode="after")
    def _receipt_invariants(self) -> "ExecutionReceipt":
        if self.real_model_call:
            raise ValueError("LOOP 11 MUST NOT CLAIM A REAL MODEL CALL")
        for key in LEDGER_KEYS:
            self.side_effects.setdefault(key, 0)
        return self

    def is_executed(self) -> bool:
        return self.outcome in (ExecutionOutcome.EXECUTED, ExecutionOutcome.REUSED)


def _execution_request_id(work_id: str, problem_id: str, agent_id: str, genome_hash: str,
                          registration_request_id: str, attempt: int) -> str:
    blob = f"{EXECUTION_VERSION}|{work_id}|{problem_id}|{agent_id}|{genome_hash}|" \
           f"{registration_request_id}|{attempt}"
    return "EXREQ-" + hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12].upper()


def _dependency_gate(genome: AgentGenome, registry: AgentRegistry) -> Optional[tuple]:
    """Declared dependencies must exist in-scope, not retired/failed, and be acyclic."""
    if not genome.dependencies:
        return None
    edges: Dict[str, List[str]] = {genome.agent_id: [d.agent_id for d in genome.dependencies]}
    for dependency in genome.dependencies:
        record = registry.get(dependency.agent_id)
        if record is None:
            return (EXEC_DEPENDENCY_MISSING, f"dependency {dependency.agent_id} is not registered")
        dep_genome = record.genome
        if dep_genome.work_id != genome.work_id:
            return (EXEC_DEPENDENCY_CROSS_WORK, f"{dependency.agent_id} belongs to another work")
        if dep_genome.problem_id != genome.problem_id:
            return (EXEC_DEPENDENCY_CROSS_PROBLEM, f"{dependency.agent_id} belongs to another problem")
        status = record.status
        if status is AgentStatus.RETIRED:
            return (EXEC_DEPENDENCY_RETIRED, f"{dependency.agent_id} is RETIRED")
        if status in (AgentStatus.FAILED, AgentStatus.BLOCKED, AgentStatus.REVISION_REQUIRED):
            return (EXEC_DEPENDENCY_FAILED, f"{dependency.agent_id} is {status.value}")
        if dependency.required and status not in (AgentStatus.VALIDATED, AgentStatus.FROZEN,
                                                  AgentStatus.COMPLETED, AgentStatus.READY,
                                                  AgentStatus.RUNNING, AgentStatus.RETURNED,
                                                  AgentStatus.VALIDATION_REQUIRED,
                                                  AgentStatus.CREATED):
            return (EXEC_DEPENDENCY_FAILED, f"{dependency.agent_id} is not usable ({status.value})")
        edges.setdefault(dependency.agent_id,
                         [d.agent_id for d in (dep_genome.dependencies or [])])
    cycle = detect_cycle(edges)
    if cycle:
        return (EXEC_DEPENDENCY_CYCLE, f"dependency cycle: {' -> '.join(cycle)}")
    return None


def prepare_execution_request(
    registration_request: Optional[RegistrationRequest],
    proposal: Optional[AgentGenomeProposal],
    *,
    canonical_state: Any,
    registry: Optional[AgentRegistry] = None,
    actor: str = CORE_ACTOR,
    attempt: int = 1,
    now: Optional[str] = None,
) -> ExecutionRequest:
    """Build (and validate) the canonical ExecutionRequest for a REGISTERED agent. Read-only."""
    created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()
    registry = registry or AgentRegistry.rebuild_from(canonical_state)
    genome: Optional[AgentGenome] = proposal.genome if proposal is not None else None
    base = dict(
        execution_request_id="PENDING", attempt=attempt, created_at=created,
        work_id=(genome.work_id if genome is not None else ""),
        problem_id=(genome.problem_id if genome is not None else ""),
        agent_id=(genome.agent_id if genome is not None else ""),
        task_id=(genome.task_id if genome is not None else ""),
        registration_request_id=(registration_request.request_id
                                 if registration_request is not None else ""),
        provenance=[f"LOOP 11 execution boundary v{EXECUTION_VERSION} — "
                    f"{EXECUTION_BOUNDARY_AUTHORITY}",
                    "AgentRuntime remains the ONE execution authority; AgentRegistry the ONE "
                    "registration/lifecycle authority"],
    )

    def _reject(code: str, detail: str) -> ExecutionRequest:
        data = dict(base)
        data.update({"status": ExecutionRequestStatus.REJECTED, "reason_code": code,
                     "rejections": [ExecutionRejection(reason_code=code, detail=detail)]})
        data["provenance"] = [*base["provenance"], detail]
        return ExecutionRequest(**data)

    if actor != CORE_ACTOR:
        return _reject(EXEC_ACTOR_UNAUTHORIZED,
                       f"actor '{actor}' may not request an execution (only EM Core does)")
    if registration_request is None:
        return _reject(EXEC_REGISTRATION_REQUEST_MISSING, "no RegistrationRequest was supplied")
    if getattr(registration_request.status, "value", registration_request.status) \
            != RegistrationRequestStatus.VALIDATED.value:
        return _reject(EXEC_REGISTRATION_NOT_VALIDATED,
                       f"the registration request is {registration_request.status}")
    if proposal is None or genome is None:
        return _reject(EXEC_PROPOSAL_MISSING, "the proposal that owns the genome is required")
    # The AUTHORITATIVE grant is the envelope the REGISTRATION validated — never a mutable copy.
    envelope = registration_request.input_contract
    if envelope is None:
        return _reject(EXEC_ENVELOPE_MISMATCH, "the validated registration carries no input contract")
    proposal_envelope = proposal.input_contract
    if proposal_envelope is not None and \
            proposal_envelope.model_dump(mode="json") != envelope.model_dump(mode="json"):
        return _reject(EXEC_ENVELOPE_MISMATCH,
                       "the proposal's envelope differs from the VALIDATED one (widening attempt)")

    record = registry.get(genome.agent_id)
    if record is None:
        return _reject(EXEC_AGENT_NOT_REGISTERED, f"{genome.agent_id} is not registered")
    if record.genome.hash() != genome.hash():
        return _reject(EXEC_GENOME_MISMATCH,
                       "the registered genome differs from the proposed genome (stale or tampered)")
    if genome.hash_version() != HASH_VERSION_V2:
        return _reject(EXEC_HASH_VERSION_MISMATCH, genome.hash_version())
    if registration_request.agent_id != genome.agent_id:
        return _reject(EXEC_GENOME_MISMATCH, "the registration request names another agent")
    try:
        envelope.assert_matches(genome)
    except AgentContractError as exc:
        if exc.reason_code == "ENVELOPE_GENOME_MISMATCH":
            return _reject(EXEC_ENVELOPE_MISMATCH, "the envelope authorizes a different genome hash")
        return _reject(EXEC_ENVELOPE_MISMATCH, f"{exc.reason_code}: {exc}")

    # A proposal and a registration request DECLARE the scope they belong to (LOOP 6 traceability).
    # A declaration that disagrees with the genome it carries is a SCOPE LIE, and it is refused even
    # when the envelope, the registry record and the genome are internally consistent among themselves.
    for owner, declared_obj in (("proposal", proposal),
                                ("registration request", registration_request)):
        for field, label in (("work_id", "work"), ("problem_id", "problem")):
            declared = getattr(declared_obj, field, "") or ""
            actual = getattr(genome, field, "") or ""
            if declared and declared != actual:
                return _reject(EXEC_SCOPE_MISMATCH,
                               f"the {owner} declares {label} {declared} but its genome is {actual}")

    work_id = getattr(getattr(canonical_state, "work", None), "work_id", "")
    problem_id = getattr(getattr(canonical_state, "problem", None), "problem_id", "")
    if (work_id and work_id != genome.work_id) or (problem_id and problem_id != genome.problem_id):
        return _reject(EXEC_SCOPE_MISMATCH,
                       f"genome scope {genome.work_id}/{genome.problem_id} != state "
                       f"{work_id}/{problem_id}")
    if envelope.work_id != genome.work_id or envelope.problem_id != genome.problem_id:
        return _reject(EXEC_SCOPE_MISMATCH, "the envelope scope differs from the genome scope")

    if record.status is not AgentStatus.READY:
        return _reject(EXEC_LIFECYCLE_NOT_READY,
                       f"the agent is {record.status.value}; execution requires READY")

    dependency_verdict = _dependency_gate(genome, registry)
    if dependency_verdict is not None:
        return _reject(*dependency_verdict)

    budget = envelope.budget.model_dump(mode="json")
    for key, ceiling in HARD_BUDGET.items():
        value = budget.get(key, 0)
        if not isinstance(value, int) or value < 0:
            return _reject(EXEC_BUDGET_INVALID, f"{key}={value!r}")
        if value > ceiling:
            return _reject(EXEC_BUDGET_ESCALATION, f"{key}={value} > ceiling {ceiling}")
        if value > getattr(genome.resource_budget, key):
            return _reject(EXEC_BUDGET_ESCALATION,
                           f"{key}={value} > the genome budget "
                           f"{getattr(genome.resource_budget, key)}")
    # A grant that cannot pay for what it authorizes is an IMPOSSIBLE execution, not an escalation.
    for key in CONSUMPTION_BUDGET:
        if int(budget.get(key, 0)) < 1:
            return _reject(EXEC_BUDGET_INVALID, f"{key}={budget.get(key)} (no execution possible)")

    if (registration_request.provider_selection != PROVIDER_SELECTION_DEFERRED
            or registration_request.authority_scope != "PROPOSER"
            or registration_request.output_contract.get("properties", {})
                .get("validation_status", {}).get("const") != "CANDIDATE"):
        return _reject(EXEC_REQUEST_TAMPERED,
                       "the registration request's authority/provider/output invariants were altered")

    genome_hash = genome.hash()
    checks = ["registration_request_is_validated", "agent_is_registered", "genome_matches_registry",
              "hash_version_is_v2", "envelope_matches_genome", "work_scope", "problem_scope",
              "lifecycle_is_ready", "dependencies_ok", "budget_within_genome_and_ceiling",
              "request_invariants_hold"]
    data = dict(base)
    data.update({
        "execution_request_id": _execution_request_id(genome.work_id, genome.problem_id,
                                                      genome.agent_id, genome_hash,
                                                      registration_request.request_id, attempt),
        "status": ExecutionRequestStatus.VALIDATED,
        "reason_code": EXEC_READY_TO_EXECUTE,
        "genome_hash": genome_hash,
        "genome_hash_version": genome.hash_version(),
        "envelope": envelope,
        "budget": budget,
        "dependencies": list(genome.dependencies),
        "validation_checks": checks,
        "provenance": [
            *base["provenance"],
            f"{EXEC_READY_TO_EXECUTE}: registration {registration_request.request_id} -> "
            f"{genome.agent_id} (READY, hash {genome_hash[:12]}...)",
            "the agent receives ONLY its authorized TaskEnvelope (never the CanonicalWorkState)",
        ],
    })
    return ExecutionRequest(**data)


def _ledger(registry: AgentRegistry, provider: Any, *, count_before: int, executions_before: int,
            model_calls_before: int, lifecycle_before: int) -> Dict[str, int]:
    """MEASURE the side effects of one execution (deltas observed, never declared)."""
    ledger = {key: 0 for key in LEDGER_KEYS}
    ledger["runtime_execution"] = 1
    ledger["model_call"] = max(0, len(getattr(provider, "calls", [])) - model_calls_before)
    ledger["agent_created"] = max(0, registry.count() - count_before)
    ledger["registry_mutation"] = ledger["agent_created"]
    ledger["lifecycle_mutation"] = sum(len(r.history) for r in registry.snapshot().records) \
        - lifecycle_before
    ledger["external_call"] = 0                       # the deterministic provider never leaves the box
    ledger["tasknetwork_mutation"] = 0                # set by the caller from a dump comparison
    ledger["canonical_mutation"] = 0                  # set by the caller from a fingerprint comparison
    ledger["work_persistence"] = 0                    # the caller decides when to persist
    ledger["evidence_persistence"] = 0                # evidence is referenced, never invented
    return ledger


class RegisteredAgentExecutor:
    """Consumes a VALIDATED ExecutionRequest and DELEGATES the execution to AgentRuntime.

    It executes nothing itself: no provider call, no lifecycle write, no record write, no store. It
    only prepares the request, observes the outcome and reports the measured side effects.
    """

    AUTHORITY = EXECUTION_BOUNDARY_AUTHORITY

    def __init__(self, registry: AgentRegistry, runtime: AgentRuntime) -> None:
        self.registry = registry
        self.runtime = runtime

    def execute(
        self,
        request: Optional[ExecutionRequest],
        proposal: Optional[AgentGenomeProposal],
        *,
        canonical_state: Any,
        now: Optional[str] = None,
    ) -> ExecutionReceipt:
        created = now or datetime.datetime.now(datetime.timezone.utc).isoformat()

        def _reject(code: str, detail: str, request_obj: Optional[ExecutionRequest] = None):
            return ExecutionReceipt(
                receipt_id="EXRCP-" + (request_obj.execution_request_id[6:]
                                       if request_obj is not None else "MISSING"),
                execution_request_id=request_obj.execution_request_id if request_obj else "",
                outcome=ExecutionOutcome.REJECTED, reason_code=code,
                agent_id=request_obj.agent_id if request_obj else "",
                work_id=request_obj.work_id if request_obj else "",
                problem_id=request_obj.problem_id if request_obj else "",
                task_id=request_obj.task_id if request_obj else "",
                genome_hash=request_obj.genome_hash if request_obj else "",
                provider=self.runtime.provider.name, model=getattr(self.runtime.provider, "model", ""),
                side_effects={key: 0 for key in LEDGER_KEYS},
                provenance=[detail], created_at=created)

        if not isinstance(request, ExecutionRequest):
            return _reject("EXEC_REQUEST_MISSING", "no ExecutionRequest was supplied")
        if not request.is_validated():
            return _reject(EXEC_RUNTIME_REFUSED,
                           f"the execution request is {request.status.value}; nothing was executed",
                           request)
        expected_id = _execution_request_id(request.work_id, request.problem_id, request.agent_id,
                                            request.genome_hash, request.registration_request_id,
                                            request.attempt)
        if expected_id != request.execution_request_id:
            return _reject(EXEC_REQUEST_TAMPERED,
                           f"execution request identity {request.execution_request_id} does not "
                           f"match its bindings ({expected_id})", request)
        if proposal is None or proposal.genome is None:
            return _reject(EXEC_PROPOSAL_MISSING, "the proposal that owns the genome is required",
                           request)
        genome = proposal.genome
        envelope = request.envelope

        fingerprint_before = canonical_state_fingerprint(canonical_state)
        network_before = canonical_state.problem.structured_problem.task_network.model_dump(mode="json") \
            if canonical_state.problem and canonical_state.problem.structured_problem else None
        count_before = self.registry.count()
        executions_before = len(self.registry.snapshot().executions)
        model_calls_before = len(getattr(self.runtime.provider, "calls", []))
        lifecycle_before = sum(len(r.history) for r in self.registry.snapshot().records)

        execution = self.runtime.execute(genome, envelope, attempt=request.attempt)

        ledger = _ledger(self.registry, self.runtime.provider, count_before=count_before,
                         executions_before=executions_before, model_calls_before=model_calls_before,
                         lifecycle_before=lifecycle_before)
        fingerprint_after = canonical_state_fingerprint(canonical_state)
        ledger["canonical_mutation"] = int(fingerprint_after != fingerprint_before)
        if network_before is not None:
            network_after = canonical_state.problem.structured_problem.task_network.model_dump(mode="json")
            ledger["tasknetwork_mutation"] = int(network_after != network_before)
        created_record = len(self.registry.snapshot().executions) > executions_before

        if execution.failure_reason and execution.status is AgentStatus.BLOCKED:
            outcome = ExecutionOutcome.BLOCKED
        elif execution.status is AgentStatus.FAILED:
            outcome = ExecutionOutcome.FAILED
        elif execution.status is AgentStatus.VALIDATION_REQUIRED and execution.finished_at:
            outcome = ExecutionOutcome.EXECUTED if created_record else ExecutionOutcome.REUSED
        else:
            outcome = ExecutionOutcome.BLOCKED

        return ExecutionReceipt(
            receipt_id=f"EXRCP-{request.execution_request_id[6:]}",
            execution_request_id=request.execution_request_id,
            execution_id=execution.execution_id,
            outcome=outcome,
            reason_code=(EXEC_READY_TO_EXECUTE if outcome in (ExecutionOutcome.EXECUTED,
                                                             ExecutionOutcome.REUSED)
                         else (execution.failure_reason or EXEC_RUNTIME_REFUSED)),
            agent_id=genome.agent_id, work_id=genome.work_id, problem_id=genome.problem_id,
            task_id=genome.task_id, genome_hash=execution.genome_hash,
            provider=execution.provider, model=execution.model, real_model_call=False,
            record_status=execution.status.value,
            return_status=(execution.return_package.status.value
                           if execution.return_package is not None else ""),
            latency_ms=execution.latency_ms, evidence_refs=list(execution.evidence_ids),
            side_effects=ledger,
            provenance=[
                f"LOOP 11 execution boundary: request {request.execution_request_id} -> "
                f"execution {execution.execution_id} ({execution.status.value})",
                f"provider {execution.provider} (DETERMINISTIC LOCAL; no real model call)",
                "AgentRuntime performed every execution check; AgentRegistry every lifecycle write",
            ],
            created_at=created)
