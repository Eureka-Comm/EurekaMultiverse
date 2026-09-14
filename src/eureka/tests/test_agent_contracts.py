"""EUREKA 5.1 — LOOP 1 tests: AGENT CONTRACT FOUNDATION (single contractual authority).

Mandated coverage (Harness LOOP 1 + explicit human authorization of 2026-09-12):
schema · serialization · invalid values · missing fields · dependency validation ·
evidence requirements · freeze requirements · backwards compatibility ·
identity collision · cognitive ownership mutation · authority escalation · model substitution ·
policy mutation · frozen genome mutation.

Contract violations raise `AgentContractError` (fail closed); schema violations raise pydantic
`ValidationError`. Both are asserted explicitly — never "test passes because nothing raised".
"""
import pytest
from pydantic import ValidationError

from src.eureka.universe.agent_definition import AgentDefinition
from src.eureka.universe.agent_genome import (FAMILY_OWNER, HARD_BUDGET, MAX_DEPTH, AgentContractError,
                                             AgentDependency, AgentDependencyKind,
                                             AgentExecutionRecord, AgentGenome, AgentIdentity,
                                             AgentReference, AgentStatus, CognitiveFamily,
                                             ModelRequirement, NetworkRole, ReasoningClass,
                                             ResourceBudget, ReturnPackage, ReturnStatus,
                                             SubproblemDiscovery, TaskEnvelope,
                                             agent_definition_from_genome,
                                             agent_status_from_deployment_state,
                                             detect_cycle, detect_identity_collision,
                                             genome_from_agent_definition, genome_from_provider_stub,
                                             transition)
from src.eureka.universe.cognitive_provider import AgentDefinition as ProviderStubDefinition

WORK = "WORK-EMERGENT-1"
PROBLEM = "PROB-EMERGENT-1"
TASK = "TASK-LEADTIME-EUROPE"


def _identity(family=CognitiveFamily.PREDICTOR, role=NetworkRole.SEGREGATOR,
              predicate="LeadTime", context="Europe") -> AgentIdentity:
    return AgentIdentity(cognitive_family=family, network_role=role, predicate=predicate, context=context)


def _genome(**overrides) -> AgentGenome:
    data = dict(identity=_identity(), work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                objective="Predict lead time for European suppliers",
                questions=["Does lead time depend on supplier?"],
                predicates=["LeadTime"], constraints=["No fabrication"],
                authoritative_inputs=["PROBLEM"], knowledge_sources=["WKD-0"],
                tools=["acfl.evaluate"], model_requirements=ModelRequirement(
                    reasoning=ReasoningClass.DEEP, min_context_tokens=16000),
                evidence_requirements=["supplier_lead_time_series"],
                resource_budget=ResourceBudget(max_runtime_seconds=120, max_model_calls=2),
                validation_rules=["EVIDENCE_REQUIRED"], freeze_requirement=True,
                provenance=["created by Agent Necessity (test)"])
    data.update(overrides)
    return AgentGenome(**data)


# ============================================================================================= #
# schema · serialization · mandated fields
# ============================================================================================= #
def test_genome_schema_and_serialization_roundtrip():
    g = _genome()
    dumped = g.model_dump(mode="json")
    revived = AgentGenome.model_validate(dumped)
    assert revived.hash() == g.hash()                      # stable content identity
    assert revived.agent_id == "PRED-SEG-LeadTime-Europe"
    assert revived.cognitive_owner == "EM Predictor"       # family -> constitutional owner
    assert revived.authority_scope == "PROPOSER"           # agents never gain authority


def test_genome_declares_every_mandated_field():
    fields = set(AgentGenome.model_fields)
    for required in ("identity", "work_id", "problem_id", "task_id", "objective", "questions",
                     "predicates", "constraints", "authoritative_inputs", "knowledge_sources",
                     "tools", "model_requirements", "dependencies", "upstream_agents",
                     "downstream_agents", "output_schema", "evidence_requirements", "uncertainty",
                     "execution_level", "resource_budget", "validation_rules", "freeze_requirement",
                     "human_escalation_rules", "return_to", "version"):
        assert required in fields, f"AgentGenome is missing the mandated field '{required}'"
    # cognitive_family / network_role live in the identity value object (single place)
    assert set(AgentIdentity.model_fields) == {"cognitive_family", "network_role", "predicate", "context"}
    # the genome must NOT be an LLM/model contract: no vendor pin, no prompt
    assert "model" not in fields and "system_prompt" not in fields


