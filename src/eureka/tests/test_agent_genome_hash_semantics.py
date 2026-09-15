"""EUREKA 5.1 — LOOP 6R tests: F11 REPAIR — AgentGenome hash semantics (semantic identity).

F11 (repaired here): ``AgentGenome.hash()`` was documented as a CONTENT hash but included
``created_at`` (and ``provenance``), so two semantically identical genomes hashed differently and
``AgentRegistry`` idempotency was clock-dependent (~4-7% flake).

Repair: ``hash()`` is the SEMANTIC identity (V2). ``created_at`` is VOLATILE metadata,
``frozen`` is LIFECYCLE metadata and ``provenance`` is EVIDENCE/AUDIT metadata — none of them is
semantic content. The legacy payload is preserved as ``hash_v1()`` so historical hashes keep
verifying (no silent migration), and the audit trail stays tamper-evident through ``audit_hash()``.

F11 GATE coverage: semantic identity defined · volatile metadata separated · deterministic hash
proven · reconstructed genome produces the same semantic hash · meaningful mutation changes the hash
· Registry implications · Runtime implications · historical compatibility · no silent migration ·
no data loss · regression · evidence.
"""
import pytest

from src.eureka.universe.agent_genome import (EVIDENCE_METADATA_KEYS, HASH_VERSION_V1,
                                             HASH_VERSION_V2, LIFECYCLE_METADATA_KEYS,
                                             VOLATILE_METADATA_KEYS, AgentContractError,
                                             AgentDependency, AgentGenome, AgentIdentity,
                                             AgentNetworkState, AgentReference, AgentStatus,
                                             CognitiveFamily, EmergentAgentRecord, NetworkRole,
                                             ResourceBudget, TaskEnvelope,
                                             detect_identity_collision)
from src.eureka.universe.agent_registry import AgentRegistry
from src.eureka.universe.canonical_state import CanonicalWorkState
from src.eureka.universe.work_model import EurekaWork

WORK = "WORK-6R"
PROBLEM = "PROB-6R"
EXCLUDED = VOLATILE_METADATA_KEYS | LIFECYCLE_METADATA_KEYS | EVIDENCE_METADATA_KEYS
SEMANTIC_FIELDS = [name for name in AgentGenome.model_fields if name not in EXCLUDED]


def _genome(**overrides) -> AgentGenome:
    data = dict(
        identity=AgentIdentity(cognitive_family=CognitiveFamily.PREDICTOR,
                               network_role=NetworkRole.SEGREGATOR, predicate="demanda",
                               context="Europa"),
        work_id=WORK, problem_id=PROBLEM, task_id="TASK-1", objective="analyse precio -> demanda",
        predicates=["precio -> demanda"], tools=["analyze_dataset"],
        evidence_requirements=["series:precio"], resource_budget=ResourceBudget(max_model_calls=2),
        provenance=["proposed by the necessity test"])
    data.update(overrides)
    return AgentGenome(**data)


def _canonical() -> CanonicalWorkState:
    from src.eureka.universe.problem_model import ProblemModel
    canonical = CanonicalWorkState(work=EurekaWork(work_id=WORK, title="t", user_intent="u",
                                                   task_category="c", problem_statement="p"))
    canonical.problem = ProblemModel(intent="u", objective="o", problem_id=PROBLEM)
    return canonical


# ============================================================================================= #
# 1-5. SEMANTIC IDENTITY DEFINITION
# ============================================================================================= #
def test_metadata_classes_are_declared_and_disjoint():
    assert VOLATILE_METADATA_KEYS == frozenset({"created_at"})
    assert LIFECYCLE_METADATA_KEYS == frozenset({"frozen"})
    assert EVIDENCE_METADATA_KEYS == frozenset({"provenance"})
    assert not (VOLATILE_METADATA_KEYS & LIFECYCLE_METADATA_KEYS)
    assert not (VOLATILE_METADATA_KEYS & EVIDENCE_METADATA_KEYS)
    assert not (LIFECYCLE_METADATA_KEYS & EVIDENCE_METADATA_KEYS)
    # every declared field is classified: either semantic or in exactly one metadata class
    assert set(AgentGenome.model_fields) == set(SEMANTIC_FIELDS) | set(EXCLUDED)
    assert "created_at" in AgentGenome.model_fields and "created_at" not in SEMANTIC_FIELDS


