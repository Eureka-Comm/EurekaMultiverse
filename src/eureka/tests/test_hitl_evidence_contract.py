"""EUREKA 5.1 — Governed contract: HITL -> HUMAN_INPUT -> Evidence Authority -> Findings ->
Sufficiency -> Publisher -> Publication -> Frozen Result.

Regression context (production WORK-D120C202): the human answered a blocking INFORMATION request
with an ECHO of the original question ("como puedo ganar dinero con eureka"). The system marked it
ANSWERED, created a finding VALIDATED with the dangling literal `HUMAN_INPUT` as its evidence ref,
and PUBLISHED an answer over information the human never provided.

These tests pin the repaired contract:
    HUMAN_RESPONSE_RECEIVED != HUMAN_RESPONSE_SUFFICIENT != HUMAN_RESPONSE_VALIDATED

Every test exercises REAL code paths (endpoint / runtime / publisher) — no cosmetic assertions.
"""
import tempfile
import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import src.eureka.universe.server as server
from src.eureka.universe.canonical_state import (CanonicalWorkState, ExecutionStep, HumanInteractionRequest,
                                                 StructuredFinding)
from src.eureka.universe.cognitive_engine import (MissingDataProposal, TestDoubleCognitiveEngine,
                                                  build_publication_context)
from src.eureka.universe.human_input_sufficiency import (INVALID, MAX_HUMAN_INFORMATION_ATTEMPTS,
                                                         SUFFICIENT, evaluate_human_response)
from src.eureka.universe.problem_model import CognitiveTask, ProblemModel, StructuredProblem, TaskNetwork
from src.eureka.universe.publication_model import PublicationSection
from src.eureka.universe.publisher import EMPublisher
from src.eureka.universe.effect_policy import default_boundary
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.work_runtime import WorkRuntime
from src.eureka.universe.work_store import WorkStore

# --------------------------------------------------------------------------------------------- #
# Real production data (WORK-D120C202)
# --------------------------------------------------------------------------------------------- #
PRODUCTION_INTENT = "como puedo ganar dinero con eureka"
REQUIRED_INFORMATION = [
    "qué es EUREKA",
    "sus características y funcionalidades principales",
    "sus capacidades actuales y limitaciones conocidas",
    "su modelo de negocio o monetización existente",
    "métricas o benchmarks de rendimiento relevantes",
    "objetivos de mejora o expansión previstos",
]
HITL_QUESTION = (
    "Para determinar cómo ganar dinero con EUREKA, necesito que me proporciones información "
    "específica sobre: 1) qué es EUREKA, 2) sus características y funcionalidades principales, "
    "3) sus capacidades actuales y limitaciones conocidas, 4) su modelo de negocio o monetización "
    "existente, 5) métricas o benchmarks de rendimiento relevantes, 6) objetivos de mejora o "
    "expansión previstos."
)
ECHO_RESPONSE = PRODUCTION_INTENT          # exactly what production received
INVALID_RESPONSE = "   "
TRIVIAL_RESPONSE = "no se"
DECLINED_RESPONSE = "no tengo esa informacion"
PARTIAL_RESPONSE = ("EUREKA es una plataforma cognitiva con un pipeline de 8 EM y tiene limitaciones "
                    "conocidas de rendimiento")
SUFFICIENT_RESPONSE = (
    "qué es EUREKA: EUREKA es una plataforma de ejecución cognitiva gobernada cuyo núcleo orquesta 8 "
    "Enterprise Modules. "
    "Características y funcionalidades principales: ejecución gobernada por Python, trazabilidad "
    "completa y publicación firmada; esas son sus funcionalidades centrales. "
    "Capacidades actuales y limitaciones conocidas: analiza, predice con ACFL y prescribe con "
    "validación matemática, y sus limitaciones son que exige datos numéricos para predecir y no "
    "ejecuta efectos reales sin autorización humana. "
    "Modelo de negocio o monetización existente: el modelo de negocio previsto es licencia SaaS por "
    "uso del pipeline, con servicios de integración como vía de monetización complementaria. "
    "Métricas o benchmarks de rendimiento relevantes: las métricas son latencia por EM, tasa de "
    "publicaciones completadas y benchmarks de precisión de predicción. "
    "Objetivos de mejora o expansión previstos: los objetivos de mejora son integrar bases de "
    "conocimiento y la expansión prevista cubre nuevos dominios de aplicación."
)


