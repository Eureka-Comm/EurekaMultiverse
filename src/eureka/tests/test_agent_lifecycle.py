"""EUREKA 5.1 — LOOP 9 tests: AGENT LIFECYCLE (canonical state machine, persistence, protection).

The lifecycle is the EXISTING canonical one (LOOP 1/2): 13 statuses, ONE ALLOWED_TRANSITIONS table,
ONE `transition()` validator, and registry operations that are the registry's own authority. This
loop VERIFIES it exhaustively and hardens the gaps it finds — it invents no transition.

Covered: the closed state machine · the legal path with history · illegal transitions · idempotency ·
persistence · restart recovery · scope protection · identity protection · hash protection · actor
authority · stale/frozen genome protection · supersede/retire semantics · no execution/model.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.getcwd(), "src"))

from src.eureka.universe.agent_genome import (ALLOWED_TRANSITIONS, HASH_VERSION_V2,
                                             AgentContractError, AgentDependency, AgentGenome,
                                             AgentIdentity, AgentNetworkState, AgentReference,
                                             AgentStatus, CognitiveFamily, EmergentAgentRecord,
                                             NetworkRole, ResourceBudget, LifecycleEvent,
                                             transition)
from src.eureka.universe.agent_registry import CORE_ACTOR, AgentRegistry, agent_actor
from src.eureka.universe.canonical_identity import canonical_state_fingerprint
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.problem_model import ProblemModel
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_store import WorkStore

WORK = "WORK-L9"
PROBLEM = "PROB-L9"
AGENT_ID = "PRED-SEG-demanda-Europa"
FIXED = "2026-09-12T00:00:00+00:00"

#: The path this loop proves end to end (the canonical machine, nothing invented).
LEGAL_PATH = (AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
              AgentStatus.VALIDATION_REQUIRED, AgentStatus.VALIDATED, AgentStatus.FROZEN,
              AgentStatus.COMPLETED, AgentStatus.RETIRED)


def _genome(**overrides) -> AgentGenome:
    data = dict(
        identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                               network_role=NetworkRole.SEGREGATOR, predicate="demanda",
                               context="Europa"),
        work_id=WORK, problem_id=PROBLEM, task_id="TASK-1", objective="analyse precio -> demanda",
        tools=["analyze_dataset"], resource_budget=ResourceBudget(max_model_calls=2),
        provenance=["LOOP 9 fixture"])
    data.update(overrides)
    return AgentGenome(**data)


def _canonical() -> CanonicalWorkState:
    canonical = CanonicalWorkState(work=EurekaWork(work_id=WORK, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=PROBLEM)
    return canonical


def _registry_with_agent(canonical=None):
    canonical = canonical or _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    record = registry.register(_genome(), reason="LOOP 9 fixture")
    return canonical, registry, record


def _walk(registry, agent_id, statuses, actor=CORE_ACTOR):
    record = None
    for status in statuses:
        record = registry.advance(agent_id, status, actor=actor, reason=f"-> {status.value}")
    return record


# ============================================================================================= #
# THE CLOSED STATE MACHINE
# ============================================================================================= #
def test_status_set_and_transition_table_are_closed():
    statuses = set(AgentStatus)
    assert len(statuses) == 13
    assert set(ALLOWED_TRANSITIONS) == statuses          # every status is declared
    for status, targets in ALLOWED_TRANSITIONS.items():
        assert all(isinstance(t, AgentStatus) for t in targets), status
        assert status not in targets                     # no self-transition
        assert len(set(targets)) == len(targets)         # no duplicates
    assert ALLOWED_TRANSITIONS[AgentStatus.RETIRED] == ()   # terminal


@pytest.mark.parametrize("current", list(AgentStatus))
@pytest.mark.parametrize("new", list(AgentStatus))
def test_transition_matrix_is_exhaustively_enforced(current, new):
    if new in ALLOWED_TRANSITIONS[current]:
        assert transition(current, new) is new
    else:
        with pytest.raises(AgentContractError) as err:
            transition(current, new)
        assert err.value.reason_code == "ILLEGAL_LIFECYCLE_TRANSITION"


def test_the_legal_path_is_traversable_with_a_full_history():
    canonical, registry, record = _registry_with_agent()
    assert record.status is AgentStatus.CREATED
    final = _walk(registry, AGENT_ID, LEGAL_PATH)
    assert final.status is AgentStatus.RETIRED
    assert [event.to_status for event in final.history] == [AgentStatus.CREATED, *LEGAL_PATH]
    assert all(event.actor == CORE_ACTOR for event in final.history)
    assert final.frozen_genome_hash and final.frozen_genome_hash_version == HASH_VERSION_V2


def test_illegal_transition_is_rejected_and_leaves_the_record_untouched():
    canonical, registry, record = _registry_with_agent()
    before = record.model_dump(mode="json")
    for illegal in (AgentStatus.RUNNING, AgentStatus.VALIDATED, AgentStatus.FROZEN,
                    AgentStatus.COMPLETED):
        with pytest.raises(AgentContractError) as err:
            registry.advance(AGENT_ID, illegal, actor=CORE_ACTOR)
        assert err.value.reason_code == "ILLEGAL_LIFECYCLE_TRANSITION"
    assert record.model_dump(mode="json") == before
    assert record.status is AgentStatus.CREATED


def test_no_self_transition_is_allowed():
    canonical, registry, record = _registry_with_agent()
    with pytest.raises(AgentContractError) as err:
        registry.advance(AGENT_ID, AgentStatus.CREATED, actor=CORE_ACTOR)
    assert err.value.reason_code == "ILLEGAL_LIFECYCLE_TRANSITION"


def test_replay_of_a_completed_transition_is_illegal_not_silent():
    """Re-issuing the SAME transition (idempotency attempt) is refused, never silently accepted."""
    canonical, registry, record = _registry_with_agent()
    registry.advance(AGENT_ID, AgentStatus.READY, actor=CORE_ACTOR)
    with pytest.raises(AgentContractError):
        registry.advance(AGENT_ID, AgentStatus.READY, actor=CORE_ACTOR)
    assert registry.resolve(AGENT_ID).status is AgentStatus.READY


# ============================================================================================= #
# AUTHORITY OF EACH TRANSITION
# ============================================================================================= #
def test_actor_authority_per_transition():
    canonical, registry, record = _registry_with_agent()
    # an agent may only report the outcome of ITS OWN execution
    own = agent_actor(AGENT_ID)
    with pytest.raises(AgentContractError) as err:
        registry.advance(AGENT_ID, AgentStatus.READY, actor=own)
    assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    registry.advance(AGENT_ID, AgentStatus.READY, actor=CORE_ACTOR)
    registry.advance(AGENT_ID, AgentStatus.RUNNING, actor=CORE_ACTOR)
    # the agent itself can report RETURNED / FAILED ...
    returned = registry.advance(AGENT_ID, AgentStatus.RETURNED, actor=own, reason="done")
    assert returned.status is AgentStatus.RETURNED
    # ... but never VALIDATED (validation is external)
    with pytest.raises(AgentContractError) as err:
        registry.advance(AGENT_ID, AgentStatus.VALIDATION_REQUIRED, actor=own)
    assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    # a foreign/unknown actor is refused everywhere
    for actor in ("AGENT:otro", "DeepSeek", "anonymous", "EM Predictor"):
        with pytest.raises(AgentContractError) as err:
            registry.advance(AGENT_ID, AgentStatus.VALIDATION_REQUIRED, actor=actor)
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR"


def test_an_agent_cannot_validate_or_freeze_itself():
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, (AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
                               AgentStatus.VALIDATION_REQUIRED))
    own = agent_actor(AGENT_ID)
    for status in (AgentStatus.VALIDATED, AgentStatus.FROZEN, AgentStatus.COMPLETED):
        with pytest.raises(AgentContractError) as err:
            registry.advance(AGENT_ID, status, actor=own)
        assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    assert registry.resolve(AGENT_ID).status is AgentStatus.VALIDATION_REQUIRED


def test_supersede_requires_core_and_links_the_successor():
    canonical, registry, record = _registry_with_agent()
    # a successor must carry a NEW identity (a revision creates a successor artifact)
    revised = _genome(objective="a revised objective")
    revised.identity = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                     network_role=NetworkRole.SEGREGATOR,
                                     predicate="demanda_v2", context="Europa")
    with pytest.raises(AgentContractError) as err:
        registry.supersede(AGENT_ID, revised, actor=agent_actor(AGENT_ID))
    assert err.value.reason_code == "UNAUTHORIZED_ACTOR"
    successor = registry.supersede(AGENT_ID, revised, actor=CORE_ACTOR, reason="revision")
    assert successor.agent_id == "PRED-SEG-demanda_v2-Europa"
    assert successor.supersedes == AGENT_ID
    assert registry.resolve(AGENT_ID).superseded_by == successor.agent_id
    # the SAME identity cannot be superseded by itself
    with pytest.raises(AgentContractError) as err:
        registry.supersede(successor.agent_id, revised, actor=CORE_ACTOR)
    assert err.value.reason_code == "SUPERSEDE_REQUIRES_NEW_IDENTITY"


# ============================================================================================= #
# IDENTITY / HASH / GENOME PROTECTION
# ============================================================================================= #
def test_lifecycle_never_changes_identity_or_genome_content():
    canonical, registry, record = _registry_with_agent()
    identity_before = record.genome.identity.model_dump(mode="json")
    hash_before = record.genome.hash()
    _walk(registry, AGENT_ID, LEGAL_PATH)
    final = registry.resolve(AGENT_ID)
    assert final.agent_id == AGENT_ID
    assert final.genome.identity.model_dump(mode="json") == identity_before
    assert final.genome.hash() == hash_before                     # content untouched
    assert final.genome.agent_id == AGENT_ID


def test_frozen_hash_is_recorded_once_and_never_rewritten():
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:6])                     # ...-> FROZEN
    frozen = registry.resolve(AGENT_ID)
    stored_hash, stored_version = frozen.frozen_genome_hash, frozen.frozen_genome_hash_version
    assert stored_hash == frozen.genome.hash() and stored_version == HASH_VERSION_V2
    registry.advance(AGENT_ID, AgentStatus.COMPLETED, actor=CORE_ACTOR)
    assert frozen.frozen_genome_hash == stored_hash               # never rewritten
    assert frozen.frozen_genome_hash_version == stored_version
    assert frozen.assert_frozen_integrity() is None


def test_a_frozen_genome_that_was_mutated_blocks_advancement():
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:6])
    frozen = registry.resolve(AGENT_ID)
    frozen.genome.objective = "tampered after freezing"           # real mutation
    with pytest.raises(AgentContractError) as err:
        registry.advance(AGENT_ID, AgentStatus.COMPLETED, actor=CORE_ACTOR)
    assert err.value.reason_code == "FROZEN_GENOME_MUTATION"
    assert frozen.status is AgentStatus.FROZEN                    # not advanced


def test_update_genome_is_refused_on_a_frozen_agent():
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:6])
    with pytest.raises(AgentContractError):
        registry.update_genome(AGENT_ID, {"objective": "new"}, actor=CORE_ACTOR)


# ============================================================================================= #
# SCOPE PROTECTION
# ============================================================================================= #
def test_unknown_agent_is_not_resolvable():
    canonical, registry, record = _registry_with_agent()
    with pytest.raises(AgentContractError) as err:
        registry.resolve("PRED-SEG-desconocido-Europa")
    assert err.value.reason_code == "AGENT_NOT_FOUND"
    assert registry.get("PRED-SEG-desconocido-Europa") is None


def test_lifecycle_cannot_operate_on_a_foreign_scope_record():
    """A record in the work's container that claims ANOTHER work must not be advanceable."""
    canonical = _canonical()
    foreign = EmergentAgentRecord(genome=_genome(work_id="WORK-OTHER", problem_id="PROB-OTHER"),
                                  status=AgentStatus.CREATED, provenance=["contamination fixture"])
    canonical.agent_network = AgentNetworkState(records=[foreign])
    registry = AgentRegistry.rebuild_from(canonical)
    with pytest.raises(AgentContractError) as err:
        registry.advance(foreign.agent_id, AgentStatus.READY, actor=CORE_ACTOR)
    assert err.value.reason_code in ("CROSS_WORK_CONTAMINATION", "CROSS_PROBLEM_CONTAMINATION")


