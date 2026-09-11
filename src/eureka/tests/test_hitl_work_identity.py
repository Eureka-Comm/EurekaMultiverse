"""EUREKA 5.1 — Work identity + submit idempotency contract (HITL).

Production evidence that motivated this file:

    GET  /api/work/WORK-B39C51D1/state      -> status = WAITING_FOR_HUMAN_INPUT
    POST /api/work/WORK-8DD6B1D1/human_input   (another work!)      <- anomaly A
    POST /api/work/WORK-8DD6B1D1/human_input   (again, other request_id) <- anomaly B

Repaired contract under test:

1. A human answer names the `HumanInteractionRequest` it answers, and that request belongs to the
   work in the URL — validated by Python BEFORE any state mutation (fail closed).
2. A `HumanInteractionRequest` is CANONICALLY bound to its Work (`work_id` stamped by the model).
3. Repeating the SAME submission for the SAME request is idempotent: same verdict, no duplicate
   HumanContribution / Evidence / StructuredFinding.
4. Answering an already-answered or superseded request fails closed.
"""
import tempfile
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.eureka.universe.server as server
from src.eureka.universe.canonical_state import (CanonicalWorkState, ExecutionStep, HumanInteractionRequest,
                                                 StructuredFinding)
from src.eureka.universe.cognitive_engine import TestDoubleCognitiveEngine
from src.eureka.universe.human_input_sufficiency import SUFFICIENT
from src.eureka.universe.problem_model import CognitiveTask, ProblemModel, StructuredProblem, TaskNetwork
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_runtime import WorkRuntime
from src.eureka.universe.work_store import WorkStore

REQUIRED_INFORMATION = [
    "qué es EUREKA",
    "sus características y funcionalidades principales",
    "sus capacidades actuales y limitaciones conocidas",
    "su modelo de negocio o monetización existente",
    "métricas o benchmarks de rendimiento relevantes",
    "objetivos de mejora o expansión previstos",
]
HITL_QUESTION = ("Para determinar cómo ganar dinero con EUREKA, necesito que me proporciones "
                 "información específica sobre: 1) qué es EUREKA, 2) sus características y "
                 "funcionalidades principales, 3) sus capacidades actuales y limitaciones conocidas, "
                 "4) su modelo de negocio o monetización existente, 5) métricas o benchmarks de "
                 "rendimiento relevantes, 6) objetivos de mejora o expansión previstos.")
INTENT = "como puedo ganar dinero con eureka"
SUFFICIENT_RESPONSE = (
    "qué es EUREKA: EUREKA es una plataforma de ejecución cognitiva gobernada cuyo núcleo orquesta 8 "
    "Enterprise Modules. Características y funcionalidades principales: ejecución gobernada por Python "
    "y trazabilidad completa, esas son sus funcionalidades principales. Capacidades actuales y "
    "limitaciones conocidas: analiza y predice, y sus limitaciones son exigir datos numéricos. "
    "Modelo de negocio o monetización existente: licencia SaaS por uso del pipeline, con integración "
    "como vía de monetización. Métricas o benchmarks de rendimiento relevantes: latencia por EM y "
    "benchmarks de precisión. Objetivos de mejora o expansión previstos: los objetivos de mejora son "
    "integrar bases de conocimiento y la expansión prevista cubre nuevos dominios.")