def test_identity_string_is_deterministic_and_parsable():
    ident = _identity()
    assert ident.agent_id == "PRED-SEG-LeadTime-Europe"
    parsed = AgentIdentity.parse(ident.agent_id)
    assert parsed == ident
    with pytest.raises(AgentContractError) as err:
        AgentIdentity.parse("nonsense")
    assert err.value.reason_code == "MALFORMED_AGENT_ID"
    with pytest.raises(AgentContractError) as err2:
        AgentIdentity.parse("XXX-SEG-LeadTime-Europe")
    assert err2.value.reason_code == "UNKNOWN_FAMILY_PREFIX"


def test_family_to_owner_mapping_is_one_to_one():
    owners = list(FAMILY_OWNER.values())
    assert len(owners) == len(set(owners)) == len(CognitiveFamily)
    assert FAMILY_OWNER[CognitiveFamily.PREDICTOR] == "EM Predictor"


# ============================================================================================= #
# invalid values · missing fields
# ============================================================================================= #
def test_invalid_values_are_rejected():
    with pytest.raises(ValidationError):
        _identity(family="NOT_A_FAMILY")                                  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        _identity(predicate="Lead-Time")                                  # dashes break parsing
    with pytest.raises(ValidationError):
        ResourceBudget(max_runtime_seconds=-1)
    with pytest.raises(ValidationError):
        ResourceBudget(max_model_calls=HARD_BUDGET["max_model_calls"] + 1)  # hard cap
    with pytest.raises(ValidationError):
        _genome(uncertainty="MAYBE")
    with pytest.raises(ValidationError):
        _genome(execution_level="ROOT")
    with pytest.raises(ValidationError):
        _genome(unknown_field="x")                                        # extra="forbid"


def test_missing_required_fields_are_rejected():
    for missing in ("work_id", "problem_id", "task_id", "objective", "identity"):
        data = dict(identity=_identity(), work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                    objective="o")
        data.pop(missing)
        with pytest.raises(ValidationError):
            AgentGenome(**data)
    with pytest.raises(ValidationError):
        _genome(return_to="EM Actioner")        # not Core and not the family owner


# ============================================================================================= #
# identity collision · cognitive ownership · authority · model · policy
# ============================================================================================= #
def test_identity_collision_is_detected():
    a = _genome()
    b = _genome(objective="DIFFERENT objective but same identity")
    assert detect_identity_collision([a, b]) == ["PRED-SEG-LeadTime-Europe"]
    assert detect_identity_collision([a, a.model_copy(deep=True)]) == []      # same content: no collision
    other = _genome(identity=_identity(predicate="SupplierReliability"))
    assert detect_identity_collision([a, other]) == []


def test_cognitive_ownership_cannot_be_mutated_by_payload():
    g = _genome()
    with pytest.raises(AgentContractError) as err:
        g.assert_no_authority_escalation({"cognitive_family": "PRESCRIPTOR"})
    assert err.value.reason_code == "AUTHORITY_ESCALATION_ATTEMPT"
    with pytest.raises(AgentContractError) as err2:
        g.assert_no_authority_escalation({"owner": "EM Core"})
    assert err2.value.reason_code == "FORBIDDEN_FIELD"


def test_authority_escalation_is_rejected():
    g = _genome()
    for payload in ({"authority_scope": "AUTHORITY"}, {"canonical_status": "CANONICAL"},
                    {"execution_mode": "REAL_EXECUTION"}, {"bypass_governance": True},
                    {"promote": True}, {"release": True}, {"approved": True}, {"is_admin": True}):
        with pytest.raises(AgentContractError):
            g.assert_no_authority_escalation(payload)
    # a genome that simply does NOT change authority is accepted
    g.assert_no_authority_escalation({"authority_scope": "PROPOSER", "objective": "same"})


def test_model_substitution_requires_explicit_authorization():
    g = _genome()
    g.assert_model_allowed(["deepseek-chat", "llama3"], "deepseek-chat")      # authorized: ok
    with pytest.raises(AgentContractError) as err:
        g.assert_model_allowed(["deepseek-chat"], "some-other-model")
    assert err.value.reason_code == "UNAUTHORIZED_MODEL"
    # the genome declares requirements; it cannot pin a vendor model as authority
    assert "model" not in AgentGenome.model_fields
    assert g.model_requirements.allow_fallback is False        # fallback only if authorized


