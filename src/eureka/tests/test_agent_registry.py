"""EUREKA 5.1 — LOOP 2 tests: AGENT REGISTRY / LIFECYCLE (derived index, no second store).

Mandated coverage (Harness LOOP 2 + human decision of 2026-09-12):
register/resolve/get/list/activate/pause/complete/retire/supersede · CONSTITUTIONAL vs EMERGENT
separation · canonical lifecycle · and the adversarial set: duplicate agent, fake Core, authority
escalation, cross-work contamination, frozen mutation, illegal lifecycle transition.

Persistence is NOT a second authority: the registry is derived from — and mutates only — the
`agent_network` container inside the canonical Work state, persisted by the existing WorkStore.
"""
import pathlib
import tempfile

import pytest

from src.eureka.universe.agent_genome import (CONSTITUTIONAL_EM, AgentContractError, AgentGenome,
                                             AgentIdentity, AgentNetworkState, AgentStatus,
                                             CognitiveFamily, NetworkRole, ResourceBudget)
from src.eureka.universe.agent_registry import CORE_ACTOR, AgentRegistry, agent_actor
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.problem_model import ProblemModel
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-EMERGENT-1"
PROBLEM = "PROB-EMERGENT-1"


def _canonical(work_id: str = WORK, problem_id: str = PROBLEM) -> CanonicalWorkState:
    canonical = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=problem_id)
    return canonical


def _identity(predicate: str = "LeadTime", context: str = "Europe",
              family: CognitiveFamily = CognitiveFamily.PREDICTOR,
              role: NetworkRole = NetworkRole.SEGREGATOR) -> AgentIdentity:
    return AgentIdentity(cognitive_family=family, network_role=role, predicate=predicate, context=context)


def _genome(predicate: str = "LeadTime", work_id: str = WORK, problem_id: str = PROBLEM,
            **overrides) -> AgentGenome:
    data = dict(identity=_identity(predicate), work_id=work_id, problem_id=problem_id,
                task_id=f"TASK-{predicate}", objective=f"Analyse {predicate}",
                tools=["acfl.evaluate"], evidence_requirements=["series"],
                resource_budget=ResourceBudget(max_model_calls=2),
                provenance=["proposed by necessity test"])
    data.update(overrides)
    return AgentGenome(**data)


@pytest.fixture
def registry():
    canonical = _canonical()
    reg = AgentRegistry.rebuild_from(canonical)
    return reg, canonical


# ============================================================================================= #
# register / resolve / get / list
# ============================================================================================= #
def test_register_resolve_get_and_history(registry):
    reg, canonical = registry
    rec = reg.register(_genome(), reason="authorized by Core")
    assert rec.agent_id == "PRED-SEG-LeadTime-Europe"
    assert rec.status is AgentStatus.CREATED
    assert rec.work_id == WORK and rec.problem_id == PROBLEM
    assert [e.to_status for e in rec.history] == [AgentStatus.CREATED]
    assert any("registered by EM Core" in p for p in rec.provenance)
    assert reg.resolve(rec.agent_id) is rec and reg.get(rec.agent_id) is rec
    assert reg.count() == 1
    # the record lives INSIDE the canonical state (no second store)
    assert canonical.agent_network.records[0] is rec


def test_resolve_unknown_agent_fails_closed(registry):
    reg, _ = registry
    assert reg.get("PRED-SEG-Nope-Europe") is None
    with pytest.raises(AgentContractError) as err:
        reg.resolve("PRED-SEG-Nope-Europe")
    assert err.value.reason_code == "AGENT_NOT_FOUND"