def _mutate_field(genome: AgentGenome, field: str) -> None:
    """Apply a MEANINGFUL mutation to one semantic field (adversarial per-field coverage)."""
    current = getattr(genome, field)
    if field == "authority_scope":
        object.__setattr__(genome, field, "OWNER")                # frozen field
    elif field == "identity":
        genome.identity = genome.identity.model_copy(update={"context": "Asia"})
    elif field == "model_requirements":
        genome.model_requirements = genome.model_requirements.model_copy(
            update={"min_context_tokens": 16000})
    elif field == "resource_budget":
        genome.resource_budget = ResourceBudget(max_model_calls=3)
    elif field == "output_schema":
        genome.output_schema = {**current, "extra": {"type": "string"}}
    elif field == "dependencies":
        genome.dependencies = list(current) + [AgentDependency(agent_id="PRED-SEG-otro-Asia")]
    elif field in ("upstream_agents", "downstream_agents"):
        setattr(genome, field, list(current) + [AgentReference(
            agent_id="PRED-SEG-otro-Asia", network_role=NetworkRole.SEGREGATOR, work_id=WORK)])
    elif isinstance(current, bool):
        setattr(genome, field, not current)
    elif isinstance(current, list):
        setattr(genome, field, list(current) + ["X"])
    elif isinstance(current, str):
        if field == "return_to":            # toggle between the two values the contract allows
            setattr(genome, field, "EM Core" if current != "EM Core" else "EM Predictor")
            return
        setattr(genome, field, {"uncertainty": "HIGH", "execution_level": "SYSTEM",
                                "version": "1.1",
                                "work_id": "WORK-OTHER", "problem_id": "PROB-OTHER",
                                "task_id": "TASK-2"}.get(field, current + "X"))
    else:                                                        # pragma: no cover - defensive
        raise AssertionError(f"unhandled field {field}")


@pytest.mark.parametrize("field", SEMANTIC_FIELDS)
def test_every_semantic_field_changes_the_hash(field):
    base = _genome()
    mutated = base.model_copy(deep=True)
    _mutate_field(mutated, field)
    assert base.hash() != mutated.hash(), f"mutating '{field}' did not change the semantic hash"
    assert base.audit_hash() != mutated.audit_hash()


def test_semantically_identical_genomes_hash_equally():
    """The F11 defect: identical content built at different times must hash EQUALLY."""
    first = _genome()
    second = _genome()
    second.created_at = "2030-01-01T00:00:00+00:00"        # forced, not timing luck
    assert first.created_at != second.created_at
    assert first.hash() == second.hash()
    assert first.hash_v1() != second.hash_v1()             # the LEGACY payload was clock-dependent
    assert detect_identity_collision([first, second]) == []


# ============================================================================================= #
# 6-9. METADATA SEPARATION (volatile / lifecycle / evidence)
# ============================================================================================= #
def test_volatile_and_lifecycle_metadata_are_excluded():
    base = _genome()
    volatile = base.model_copy(deep=True)
    volatile.created_at = "2040-01-01T00:00:00+00:00"
    frozen = base.model_copy(deep=True)
    frozen.frozen = True
    assert base.hash() == volatile.hash() == frozen.hash()
    # ...but the metadata is NOT lost: it stays in the model (no data loss)
    dumped = volatile.model_dump(mode="json")
    assert dumped["created_at"] == "2040-01-01T00:00:00+00:00"
    assert "frozen" in base.model_dump(mode="json") and "provenance" in dumped


def test_provenance_is_evidence_metadata_not_semantic_identity():
    first = _genome(provenance=["proposed by the necessity test"])
    second = _genome(provenance=["registered by EM Core", "extra audit line"])
    assert first.hash() == second.hash()                    # same unit, different audit trail
    assert first.audit_hash() != second.audit_hash()        # the trail stays tamper-evident
    assert first.provenance != second.provenance            # and is preserved (no data loss)


