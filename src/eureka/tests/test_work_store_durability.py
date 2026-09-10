"""LS-WORKDUR — Durable Work Authority: restart-safe workspace -> whatif -> decision -> execution -> audit.

The fundamental guarantee proven here: the SAME work_id and SEMANTIC state (Q2 identity) survive a
"restart", where restart means a NEW authority instance (or a NEW OS process via subprocess) reading
the SAME durable storage. Two instances are independent runtimes (``A != B``), yet resolve the SAME
work and the SAME Q2 identity. Scenario WHAT-IF / decision / execution all keep working across it.
"""
import json
import os
import subprocess
import sys
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.eureka.universe.work_store import WorkStore, CorruptWorkError
from src.eureka.universe.scenario_transport import make_router
from src.eureka.universe.scenario_service import ScenarioService
from src.eureka.universe.scenario_repository import ScenarioRepository
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, StructuredFinding, WorkResult
from src.eureka.universe.canonical_identity import canonical_state_fingerprint

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def _mk_real(work_id: str) -> CanonicalWorkState:
    real = CanonicalWorkState(work=EurekaWork(
        work_id=work_id, title="Real Work", user_intent="analyze dataset",
        task_category="DESCRIPTOR", problem_statement="Analyze dataset X"))
    real.knowledge.findings.append(StructuredFinding(
        finding_id="F-1", statement="correlation found", finding_type="RELATIONAL", evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id=work_id, summary="done",
                             status="AVAILABLE", confidence=0.9)
    return real


def _build_app(work_store, scenario_dir, artifact_dir):
    service = ScenarioService(repository=ScenarioRepository(scenario_dir), artifact_dir=artifact_dir)
    app = FastAPI()
    app.include_router(make_router(service, work_resolver=lambda wid: work_store.get(wid)), prefix="/api")
    return app, service


# ---- 1) real restart: two INDEPENDENT authority instances, same durable storage ---------------- #
def test_two_instances_resolve_same_work_and_q2_identity():
    work_dir = tempfile.mkdtemp()
    A = WorkStore(work_dir)
    real = _mk_real("W-RESTART")
    A["W-RESTART"] = real
    fpA = canonical_state_fingerprint(A["W-RESTART"])

    B = WorkStore(work_dir)  # INSTANCE B — a separate runtime/object, same storage
    wb = B["W-RESTART"]
    assert B["W-RESTART"] is not real          # A != B as runtime objects
    assert canonical_state_fingerprint(wb) == fpA  # same Q2 semantic identity => durable
    assert "W-RESTART" in B
    assert sorted(B.keys()) == ["W-RESTART"]


# ---- 2) full governed pipeline survives a restart --------------------------------------------- #
def test_full_pipeline_survives_restart():
    work_dir = tempfile.mkdtemp()
    scenario_dir = tempfile.mkdtemp()
    artifact_dir = tempfile.mkdtemp()
    sid = "SCN-RESTART"

    # INSTANCE A
    storeA = WorkStore(work_dir)
    appA, _ = _build_app(storeA, scenario_dir, artifact_dir)
    cA = TestClient(appA)
    realA = _mk_real("W-RESTART")
    storeA["W-RESTART"] = realA
    assert cA.post("/api/scenario/whatif", json={"scenario_id": sid, "work_id": "W-RESTART",
                                                 "assumptions": [{"delta": 0.1}]}).status_code == 200
    sc_before = cA.get(f"/api/scenario/{sid}").json()["source_state_identity"]
    cA.post(f"/api/scenario/{sid}/authorize", json={"work_id": "W-RESTART", "decision_type": "CONFIRM",
                                                    "rationale": "ok", "human_actor": "a"})
    decision_id = cA.get(f"/api/scenario/{sid}/decision").json()["decision_id"]

    # RESTART -> INSTANCE B (new WorkStore + new ScenarioService/Repository over the SAME dirs)
    storeB = WorkStore(work_dir)
    appB, _ = _build_app(storeB, scenario_dir, artifact_dir)
    cB = TestClient(appB)

    assert storeB.get("W-RESTART") is not None                                 # work (durable) resolves
    assert cB.get(f"/api/scenario/{sid}/result").status_code == 200         # scenario result persisted
    assert cB.get(f"/api/scenario/{sid}").json()["source_state_identity"] == sc_before  # Q2 preserved
    got_dec = cB.get(f"/api/scenario/{sid}/decision").json()
    assert got_dec["decision_id"] == decision_id
    assert got_dec["authority"] == "HUMAN_DECISION"

    # EXECUTE on instance B (Q2 re-validated against the durable work, Q4, real effect)
    r = cB.post(f"/api/scenario/{sid}/execute", json={"work_id": "W-RESTART"})
    assert r.status_code == 200
    e = r.json()
    assert e["status"] == "SUCCEEDED"
    assert e["authority"] == "HUMAN_DECISION"
    assert e["canonical_status"] == "NON_CANONICAL"
    assert e["effect"]["exists"] is True
    assert cB.get(f"/api/scenario/{sid}/execution").json()["execution_id"] == e["execution_id"]
    assert cB.get("/api/scenario/executions").status_code == 200

    # idempotency survives restart: the same execution request returns the SAME execution_id
    r2 = cB.post(f"/api/scenario/{sid}/execute", json={"work_id": "W-RESTART"})
    assert r2.status_code == 200
    assert r2.json()["execution_id"] == e["execution_id"]


# ---- 3) stale AFTER restart: source identity must still be re-validated ----------------------- #
def test_stale_after_restart_fails_closed():
    work_dir = tempfile.mkdtemp()
    scenario_dir = tempfile.mkdtemp()
    artifact_dir = tempfile.mkdtemp()
    sid = "SCN-STALE-RT"
    storeA = WorkStore(work_dir)
    appA, _ = _build_app(storeA, scenario_dir, artifact_dir)
    cA = TestClient(appA)
    realA = _mk_real("W-STALE")
    storeA["W-STALE"] = realA
    cA.post("/api/scenario/whatif", json={"scenario_id": sid, "work_id": "W-STALE",
                                          "assumptions": [{"delta": 0.1}]})
    cA.post(f"/api/scenario/{sid}/authorize", json={"work_id": "W-STALE", "decision_type": "CONFIRM"})

    # restart to instance B, then MUTATE the durable work (semantically relevant to Q2)
    storeB = WorkStore(work_dir)
    appB, _ = _build_app(storeB, scenario_dir, artifact_dir)
    cB = TestClient(appB)
    realB = storeB["W-STALE"]          # loaded from durable storage
    realB.knowledge.findings.append(StructuredFinding(finding_id="F-2", statement="new info",
                                                      finding_type="RELATIONAL"))
    storeB["W-STALE"] = realB          # persist the mutation (work authority)
    r = cB.post(f"/api/scenario/{sid}/execute", json={"work_id": "W-STALE"})
    assert r.status_code == 409
    assert r.json()["detail"]["error"] == "STALE_SOURCE"
    assert r.json()["detail"]["execution"]["effect"] == {}   # no effect (fail-closed)


# ---- 4) corrupt durable work -> fail closed (never fabricate) --------------------------------- #
def test_corrupt_work_fails_closed():
    work_dir = tempfile.mkdtemp()
    WorkStore(work_dir).__setitem__("W-GOOD", _mk_real("W-GOOD"))
    # corrupt a record
    with open(os.path.join(work_dir, "W-BAD.json"), "w", encoding="utf-8") as f:
        f.write("{ this is not valid json")
    store = WorkStore(work_dir)
    with pytest.raises(CorruptWorkError):
        _ = store["W-BAD"]          # __getitem__ raises (fail-closed)
    with pytest.raises(CorruptWorkError):
        _ = store.get("W-BAD")      # get also raises
    # a good work is still readable (isolation)
    assert store["W-GOOD"].work.work_id == "W-GOOD"


# ---- 5) unknown work after restart -> fail closed (no synthetic fallback) --------------------- #
def test_unknown_work_after_restart():
    work_dir = tempfile.mkdtemp()
    storeB = WorkStore(work_dir)     # fresh instance (post-restart)
    assert storeB.get("W-UNKNOWN") is None
    assert "W-UNKNOWN" not in storeB
    with pytest.raises(KeyError):
        _ = storeB["W-UNKNOWN"]
    # and the scenario WHAT-IF rejects an unknown work via the SAME durable authority
    scenario_dir = tempfile.mkdtemp()
    app, _ = _build_app(storeB, scenario_dir, tempfile.mkdtemp())
    c = TestClient(app)
    r = c.post("/api/scenario/whatif", json={"scenario_id": "SCN-U", "work_id": "W-UNKNOWN",
                                             "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "WORK_NOT_FOUND"


# ---- 6) REAL process restart via subprocess (a genuinely different OS process) ---------------- #
def test_restart_via_subprocess_preserves_identity():
    work_dir = tempfile.mkdtemp()
    storeA = WorkStore(work_dir)
    real = _mk_real("W-SUBPROC")
    storeA["W-SUBPROC"] = real
    fp = canonical_state_fingerprint(real)

    code = (
        "import sys, json, os\n"
        "sys.path.insert(0, os.environ['EUREKA_PYTHONPATH'])\n"
        "from src.eureka.universe.work_store import WorkStore\n"
        "from src.eureka.universe.canonical_identity import canonical_state_fingerprint\n"
        "w = WorkStore(os.environ['EUREKA_WORK_STORAGE_DIR'])['W-SUBPROC']\n"
        "print(canonical_state_fingerprint(w))\n"
    )
    env = dict(os.environ, EUREKA_WORK_STORAGE_DIR=work_dir, EUREKA_PYTHONPATH=REPO_ROOT)
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env)
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == fp  # the NEW OS process sees the SAME Q2 identity