def test_policy_mutation_and_frozen_genome_mutation():
    g = _genome().freeze()
    same = AgentGenome.model_validate(g.model_dump(mode="json"))
    g.assert_compatible_with(same)                              # unchanged content: accepted
    mutated = AgentGenome.model_validate({**g.model_dump(mode="json"),
                                          "validation_rules": ["NO_EVIDENCE_NEEDED"]})
    with pytest.raises(AgentContractError) as err:
        g.assert_compatible_with(mutated)
    assert err.value.reason_code == "FROZEN_GENOME_MUTATION"
    with pytest.raises(ValidationError):
        AgentGenome(**{**g.model_dump(mode="json"), "tools": ["*"], "unknown": 1})


# ============================================================================================= #
# dependencies · cycles
# ============================================================================================= #
def test_dependency_validation_fails_closed():
    with pytest.raises(AgentContractError) as err:
        _genome(dependencies=[AgentDependency(agent_id="PRED-SEG-LeadTime-Europe")])
    assert err.value.reason_code == "SELF_DEPENDENCY"
    with pytest.raises(AgentContractError) as err2:
        _genome(dependencies=[AgentDependency(agent_id="PRED-SEG-A-Europe"),
                              AgentDependency(agent_id="PRED-SEG-A-Europe",
                                              kind=AgentDependencyKind.EVIDENCE)])
    assert err2.value.reason_code == "DUPLICATE_DEPENDENCY"
    with pytest.raises(AgentContractError) as err3:
        _genome(upstream_agents=[AgentReference(agent_id="DESC-SEG-X-Europe",
                                               network_role=NetworkRole.SEGREGATOR,
                                               work_id="WORK-OTHER")])
    assert err3.value.reason_code == "CROSS_WORK_REFERENCE"
    ok = _genome(dependencies=[AgentDependency(agent_id="DESC-SEG-Suppliers-Europe")])
    assert ok.dependencies[0].required is True


def test_cycle_detection():
    assert detect_cycle({"a": ["b"], "b": ["a"]}) == ["a", "b", "a"]
    assert detect_cycle({"a": ["b"], "b": ["c"], "c": []}) is None
    assert detect_cycle({"a": ["a"]}) == ["a", "a"]


# ============================================================================================= #
# evidence · provenance · freeze requirements on the RETURN contract
# ============================================================================================= #
def _return(**overrides) -> ReturnPackage:
    data = dict(return_id="RET-1", work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                agent_id="PRED-SEG-LeadTime-Europe", execution_id="EXEC-1",
                result={"lead_time_days": 12}, predicates=["LeadTime"],
                evidence_refs=["EVI-1"], provenance=["agent:PRED-SEG-LeadTime-Europe"])
    data.update(overrides)
    return ReturnPackage(**data)


def test_evidence_and_provenance_requirements_are_enforced():
    g = _genome()                                   # requires evidence
    _return().validate_against(g)                   # evidence + provenance present: accepted
    with pytest.raises(AgentContractError) as err:
        _return(evidence_refs=[]).validate_against(g)
    assert err.value.reason_code == "EVIDENCE_REQUIRED_MISSING"
    with pytest.raises(AgentContractError) as err2:
        _return(provenance=[]).validate_against(g)
    assert err2.value.reason_code == "PROVENANCE_REQUIRED"
    no_evidence_genome = _genome(evidence_requirements=[])
    _return(evidence_refs=[]).validate_against(no_evidence_genome)     # nothing required: accepted


def test_return_package_is_always_a_candidate():
    with pytest.raises(AgentContractError) as err:
        _return(validation_status="VALIDATED")
    assert err.value.reason_code == "AGENT_CANNOT_SELF_VALIDATE"
    r = _return(status=ReturnStatus.SUBPROBLEM_DISCOVERED,
                subproblem_discoveries=[SubproblemDiscovery(
                    statement="supplier reliability may explain lead time",
                    proposed_predicate="SupplierReliability",
                    proposed_family=CognitiveFamily.PREDICTOR,
                    reason="observed dispersion across suppliers")],
                recommended_agents=["PRED-SEG-SupplierReliability-Europe"])
    assert r.recommended_agents and r.subproblem_discoveries
    r.validate_against(_genome(evidence_requirements=[]))
    with pytest.raises(AgentContractError) as err2:
        _return(work_id="WORK-OTHER").validate_against(_genome())
    assert err2.value.reason_code == "CROSS_WORK_CONTAMINATION"