def _seed_work(store, work_id, *, with_request=True):
    canonical = CanonicalWorkState(work=EurekaWork(work_id=work_id, title="t", user_intent=INTENT,
                                                   task_category="KNOWLEDGE_ANSWER",
                                                   problem_statement=INTENT))
    canonical.problem = ProblemModel(intent=INTENT, objective="Determinar cómo ganar dinero",
                                     operation_mode="KNOWLEDGE_ANSWER")
    canonical.problem.structured_problem = StructuredProblem(task_network=TaskNetwork(tasks=[
        CognitiveTask(task_id="publish", description="p", owner="EM Publisher", expected_outputs=["a"])]))
    canonical.execution_plan.steps.append(ExecutionStep(
        step_id="publish", capability_id="generate_summary", target="EM Publisher",
        canonical_em="EM Publisher", status="WAITING_FOR_HUMAN_INPUT", produces_result=True))
    if with_request:
        canonical.human_requests.append(HumanInteractionRequest(
            type="INFORMATION", question=HITL_QUESTION, reason="faltan datos",
            required_information=list(REQUIRED_INFORMATION), blocking=True, status="PENDING"))
    canonical.status = "WAITING_FOR_HUMAN_INPUT"
    store[work_id] = canonical
    return canonical


@pytest.fixture
def two_works(monkeypatch, tmp_path):
    """Work A (with a pending HITL request) and an unrelated Work B."""
    store = WorkStore(str(tmp_path / "works"))
    runtime = WorkRuntime(cognitive_engine=TestDoubleCognitiveEngine())
    runtime.publisher.publication_dir = str(tmp_path / "publications")
    a = _seed_work(store, "WORK-A")
    b = _seed_work(store, "WORK-B", with_request=False)
    monkeypatch.setattr(server, "works_db", store)
    monkeypatch.setattr(server, "evidence_store", {})
    monkeypatch.setattr(server, "runtime", runtime)
    return SimpleNamespace(client=TestClient(server.app), store=store, request_a=a.human_requests[0].request_id,
                           work_a="WORK-A", work_b="WORK-B")


# ============================================================================================= #
# TEST 7 — a HumanRequest of Work A can NEVER be answered through Work B (fail closed)
# ============================================================================================= #
def test_cross_work_submission_fails_closed_and_touches_nothing(two_works):
    r = two_works.client.post(f"/api/work/{two_works.work_b}/human_input",
                              json={"type": "INFORMATION", "request_id": two_works.request_a,
                                    "value": SUFFICIENT_RESPONSE})
    assert r.status_code == 409
    assert r.json()["detail"]["reason_code"] == "REQUEST_NOT_IN_WORK"
    b = two_works.store["WORK-B"]
    assert b.human_contributions == [] and b.evidence == [] and b.knowledge.findings == []
    assert b.evidence_ids == [] and b.human_requests == []
    assert b.status == "WAITING_FOR_HUMAN_INPUT"
    a = two_works.store["WORK-A"]
    assert a.human_requests[0].status == "PENDING" and a.human_contributions == []
    assert a.knowledge.findings == []


# ============================================================================================= #
# A human answer must NAME the request it answers (no implicit "first request" binding)
# ============================================================================================= #
def test_submission_without_request_id_fails_closed(two_works):
    r = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                              json={"type": "INFORMATION", "value": SUFFICIENT_RESPONSE})
    assert r.status_code == 409
    assert r.json()["detail"]["reason_code"] == "REQUEST_ID_REQUIRED"
    assert two_works.store["WORK-A"].human_contributions == []


def test_unknown_request_id_fails_closed(two_works):
    r = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                              json={"type": "INFORMATION", "request_id": "REQ-DOES-NOT-EXIST",
                                    "value": SUFFICIENT_RESPONSE})
    assert r.status_code == 409
    assert r.json()["detail"]["reason_code"] == "REQUEST_NOT_IN_WORK"


# ============================================================================================= #
# TEST 1 — the answer lands on the work that owns the request
# ============================================================================================= #
def test_answer_lands_on_the_owning_work(two_works):
    r = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                              json={"type": "INFORMATION", "request_id": two_works.request_a,
                                    "value": SUFFICIENT_RESPONSE})
    assert r.status_code == 200
    a = two_works.store["WORK-A"]
    assert a.human_requests[0].work_id == "WORK-A"          # canonical association stamped
    assert a.human_requests[0].status == "ANSWERED"
    assert a.human_requests[0].sufficiency_status == SUFFICIENT
    assert two_works.store["WORK-B"].human_contributions == []