def test_cross_work_reference_is_refused_at_construction():
    with pytest.raises(AgentContractError) as err:
        _genome(upstream_agents=[AgentReference(agent_id="PRED-SEG-otro-Asia",
                                                network_role=NetworkRole.SEGREGATOR,
                                                work_id="WORK-OTHER")])
    assert err.value.reason_code == "CROSS_WORK_REFERENCE"


def test_scope_escape_via_a_new_genome_is_refused():
    canonical, registry, record = _registry_with_agent()
    escaping = _genome(problem_id="PROB-OTHER")
    escaping.identity = AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                                      network_role=NetworkRole.SEGREGATOR,
                                      predicate="demanda_v3", context="Europa")
    with pytest.raises(AgentContractError) as err:
        registry.supersede(AGENT_ID, escaping, actor=CORE_ACTOR)
    assert err.value.reason_code in ("CROSS_PROBLEM_CONTAMINATION", "CROSS_WORK_CONTAMINATION")


# ============================================================================================= #
# PERSISTENCE AND RESTART RECOVERY
# ============================================================================================= #
def test_history_persists_through_the_existing_workstore(tmp_path):
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:4])
    before = registry.resolve(AGENT_ID).model_dump(mode="json")
    store = WorkStore(storage_dir=str(tmp_path))
    store[WORK] = canonical
    reloaded = WorkStore(storage_dir=str(tmp_path))[WORK]
    restored = reloaded.agent_network.records[0]
    assert restored.model_dump(mode="json") == before
    assert [e.to_status for e in restored.history][1:] == list(LEGAL_PATH[:4])