def test_freeze_requirement_is_declared_and_carried():
    assert _genome().freeze_requirement is True
    assert _genome(freeze_requirement=False).freeze_requirement is False
    assert _genome().model_dump(mode="json")["freeze_requirement"] is True


# ============================================================================================= #
# lifecycle
# ============================================================================================= #
def test_lifecycle_allowed_and_illegal_transitions():
    assert transition(AgentStatus.PROPOSED, AgentStatus.CREATED) is AgentStatus.CREATED
    chain = [AgentStatus.CREATED, AgentStatus.READY, AgentStatus.RUNNING, AgentStatus.RETURNED,
             AgentStatus.VALIDATION_REQUIRED, AgentStatus.VALIDATED, AgentStatus.FROZEN,
             AgentStatus.COMPLETED]
    current = AgentStatus.PROPOSED
    for nxt in chain:
        current = transition(current, nxt)
    assert current is AgentStatus.COMPLETED
    with pytest.raises(AgentContractError) as err:
        transition(AgentStatus.PROPOSED, AgentStatus.VALIDATED)
    assert err.value.reason_code == "ILLEGAL_LIFECYCLE_TRANSITION"
    with pytest.raises(AgentContractError):
        transition(AgentStatus.RETIRED, AgentStatus.READY)      # RETIRED is terminal


def test_legacy_deployment_lifecycle_maps_onto_the_canonical_one():
    for legacy, expected in (("PROPOSED", AgentStatus.PROPOSED), ("DESIGNED", AgentStatus.CREATED),
                             ("VALIDATED", AgentStatus.VALIDATED), ("FROZEN", AgentStatus.FROZEN),
                             ("REGISTERED", AgentStatus.READY), ("ACTIVE", AgentStatus.RUNNING)):
        assert agent_status_from_deployment_state(legacy) is expected
    with pytest.raises(AgentContractError) as err:
        agent_status_from_deployment_state("SOMETHING_ELSE")
    assert err.value.reason_code == "UNKNOWN_DEPLOYMENT_STATE"


# ============================================================================================= #
# budget · envelope · execution record
# ============================================================================================= #
def test_budget_cannot_escalate():
    parent = ResourceBudget(max_runtime_seconds=100, max_model_calls=4, max_depth=1)
    # a child gets a SMALLER-or-equal budget: max_depth is the REMAINING depth allowance
    child = parent.child(max_runtime_seconds=60, max_model_calls=2, max_depth=0)
    assert (child.max_runtime_seconds, child.max_model_calls, child.max_depth) == (60, 2, 0)
    with pytest.raises(AgentContractError) as err:
        parent.child(max_runtime_seconds=200)
    assert err.value.reason_code == "BUDGET_ESCALATION"
    with pytest.raises(AgentContractError) as err_depth:
        parent.child(max_depth=2)                     # deeper than the parent's remaining allowance
    assert err_depth.value.reason_code == "BUDGET_ESCALATION"
    with pytest.raises(AgentContractError) as err2:
        parent.child(nonexistent_field=1)
    assert err2.value.reason_code == "UNKNOWN_BUDGET_FIELD"
    assert parent.exhausted(elapsed_seconds=101) == "BUDGET_RUNTIME_EXHAUSTED"
    assert parent.exhausted(model_calls=5) == "BUDGET_MODEL_CALLS_EXHAUSTED"
    assert parent.exhausted(elapsed_seconds=1, model_calls=1) is None
    assert MAX_DEPTH == HARD_BUDGET["max_depth"]


def test_task_envelope_authorization_is_explicit_and_work_bound():
    g = _genome()
    env = TaskEnvelope(envelope_id="ENV-1", work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                       agent_id=g.agent_id, genome_hash=g.hash(),
                       authorized_inputs=["PROBLEM"], authorized_evidence_ids=["EVI-1"],
                       allowed_tools=["acfl.evaluate"], budget=ResourceBudget(max_model_calls=2))
    env.assert_matches(g)
    assert env.authorizes_evidence("EVI-1") and not env.authorizes_evidence("EVI-2")
    assert env.authorizes_tool("acfl.evaluate") and not env.authorizes_tool("fs.write")
    with pytest.raises(ValidationError):
        TaskEnvelope(envelope_id="ENV-2", work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                     agent_id=g.agent_id, genome_hash=g.hash(), authorized_evidence_ids=["*"])
    with pytest.raises(AgentContractError) as err:
        TaskEnvelope(envelope_id="ENV-3", work_id="WORK-OTHER", problem_id=PROBLEM, task_id=TASK,
                     agent_id=g.agent_id, genome_hash=g.hash()).assert_matches(g)
    assert err.value.reason_code == "CROSS_WORK_CONTAMINATION"
    with pytest.raises(AgentContractError) as err2:
        TaskEnvelope(envelope_id="ENV-4", work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                     agent_id=g.agent_id, genome_hash="stalehash123").assert_matches(g)
    assert err2.value.reason_code == "ENVELOPE_GENOME_MISMATCH"