# ============================================================================================= #
# TEST 8 / TEST 3 — idempotency: repeated identical submission never duplicates anything
# ============================================================================================= #
def test_identical_resubmission_is_idempotent(two_works):
    body = {"type": "INFORMATION", "request_id": two_works.request_a, "value": SUFFICIENT_RESPONSE}
    first = two_works.client.post(f"/api/work/{two_works.work_a}/human_input", json=body)
    assert first.status_code == 200
    a = two_works.store["WORK-A"]
    ev_id = first.json()["response_evidence_id"]
    counts = (len(a.human_contributions), len([e for e in a.evidence if e.source == "HUMAN"]),
              len([f for f in a.knowledge.findings if f.status == "VALIDATED"]))
    assert counts == (1, 1, 1)

    second = two_works.client.post(f"/api/work/{two_works.work_a}/human_input", json=body)  # the "double submit"
    assert second.status_code == 200
    assert second.json()["status"] == "IDEMPOTENT_REPLAY"
    assert second.json()["contribution_id"] is None
    assert second.json()["human_response_sufficiency"] == SUFFICIENT
    assert second.json()["response_evidence_id"] == ev_id
    a = two_works.store["WORK-A"]
    assert (len(a.human_contributions), len([e for e in a.evidence if e.source == "HUMAN"]),
            len([f for f in a.knowledge.findings if f.status == "VALIDATED"])) == counts
    assert len([e for e in a.evidence if e.evidence_id == ev_id]) == 1


def test_different_content_on_answered_request_fails_closed(two_works):
    body = {"type": "INFORMATION", "request_id": two_works.request_a, "value": SUFFICIENT_RESPONSE}
    assert two_works.client.post(f"/api/work/{two_works.work_a}/human_input", json=body).status_code == 200
    other = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                                  json={**body, "value": SUFFICIENT_RESPONSE + " (texto distinto)"})
    assert other.status_code == 409
    assert other.json()["detail"]["reason_code"] == "REQUEST_ALREADY_ANSWERED"
    assert len(two_works.store["WORK-A"].human_contributions) == 1


def test_answering_a_superseded_request_fails_closed(two_works):
    # 1st: the production echo -> INSUFFICIENT -> the backend opens a governed follow-up
    echo = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                                 json={"type": "INFORMATION", "request_id": two_works.request_a,
                                       "value": INTENT})
    assert echo.status_code == 200 and echo.json()["human_response_sufficiency"] == "INSUFFICIENT"
    a = two_works.store["WORK-A"]
    follow_up = [h for h in a.human_requests if h.status == "PENDING"]
    assert len(follow_up) == 1 and follow_up[0].request_id != two_works.request_a
    # the ORIGINAL request can no longer be answered: the open one is the follow-up
    late = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                                 json={"type": "INFORMATION", "request_id": two_works.request_a,
                                       "value": SUFFICIENT_RESPONSE})
    assert late.status_code == 409
    assert late.json()["detail"]["reason_code"] == "REQUEST_SUPERSEDED"
    # ...and the follow-up IS answerable, landing on the same work
    ok = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                               json={"type": "INFORMATION", "request_id": follow_up[0].request_id,
                                     "value": SUFFICIENT_RESPONSE})
    assert ok.status_code == 200 and ok.json()["human_response_sufficiency"] == SUFFICIENT
    a = two_works.store["WORK-A"]
    assert len([e for e in a.evidence if e.source == "HUMAN"]) == 2      # one per submission attempt
    assert len([f for f in a.knowledge.findings if f.status == "VALIDATED"]) == 1   # only the sufficient one
    assert all(f.evidence_refs and f.evidence_refs[0] in a.evidence_ids
               for f in a.knowledge.findings if f.status == "VALIDATED")