def test_audit_hash_covers_content_and_trail():
    base = _genome()
    content_changed = base.model_copy(deep=True)
    content_changed.objective = "different"
    trail_changed = base.model_copy(deep=True)
    trail_changed.provenance = ["rewritten audit trail"]
    assert base.audit_hash() != content_changed.audit_hash()
    assert base.audit_hash() != trail_changed.audit_hash()
    assert base.audit_hash() == base.model_copy(deep=True).audit_hash()   # deterministic


def test_hash_format_and_versions_are_declared():
    genome = _genome()
    assert len(genome.hash()) == 64 and len(genome.hash_v1()) == 64
    assert genome.hash_version() == HASH_VERSION_V2
    assert genome.verify_hash(genome.hash()) == HASH_VERSION_V2
    assert genome.verify_hash(genome.hash_v1()) == HASH_VERSION_V1
    assert genome.verify_hash("0" * 64) is None
    assert genome.verify_hash("") is None
    assert genome.hash() != genome.hash_v1()                # different semantics, same genome


# ============================================================================================= #
# 10-13. DETERMINISM AND REPRODUCIBILITY
# ============================================================================================= #
def test_hash_is_deterministic_over_200_constructions():
    hashes = {_genome().hash() for _ in range(200)}         # each with its own wall-clock timestamp
    assert len(hashes) == 1                                 # the F11 flake is gone


def test_registry_idempotency_is_deterministic_over_200_registrations():
    """The exact previously-flaky scenario (~4-7% failure): identical content must REUSE."""
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    first = registry.register(_genome())
    reuses = 0
    for _ in range(200):
        if registry.register(_genome()) is first:
            reuses += 1
    assert reuses == 200
    assert registry.count() == 1
    # incompatible content on the SAME identity still fails closed
    other = _genome(objective="a different objective")
    with pytest.raises(AgentContractError) as err:
        registry.register(other)
    assert err.value.reason_code == "DUPLICATE_AGENT"


def test_reconstructed_genome_is_not_stale_but_a_mutation_is():
    """Runtime/envelope implication: the canonical check now compares SEMANTIC hashes."""
    genome = _genome()
    envelope = TaskEnvelope(envelope_id="E", work_id=WORK, problem_id=PROBLEM, task_id="TASK-1",
                            agent_id=genome.agent_id, genome_hash=genome.hash(),
                            authorized_inputs=["precio"], allowed_tools=["analyze_dataset"])
    reconstructed = _genome()
    reconstructed.created_at = "2035-05-05T00:00:00+00:00"
    assert envelope.assert_matches(reconstructed) is None    # volatile difference: NOT stale
    mutated = genome.model_copy(deep=True)
    mutated.objective = "different"
    with pytest.raises(AgentContractError) as err:
        envelope.assert_matches(mutated)
    assert err.value.reason_code == "ENVELOPE_GENOME_MISMATCH"


def test_serialization_round_trip_preserves_hash_semantics():
    genome = _genome()
    restored = AgentGenome.model_validate(genome.model_dump(mode="json"))
    assert restored.hash() == genome.hash()
    assert restored.hash_v1() == genome.hash_v1()
    assert restored.audit_hash() == genome.audit_hash()


# ============================================================================================= #
# 14-17. HISTORICAL COMPATIBILITY / NO SILENT MIGRATION
# ============================================================================================= #
def test_legacy_v1_frozen_hash_still_verifies():
    genome = _genome()
    record = EmergentAgentRecord(genome=genome, status=AgentStatus.FROZEN,
                                 frozen_genome_hash=genome.hash_v1(),
                                 frozen_genome_hash_version=HASH_VERSION_V1)
    assert record.frozen_genome_hash_version == HASH_VERSION_V1
    assert record.assert_frozen_integrity() is None
    # the stored hash is NEVER rewritten by verification (no silent migration)
    assert record.frozen_genome_hash == genome.hash_v1()


def test_legacy_record_without_version_field_defaults_to_v1():
    genome = _genome()
    payload = {"genome": genome.model_dump(mode="json"), "status": "FROZEN",
               "frozen_genome_hash": genome.hash_v1()}
    record = EmergentAgentRecord.model_validate(payload)      # no version field in the payload
    assert record.frozen_genome_hash_version == HASH_VERSION_V1
    assert record.assert_frozen_integrity() is None