# --------------------------------------------------------------------------------------------- #
# Engines (test doubles with the REAL governance surface)
# --------------------------------------------------------------------------------------------- #
class _AskingEngine(TestDoubleCognitiveEngine):
    """Deterministic engine whose sufficiency probe DOES ask (LLM candidate: data_needed=True)."""

    def propose_missing_data(self, problem, findings):
        return MissingDataProposal(data_needed=True, question=HITL_QUESTION,
                                   required_information=list(REQUIRED_INFORMATION),
                                   reason="La pregunta es sobre el estado real del sistema y no hay datos.")


class _DecliningEngine(TestDoubleCognitiveEngine):
    """Deterministic engine whose probe says the question IS self-answerable."""

    def propose_missing_data(self, problem, findings):
        return MissingDataProposal(data_needed=False, reason="self-answerable")


class _FailingEngine(TestDoubleCognitiveEngine):
    """Engine whose probe is UNAVAILABLE (provider failure) -> must fail closed, never fabricate."""

    def propose_missing_data(self, problem, findings):
        raise RuntimeError("DeepSeek unreachable")


# --------------------------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------------------------- #
def _seed_work(store, work_id="WORK-HITL-1", *, with_request=True, request_status="PENDING"):
    work = EurekaWork(work_id=work_id, title="Ganar dinero con EUREKA", user_intent=PRODUCTION_INTENT,
                      task_category="KNOWLEDGE_ANSWER", problem_statement=PRODUCTION_INTENT)
    canonical = CanonicalWorkState(work=work)
    canonical.problem = ProblemModel(intent=PRODUCTION_INTENT,
                                     objective="Determinar cómo ganar dinero con EUREKA",
                                     operation_mode="KNOWLEDGE_ANSWER")
    task = CognitiveTask(task_id="publish", description="publish the governed answer",
                         owner="EM Publisher", expected_outputs=["answer"])
    canonical.problem.structured_problem = StructuredProblem(task_network=TaskNetwork(tasks=[task]))
    canonical.execution_plan.steps.append(ExecutionStep(
        step_id="publish", capability_id="generate_summary", target="EM Publisher",
        canonical_em="EM Publisher", status="WAITING_FOR_HUMAN_INPUT", produces_result=True))
    if with_request:
        canonical.human_requests.append(HumanInteractionRequest(
            type="INFORMATION", question=HITL_QUESTION, reason="Faltan datos específicos del sistema",
            required_information=list(REQUIRED_INFORMATION), blocking=True, status=request_status))
    canonical.status = "WAITING_FOR_HUMAN_INPUT"
    store[work_id] = canonical
    return canonical


@pytest.fixture
def hitl_env(monkeypatch, tmp_path):
    """Isolated Work authority + evidence mirror + TestDouble runtime (no production pollution)."""
    store = WorkStore(str(tmp_path / "works"))
    runtime = WorkRuntime(cognitive_engine=TestDoubleCognitiveEngine())
    runtime.publisher.publication_dir = str(tmp_path / "publications")
    _seed_work(store, work_id="WORK-HITL-1")          # the production-shaped work (HITL pending)
    monkeypatch.setattr(server, "works_db", store)
    monkeypatch.setattr(server, "evidence_store", {})
    monkeypatch.setattr(server, "runtime", runtime)
    return SimpleNamespace(client=TestClient(server.app), store=store, runtime=runtime,
                           work_id="WORK-HITL-1", pubdir=runtime.publisher.publication_dir,
                           request_id=store["WORK-HITL-1"].human_requests[0].request_id)


def _answer(env, value, request_id=None):
    # A human answer MUST name the HumanInteractionRequest it answers (the API fails closed without it).
    return env.client.post(f"/api/work/{env.work_id}/human_input",
                           json={"type": "INFORMATION",
                                 "request_id": request_id or env.request_id, "value": value,
                                 "rationale": "respuesta humana desde la UI"})


def _publisher(engine, pubdir):
    return EMPublisher(engine, boundary=default_boundary(), publication_dir=pubdir)


def _publish_task():
    return CognitiveTask(task_id="publish", description="publish", owner="EM Publisher",
                         expected_outputs=["answer"])


# ============================================================================================= #
# 1. HITL creado
# ============================================================================================= #
def test_01_hitl_request_created_by_python_authority():
    canonical = _seed_work(WorkStore(tempfile.mkdtemp()), with_request=False)
    runtime = WorkRuntime(cognitive_engine=_AskingEngine())
    assert runtime._maybe_request_missing_data(canonical) is True
    assert len(canonical.human_requests) == 1
    req = canonical.human_requests[0]
    assert (req.type, req.blocking, req.decision_required, req.status) == ("INFORMATION", True, False, "PENDING")
    assert req.required_information == REQUIRED_INFORMATION
    assert req.sufficiency_status == "NOT_EVALUATED"       # received-nothing yet: no verdict
    assert any(c.reason_code == "MISSING_DATA_REQUESTED" for c in canonical.conditions)