def test_constitutional_and_emergent_are_separate(registry):
    reg, _ = registry
    constitutional = reg.constitutional_agents()
    assert [c["agent_id"] for c in constitutional] == list(CONSTITUTIONAL_EM)
    assert all(c["kind"] == "CONSTITUTIONAL" for c in constitutional)
    assert reg.list(kind="CONSTITUTIONAL") == []           # the nucleus is not registered here
    reg.register(_genome())
    assert [r.agent_id for r in reg.list()] == ["PRED-SEG-LeadTime-Europe"]
    assert [r.agent_id for r in reg.list(kind="ALL")] == ["PRED-SEG-LeadTime-Europe"]
    assert reg.count() == 1


def test_cannot_impersonate_a_constitutional_agent(registry):
    reg, _ = registry
    # (a) structurally impossible: every derived identity carries a family prefix, never "EM ..."
    assert not _identity("Core").agent_id.startswith("EM ")
    assert not _identity("LeadTime").agent_id.startswith("EM ")
    # (b) defence in depth: the id space of the nucleus is explicitly guarded
    with pytest.raises(AgentContractError) as err:
        reg._assert_not_constitutional_id("EM Core")
    assert err.value.reason_code == "CONSTITUTIONAL_IMPERSONATION"
    reg.register(_genome())          # a normal emergent agent is accepted
    assert reg.count() == 1