def test_execution_record_advances_only_legally():
    rec = AgentExecutionRecord(execution_id="EXEC-1", work_id=WORK, problem_id=PROBLEM, task_id=TASK,
                               agent_id="PRED-SEG-LeadTime-Europe", provider="DeepSeekAdapter",
                               model="deepseek-chat")
    assert rec.status is AgentStatus.CREATED                   # a record is born CREATED
    rec.advance(AgentStatus.READY)
    rec.advance(AgentStatus.RUNNING)
    rec.advance(AgentStatus.RETURNED)
    rec.return_package = _return()
    assert rec.return_package.validation_status == "CANDIDATE"
    rec.advance(AgentStatus.VALIDATION_REQUIRED)
    rec.advance(AgentStatus.VALIDATED)
    with pytest.raises(AgentContractError):
        rec.advance(AgentStatus.RUNNING)                       # VALIDATED -> RUNNING is illegal
    with pytest.raises(AgentContractError):
        rec.advance(AgentStatus.CREATED)                        # no going back either


# ============================================================================================= #
# backwards compatibility with the two existing AgentDefinition classes
# ============================================================================================= #
def test_backwards_compatibility_with_em_installer_agent_definition():
    ad = AgentDefinition(agent_id="legacy-agent", version="2.1",
                         system_prompt="You are a legacy agent.", input_schema={"type": "object"},
                         output_schema={"type": "object", "properties": {"x": {"type": "number"}}},
                         capabilities=["predict"], forbidden_operations=["execute"],
                         knowledge_sources=["KNOW-1"], provider_policy={"timeout": 240})
    g = genome_from_agent_definition(ad, identity=_identity(), work_id=WORK, problem_id=PROBLEM,
                                     task_id=TASK, objective="Adapted objective")
    assert g.version == "2.1"
    assert g.tools == ["predict"] and g.forbidden_operations == ["execute"]
    assert g.knowledge_sources == ["KNOW-1"] and g.output_schema["properties"]["x"]["type"] == "number"
    assert g.resource_budget.max_runtime_seconds == 240        # provider_policy.timeout -> budget
    assert any("system_prompt is non-authoritative" in p for p in g.provenance)
    # the legacy contract is still constructible from the genome (compatibility projection)
    projected = agent_definition_from_genome(g)
    rebuilt = AgentDefinition(**projected)
    assert rebuilt.agent_id == g.agent_id and rebuilt.capabilities == ["predict"]


def test_backwards_compatibility_with_provider_stub_definition():
    stub = ProviderStubDefinition(description="legacy provider stub", system_prompt="p",
                                  tools=["t1", "t2"], model="deepseek-chat")
    g = genome_from_provider_stub(stub, identity=_identity(), work_id=WORK, problem_id=PROBLEM,
                                  task_id=TASK, objective="o")
    assert g.tools == ["t1", "t2"]
    assert any("requested_model=deepseek-chat" in p for p in g.provenance)
    assert "model" not in AgentGenome.model_fields           # the stub's model is NOT genome authority


# ============================================================================================= #
# invariant: this module creates no second authority / store
# ============================================================================================= #
def test_contract_module_defines_no_store_registry_or_factory_authority():
    import src.eureka.universe.agent_genome as mod
    public_classes = [n for n, o in vars(mod).items()
                      if isinstance(o, type) and o.__module__ == mod.__name__]
    forbidden_suffixes = ("Store", "Registry", "Factory", "Runtime", "Repository", "Database")
    offenders = [n for n in public_classes if n.endswith(forbidden_suffixes)]
    assert offenders == [], f"LOOP 1 must not create persistence/authority objects: {offenders}"
    # and the canonical contract is the ONLY genome/definition authority exported here
    assert "AgentGenome" in public_classes and "AgentIdentity" in public_classes