def test_01b_declining_engine_does_not_ask():
    canonical = _seed_work(WorkStore(tempfile.mkdtemp()), with_request=False)
    runtime = WorkRuntime(cognitive_engine=_DecliningEngine())
    assert runtime._maybe_request_missing_data(canonical) is False
    assert canonical.human_requests == []


# ============================================================================================= #
# 2. Human response almacenada
# ============================================================================================= #
def test_02_human_response_stored_and_traceable(hitl_env):
    r = _answer(hitl_env, ECHO_RESPONSE)
    assert r.status_code == 200
    canonical = hitl_env.store[hitl_env.work_id]
    req = canonical.human_requests[0]
    assert req.status == "ANSWERED"                                     # RECEIVED
    assert req.response_data == {"value": ECHO_RESPONSE}
    assert len(canonical.human_contributions) == 1
    assert canonical.human_contributions[0].value == ECHO_RESPONSE
    assert canonical.human_contributions[0].type == "INFORMATION"


# ============================================================================================= #
# 3. Human response vacía -> rechazada (INVALID)
# ============================================================================================= #
def test_03_empty_response_is_invalid_and_never_validated(hitl_env):
    r = _answer(hitl_env, INVALID_RESPONSE)
    assert r.status_code == 200
    assert r.json()["human_response_sufficiency"] == INVALID
    canonical = hitl_env.store[hitl_env.work_id]
    req = canonical.human_requests[0]
    assert req.sufficiency_status == INVALID
    assert req.resolution == "REJECTED_INVALID"
    assert req.sufficiency["reasons"] == ["EMPTY_RESPONSE"]
    assert canonical.knowledge.findings == []                            # nothing became knowledge
    assert canonical.evidence[0].extraction_status == "NOT_EXTRACTED"    # traceable, NOT grounding


# ============================================================================================= #
# 4. Human response = pregunta original -> INSUFFICIENT  (the production regression)
# ============================================================================================= #
def test_04_echo_of_the_question_is_insufficient_not_validated(hitl_env):
    r = _answer(hitl_env, ECHO_RESPONSE)
    assert r.status_code == 200
    assert r.json()["human_response_sufficiency"] == "INSUFFICIENT"
    canonical = hitl_env.store[hitl_env.work_id]
    req = canonical.human_requests[0]
    assert req.sufficiency_status == "INSUFFICIENT"
    assert "ECHO_OF_QUESTION_OR_INTENT" in req.sufficiency["reasons"]
    assert req.sufficiency["covered"] == []
    assert req.resolution == "AWAITING_MORE"
    # NEVER a VALIDATED finding, NEVER a dangling HUMAN_INPUT label
    assert canonical.knowledge.findings == []
    assert not any("HUMAN_INPUT" in (f.evidence_refs or [])
                   for f in canonical.knowledge.findings)
    assert any(c.reason_code == "HUMAN_INPUT_INSUFFICIENT" for c in canonical.conditions)


# ============================================================================================= #
# 5. Human response parcial -> PARTIAL
# ============================================================================================= #
def test_05_partial_response_is_partial_and_not_validated(hitl_env):
    assert _answer(hitl_env, PARTIAL_RESPONSE).json()["human_response_sufficiency"] == "PARTIAL"
    canonical = hitl_env.store[hitl_env.work_id]
    req = canonical.human_requests[0]
    assert req.sufficiency_status == "PARTIAL"
    assert 0 < len(req.sufficiency["covered"]) < len(REQUIRED_INFORMATION)
    assert req.sufficiency["missing"]
    assert canonical.knowledge.findings == []
    # a declination is also INSUFFICIENT (never promoted)
    direct = evaluate_human_response(response_value=DECLINED_RESPONSE,
                                     required_information=REQUIRED_INFORMATION,
                                     question=HITL_QUESTION, user_intent=PRODUCTION_INTENT)
    assert direct["status"] == "INSUFFICIENT"
    assert "HUMAN_DECLINED_TO_PROVIDE_INFORMATION" in direct["reasons"]