def test_new_freeze_uses_the_semantic_hash_and_records_its_version():
    canonical = _canonical()
    registry = AgentRegistry.rebuild_from(canonical)
    record = registry.register(_genome(), reason="LOOP 6R test")
    for status in (AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
                   AgentStatus.VALIDATION_REQUIRED, AgentStatus.VALIDATED):
        registry.advance(record.agent_id, status, actor="EM Core")
    frozen = registry.advance(record.agent_id, AgentStatus.FROZEN, actor="EM Core")
    assert frozen.frozen_genome_hash == frozen.genome.hash()
    assert frozen.frozen_genome_hash_version == HASH_VERSION_V2
    assert frozen.assert_frozen_integrity() is None


def test_frozen_tamper_is_detected_under_both_versions():
    genome = _genome()
    for version, stored in ((HASH_VERSION_V1, genome.hash_v1()),
                            (HASH_VERSION_V2, genome.hash())):
        record = EmergentAgentRecord(genome=genome.model_copy(deep=True), status=AgentStatus.FROZEN,
                                     frozen_genome_hash=stored, frozen_genome_hash_version=version)
        record.genome.objective = "tampered"                  # real mutation
        with pytest.raises(AgentContractError) as err:
            record.assert_frozen_integrity()
        assert err.value.reason_code == "FROZEN_GENOME_MUTATION"


def test_relabelled_hash_version_fails_closed():
    """A hash re-labelled with another version (without migrating the value) must be rejected."""
    genome = _genome()
    record = EmergentAgentRecord(genome=genome, status=AgentStatus.FROZEN,
                                 frozen_genome_hash=genome.hash_v1(),
                                 frozen_genome_hash_version=HASH_VERSION_V2)
    with pytest.raises(AgentContractError) as err:
        record.assert_frozen_integrity()
    assert err.value.reason_code == "FROZEN_HASH_VERSION_MISMATCH"


def test_frozen_genome_mutation_guard_uses_semantic_identity():
    genome = _genome()
    genome.freeze()
    volatile_only = genome.model_copy(deep=True)
    volatile_only.created_at = "2040-01-01T00:00:00+00:00"
    assert genome.assert_compatible_with(volatile_only) is None      # metadata, not content
    content = genome.model_copy(deep=True)
    content.tools = ["other_tool"]
    with pytest.raises(AgentContractError) as err:
        genome.assert_compatible_with(content)
    assert err.value.reason_code == "FROZEN_GENOME_MUTATION"


# ============================================================================================= #
# ADVERSARIAL
# ============================================================================================= #
def test_adversarial_metadata_cannot_hide_a_content_change():
    """Stripping/rewriting metadata cannot mask a semantic mutation (audit hash catches it)."""
    base = _genome()
    attacker = base.model_copy(deep=True)
    attacker.objective = "silently changed"
    attacker.created_at = base.created_at                    # hide the change in the timestamp
    attacker.provenance = list(base.provenance)              # and keep the trail identical
    assert attacker.hash() != base.hash()                    # content change still visible
    assert attacker.audit_hash() != base.audit_hash()


def test_adversarial_field_swap_does_not_collide():
    first = _genome()
    swapped = first.model_copy(deep=True)
    swapped.objective, swapped.task_id = first.task_id, first.objective
    assert swapped.hash() != first.hash()


def test_adversarial_whitespace_is_semantic():
    first = _genome()
    spaced = first.model_copy(deep=True)
    spaced.objective = first.objective + " "
    assert spaced.hash() != first.hash()


def test_f11_gate_deterministic_repair_summary():
    """The gate's own evidence, computed deterministically (no timing dependence)."""
    reference = _genome()
    variants = []
    for stamp in ("2020-01-01T00:00:00+00:00", "2026-09-12T00:00:00+00:00",
                  "2035-06-30T12:00:00+00:00"):
        variant = _genome()
        variant.created_at = stamp
        variants.append(variant)
    assert len({v.hash() for v in variants}) == 1            # same semantic identity
    assert len({v.hash_v1() for v in variants}) == 3         # the V1 defect, pinned
    assert all(v.hash() == reference.hash() for v in variants)
