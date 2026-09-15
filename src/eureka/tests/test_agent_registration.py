"""EUREKA 5.1 — LOOP 8 tests: AGENT REGISTRATION BOUNDARY.

    VALIDATED RegistrationRequest -> AgentRegistry.register() -> registered (CREATED) agent

Proves: registration happens ONLY from a validated request, through the registry (sole authority),
scoped to one Work and one Problem, idempotent for identical content, fail-closed for incompatible
duplicates and for every altered/stale/foreign input — with ZERO activation, execution, model or
provider activity, and no canonical-content drift.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.eureka.universe.agent_factory import (AgentFactory, REQUEST_PROVIDER_PIN,
                                               RegistrationRequestStatus)
from src.eureka.universe.agent_genome import (HASH_VERSION_V2, AgentStatus, AgentNetworkState,
                                              EmergentAgentRecord)
from src.eureka.universe.agent_genome_proposal import AgentGenomeDesigner
from src.eureka.universe.agent_necessity import AgentNecessityTest
from src.eureka.universe.agent_registration import (REGISTRATION_CONTENT_MISMATCH,
                                                    REGISTRATION_DUPLICATE_INCOMPATIBLE,
                                                    REGISTRATION_FROM_VALIDATED_REQUEST,
                                                    REGISTRATION_IDENTITY_MISMATCH,
                                                    REGISTRATION_PROPOSAL_MISSING,
                                                    REGISTRATION_REQUEST_MISSING,
                                                    REGISTRATION_REQUEST_NOT_VALIDATED,
                                                    REGISTRATION_SCOPE_MISMATCH,
                                                    REGISTRATION_STALE_REQUEST, REASON_CODES,
                                                    REGISTRAR_AUTHORITY, AgentRegistrar,
                                                    RegistrationOutcome, RegistrationReceipt)
from src.eureka.universe.agent_registry import AgentRegistry
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.capability_fabric import CapabilityRegistry
from src.eureka.universe.cognitive_engine import (SemanticProposal, StructuralProposal,
                                                 TestDoubleCognitiveEngine)
from src.eureka.universe.orchestrator import WorkOrchestrator
from src.eureka.universe.problem_compiler import ProblemCompiler
from src.eureka.universe.problem_model import (CognitiveTask, ProblemModel, StructuredProblem,
                                              TaskNetwork)
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L8"
PROBLEM = "PROB-L8"
FIXED = "2026-09-12T00:00:00+00:00"
AGENT_ID = "PRED-SEG-demanda-Europa"
_MODULE = os.path.join("src", "eureka", "universe", "agent_registration.py")


def _reg() -> CapabilityRegistry:
    cr = CapabilityRegistry()
    cr.load_defaults()
    return cr


def _ready(work_id=WORK, problem_id=PROBLEM):
    """Full upstream chain: canonical state + compilation + necessity + proposal + request."""
    canonical = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    structured = StructuredProblem(
        variables=["precio", "demanda"], entities=["Europa"], relationships=["precio -> demanda"],
        unknowns=[], task_network=TaskNetwork(tasks=[CognitiveTask(
            task_id="T1", description="Establish current state", owner="EM Descriptor",
            expected_outputs=["current state"])]))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=problem_id,
                                     context="Europa", structured_problem=structured)
    compilation = ProblemCompiler(_reg()).compile(canonical.problem, structured, work_id=work_id,
                                                  now=FIXED)
    canonical.problem_compilation = compilation
    report = AgentNecessityTest(_reg()).evaluate_compilation(
        compilation, canonical_state=canonical, expected_work_id=work_id,
        expected_problem_id=problem_id, now=FIXED)
    canonical.agent_necessity = report
    evaluation = next(e for e in report.evaluations if e.decision.value == "NECESSARY")
    candidate = next(c for c in compilation.candidates if c.candidate_id == evaluation.candidate_id)
    proposal = AgentGenomeDesigner(_reg()).propose(evaluation, candidate=candidate,
                                                   canonical_state=canonical, now=FIXED)
    canonical.agent_genome_proposals.append(proposal)
    request = AgentFactory(_reg()).prepare_registration_request(
        proposal, candidate=candidate, compilation=compilation, canonical_state=canonical,
        now=FIXED)
    assert request.status is RegistrationRequestStatus.VALIDATED
    return canonical, proposal, request


def _registrar() -> AgentRegistrar:
    return AgentRegistrar(_reg())


# ============================================================================================= #
# 0. SURFACE / AUTHORITY
# ============================================================================================= #
def test_registrar_surface_is_registration_only():
    public = [m for m in dir(AgentRegistrar) if not m.startswith("_")]
    methods = [m for m in public if callable(getattr(AgentRegistrar, m))]
    assert public == ["AUTHORITY", "register"]
    assert methods == ["register"]
    for marker in ("activate", "execute", "run", "route", "publish", "freeze", "provider",
                   "model", "create", "spawn", "validate_own"):
        assert not any(marker in m.lower() for m in methods), marker
    assert AgentRegistrar.AUTHORITY == REGISTRAR_AUTHORITY
    assert len(REASON_CODES) == 12


def test_receipt_invariants_cannot_be_escalated():
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", authority="REGISTRATION_AND_EXECUTION")
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", activates_agents=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", executes_agents=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", calls_model=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", selects_provider=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", publishes=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", mutates_task_network=True)
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", provider_selection="DEEPSEEK")
    # a REGISTERED receipt must carry full traceability
    with pytest.raises(Exception):
        RegistrationReceipt(receipt_id="R", outcome=RegistrationOutcome.REGISTERED,
                            reason_code=REGISTRATION_FROM_VALIDATED_REQUEST, agent_id=AGENT_ID)


def test_module_reaches_no_runtime_provider_or_store():
    source = open(_MODULE, encoding="utf-8").read()
    for banned in ("AgentRuntime", "DeterministicModelProvider", "DeepSeekModelProvider",
                   "OllamaModelProvider", "requests.", "urlopen", "AgentStore", "RegistrationStore"):
        assert banned not in source, banned
    import ast
    tree = ast.parse(source)
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    used |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
    for banned in ("AgentRuntime", "ProviderResult", "WorkStore"):
        assert banned not in used, banned


# ============================================================================================= #
# 1-6. THE POSITIVE BOUNDARY
# ============================================================================================= #
def test_validated_request_registers_through_the_registry():
    canonical, proposal, request = _ready()
    receipt = _registrar().register(request, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REGISTERED
    assert receipt.reason_code == REGISTRATION_FROM_VALIDATED_REQUEST
    assert receipt.is_registered() is True and receipt.idempotent is False
    assert receipt.agent_id == AGENT_ID
    assert receipt.request_id == request.request_id
    assert receipt.work_id == WORK and receipt.problem_id == PROBLEM
    assert receipt.registry_count_before == 0 and receipt.registry_count_after == 1
    assert receipt.genome_hash_version == HASH_VERSION_V2
    assert len(receipt.genome_hash) == 64
    assert receipt.record_status == AgentStatus.CREATED.value
    # the write happened in the EXISTING canonical container (no new store)
    assert len(canonical.agent_network.records) == 1
    record = canonical.agent_network.records[0]
    assert record.agent_id == AGENT_ID
    assert record.status is AgentStatus.CREATED                 # NOT activated
    assert request.request_id in record.history[-1].reason      # durable traceability
    assert any("registered by" in line for line in record.provenance)


def test_registration_is_idempotent_for_identical_content():
    canonical, proposal, request = _ready()
    registrar = _registrar()
    first = registrar.register(request, proposal, canonical_state=canonical, now=FIXED)
    second = registrar.register(request, proposal, canonical_state=canonical, now=FIXED)
    assert first.outcome is RegistrationOutcome.REGISTERED
    assert second.outcome is RegistrationOutcome.REUSED
    assert second.idempotent is True
    assert second.registry_count_after == 1
    assert len(canonical.agent_network.records) == 1             # no duplicate
    # a freshly rebuilt registry still resolves the single record (derived index)
    assert AgentRegistry.rebuild_from(canonical).count() == 1


def test_incompatible_duplicate_is_rejected_without_partial_write():
    canonical, proposal, request = _ready()
    registrar = _registrar()
    assert registrar.register(request, proposal, canonical_state=canonical,
                              now=FIXED).is_registered()
    # same identity, different content -> the registry refuses; nothing is added
    other_genome = proposal.genome.model_copy(deep=True)
    other_genome.objective = "a different objective"
    other_proposal = proposal.model_copy(update={"genome": other_genome})
    receipt = registrar.register(request, other_proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code in (REGISTRATION_CONTENT_MISMATCH,
                                   REGISTRATION_STALE_REQUEST,
                                   REGISTRATION_DUPLICATE_INCOMPATIBLE)
    assert len(canonical.agent_network.records) == 1


def test_registration_is_scoped_to_work_and_problem():
    canonical, proposal, request = _ready()
    # a request whose scope does not match the state must never be written
    foreign = request.model_copy(update={"work_id": "WORK-OTHER"})
    receipt = _registrar().register(foreign, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code == REGISTRATION_SCOPE_MISMATCH
    assert canonical.agent_network.records == []
    foreign_problem = request.model_copy(update={"problem_id": "PROB-OTHER"})
    receipt = _registrar().register(foreign_problem, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.reason_code == REGISTRATION_SCOPE_MISMATCH
    assert canonical.agent_network.records == []


def test_registration_only_accepts_a_validated_request():
    canonical, proposal, request = _ready()
    for status in (RegistrationRequestStatus.REJECTED,):
        altered = request.model_copy(update={"status": status})
        receipt = _registrar().register(altered, proposal, canonical_state=canonical, now=FIXED)
        assert receipt.outcome is RegistrationOutcome.REJECTED
        assert receipt.reason_code == REGISTRATION_REQUEST_NOT_VALIDATED
    assert canonical.agent_network.records == []
    missing = _registrar().register(None, proposal, canonical_state=canonical, now=FIXED)
    assert missing.reason_code == REGISTRATION_REQUEST_MISSING


def test_missing_proposal_is_rejected():
    canonical, proposal, request = _ready()
    receipt = _registrar().register(request, None, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code == REGISTRATION_PROPOSAL_MISSING
    assert canonical.agent_network.records == []


# ============================================================================================= #
# 7-12. STALENESS, CONTENT AND IDENTITY PROTECTION
# ============================================================================================= #
def test_stale_proposal_is_rejected():
    canonical, proposal, request = _ready()
    stale = proposal.model_copy(deep=True)
    stale.provenance = [*proposal.provenance, "tampered after validation"]
    receipt = _registrar().register(request, stale, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code == REGISTRATION_STALE_REQUEST
    assert canonical.agent_network.records == []


def test_genome_content_mismatch_is_rejected():
    canonical, proposal, request = _ready()
    genome = proposal.genome.model_copy(deep=True)
    genome.predicates = ["precio -> otra_cosa"]
    altered = proposal.model_copy(update={"genome": genome})
    receipt = _registrar().register(request, altered, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code in (REGISTRATION_CONTENT_MISMATCH, REGISTRATION_STALE_REQUEST)
    assert canonical.agent_network.records == []


def test_identity_mismatch_is_rejected():
    canonical, proposal, request = _ready()
    forged = request.model_copy(update={"agent_id": "PRED-SEG-otra-Europa"})
    receipt = _registrar().register(forged, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code in (REGISTRATION_IDENTITY_MISMATCH, REGISTRATION_STALE_REQUEST)
    assert canonical.agent_network.records == []


def test_volatile_metadata_does_not_block_registration():
    """After the LOOP 6R repair a new timestamp is not a content change (F11 semantics apply)."""
    canonical, proposal, request = _ready()
    volatile = proposal.model_copy(deep=True)
    volatile.genome = proposal.genome.model_copy(deep=True)
    volatile.genome.created_at = "2035-01-01T00:00:00+00:00"
    receipt = _registrar().register(request, volatile, canonical_state=canonical, now=FIXED)
    assert receipt.is_registered()
    assert canonical.agent_network.records[0].agent_id == AGENT_ID


def test_registration_does_not_change_the_canonical_content_identity():
    canonical, proposal, request = _ready()
    before_fingerprint = canonical_state_fingerprint(canonical)
    before_network = canonical.problem.structured_problem.task_network.model_dump(mode="json")
    before_problem = canonical.problem.model_dump(mode="json")
    assert _registrar().register(request, proposal, canonical_state=canonical, now=FIXED).is_registered()
    assert canonical_state_fingerprint(canonical) == before_fingerprint   # agent_network is not content
    assert canonical.problem.structured_problem.task_network.model_dump(mode="json") == before_network
    assert canonical.problem.model_dump(mode="json") == before_problem    # TaskNetwork untouched


def test_registration_never_activates_or_executes():
    canonical, proposal, request = _ready()
    receipt = _registrar().register(request, proposal, canonical_state=canonical, now=FIXED)
    record = canonical.agent_network.records[0]
    assert record.status is AgentStatus.CREATED
    assert AgentStatus.RUNNING not in [event.to_status for event in record.history]
    assert canonical.agent_network.executions == []                 # no execution record
    assert receipt.activates_agents is False and receipt.executes_agents is False
    assert receipt.calls_model is False and receipt.selects_provider is False
    assert receipt.publishes is False and receipt.mutates_task_network is False


# ============================================================================================= #
# 13-18. PERSISTENCE, RESTART, DETERMINISM
# ============================================================================================= #
def test_registration_persists_through_the_existing_workstore(tmp_path):
    canonical, proposal, request = _ready()
    receipt = _registrar().register(request, proposal, canonical_state=canonical, now=FIXED)
    store = WorkStore(storage_dir=str(tmp_path))
    store[canonical.work.work_id] = canonical
    reloaded = WorkStore(storage_dir=str(tmp_path))[canonical.work.work_id]
    assert len(reloaded.agent_network.records) == 1
    record = reloaded.agent_network.records[0]
    assert record.agent_id == AGENT_ID and record.status is AgentStatus.CREATED
    assert request.request_id in record.history[-1].reason
    assert record.genome.verify_hash(receipt.genome_hash) == HASH_VERSION_V2
    record.assert_frozen_integrity()                                # not frozen: no-op, must not raise


def test_restart_reconstruction_and_idempotent_reregistration(tmp_path):
    canonical, proposal, request = _ready()
    store = WorkStore(storage_dir=str(tmp_path))
    assert _registrar().register(request, proposal, canonical_state=canonical, now=FIXED).is_registered()
    store[canonical.work.work_id] = canonical
    restarted = WorkStore(storage_dir=str(tmp_path))[canonical.work.work_id]
    registry = AgentRegistry.rebuild_from(restarted)
    assert registry.count() == 1 and registry.resolve(AGENT_ID) is not None
    again = AgentRegistrar(_reg()).register(request, proposal, canonical_state=restarted, now=FIXED)
    assert again.outcome is RegistrationOutcome.REUSED
    assert again.idempotent is True and registry.count() == 1


def test_registration_receipt_is_deterministic():
    canonical_a, proposal_a, request_a = _ready()
    receipts = []
    for _ in range(5):
        canonical, proposal, request = _ready()
        receipts.append(_registrar().register(request, proposal, canonical_state=canonical, now=FIXED))
    payloads = [{k: v for k, v in r.model_dump(mode="json").items()
                 if k not in ("created_at", "receipt_id")} for r in receipts]
    assert len({json.dumps(p, sort_keys=True) for p in payloads}) == 1


def test_rejected_receipts_leave_the_state_byte_identical():
    canonical, proposal, request = _ready()
    before = canonical.agent_network.model_dump(mode="json")
    for bad_request, bad_proposal in ((None, proposal),
                                      (request.model_copy(update={"status": "REJECTED"}), proposal),
                                      (request, None),
                                      (request, proposal.model_copy(update={"provenance": []}))):
        receipt = _registrar().register(bad_request, bad_proposal, canonical_state=canonical,
                                        now=FIXED)
        assert receipt.outcome is RegistrationOutcome.REJECTED
    assert canonical.agent_network.model_dump(mode="json") == before


# ============================================================================================= #
# ADVERSARIAL
# ============================================================================================= #
def test_adversarial_registration_cannot_be_forced_without_validation():
    """A rejected/altered provider-pinned request must never reach the registry."""
    canonical, proposal, request = _ready()
    pinned = request.model_copy(update={"provider_selection": "DEEPSEEK"})
    try:
        receipt = _registrar().register(pinned, proposal, canonical_state=canonical, now=FIXED)
        assert receipt.outcome is RegistrationOutcome.REJECTED
    except Exception:
        pass                                            # a construction-level refusal is also closed
    assert canonical.agent_network.records == []


def test_adversarial_cross_scope_genome_is_refused_by_the_registry():
    """The genome itself carries the scope: a foreign-scope genome cannot be registered here."""
    canonical, proposal, request = _ready()
    foreign = proposal.genome.model_copy(deep=True)
    foreign.work_id = "WORK-OTHER"
    foreign.problem_id = "PROB-OTHER"
    altered = proposal.model_copy(update={"genome": foreign})
    receipt = _registrar().register(request, altered, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert canonical.agent_network.records == []


def test_adversarial_receipt_cannot_claim_registration_without_a_write():
    canonical, proposal, request = _ready()
    receipt = _registrar().register(None, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.registry_count_before == receipt.registry_count_after == 0
    assert receipt.genome_hash == "" and receipt.record_status == ""


def test_reason_codes_are_all_exercised():
    source = open(os.path.abspath(__file__), encoding="utf-8").read()
    module = open(_MODULE, encoding="utf-8").read()
    for code in REASON_CODES:
        assert code in module
        if code != REGISTRATION_FROM_VALIDATED_REQUEST:
            assert code in source, code


def test_unauthorized_actor_cannot_register():
    """No agent (and no other caller) can register: only EM Core."""
    from src.eureka.universe.agent_registration import REGISTRATION_ACTOR_UNAUTHORIZED
    canonical, proposal, request = _ready()
    for actor in ("AGENT:pred-seg-demanda-europa", "DeepSeek", "anonymous", "EM Predictor"):
        receipt = _registrar().register(request, proposal, canonical_state=canonical,
                                        actor=actor, now=FIXED)
        assert receipt.outcome is RegistrationOutcome.REJECTED
        assert receipt.reason_code == REGISTRATION_ACTOR_UNAUTHORIZED
    assert canonical.agent_network.records == []          # nothing was written


def test_tampered_request_invariants_are_rejected():
    """A request whose authority/provider/output invariants were altered is refused."""
    from src.eureka.universe.agent_registration import REGISTRATION_REQUEST_TAMPERED
    canonical, proposal, request = _ready()
    tampered = request.model_copy(update={"provider_selection": "DEEPSEEK"})
    receipt = _registrar().register(tampered, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code == REGISTRATION_REQUEST_TAMPERED
    assert canonical.agent_network.records == []


def test_unexpected_registry_failure_fails_closed(monkeypatch):
    """Any unmapped registry error must surface as REGISTRATION_REGISTRY_REFUSED with no write."""
    from src.eureka.universe import agent_registry as registry_module
    from src.eureka.universe.agent_genome import AgentContractError
    from src.eureka.universe.agent_registration import REGISTRATION_REGISTRY_REFUSED
    canonical, proposal, request = _ready()

    def _boom(self, genome, **kwargs):
        raise AgentContractError("SOME_UNEXPECTED_REGISTRY_ERROR", genome.agent_id)

    monkeypatch.setattr(registry_module.AgentRegistry, "register", _boom)
    receipt = _registrar().register(request, proposal, canonical_state=canonical, now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REJECTED
    assert receipt.reason_code == REGISTRATION_REGISTRY_REFUSED
    assert canonical.agent_network.records == []


# ============================================================================================= #
# REAL ORCHESTRATOR E2E
# ============================================================================================= #
E2E_INTENT = "LOOP8 E2E: analizar el impacto del precio en la demanda en Europa y decidir el plan"


def _e2e_orchestrator() -> WorkOrchestrator:
    engine = TestDoubleCognitiveEngine()
    engine.semantic_fixtures[E2E_INTENT] = SemanticProposal(
        intent_category="DECISION",
        problem_understanding="Impacto del precio sobre la demanda",
        objective="Evaluar el impacto del precio en la demanda y decidir el plan",
        context="Europa", evidence_requirements=["serie historica de precios"],
        constraints=["sin datos personales"], unknowns=["elasticidad real"],
        risk="sesgo de seleccion", questions=["¿es estable la elasticidad?"],
        assumptions=["mercado competitivo"], authority="No authority required")
    engine.structural_fixtures[E2E_INTENT] = StructuralProposal(
        entities=["Europa"], variables=["precio", "demanda"], relationships=["precio -> demanda"],
        unknowns=["elasticidad real"], evidence_requirements=["serie historica de precios"],
        task_proposals=[
            CognitiveTask(task_id="E2E-T1", description="Establish current state",
                          owner="EM Descriptor", expected_outputs=["current state"], dependencies=[]),
            CognitiveTask(task_id="E2E-T2", description="Identify explanatory factors",
                          owner="EM Descriptor", expected_outputs=["factors"], dependencies=[]),
            CognitiveTask(task_id="E2E-T3", description="Evaluate future scenarios",
                          owner="EM Predictor", expected_outputs=["predictions"],
                          dependencies=["E2E-T1", "E2E-T2"])])
    return WorkOrchestrator(_reg(), engine)


def test_e2e_real_pipeline_registration_boundary():
    canonical = _e2e_orchestrator().orchestrate(E2E_INTENT)
    request = canonical.agent_registration_requests[0]
    proposal = canonical.agent_genome_proposals[0]
    assert canonical.agent_network.records == []            # LOOP 7 stopped at the request
    receipt = AgentRegistrar(_reg()).register(request, proposal, canonical_state=canonical,
                                              now=FIXED)
    assert receipt.outcome is RegistrationOutcome.REGISTERED
    assert receipt.agent_id == AGENT_ID
    assert canonical.agent_network.records[0].status is AgentStatus.CREATED
    assert canonical.agent_network.executions == []
    assert receipt.genome_hash_version == HASH_VERSION_V2
    # idempotent on a second pass, still one record, still no execution
    again = AgentRegistrar(_reg()).register(request, proposal, canonical_state=canonical, now=FIXED)
    assert again.outcome is RegistrationOutcome.REUSED
    assert len(canonical.agent_network.records) == 1