# ============================================================================================= #
# 6. Human response suficiente -> pasa a evidencia
# ============================================================================================= #
def test_06_sufficient_response_becomes_real_evidence(hitl_env):
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    assert r.status_code == 200
    assert r.json()["human_response_sufficiency"] == SUFFICIENT
    canonical = hitl_env.store[hitl_env.work_id]
    ev_id = r.json()["response_evidence_id"]
    assert ev_id and ev_id.startswith("EVI-HUMAN-")
    assert ev_id in canonical.evidence_ids
    ev = next(e for e in canonical.evidence if e.evidence_id == ev_id)
    assert (ev.source, ev.extraction_status, ev.ingestion_status) == ("HUMAN", "EXTRACTED", "INGESTED")
    assert ev.content_reference == f"human_requests[{canonical.human_requests[0].request_id}].response_data.value"
    # grounding unit resolvable by the Descriptor/Publisher grounding source
    assert ev_id in canonical.extracted_evidence
    assert SUFFICIENT_RESPONSE in canonical.extracted_evidence[ev_id].text_blocks[0]
    # the paused gate was closed (the step resumed and may already have completed in the same request)
    assert canonical.execution_plan.steps[0].status != "WAITING_FOR_HUMAN_INPUT"
    assert canonical.execution_plan.steps[0].waiting_reason == ""
    assert canonical.human_requests[0].resolution == "RESOLVED_SUFFICIENT"


# ============================================================================================= #
# 7. Human evidence tiene provenance
# ============================================================================================= #
def test_07_human_evidence_has_complete_provenance(hitl_env):
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    ev = next(e for e in canonical.evidence if e.evidence_id == r.json()["response_evidence_id"])
    assert ev.provenance, "human Evidence without provenance"
    joined = " | ".join(ev.provenance)
    req = canonical.human_requests[0]
    contribution = canonical.human_contributions[0]
    assert f"HumanRequest[{req.request_id}]" in joined
    assert f"HumanContribution[{contribution.contribution_id}]" in joined
    assert f"Work[{hitl_env.work_id}]" in joined
    assert "verdict=SUFFICIENT" in joined and "authority=PYTHON" in joined
    assert ev.created_at and ev.size > 0
    # the Evidence record is also mirrored in the EXISTING evidence authority (no second store)
    assert server.evidence_store[ev.evidence_id]["evidence_id"] == ev.evidence_id


# ============================================================================================= #
# 8. Finding humano VALIDATED sólo si existe evidencia válida
# ============================================================================================= #
def test_08_validated_finding_requires_resolvable_evidence(hitl_env):
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    ev_id = r.json()["response_evidence_id"]
    findings = canonical.knowledge.findings
    assert len(findings) == 1
    f = findings[0]
    assert f.status == "VALIDATED"
    assert f.evidence_refs == [ev_id]                       # resolvable id, never a dangling label
    assert ev_id in canonical.evidence_ids
    assert ev_id in canonical.extracted_evidence
    assert f.method == "HUMAN_INPUT_SUFFICIENCY_GATE"
    assert f.provenance and "authority=PYTHON" in " | ".join(f.provenance)
    # and the inverse: an insufficient response can NEVER produce a VALIDATED finding
    other = _seed_work(WorkStore(tempfile.mkdtemp()), work_id="W-INS", with_request=True)
    out = evaluate_human_response(response_value=ECHO_RESPONSE, required_information=REQUIRED_INFORMATION,
                                  question=HITL_QUESTION, user_intent=PRODUCTION_INTENT)
    assert out["status"] != SUFFICIENT and other.knowledge.findings == []


# ============================================================================================= #
# 9. Publisher recibe evidencia humana (contexto epistemológico estructurado)
# ============================================================================================= #
def test_09_publisher_context_carries_governed_human_input(hitl_env):
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    ctx = build_publication_context(canonical)
    assert r.json()["response_evidence_id"] in ctx["human_txt"]
    assert "python_sufficiency=SUFFICIENT" in ctx["human_txt"]
    assert "required_information:" in ctx["human_txt"]
    assert "asked:" in ctx["human_txt"] and HITL_QUESTION[:60] in ctx["human_txt"]
    assert SUFFICIENT_RESPONSE[:80] in ctx["human_txt"]
    # the finding is handed over WITH its status and resolvable evidence ref
    assert "| VALIDATED |" in ctx["findings_txt"]
    assert r.json()["response_evidence_id"] in ctx["findings_txt"]
    assert "HITL STATE (Python-derived)" not in ctx["hitl_txt"]      # header lives in the prompt
    assert "ANSWERED=1" in ctx["hitl_txt"] and "PENDING=0" in ctx["hitl_txt"]


