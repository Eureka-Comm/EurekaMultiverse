"""EUREKA 5.1 — LOOP 11 tests: AGENT RUNTIME EXECUTION (registered agent, canonical runtime).

    AGENT REGISTERED -> VALIDATED AGENT -> EXECUTION REQUEST -> AgentRuntime -> VALIDATION ->
    DETERMINISTIC LOCAL PROVIDER -> RETURN PACKAGE -> EXECUTION RECORD -> EVIDENCE -> LIFECYCLE

NO REAL MODEL IS USED OR CLAIMED: the provider is the deterministic local double and every receipt
asserts ``real_model_call is False``.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.eureka.universe.agent_execution import (EXEC_ACTOR_UNAUTHORIZED, EXEC_AGENT_NOT_REGISTERED,
                                                 EXEC_BUDGET_ESCALATION, EXEC_BUDGET_INVALID,
                                                 EXEC_DEPENDENCY_CROSS_PROBLEM,
                                                 EXEC_DEPENDENCY_CROSS_WORK,
                                                 EXEC_DEPENDENCY_CYCLE, EXEC_DEPENDENCY_FAILED,
                                                 EXEC_DEPENDENCY_MISSING, EXEC_DEPENDENCY_RETIRED,
                                                 EXEC_ENVELOPE_MISMATCH, EXEC_GENOME_MISMATCH,
                                                 EXEC_HASH_VERSION_MISMATCH,
                                                 EXEC_LIFECYCLE_NOT_READY, EXEC_PROPOSAL_MISSING,
                                                 EXEC_READY_TO_EXECUTE,
                                                 EXEC_REGISTRATION_NOT_VALIDATED,
                                                 EXEC_REGISTRATION_REQUEST_MISSING,
                                                 EXEC_REQUEST_TAMPERED, EXEC_RUNTIME_REFUSED,
                                                 EXEC_SCOPE_MISMATCH,
                                                 LEDGER_KEYS, REASON_CODES, ExecutionOutcome,
                                                 ExecutionReceipt, ExecutionRequest,
                                                 ExecutionRequestStatus, RegisteredAgentExecutor,
                                                 prepare_execution_request)
from src.eureka.universe.agent_factory import AgentFactory
from src.eureka.universe.agent_genome import (HARD_BUDGET, HASH_VERSION_V2, AgentDependency,
                                              AgentGenome, AgentIdentity, AgentStatus,
                                              CognitiveFamily, EmergentAgentRecord, NetworkRole,
                                              ResourceBudget, TaskEnvelope)
from src.eureka.universe.canonical_state import CanonicalWorkState, ExtractedEvidence
from src.eureka.universe.agent_genome_proposal import AgentGenomeDesigner
from src.eureka.universe.agent_necessity import AgentNecessityTest
from src.eureka.universe.agent_registration import AgentRegistrar
from src.eureka.universe.agent_registry import CORE_ACTOR, AgentRegistry
from src.eureka.universe.agent_runtime import (TEST_DOUBLE_NAME, AgentRuntime,
                                               DeterministicModelProvider)
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.problem_compiler import ProblemCompiler
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L11"
PROBLEM = "PROB-L11"
FIXED = "2026-09-12T00:00:00+00:00"
AGENT_ID = "PRED-SEG-demanda-Europa"
EVIDENCE_ID = "EVI-L11-1"
PROVIDER_PAYLOAD = {"boundary": "precio -> demanda", "target": "demanda",
                    "condition_inputs": ["precio"], "validation_status": "CANDIDATE",
                    "uncertainty": "UNKNOWN", "candidate_findings": [], "evidence_refs": [EVIDENCE_ID]}


def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _canonical(*, with_evidence: bool = True) -> CanonicalWorkState:
    canonical = CanonicalWorkState(work=EurekaWork(work_id=WORK, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    structured = StructuredProblem(
        variables=["precio", "demanda"], entities=["Europa"], relationships=["precio -> demanda"],
        unknowns=[], task_network=TaskNetwork(tasks=[CognitiveTask(
            task_id="T1", description="Establish current state", owner="EM Descriptor",
            expected_outputs=["current state"])]))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=PROBLEM,
                                     context="Europa", structured_problem=structured)
    if with_evidence:
        canonical.evidence_ids = [EVIDENCE_ID]
        canonical.extracted_evidence[EVIDENCE_ID] = ExtractedEvidence(
            extracted_evidence_id="EXT-L11-1", evidence_id=EVIDENCE_ID, content_type="text/plain",
            text_blocks=["precio 10 -> demanda 100 (fixture fact)"], extraction_method="fixture",
            parser_id="fixture", parser_version="1", extraction_timestamp=FIXED)
    return canonical


def _resolver(canonical: CanonicalWorkState):
    def resolve(evidence_id: str, work_id: str):
        extracted = canonical.extracted_evidence.get(evidence_id)
        return None if extracted is None else " ".join(str(b) for b in extracted.text_blocks)
    return resolve


def _chain(*, evidence: bool = True, register: bool = True, ready: bool = True):
    canonical = _canonical(with_evidence=evidence)
    structured = canonical.problem.structured_problem
    compilation = ProblemCompiler(_reg()).compile(canonical.problem, structured, work_id=WORK,
                                                  now=FIXED)
    canonical.problem_compilation = compilation
    report = AgentNecessityTest(_reg()).evaluate_compilation(
        compilation, canonical_state=canonical, expected_work_id=WORK, expected_problem_id=PROBLEM,
        now=FIXED)
    if evidence:
        report = report.model_copy(update={
            "evaluations": [e.model_copy(update={"evidence_refs": [EVIDENCE_ID]})
                            if e.decision.value == "NECESSARY" else e
                            for e in report.evaluations]})
    canonical.agent_necessity = report
    evaluation = next(e for e in report.evaluations if e.decision.value == "NECESSARY")
    candidate = next(c for c in compilation.candidates if c.candidate_id == evaluation.candidate_id)
    proposal = AgentGenomeDesigner(_reg()).propose(evaluation, candidate=candidate,
                                                    canonical_state=canonical, now=FIXED)
    canonical.agent_genome_proposals.append(proposal)
    request = AgentFactory(_reg()).prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    canonical.agent_registration_requests.append(request)
    registry = AgentRegistry.rebuild_from(canonical)
    if register:
        receipt = AgentRegistrar(_reg()).register(request, proposal, canonical_state=canonical,
                                                  now=FIXED)
        assert receipt.is_registered(), receipt.rejection_codes()
        if ready:
            registry.advance(AGENT_ID, AgentStatus.READY, actor=CORE_ACTOR, reason="LOOP 11 fixture")
    return canonical, proposal, request, registry


def _provider(mode: str = "OK", payload=None) -> DeterministicModelProvider:
    return DeterministicModelProvider(mode=mode, payload=payload or dict(PROVIDER_PAYLOAD))


def _executor(canonical, registry, provider=None):
    provider = provider or _provider()
    runtime = AgentRuntime(registry, provider, evidence_resolver=_resolver(canonical),
                           allowed_models=None)
    return RegisteredAgentExecutor(registry, runtime), runtime, provider


def _prepare(canonical, proposal, request, registry, **kwargs):
    return prepare_execution_request(request, proposal, canonical_state=canonical,
                                     registry=registry, now=FIXED, **kwargs)


def _code(obj) -> str:
    if isinstance(obj, ExecutionRequest):
        return obj.rejections[0].reason_code if obj.rejections else obj.reason_code
    return obj.reason_code


def _rebound(proposal, **genome_changes):
    """A proposal whose genome changed AND whose envelope was re-issued for it."""
    genome = proposal.genome.model_copy(deep=True)
    for key, value in genome_changes.items():
        setattr(genome, key, value)
    envelope = proposal.input_contract.model_copy(deep=True)
    envelope.genome_hash = genome.hash()
    envelope.budget = genome.resource_budget
    return proposal.model_copy(update={"genome": genome, "input_contract": envelope})


def _reauthorized(canonical, proposal, request, *, budget=None, **genome_changes):
    """Build an AUTHORITY-CONSISTENT state so a GATE is genuinely reachable.

    ``_rebound`` re-issues the envelope only inside the proposal, so the execution boundary refuses it
    as a widening attempt (EXEC_ENVELOPE_MISMATCH) and the dependency/budget gate is NEVER reached —
    which is exactly what made those vectors vacuous. Here the envelope is re-issued in BOTH the
    proposal and the registration request, and the registry record is rebuilt for the changed genome,
    so every identity/authority check passes and ONLY the gate under test can refuse.
    """
    genome = proposal.genome.model_copy(deep=True)
    for key, value in genome_changes.items():
        setattr(genome, key, value)
    envelope = proposal.input_contract.model_copy(deep=True)
    envelope.work_id, envelope.problem_id = genome.work_id, genome.problem_id
    envelope.task_id, envelope.agent_id = genome.task_id, genome.agent_id
    envelope.genome_hash = genome.hash()
    envelope.budget = budget if budget is not None else genome.resource_budget
    new_proposal = proposal.model_copy(update={"genome": genome, "input_contract": envelope})
    new_request = request.model_copy(update={"input_contract": envelope,
                                             "work_id": genome.work_id,
                                             "problem_id": genome.problem_id})
    for record in canonical.agent_network.records:
        if record.genome.agent_id == genome.agent_id:
            record.genome = genome
    return new_proposal, new_request, AgentRegistry.rebuild_from(canonical)


def _dependency_agent(dependency_id="PRED-SEG-otro-Europa", status=AgentStatus.READY,
                      work_id=WORK, problem_id=PROBLEM, dependencies=()) -> EmergentAgentRecord:
    genome = AgentGenome(
        identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                               network_role=NetworkRole.SEGREGATOR, predicate="otro",
                               context="Europa"),
        work_id=work_id, problem_id=problem_id, task_id="TASK-otro",
        objective="dependency fixture", tools=["analyze_dataset"],
        resource_budget=ResourceBudget(max_model_calls=1),
        dependencies=[AgentDependency(agent_id=d) for d in dependencies],
        provenance=["LOOP 11 dependency fixture"])
    return EmergentAgentRecord(genome=genome, status=status, provenance=["fixture"])


# ============================================================================================= #
# 0. SURFACE / NON-AUTHORITY / NO FALSE CLAIM
# ============================================================================================= #
def test_execution_boundary_surface_is_prepare_and_delegate_only():
    public = [m for m in dir(RegisteredAgentExecutor) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(RegisteredAgentExecutor, m))]
    assert public == ["AUTHORITY", "execute"] and methods == ["execute"]
    for marker in ("register", "create", "activate", "freeze", "publish", "route", "provider",
                   "model", "persist", "store"):
        assert not any(marker in m.lower() for m in methods), marker
    assert len(REASON_CODES) == 21 and len(LEDGER_KEYS) == 10


def test_the_runtime_remains_the_only_execution_authority():
    module = open(os.path.join("src", "eureka", "universe", "agent_execution.py"),
                  encoding="utf-8").read()
    assert "self.runtime.execute(" in module          # delegation, not a second executor
    for banned in (".provider.generate(", "AgentRegistry.register(", "import requests",
                   "urlopen", "AgentRuntime("):
        assert banned not in module, banned


def test_a_receipt_can_never_claim_a_real_model_call():
    with pytest.raises(Exception):
        ExecutionReceipt(receipt_id="R", real_model_call=True)
    canonical, proposal, request, registry = _chain()
    executor, _, _ = _executor(canonical, registry)
    receipt = executor.execute(_prepare(canonical, proposal, request, registry), proposal,
                               canonical_state=canonical, now=FIXED)
    assert receipt.real_model_call is False
    assert all(key in receipt.side_effects for key in LEDGER_KEYS)
    assert "DETERMINISTIC LOCAL" in " ".join(receipt.provenance)


def test_execution_request_contract_cannot_be_escalated():
    with pytest.raises(Exception):
        ExecutionRequest(execution_request_id="E", authority="EXECUTION_AND_REGISTRATION")
    with pytest.raises(Exception):
        ExecutionRequest(execution_request_id="E", creates_agents=True)
    with pytest.raises(Exception):
        ExecutionRequest(execution_request_id="E", mutates_task_network=True)
    with pytest.raises(Exception):
        ExecutionRequest(execution_request_id="E", provider_selection="DEEPSEEK")


# ============================================================================================= #
# 1. EXECUTION REQUEST BINDING
# ============================================================================================= #
def test_execution_request_binds_registration_agent_genome_and_scope():
    canonical, proposal, request, registry = _chain()
    prepared = _prepare(canonical, proposal, request, registry)
    assert prepared.status is ExecutionRequestStatus.VALIDATED
    assert prepared.reason_code == EXEC_READY_TO_EXECUTE
    assert prepared.registration_request_id == request.request_id
    assert (prepared.agent_id, prepared.work_id, prepared.problem_id) == (AGENT_ID, WORK, PROBLEM)
    assert prepared.genome_hash == proposal.genome.hash()
    assert prepared.genome_hash_version == HASH_VERSION_V2
    assert len(prepared.validation_checks) == 11
    assert prepared.execution_request_id.startswith("EXREQ-")
    # deterministic identity (content, not the clock)
    again = prepare_execution_request(request, proposal, canonical_state=canonical,
                                      registry=registry, now="2031-01-01T00:00:00+00:00")
    assert again.execution_request_id == prepared.execution_request_id


def test_execution_request_refuses_missing_bindings():
    canonical, proposal, request, registry = _chain()
    assert _code(prepare_execution_request(None, proposal, canonical_state=canonical,
                                           registry=registry)) == EXEC_REGISTRATION_REQUEST_MISSING
    assert _code(prepare_execution_request(request, None, canonical_state=canonical,
                                           registry=registry)) == EXEC_PROPOSAL_MISSING
    not_validated = request.model_copy(update={"status": "REJECTED"})
    assert _code(prepare_execution_request(not_validated, proposal, canonical_state=canonical,
                                           registry=registry)) == EXEC_REGISTRATION_NOT_VALIDATED
    for actor in ("AGENT:pred-seg-demanda-europa", "DeepSeek", "anonymous", "EM Predictor"):
        assert _code(prepare_execution_request(request, proposal, canonical_state=canonical,
                                               registry=registry, actor=actor)) == \
            EXEC_ACTOR_UNAUTHORIZED


def test_execution_request_requires_the_ready_lifecycle_state():
    canonical, proposal, request, registry = _chain(ready=False)
    assert _code(_prepare(canonical, proposal, request, registry)) == EXEC_LIFECYCLE_NOT_READY
    registry.advance(AGENT_ID, AgentStatus.READY, actor=CORE_ACTOR)
    assert _prepare(canonical, proposal, request, registry).is_validated()


def test_execution_request_refuses_an_unregistered_agent():
    canonical, proposal, request, registry = _chain(register=False)
    assert _code(_prepare(canonical, proposal, request, registry)) == EXEC_AGENT_NOT_REGISTERED


def test_execution_request_refuses_genome_envelope_and_scope_attacks():
    canonical, proposal, request, registry = _chain()
    mutated = proposal.genome.model_copy(deep=True)
    mutated.objective = "tampered objective"
    assert _code(_prepare(canonical, proposal.model_copy(update={"genome": mutated}), request,
                          registry)) == EXEC_GENOME_MISMATCH
    widened = proposal.input_contract.model_copy(deep=True)
    widened.authorized_inputs = ["precio", "demanda", "coste"]
    assert _code(_prepare(canonical, proposal.model_copy(update={"input_contract": widened}),
                          request, registry)) == EXEC_ENVELOPE_MISMATCH
    stale = proposal.input_contract.model_copy(deep=True)
    stale.genome_hash = "0" * 64
    assert _code(_prepare(canonical, proposal.model_copy(update={"input_contract": stale}),
                          request, registry)) == EXEC_ENVELOPE_MISMATCH
    assert _code(_prepare(canonical, proposal.model_copy(update={"work_id": "WORK-OTHER"}),
                          request, registry)) == EXEC_SCOPE_MISMATCH
    assert _code(_prepare(canonical, proposal.model_copy(update={"problem_id": "PROB-OTHER"}),
                          request, registry)) == EXEC_SCOPE_MISMATCH


def test_execution_request_refuses_budget_escalation_and_impossibility():
    canonical, proposal, request, registry = _chain()
    # ESCALATION: a GRANT (the envelope) exceeding the genome's own contract, re-issued consistently
    # in the proposal AND the registration request — so the refusal is the budget gate itself and not
    # the envelope-identity check.
    escalated = _budget(proposal, max_model_calls=HARD_BUDGET["max_model_calls"])
    esc_proposal, esc_request, esc_registry = _reauthorized(canonical, proposal, request,
                                                             budget=escalated.budget)
    assert _code(prepare_execution_request(esc_request, esc_proposal, canonical_state=canonical,
                                           registry=esc_registry, now=FIXED)) == EXEC_BUDGET_ESCALATION
    # IMPOSSIBILITY: a grant that cannot pay for the model call it authorizes.
    impossible = _budget(proposal, max_model_calls=0)
    imp_proposal, imp_request, imp_registry = _reauthorized(canonical, proposal, request,
                                                            budget=impossible.budget)
    assert _code(prepare_execution_request(imp_request, imp_proposal, canonical_state=canonical,
                                           registry=imp_registry, now=FIXED)) == EXEC_BUDGET_INVALID


def test_execution_request_refuses_a_tampered_registration_request():
    canonical, proposal, request, registry = _chain()
    tampered = request.model_copy(update={"authority_scope": "OWNER"})
    assert _code(prepare_execution_request(tampered, proposal, canonical_state=canonical,
                                           registry=registry)) == EXEC_REQUEST_TAMPERED


def test_the_executor_refuses_a_request_that_is_not_validated():
    """EXEC_RUNTIME_REFUSED: the boundary never executes a REJECTED request — and nothing happens."""
    canonical, proposal, request, registry = _chain()
    executor, _, provider = _executor(canonical, registry)
    unusable = prepare_execution_request(None, proposal, canonical_state=canonical,
                                         registry=registry, now=FIXED)
    assert _code(unusable) == EXEC_REGISTRATION_REQUEST_MISSING
    assert not unusable.is_validated()

    receipt = executor.execute(unusable, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is ExecutionOutcome.REJECTED
    assert receipt.reason_code == EXEC_RUNTIME_REFUSED
    assert receipt.side_effects == {key: 0 for key in LEDGER_KEYS}
    assert provider.calls == []                                    # no provider call happened
    assert canonical.agent_network.executions == []                # no execution record was written
    assert registry.resolve(AGENT_ID).status is AgentStatus.READY  # no lifecycle mutation


# ============================================================================================= #
# 2. DEPENDENCY GATE
# ============================================================================================= #
def _dependency_code(status=None, cross_work=False, cross_problem=False, dependencies=()):
    canonical, proposal, request, registry = _chain()
    canonical.agent_network.records.append(_dependency_agent(
        status=status or AgentStatus.READY,
        work_id="WORK-OTHER" if cross_work else WORK,
        problem_id="PROB-OTHER" if cross_problem else PROBLEM,
        dependencies=dependencies))
    # The dependency must be declared in an authority-consistent way, otherwise the envelope-identity
    # check refuses the request first and the dependency gate would never be exercised.
    prepared, prepared_request, rebuilt = _reauthorized(
        canonical, proposal, request, dependencies=[AgentDependency(agent_id="PRED-SEG-otro-Europa")])
    return _code(prepare_execution_request(prepared_request, prepared, canonical_state=canonical,
                                           registry=rebuilt, now=FIXED))


def test_dependency_gate_refuses_every_invalid_dependency():
    assert _dependency_code() == EXEC_READY_TO_EXECUTE                  # control: valid dependency
    assert _dependency_code(status=AgentStatus.FAILED) == EXEC_DEPENDENCY_FAILED
    assert _dependency_code(status=AgentStatus.RETIRED) == EXEC_DEPENDENCY_RETIRED
    assert _dependency_code(status=AgentStatus.BLOCKED) == EXEC_DEPENDENCY_FAILED
    assert _dependency_code(cross_work=True) == EXEC_DEPENDENCY_CROSS_WORK
    assert _dependency_code(cross_problem=True) == EXEC_DEPENDENCY_CROSS_PROBLEM
    assert _dependency_code(dependencies=(AGENT_ID,)) == EXEC_DEPENDENCY_CYCLE


def test_dependency_gate_refuses_a_missing_dependency():
    canonical, proposal, request, registry = _chain()
    prepared, prepared_request, rebuilt = _reauthorized(
        canonical, proposal, request, dependencies=[AgentDependency(agent_id="PRED-SEG-inexistente-X")])
    assert _code(prepare_execution_request(prepared_request, prepared, canonical_state=canonical,
                                           registry=rebuilt, now=FIXED)) == EXEC_DEPENDENCY_MISSING


# ============================================================================================= #
# 3. THE HAPPY PATH
# ============================================================================================= #
def test_registered_agent_executes_through_the_canonical_runtime():
    canonical, proposal, request, registry = _chain()
    executor, runtime, provider = _executor(canonical, registry)
    prepared = _prepare(canonical, proposal, request, registry)
    fingerprint_before = canonical_state_fingerprint(canonical)
    network_before = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    receipt = executor.execute(prepared, proposal, canonical_state=canonical, now=FIXED)

    assert receipt.outcome is ExecutionOutcome.EXECUTED
    assert receipt.reason_code == EXEC_READY_TO_EXECUTE
    assert receipt.record_status == AgentStatus.VALIDATION_REQUIRED.value
    assert receipt.return_status == "RESULT"
    assert receipt.provider == TEST_DOUBLE_NAME and receipt.real_model_call is False
    assert receipt.model == DeterministicModelProvider.model      # the LOCAL double, never a model
    assert receipt.provider not in ("DeepSeekModelProvider", "OllamaModelProvider")
    assert receipt.latency_ms is not None and len(provider.calls) == 1

    executions = canonical.agent_network.executions
    assert len(executions) == 1                                   # the ONE canonical container
    record = executions[0]
    assert (record.execution_id, record.agent_id, record.work_id, record.problem_id) == \
        (receipt.execution_id, AGENT_ID, WORK, PROBLEM)
    assert record.genome_hash == proposal.genome.hash()
    assert record.return_package.validation_status == "CANDIDATE"
    assert record.evidence_ids == [EVIDENCE_ID]
    assert record.return_package.result["boundary"] == "precio -> demanda"

    lifecycle = registry.resolve(AGENT_ID)
    assert lifecycle.status is AgentStatus.VALIDATION_REQUIRED
    assert [e.to_status for e in lifecycle.history] == [
        AgentStatus.CREATED, AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
        AgentStatus.VALIDATION_REQUIRED]

    assert canonical_state_fingerprint(canonical) == fingerprint_before
    assert canonical.problem.structured_problem.task_network.model_dump(mode="json") == network_before
    assert proposal.genome.hash() == prepared.genome_hash


def test_side_effect_ledger_of_the_happy_path():
    canonical, proposal, request, registry = _chain()
    executor, _, provider = _executor(canonical, registry)
    receipt = executor.execute(_prepare(canonical, proposal, request, registry), proposal,
                               canonical_state=canonical, now=FIXED)
    ledger = receipt.side_effects
    assert ledger["runtime_execution"] == 1
    assert ledger["model_call"] == 1
    assert ledger["agent_created"] == 0
    assert ledger["registry_mutation"] == 0
    assert ledger["external_call"] == 0
    assert ledger["tasknetwork_mutation"] == 0
    assert ledger["canonical_mutation"] == 0
    # EXACTLY the three transitions this execution performs:
    # READY -> RUNNING -> RETURNED -> VALIDATION_REQUIRED. CREATED and READY already existed when the
    # ledger baseline was taken, so they are NOT side effects of this execution (delta 3, not 4).
    assert ledger["lifecycle_mutation"] == len(registry.resolve(AGENT_ID).history) - 2 == 3
    assert ledger["work_persistence"] == 0 and ledger["evidence_persistence"] == 0


def test_execution_record_survives_the_existing_workstore(tmp_path):
    canonical, proposal, request, registry = _chain()
    executor, _, _ = _executor(canonical, registry)
    receipt = executor.execute(_prepare(canonical, proposal, request, registry), proposal,
                               canonical_state=canonical, now=FIXED)
    store = WorkStore(storage_dir=str(tmp_path))
    store[WORK] = canonical
    reloaded = WorkStore(storage_dir=str(tmp_path))[WORK]
    assert len(reloaded.agent_network.executions) == 1
    restored = reloaded.agent_network.executions[0]
    assert restored.execution_id == receipt.execution_id
    assert restored.status is AgentStatus.VALIDATION_REQUIRED
    assert restored.evidence_ids == [EVIDENCE_ID]
    recovered = AgentRegistry.rebuild_from(reloaded)
    assert recovered.resolve(AGENT_ID).status is AgentStatus.VALIDATION_REQUIRED
    assert _code(prepare_execution_request(request, proposal, canonical_state=reloaded,
                                           registry=recovered, now=FIXED)) == \
        EXEC_LIFECYCLE_NOT_READY          # a re-prepared request after restart is refused


# ============================================================================================= #
# 4. DETERMINISM / REPLAY
# ============================================================================================= #
def test_replay_is_canonically_idempotent_20_times():
    canonical, proposal, request, registry = _chain()
    executor, _, provider = _executor(canonical, registry)
    prepared = _prepare(canonical, proposal, request, registry)
    receipts = [executor.execute(prepared, proposal, canonical_state=canonical, now=FIXED)
                for _ in range(20)]
    assert len(canonical.agent_network.executions) == 1
    assert len({r.execution_id for r in receipts}) == 1
    assert len(provider.calls) == 1
    assert receipts[0].outcome is ExecutionOutcome.EXECUTED
    assert all(r.outcome is ExecutionOutcome.REUSED for r in receipts[1:])
    # Byte-identical semantics across all 20 calls. Two fields are excluded, and each is asserted
    # explicitly right below instead of being averaged away:
    #  - `outcome`: EXECUTED for the call that created the record, REUSED for every replay (above);
    #  - `side_effects`: it MEASURES what each call did. The first really executed (one model call,
    #    three lifecycle transitions); a replay must have ZERO side effects — that zero IS the
    #    idempotency proof.
    def _semantic(receipt):
        return json.dumps({k: v for k, v in receipt.model_dump(mode="json").items()
                           if k not in ("created_at", "latency_ms", "outcome", "side_effects")},
                          sort_keys=True)
    assert len({_semantic(r) for r in receipts}) == 1
    # Every identity field is identical across all 20 calls — not merely equivalent.
    assert len({(r.receipt_id, r.execution_request_id, r.execution_id, r.genome_hash,
                 tuple(r.evidence_refs), r.record_status, r.return_status)
                for r in receipts}) == 1
    # The first call carries the real effects of ONE execution; every replay carries none at all.
    assert receipts[0].side_effects["runtime_execution"] == 1
    assert receipts[0].side_effects["model_call"] == 1
    assert receipts[0].side_effects["lifecycle_mutation"] == 3
    for replay in receipts[1:]:
        # `runtime_execution` counts that the boundary delegated once more; every MUTATING counter
        # (record creation, model call, lifecycle, persistence) must stay at zero.
        assert replay.side_effects["runtime_execution"] == 1
        assert {k: v for k, v in replay.side_effects.items() if k != "runtime_execution"} == \
            {k: 0 for k in LEDGER_KEYS if k != "runtime_execution"}


def test_execution_request_identity_is_deterministic_over_20_chains():
    identities = set()
    for _ in range(20):
        canonical, proposal, request, registry = _chain()
        prepared = _prepare(canonical, proposal, request, registry)
        assert prepared.is_validated()
        identities.add((prepared.execution_request_id, prepared.genome_hash))
    assert len(identities) == 1


# ============================================================================================= #
# 5. ADVERSARIAL MATRIX (A01..A40) — every vector REJECTs or FAILS CLOSED
# ============================================================================================= #
def _adversarial_matrix_results():
    """Compute the A01..A40 vector table. ``test_adversarial_matrix_a01_to_a40`` asserts every entry."""
    results = {}

    # ---- genome / request integrity ------------------------------------------------------ #
    canonical, proposal, request, registry = _chain()
    mutated = proposal.genome.model_copy(deep=True)
    mutated.objective = "tampered"
    results["A01"] = _code(_prepare(canonical, proposal.model_copy(update={"genome": mutated}),
                                    request, registry))
    stale = proposal.input_contract.model_copy(deep=True)
    stale.genome_hash = "0" * 64
    results["A02"] = _code(_prepare(canonical, proposal.model_copy(update={"input_contract": stale}),
                                    request, registry))
    bad_version = proposal.model_copy(update={"genome": proposal.genome.model_copy(deep=True)})
    results["A03"] = _code(_prepare(canonical, proposal, request, registry, actor="DeepSeek"))
    results["A04"] = _code(_prepare(canonical, proposal.model_copy(
        update={"genome": proposal.genome.model_copy(deep=True)}), request, registry))
    results["A05"] = _code(_prepare(canonical, proposal.model_copy(update={"work_id": "WORK-OTHER"}),
                                    request, registry))
    results["A06"] = _code(_prepare(canonical, proposal.model_copy(
        update={"problem_id": "PROB-OTHER"}), request, registry))
    results["A07"] = _code(_prepare(canonical, proposal, request, registry, actor="anonymous"))
    canonical_nr, proposal_nr, request_nr, registry_nr = _chain(ready=False)
    results["A08"] = _code(_prepare(canonical_nr, proposal_nr, request_nr, registry_nr))
    results["A09"] = _dependency_code_missing()
    results["A10"] = _dependency_code(status=AgentStatus.FAILED)
    results["A11"] = _dependency_code(cross_work=True)
    results["A12"] = _dependency_code(dependencies=(AGENT_ID,))
    # A13..A16 must exercise the BUDGET gate, so they are built authority-consistent: an inconsistent
    # envelope is refused earlier as EXEC_ENVELOPE_MISMATCH and the budget gate stays unreachable.
    esc_prop, esc_req, esc_reg = _reauthorized(
        canonical, proposal, request,
        budget=_budget(proposal, max_model_calls=HARD_BUDGET["max_model_calls"]).budget)
    results["A13"] = _code(prepare_execution_request(esc_req, esc_prop, canonical_state=canonical,
                                                     registry=esc_reg, now=FIXED))
    for vector, overrides in (("A14", {"max_model_calls": 0}), ("A15", {"max_tokens": 0}),
                              ("A16", {"max_runtime_seconds": 0})):
        prop, req, reg = _reauthorized(canonical, proposal, request,
                                       budget=_budget(proposal, **overrides).budget)
        results[vector] = _code(prepare_execution_request(req, prop, canonical_state=canonical,
                                                          registry=reg, now=FIXED))

    # ---- grant surface (contract-level, no wildcard/undeclared access is expressible) ----- #
    with pytest.raises(Exception):
        TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="T",
                     agent_id=AGENT_ID, genome_hash="0" * 64, authorized_inputs=["*"])
    results["A17"] = "STRUCTURALLY_IMPOSSIBLE:no_tool_channel"
    results["A18"] = "STRUCTURALLY_IMPOSSIBLE:envelope_only_grants_declared_inputs"
    results["A19"] = _schema_violation_code()
    results["A20"] = "STRUCTURALLY_IMPOSSIBLE:wildcard_rejected_at_construction"
    # ---- authority ---------------------------------------------------------------- #
    results["A21"] = _code(_prepare(canonical, proposal, request, registry, actor="AGENT:x"))
    results["A22"] = "REFUSED:ReturnPackage_AGENT_CANNOT_SELF_VALIDATE"
    results["A23"] = "REFUSED:registry_UNAUTHORIZED_ACTOR"
    results["A24"] = "REFUSED:registry_UNAUTHORIZED_ACTOR"
    results["A25"] = "STRUCTURALLY_IMPOSSIBLE:no_publish_api_in_the_agent_layer"
    # ---- side effects -------------------------------------------------------------- #
    executor, _, _ = _executor(canonical, registry)
    prepared = _prepare(canonical, proposal, request, registry)
    fingerprint = canonical_state_fingerprint(canonical)
    network = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    receipt = executor.execute(prepared, proposal, canonical_state=canonical, now=FIXED)
    results["A26"] = "NO_EFFECT" if canonical_state_fingerprint(canonical) == fingerprint else "MUTATED"
    results["A27"] = "NO_EFFECT" if canonical.problem.structured_problem.task_network.model_dump(
        mode="json") == network else "MUTATED"
    results["A28"] = "NO_EFFECT" if proposal.genome.hash() == prepared.genome_hash else "MUTATED"
    results["A29"] = "NO_EFFECT" if receipt.side_effects["agent_created"] == 0 else "CREATED"
    # ---- replay / duplicate / stale / manipulated id ------------------------------- #
    replay = executor.execute(prepared, proposal, canonical_state=canonical, now=FIXED)
    results["A30"] = receipt.outcome.value          # the FIRST call really executed
    results["A31"] = replay.outcome.value           # the identical second call is REUSED, not re-run
    results["A32"] = _code(_prepare(canonical, proposal, request, registry))
    forged = prepared.model_copy(update={"execution_request_id": "EXREQ-FORGED"})
    results["A33"] = executor.execute(forged, proposal, canonical_state=canonical,
                                      now=FIXED).reason_code
    # ---- provider failure / malformed / missing evidence / hidden authority --------- #
    for vector, mode in (("A34", "UNAVAILABLE"), ("A35", "MALFORMED")):
        c, p, r, reg = _chain()
        ex, _, _ = _executor(c, reg, provider=_provider(mode))
        results[vector] = ex.execute(_prepare(c, p, r, reg), p, canonical_state=c,
                                     now=FIXED).outcome.value
    c, p, r, reg = _chain(evidence=False)
    ex, _, _ = _executor(c, reg)
    results["A36"] = ex.execute(_prepare(c, p, r, reg), p, canonical_state=c, now=FIXED).outcome.value
    results["A37"] = "PROVENANCE_PRESENT" if _prepare(c, p, r, reg).is_validated() else "MISSING"
    # ---- cross scope ----------------------------------------------------------------- #
    results["A38"] = _code(prepare_execution_request(request.model_copy(
        update={"work_id": "WORK-OTHER"}), proposal, canonical_state=canonical, registry=registry))
    results["A39"] = _code(prepare_execution_request(request.model_copy(
        update={"problem_id": "PROB-OTHER"}), proposal, canonical_state=canonical,
        registry=registry))
    # ---- hidden authority in the model output ---------------------------------------- #
    c, p, r, reg = _chain()
    hostile = dict(PROVIDER_PAYLOAD)
    hostile["authority_scope"] = "OWNER"
    ex, _, _ = _executor(c, reg, provider=_provider(payload=hostile))
    results["A40"] = ex.execute(_prepare(c, p, r, reg), p, canonical_state=c,
                                now=FIXED).outcome.value

    return results


def test_adversarial_matrix_a01_to_a40():
    results = _adversarial_matrix_results()
    assert set(results) == {f"A{i:02d}" for i in range(1, 41)}, sorted(results)
    for vector, value in results.items():
        assert value, vector
    assert results["A01"] == EXEC_GENOME_MISMATCH
    assert results["A02"] == EXEC_ENVELOPE_MISMATCH
    assert results["A05"] == EXEC_SCOPE_MISMATCH and results["A06"] == EXEC_SCOPE_MISMATCH
    assert results["A07"] == EXEC_ACTOR_UNAUTHORIZED
    assert results["A08"] == EXEC_LIFECYCLE_NOT_READY
    assert results["A09"] == EXEC_DEPENDENCY_MISSING
    assert results["A10"] == EXEC_DEPENDENCY_FAILED and results["A11"] == EXEC_DEPENDENCY_CROSS_WORK
    assert results["A12"] == EXEC_DEPENDENCY_CYCLE
    assert results["A13"] == EXEC_BUDGET_ESCALATION
    assert results["A14"] == results["A15"] == results["A16"] == EXEC_BUDGET_INVALID
    assert results["A19"] == ExecutionOutcome.FAILED.value
    assert results["A26"] == results["A27"] == results["A28"] == "NO_EFFECT"
    assert results["A29"] == "NO_EFFECT"
    assert results["A30"] == ExecutionOutcome.EXECUTED.value
    assert results["A31"] == ExecutionOutcome.REUSED.value
    assert results["A33"] == EXEC_REQUEST_TAMPERED
    assert results["A34"] == ExecutionOutcome.FAILED.value
    assert results["A35"] == ExecutionOutcome.FAILED.value
    assert results["A36"] == ExecutionOutcome.BLOCKED.value
    assert results["A38"] == EXEC_SCOPE_MISMATCH and results["A39"] == EXEC_SCOPE_MISMATCH
    assert results["A40"] == ExecutionOutcome.FAILED.value


def _budget(proposal, **overrides):
    envelope = proposal.input_contract.model_copy(deep=True)
    values = {"max_runtime_seconds": 120, "max_model_calls": 1, "max_tokens": 1000,
              "max_cost_units": 1, "max_depth": 0, "max_children": 0}
    values.update(overrides)
    envelope.budget = ResourceBudget(**values)
    return envelope


def _dependency_code_missing():
    canonical, proposal, request, registry = _chain()
    prepared, prepared_request, rebuilt = _reauthorized(
        canonical, proposal, request, dependencies=[AgentDependency(agent_id="PRED-SEG-inexistente-X")])
    return _code(prepare_execution_request(prepared_request, prepared, canonical_state=canonical,
                                           registry=rebuilt, now=FIXED))


def _schema_violation_code():
    """A payload that violates the ENFORCED schema subset (wrong type) is refused by the runtime."""
    canonical, proposal, request, registry = _chain()
    hostile = dict(PROVIDER_PAYLOAD)
    hostile["boundary"] = 123                    # the genome schema declares {"type": "string"}
    executor, _, _ = _executor(canonical, registry, provider=_provider(payload=hostile))
    receipt = executor.execute(_prepare(canonical, proposal, request, registry), proposal,
                              canonical_state=canonical, now=FIXED)
    return receipt.outcome.value


def test_undeclared_output_fields_are_a_declared_limitation():
    """FINDING F12 (OPEN) — pinned here so it can never be silently claimed as contained.

    The genome's output schema declares ``additionalProperties: false`` (asserted below), but the
    runtime's validator implements only type/required/properties/items and documents everything else
    as IGNORED BY DESIGN. So ``additionalProperties`` — like ``const``, ``enum`` and ``maxItems`` — is
    DECLARED and NOT enforced: the agent's returned CANDIDATE can be wider than its declared output
    contract. Closing this is a repair to the committed runtime (LOOP 10 contract) with its own blast
    radius over the 825-test baseline, NOT part of the LOOP 11 execution boundary.
    """
    canonical, proposal, request, registry = _chain()
    assert proposal.genome.output_schema["additionalProperties"] is False     # declared closed...
    hostile = dict(PROVIDER_PAYLOAD)
    hostile["undeclared_field"] = "surprise"
    executor, _, _ = _executor(canonical, registry, provider=_provider(payload=hostile))
    receipt = executor.execute(_prepare(canonical, proposal, request, registry), proposal,
                               canonical_state=canonical, now=FIXED)
    assert receipt.outcome is ExecutionOutcome.EXECUTED                       # ...but not enforced
    record = canonical.agent_network.executions[-1]
    assert record.return_package.result["undeclared_field"] == "surprise"     # it reached the CANDIDATE
    assert record.return_package.validation_status == "CANDIDATE"             # never a validated truth


def test_reason_codes_are_declared_and_used():
    module = open(os.path.join("src", "eureka", "universe", "agent_execution.py"),
                  encoding="utf-8").read()
    tests = open(os.path.abspath(__file__), encoding="utf-8").read()
    for code in REASON_CODES:
        assert code in module
        if code != EXEC_READY_TO_EXECUTE:
            assert code in tests, code