def test_list_filters_by_status(registry):
    reg, _ = registry
    a = reg.register(_genome("LeadTime"))
    reg.register(_genome("SupplierReliability"))
    reg.advance(a.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
    ready = reg.list(status=AgentStatus.READY)
    assert [r.agent_id for r in ready] == ["PRED-SEG-LeadTime-Europe"]
    assert len(reg.list(status=AgentStatus.CREATED)) == 1


# ============================================================================================= #
# adversarial: duplicate agent · fake Core · cross-work
# ============================================================================================= #
def test_duplicate_agent_is_rejected_but_identical_registration_is_idempotent(registry):
    reg, _ = registry
    a = reg.register(_genome())
    same = reg.register(_genome())                       # identical content: REUSE (no duplicate)
    assert same is a and reg.count() == 1
    other = _genome(objective="DIFFERENT objective, same identity")
    with pytest.raises(AgentContractError) as err:
        reg.register(other)
    assert err.value.reason_code == "DUPLICATE_AGENT"
    assert reg.count() == 1


def test_fake_core_and_unauthorized_actors_are_rejected(registry):
    reg, _ = registry
    for actor in ("AGENT:someone", "DeepSeek", "anonymous", "EM Actioner"):
        with pytest.raises(AgentContractError) as err:
            reg.register(_genome(), actor=actor)
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    rec = reg.register(_genome())
    for actor in ("AGENT:someone", "DeepSeek"):
        with pytest.raises(AgentContractError):
            reg.retire(rec.agent_id, actor=actor)
    assert rec.status is AgentStatus.CREATED


def test_cross_work_and_cross_problem_registration_is_rejected(registry):
    reg, _ = registry
    with pytest.raises(AgentContractError) as err:
        reg.register(_genome(work_id="WORK-OTHER"))
    assert err.value.reason_code == "CROSS_WORK_CONTAMINATION"
    with pytest.raises(AgentContractError) as err2:
        reg.register(_genome(problem_id="PROB-OTHER"))
    assert err2.value.reason_code == "CROSS_PROBLEM_CONTAMINATION"
    assert reg.count() == 0


# ============================================================================================= #
# adversarial: authority escalation · modifying another agent
# ============================================================================================= #
def test_configuration_update_cannot_escalate_authority_or_identity(registry):
    reg, _ = registry
    rec = reg.register(_genome())
    updated = reg.update_genome(rec.agent_id, {"objective": "refined objective"})
    assert updated.genome.objective == "refined objective"
    for patch in ({"authority_scope": "AUTHORITY"}, {"canonical_status": "CANONICAL"},
                  {"execution_mode": "REAL_EXECUTION"}, {"promote": True}):
        with pytest.raises(AgentContractError):
            reg.update_genome(rec.agent_id, patch)
    with pytest.raises(AgentContractError) as err:
        reg.update_genome(rec.agent_id, {"agent_id": "PRED-SEG-Other-Europe"})
    assert err.value.reason_code == "IDENTITY_MUTATION"
    with pytest.raises(AgentContractError) as err2:
        reg.update_genome(rec.agent_id, {"work_id": "WORK-OTHER"})
    assert err2.value.reason_code == "CROSS_WORK_CONTAMINATION"
    assert reg.resolve(rec.agent_id).genome.work_id == WORK


def test_an_agent_can_only_report_its_own_outcome(registry):
    reg, _ = registry
    a = reg.register(_genome("LeadTime"))
    b = reg.register(_genome("SupplierReliability"))
    for rec in (a, b):
        reg.advance(rec.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
        reg.advance(rec.agent_id, AgentStatus.RUNNING, actor=CORE_ACTOR)
    # an agent may report ITS OWN return...
    reg.advance(a.agent_id, AgentStatus.RETURNED, actor=agent_actor(a.agent_id), reason="done")
    assert a.status is AgentStatus.RETURNED
    # ...but never touch another agent, nor validate/freeze anything
    with pytest.raises(AgentContractError) as err:
        reg.advance(b.agent_id, AgentStatus.RETURNED, actor=agent_actor(a.agent_id))
    assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    with pytest.raises(AgentContractError):
        reg.advance(a.agent_id, AgentStatus.VALIDATED, actor=agent_actor(a.agent_id))
    with pytest.raises(AgentContractError):
        reg.update_genome(b.agent_id, {"objective": "hijacked"}, actor=agent_actor(a.agent_id))


# ============================================================================================= #
# adversarial: illegal transitions · frozen mutation
# ============================================================================================= #
def test_illegal_lifecycle_transitions_are_rejected(registry):
    reg, _ = registry
    rec = reg.register(_genome())
    with pytest.raises(AgentContractError) as err:
        reg.activate(rec.agent_id)                       # CREATED -> RUNNING is illegal
    assert err.value.reason_code == "ILLEGAL_LIFECYCLE_TRANSITION"
    with pytest.raises(AgentContractError):
        reg.complete(rec.agent_id)                       # CREATED -> COMPLETED is illegal
    with pytest.raises(AgentContractError):
        reg.validate(rec.agent_id)                       # CREATED -> VALIDATED is illegal
    assert rec.status is AgentStatus.CREATED


def test_frozen_agent_cannot_be_mutated(registry):
    reg, _ = registry
    rec = reg.register(_genome())
    for status in (AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
                   AgentStatus.VALIDATION_REQUIRED, AgentStatus.VALIDATED, AgentStatus.FROZEN):
        reg.advance(rec.agent_id, status, actor=CORE_ACTOR)
    assert rec.frozen_genome_hash == rec.genome.hash()
    with pytest.raises(AgentContractError) as err:
        reg.update_genome(rec.agent_id, {"objective": "changed after freeze"})
    assert err.value.reason_code == "FROZEN_AGENT_MUTATION"
    with pytest.raises(AgentContractError) as err2:
        reg.advance(rec.agent_id, AgentStatus.RUNNING, actor=CORE_ACTOR)
    assert err2.value.reason_code == "FROZEN_AGENT_MUTATION"
    # tampering with the frozen genome is detected by the integrity check
    original = rec.genome
    rec.genome = AgentGenome.model_validate({**original.model_dump(mode="json"),
                                             "objective": "tampered"})
    with pytest.raises(AgentContractError) as err3:
        rec.assert_frozen_integrity()
    assert err3.value.reason_code == "FROZEN_GENOME_MUTATION"
    rec.genome = original
    rec.assert_frozen_integrity()
    assert reg.complete(rec.agent_id).status is AgentStatus.COMPLETED     # complete/retire allowed


# ============================================================================================= #
# happy paths · supersede
# ============================================================================================= #
def test_full_lifecycle_happy_path(registry):
    reg, _ = registry
    rec = reg.register(_genome())
    reg.advance(rec.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
    reg.activate(rec.agent_id)
    assert rec.status is AgentStatus.RUNNING
    reg.pause(rec.agent_id, reason="awaiting evidence")
    assert rec.status is AgentStatus.BLOCKED
    reg.advance(rec.agent_id, AgentStatus.READY, actor=CORE_ACTOR)       # resume
    reg.activate(rec.agent_id)
    reg.mark_returned(rec.agent_id, actor=agent_actor(rec.agent_id))
    reg.require_validation(rec.agent_id)
    reg.validate(rec.agent_id, reason="evidence verified")
    reg.freeze(rec.agent_id)
    reg.complete(rec.agent_id)
    assert rec.status is AgentStatus.COMPLETED
    assert reg.retire(rec.agent_id).status is AgentStatus.RETIRED
    assert [e.to_status for e in rec.history][0] is AgentStatus.CREATED
    assert len(rec.history) >= 10                                        # append-only audit trail


def test_supersede_retires_the_old_agent_and_links_the_successor(registry):
    reg, _ = registry
    old = reg.register(_genome("LeadTime"))
    new = reg.supersede(old.agent_id, _genome("LeadTimeV2"))
    assert new.supersedes == old.agent_id
    assert reg.resolve(old.agent_id).superseded_by == new.agent_id
    assert reg.resolve(old.agent_id).status is AgentStatus.RETIRED
    assert new.status is AgentStatus.CREATED
    assert reg.count() == 2
    with pytest.raises(AgentContractError) as err:
        reg.supersede(new.agent_id, _genome("LeadTimeV2"))     # same identity: not a successor
    assert err.value.reason_code == "SUPERSEDE_REQUIRES_NEW_IDENTITY"


# ============================================================================================= #
# persistence through the EXISTING authority (no second store)
# ============================================================================================= #
def test_agent_network_persists_through_the_work_store_and_rebuilds(tmp_path):
    canonical = _canonical()
    reg = AgentRegistry.rebuild_from(canonical)
    rec = reg.register(_genome())
    reg.advance(rec.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
    store = WorkStore(str(tmp_path / "works"))
    store[WORK] = canonical                                   # the EXISTING durable authority

    reloaded = WorkStore(str(tmp_path / "works"))[WORK]        # simulate a restart
    reg2 = AgentRegistry.rebuild_from(reloaded)                # derived index, no second store
    assert reg2.count() == 1
    restored = reg2.resolve("PRED-SEG-LeadTime-Europe")
    assert restored.status is AgentStatus.READY
    assert restored.genome.hash() == rec.genome.hash()
    assert reloaded.work.work_id == WORK                       # Work remains the authority


def test_legacy_canonical_state_without_agent_network_is_backwards_compatible(tmp_path):
    canonical = _canonical()
    payload = canonical.model_dump(mode="json")
    payload.pop("agent_network")                                # a work persisted before LOOP 2
    revived = CanonicalWorkState.model_validate(payload)
    assert revived.agent_network.records == []
    reg = AgentRegistry.rebuild_from(revived)
    assert reg.count() == 0
    reg.register(_genome())
    assert reg.count() == 1


# ============================================================================================= #
# invariant: derived index, not a persistence authority
# ============================================================================================= #
def test_registry_module_is_not_a_persistence_authority():
    src = pathlib.Path(__file__).resolve().parents[1] / "universe" / "agent_registry.py"
    text = src.read_text(encoding="utf-8")
    assert "open(" not in text, "the registry must not perform file I/O"
    import src.eureka.universe.agent_registry as mod
    classes = [n for n, o in vars(mod).items() if isinstance(o, type) and o.__module__ == mod.__name__]
    offenders = [n for n in classes
                 if n.endswith(("Store", "Database", "Repository", "FileStore", "StateStore"))]
    assert offenders == [], f"no second persistence authority allowed: {offenders}"
    assert "AgentRegistry" in classes