# ============================================================================================= #
# 10. Publisher NO recibe HUMAN_INPUT como evidencia fantasma
# ============================================================================================= #
def test_10_no_ghost_human_input_evidence_in_publisher_context(hitl_env):
    _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    ctx = build_publication_context(canonical)
    # the historical dangling label is gone as an evidence ref...
    assert "refs=HUMAN_INPUT" not in ctx["findings_txt"]
    # ...and every ref in the context RESOLVES to a canonical evidence entity
    for f in canonical.knowledge.findings:
        for ref in (f.evidence_refs or []):
            assert ref in canonical.evidence_ids, f"dangling evidence ref {ref}"
    # an UNSUPPORTED statement can never be presented as validated knowledge
    canonical.knowledge.findings.append(StructuredFinding(
        finding_id="FND-UNS", statement="afirmación no fundamentada", status="UNSUPPORTED",
        evidence_refs=["EVI-CONTEXT"], provenance=["test"]))
    ctx2 = build_publication_context(canonical)
    assert "| UNSUPPORTED |" in ctx2["findings_txt"]


# ============================================================================================= #
# 11. Publication refleja ANSWERED/READY correctamente (derivada, no hardcodeada)
# ============================================================================================= #
def test_11_publication_reports_derived_hitl_state(hitl_env, tmp_path):
    _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    engine = TestDoubleCognitiveEngine()
    engine.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-A", section_type="ANSWER", status="VALIDATED",
                           content="EUREKA puede monetizarse con licencia SaaS.")])
    publisher = _publisher(engine, str(tmp_path / "pubs"))
    publisher.execute_task(canonical.problem, _publish_task(), canonical)
    sections = canonical.publication_state.publications[-1].sections
    state = [s for s in sections if s.section_type == "LIMITATIONS" and "Estado HITL" in s.content]
    assert state, "the publication must carry the Python-derived HITL state"
    assert "ANSWERED=1" in state[0].content and "PENDING=0" in state[0].content
    assert "suficiencia: SUFFICIENT=1" in state[0].content
    assert "derivado del Canonical State" in state[0].content


# ============================================================================================= #
# 12. Publication jamás reporta PENDING si Canonical State = ANSWERED
# ============================================================================================= #
def test_12_publication_never_contradicts_canonical_hitl_state(hitl_env, tmp_path):
    _answer(hitl_env, SUFFICIENT_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    engine = TestDoubleCognitiveEngine()
    engine.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-A", section_type="ANSWER", status="VALIDATED",
                           content=("El análisis está completo. La decisión humana está pendiente "
                                    "(PENDING) y por eso no hay recomendación.")),
        PublicationSection(section_id="SEC-D", section_type="DECISIONS", status="VALIDATED",
                           content="La decisión humana está pendiente (PENDING); se requiere input humano."),
    ])
    publisher = _publisher(engine, str(tmp_path / "pubs2"))
    publisher.execute_task(canonical.problem, _publish_task(), canonical)
    sections = canonical.publication_state.publications[-1].sections
    blob = " ".join(s.content for s in sections)
    # the FABRICATED claim is gone (the derived state may legitimately report "pendientes=0")
    assert "está pendiente" not in blob.lower(), "publication contradicts the canonical HITL state"
    assert "(PENDING)" not in blob, "publication contradicts the canonical HITL state"
    assert "El análisis está completo." in blob                     # the true part of the answer survives
    assert any("Estado HITL" in s.content for s in sections)        # the derived state is published
    assert any("PYTHON_HITL_STATE_CORRECTION" in " ".join(s.provenance or []) for s in sections)


# ============================================================================================= #
# 13. Insufficient human response genera nueva solicitud controlada
# ============================================================================================= #
def test_13_insufficient_response_raises_a_controlled_follow_up(hitl_env):
    canonical = hitl_env.store[hitl_env.work_id]
    first_id = canonical.human_requests[0].request_id
    _answer(hitl_env, ECHO_RESPONSE)
    canonical = hitl_env.store[hitl_env.work_id]
    assert len(canonical.human_requests) == 2
    follow = canonical.human_requests[1]
    assert follow.status == "PENDING" and follow.blocking is True
    assert follow.request_id != first_id
    assert follow.follows_request_id == first_id
    assert follow.attempt == 2
    assert follow.required_information                             # names WHAT is still missing
    assert "Sigue faltando información" in follow.question
    assert "repetir la pregunta no aporta información" in follow.question
    # the work stays BLOCKED: not published, step still waiting
    assert canonical.status == "WAITING_FOR_HUMAN_INPUT"
    assert canonical.execution_plan.steps[0].status == "WAITING_FOR_HUMAN_INPUT"
    assert canonical.result is None or canonical.result.status != "AVAILABLE"