def test_restart_recovery_reconstructs_the_exact_lifecycle(tmp_path):
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:6])                     # up to FROZEN
    store = WorkStore(storage_dir=str(tmp_path))
    store[WORK] = canonical
    restarted = WorkStore(storage_dir=str(tmp_path))[WORK]
    recovered = AgentRegistry.rebuild_from(restarted)
    assert recovered.count() == 1
    restored = recovered.resolve(AGENT_ID)
    assert restored.status is AgentStatus.FROZEN
    assert restored.frozen_genome_hash == restored.genome.hash()
    assert restored.assert_frozen_integrity() is None
    # the lifecycle can continue from where it stopped
    assert recovered.advance(AGENT_ID, AgentStatus.COMPLETED,
                             actor=CORE_ACTOR).status is AgentStatus.COMPLETED


def test_restart_recovery_preserves_the_frozen_tamper_evidence(tmp_path):
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH[:6])
    store = WorkStore(storage_dir=str(tmp_path))
    store[WORK] = canonical
    restarted = WorkStore(storage_dir=str(tmp_path))[WORK]
    restored = restarted.agent_network.records[0]
    assert restored.genome.verify_hash(restored.frozen_genome_hash) == HASH_VERSION_V2
    restored.genome.tools = ["tampered"]                          # tamper after restart
    with pytest.raises(AgentContractError) as err:
        restored.assert_frozen_integrity()
    assert err.value.reason_code == "FROZEN_GENOME_MUTATION"


# ============================================================================================= #
# SIDE-EFFECT FIREWALL
# ============================================================================================= #
def test_lifecycle_does_not_change_the_canonical_content_identity():
    canonical, registry, record = _registry_with_agent()
    before = canonical_state_fingerprint(canonical)
    _walk(registry, AGENT_ID, LEGAL_PATH)
    assert canonical_state_fingerprint(canonical) == before       # agent layer is not content
    assert canonical.problem.model_dump(mode="json") == _canonical().problem.model_dump(mode="json")


def test_lifecycle_never_executes_or_calls_a_model():
    canonical, registry, record = _registry_with_agent()
    _walk(registry, AGENT_ID, LEGAL_PATH)
    assert canonical.agent_network.executions == []               # no execution record
    source = open(os.path.join("src", "eureka", "universe", "agent_registry.py"),
                  encoding="utf-8").read()
    for banned in ("AgentRuntime", "DeterministicModelProvider", "requests.", "urlopen"):
        assert banned not in source, banned
    assert registry.count() == 1