# ============================================================================================= #
# TEST 9 — the full chain, without duplicates
# ============================================================================================= #
def test_successful_response_chain_has_no_duplicates(two_works):
    r = two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                              json={"type": "INFORMATION", "request_id": two_works.request_a,
                                    "value": SUFFICIENT_RESPONSE})
    assert r.status_code == 200
    # replay the SAME submission twice more (the production double-submit scenario)
    for _ in range(2):
        assert two_works.client.post(f"/api/work/{two_works.work_a}/human_input",
                                     json={"type": "INFORMATION", "request_id": two_works.request_a,
                                           "value": SUFFICIENT_RESPONSE}).status_code == 200
    a = two_works.store["WORK-A"]
    assert len(a.human_contributions) == 1
    human_ev = [e for e in a.evidence if e.source == "HUMAN"]
    assert len(human_ev) == 1 and human_ev[0].extraction_status == "EXTRACTED"
    validated = [f for f in a.knowledge.findings if f.status == "VALIDATED"]
    assert len(validated) == 1
    assert validated[0].evidence_refs == [human_ev[0].evidence_id]
    assert validated[0].evidence_refs[0] in a.evidence_ids and validated[0].evidence_refs[0] in a.extracted_evidence
    assert validated[0].provenance
    assert a.frozen_result is not None
    assert len([k for k in a.frozen_result.validated_knowledge
                if k.get("finding_id") == validated[0].finding_id]) == 1
    assert a.publication_state is not None and a.publication_state.status == "PUBLISHED"


# ============================================================================================= #
# Canonical association survives persistence (single authority: the canonical model)
# ============================================================================================= #
def test_work_binding_is_canonical_and_survives_persistence(tmp_path):
    store = WorkStore(str(tmp_path / "works"))
    canonical = _seed_work(store, "WORK-PERSIST")
    req_id = canonical.human_requests[0].request_id
    # reloaded from disk -> the association is still there (stamped by the model, not by a UI surface)
    reloaded = WorkStore(str(tmp_path / "works"))["WORK-PERSIST"]
    assert reloaded.human_requests[0].work_id == "WORK-PERSIST"
    assert reloaded.human_requests[0].request_id == req_id


def test_request_created_at_construction_is_bound_to_its_work():
    """A request present when the canonical state is built is bound by the MODEL (one authority)."""
    req = HumanInteractionRequest(type="INFORMATION", question=HITL_QUESTION, reason="r",
                                  required_information=["que es EUREKA"])
    canonical = CanonicalWorkState(work=EurekaWork(work_id="WORK-CONSTRUCT", title="t", user_intent=INTENT,
                                                   task_category="c", problem_statement="p"),
                                   human_requests=[req])
    assert canonical.human_requests[0].work_id == "WORK-CONSTRUCT"


def test_legacy_persisted_work_without_work_id_self_heals():
    """Works persisted before the field existed get the association stamped when the state is LOADED."""
    req = HumanInteractionRequest(type="INFORMATION", question=HITL_QUESTION, reason="r",
                                  required_information=["que es EUREKA"])
    canonical = CanonicalWorkState(work=EurekaWork(work_id="WORK-LEGACY", title="t", user_intent=INTENT,
                                                   task_category="c", problem_statement="p"),
                                   human_requests=[req])
    payload = canonical.model_dump(mode="json")
    payload["human_requests"][0]["work_id"] = ""          # simulate the pre-field persisted payload
    revived = CanonicalWorkState.model_validate(payload)
    assert revived.human_requests[0].work_id == "WORK-LEGACY"


def test_error_code_is_actionable_for_the_ui(two_works):
    """The 409 detail carries a machine-readable reason_code + a human message (UI can explain it)."""
    r = two_works.client.post(f"/api/work/{two_works.work_b}/human_input",
                              json={"type": "INFORMATION", "request_id": two_works.request_a,
                                    "value": SUFFICIENT_RESPONSE})
    detail = r.json()["detail"]
    assert set(detail) >= {"reason_code", "message"}
    assert two_works.work_b in detail["message"] or two_works.request_a in detail["message"]