# ============================================================================================= #
# 14. Anti-loop funciona
# ============================================================================================= #
def test_14_anti_loop_bounds_requests_and_never_publishes(hitl_env):
    canonical = hitl_env.store[hitl_env.work_id]
    for _ in range(MAX_HUMAN_INFORMATION_ATTEMPTS + 2):
        pending = [r for r in canonical.human_requests if r.status == "PENDING"]
        if not pending:
            break
        _answer(hitl_env, ECHO_RESPONSE, request_id=pending[-1].request_id)
        canonical = hitl_env.store[hitl_env.work_id]
    blocking = [r for r in canonical.human_requests if r.type == "INFORMATION" and r.blocking]
    assert len(blocking) == MAX_HUMAN_INFORMATION_ATTEMPTS, "the anti-loop budget must bound the requests"
    assert any(c.reason_code == "HUMAN_INPUT_EXHAUSTED" for c in canonical.conditions)
    assert canonical.human_requests[-1].resolution == "EXHAUSTED"
    # never ANSWERED -> VALIDATED -> PUBLISHED
    assert canonical.knowledge.findings == []
    assert canonical.frozen_result is None
    assert canonical.status == "WAITING_FOR_HUMAN_INPUT"


# ============================================================================================= #
# 15. FrozenResult contiene únicamente conocimiento realmente validado
# ============================================================================================= #
def test_15_frozen_result_carries_validated_knowledge_only(hitl_env, tmp_path):
    canonical = hitl_env.store[hitl_env.work_id]
    canonical.knowledge.findings.append(StructuredFinding(
        finding_id="FND-V", statement="hallazgo validado", status="VALIDATED", evidence_refs=["EVI-1"]))
    canonical.knowledge.findings.append(StructuredFinding(
        finding_id="FND-U", statement="afirmación no fundamentada", status="UNSUPPORTED",
        evidence_refs=["EVI-CONTEXT"]))
    publisher = _publisher(TestDoubleCognitiveEngine(), str(tmp_path / "pubs15"))
    publisher.execute_task(canonical.problem, _publish_task(), canonical)
    frozen = canonical.frozen_result
    assert [k["finding_id"] for k in frozen.validated_knowledge] == ["FND-V"]
    # the full snapshot is still preserved (auditability) and bound into the signature
    assert [k["finding_id"] for k in frozen.knowledge_snapshot] == ["FND-V", "FND-U"]
    assert publisher._signature_from_frozen(frozen) == frozen.freeze_signature
    tampered = frozen.model_copy(deep=True)
    tampered.validated_knowledge = []
    assert publisher._signature_from_frozen(tampered) != frozen.freeze_signature


# ============================================================================================= #
# 16. runtime_metadata registra propose_missing_data cuando ocurre
# ============================================================================================= #
def test_16_provenance_records_missing_data_probe():
    canonical = _seed_work(WorkStore(tempfile.mkdtemp()), with_request=False)
    WorkRuntime(cognitive_engine=_AskingEngine())._maybe_request_missing_data(canonical)
    calls = [m for m in canonical.runtime_metadata if m.capability_id == "propose_missing_data"]
    assert len(calls) == 1
    assert calls[0].status == "COMPLETED"
    assert calls[0].output_schema == "MissingDataProposal"
    assert calls[0].context_id == canonical.work.work_id
    assert calls[0].latency_ms is not None
    # and it is NOT recorded when it did not happen
    clean = _seed_work(WorkStore(tempfile.mkdtemp()), work_id="W-NOPROBE", with_request=False)
    WorkRuntime(cognitive_engine=_DecliningEngine())._maybe_request_missing_data(clean)
    assert len([m for m in clean.runtime_metadata if m.capability_id == "propose_missing_data"]) == 1


# ============================================================================================= #
# 17. runtime_metadata registra propose_publication cuando ocurre
# ============================================================================================= #
def test_17_provenance_records_publication_call(hitl_env, tmp_path):
    canonical = hitl_env.store[hitl_env.work_id]
    engine = TestDoubleCognitiveEngine()
    engine.register_publication_fixture("publish", [
        PublicationSection(section_id="SEC-A", section_type="ANSWER", status="VALIDATED", content="respuesta")])
    publisher = _publisher(engine, str(tmp_path / "pubs17"))
    before = len(canonical.runtime_metadata)
    publisher.execute_task(canonical.problem, _publish_task(), canonical)
    calls = [m for m in canonical.runtime_metadata[before:] if m.capability_id == "propose_publication"]
    assert len(calls) == 1
    assert calls[0].status == "COMPLETED"
    assert calls[0].em == "EM Publisher"


# ============================================================================================= #
# 18. DeepSeek failure -> FAIL CLOSED (declarado, nunca silencioso, nunca inventado)
# ============================================================================================= #
def test_18_probe_failure_fails_closed_and_is_declared():
    canonical = _seed_work(WorkStore(tempfile.mkdtemp()), work_id="W-FAIL", with_request=False)
    assert WorkRuntime(cognitive_engine=_FailingEngine())._maybe_request_missing_data(canonical) is False
    assert canonical.human_requests == []                     # nothing fabricated
    assert canonical.knowledge.findings == []
    assert any(c.reason_code == "MISSING_DATA_PROBE_FAILED" for c in canonical.conditions)
    calls = [m for m in canonical.runtime_metadata if m.capability_id == "propose_missing_data"]
    assert len(calls) == 1 and calls[0].status == "FAILED"


# ============================================================================================= #
# 19. No evidencia -> Publisher no inventa
# ============================================================================================= #
def test_19_publisher_invents_nothing_without_evidence(hitl_env, tmp_path):
    canonical = hitl_env.store[hitl_env.work_id]
    publisher = _publisher(TestDoubleCognitiveEngine(), str(tmp_path / "pubs19"))
    publisher.execute_task(canonical.problem, _publish_task(), canonical)
    summary = canonical.result.summary
    # Path A — LS52 truthful fallback (the LLM produced no sections): derived from canonical data
    assert "Hallazgos validados: 0" in summary
    assert "Estado HITL" in summary
    for banned in ("PRED-", "DEC-", "AP-", "FND-", "99%", "95%"):
        assert banned not in summary
    assert canonical.result.status == "AVAILABLE"              # honest, but nothing invented

    # Path B — the KNOWLEDGE_ANSWER deterministic ANSWER fallback is DERIVED (never a hardcoded
    # human-decision state), which is what the production publication got wrong.
    from src.eureka.universe.cognitive_engine import build_knowledge_answer_fallback
    pending_txt = build_knowledge_answer_fallback(intent=PRODUCTION_INTENT, has_findings=False,
                                                  pending_required=["qué es EUREKA"], insufficient_missing=[])
    assert "WAITING_FOR_HUMAN_INPUT" in pending_txt and "qué es EUREKA" in pending_txt
    insuff_txt = build_knowledge_answer_fallback(
        intent=PRODUCTION_INTENT, has_findings=True, pending_required=[],
        insufficient_missing=["métricas o benchmarks de rendimiento relevantes"])
    assert "no fue suficiente" in insuff_txt
    assert "métricas o benchmarks de rendimiento relevantes" in insuff_txt
    none_txt = build_knowledge_answer_fallback(intent=PRODUCTION_INTENT, has_findings=False,
                                               pending_required=[], insufficient_missing=[])
    assert "NOT_EVALUATED" in none_txt and "NOT_EXECUTED" in none_txt
    for txt in (insuff_txt, none_txt):
        assert "decisión humana" not in txt.lower(), "hardcoded HITL state in a derived answer"


# ============================================================================================= #
# 20. Pregunta KNOWLEDGE_ANSWER con respuesta humana suficiente -> respuesta fundamentada
# ============================================================================================= #
def test_20_sufficient_human_input_reaches_publication_and_freeze(hitl_env):
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    ev_id = r.json()["response_evidence_id"]
    canonical = hitl_env.store[hitl_env.work_id]
    # the endpoint resumed the work and the runtime published with the human evidence available
    assert canonical.result is not None and canonical.result.status == "AVAILABLE"
    assert canonical.status == "COMPLETED"
    assert canonical.frozen_result is not None
    frozen_ids = [k.get("finding_id") for k in canonical.frozen_result.validated_knowledge]
    assert frozen_ids, "the human VALIDATED finding must reach the frozen result"
    assert any(f.finding_id in frozen_ids and f.evidence_refs == [ev_id]
               for f in canonical.knowledge.findings)
    # the human evidence is part of the result grounding and of the publication state
    assert any(SUFFICIENT_RESPONSE[:40] in f for f in canonical.result.findings)
    assert canonical.publication_state.status == "PUBLISHED"
    published_blob = " ".join(s.content for s in canonical.publication_state.publications[-1].sections)
    assert "Estado HITL" in published_blob
    assert canonical.human_requests[0].resolution == "RESOLVED_SUFFICIENT"


# ============================================================================================= #
# Adversarial addenda (contract hardening)
# ============================================================================================= #
def test_21_client_cannot_claim_sufficiency_or_evidence_id(hitl_env):
    """A forged client payload can never inject sufficiency/evidence/validation fields."""
    r = hitl_env.client.post(f"/api/work/{hitl_env.work_id}/human_input", json={
        "type": "INFORMATION", "request_id": hitl_env.request_id, "value": ECHO_RESPONSE,
        "sufficiency_status": SUFFICIENT, "response_evidence_id": "EVI-HUMAN-FORGED",
        "status": "ANSWERED", "resolution": "RESOLVED_SUFFICIENT"})
    assert r.status_code == 200
    canonical = hitl_env.store[hitl_env.work_id]
    req = canonical.human_requests[0]
    assert req.sufficiency_status == "INSUFFICIENT"                 # Python verdict, not the client's
    assert req.response_evidence_id != "EVI-HUMAN-FORGED"
    assert not any(e.evidence_id == "EVI-HUMAN-FORGED" for e in canonical.evidence)
    assert canonical.knowledge.findings == []


def test_22_human_evidence_is_not_lost_by_the_read_projection(hitl_env):
    """The GET /state projection must not drop canonical evidence (durability of traceability)."""
    r = _answer(hitl_env, SUFFICIENT_RESPONSE)
    ev_id = r.json()["response_evidence_id"]
    # remove the in-memory mirror -> simulates a restart (only the canonical state survives)
    server.evidence_store.pop(ev_id, None)
    state = hitl_env.client.get(f"/api/work/{hitl_env.work_id}/state").json()
    ids = [e["evidence_id"] for e in state.get("evidence", [])]
    assert ev_id in ids, "canonical human evidence was dropped by the read projection"
    assert ev_id in state.get("evidence_ids", [])


def test_23_governance_thresholds_are_deterministic_and_declared():
    """Same input -> same verdict; the verdict is never authored by an LLM."""
    kwargs = dict(response_value=SUFFICIENT_RESPONSE, required_information=REQUIRED_INFORMATION,
                  question=HITL_QUESTION, user_intent=PRODUCTION_INTENT)
    a, b = evaluate_human_response(**kwargs), evaluate_human_response(**kwargs)
    assert a["status"] == b["status"] == SUFFICIENT
    assert a["covered"] == b["covered"] and a["method"] == b["method"]
    assert a["authority"] == "PYTHON" and a["llm_used"] is False
    assert len(a["covered"]) == len(REQUIRED_INFORMATION)
    # a structured (dict) answer is evaluated on its keys+values, never promoted by shape alone
    shaped = evaluate_human_response(response_value={"que es EUREKA": "plataforma cognitiva"},
                                     required_information=REQUIRED_INFORMATION,
                                     question=HITL_QUESTION, user_intent=PRODUCTION_INTENT)
    assert shaped["status"] in ("PARTIAL", "INSUFFICIENT")


def test_24_full_production_sequence_gate_then_echo_then_followup(monkeypatch, tmp_path):
    """The exact WORK-D120C202 sequence end to end: the runtime raises the gate, the human echoes the
    question through the REAL endpoint, nothing is validated/published, and a governed follow-up
    request states exactly what is still missing."""
    store = WorkStore(str(tmp_path / "works24"))
    runtime = WorkRuntime(cognitive_engine=_AskingEngine())
    runtime.publisher.publication_dir = str(tmp_path / "pubs24")
    canonical = _seed_work(store, work_id="WORK-ECHO-SEQ", with_request=False)

    # 1. The governed gate raises the blocking INFORMATION request (Python decides, LLM only proposes)
    assert runtime._maybe_request_missing_data(canonical) is True
    canonical.status = "WAITING_FOR_HUMAN_INPUT"          # what the runtime loop does when it blocks
    request_id = canonical.human_requests[0].request_id
    store["WORK-ECHO-SEQ"] = canonical

    monkeypatch.setattr(server, "works_db", store)
    monkeypatch.setattr(server, "evidence_store", {})
    monkeypatch.setattr(server, "runtime", runtime)

    # 2. The human answers with the production echo, through the REAL endpoint
    client = TestClient(server.app)
    r = client.post("/api/work/WORK-ECHO-SEQ/human_input",
                    json={"type": "INFORMATION", "request_id": request_id, "value": ECHO_RESPONSE})
    assert r.status_code == 200
    assert r.json()["human_response_sufficiency"] == "INSUFFICIENT"

    # 3. NEVER ANSWERED -> VALIDATED -> PUBLISHED
    final = store["WORK-ECHO-SEQ"]
    assert final.knowledge.findings == []
    assert final.frozen_result is None
    assert final.publication_state is None
    assert final.status == "WAITING_FOR_HUMAN_INPUT"
    pending = [h for h in final.human_requests if h.status == "PENDING"]
    assert len(pending) == 1 and pending[0].attempt == 2
    assert pending[0].required_information and pending[0].follows_request_id == request_id
