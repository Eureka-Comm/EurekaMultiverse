"""LS-SCN-WORK — Real workspace work (CanonicalWorkState) feeds Scenario WHAT-IF via work_id.

This is the TRUE seam test: the Scenario WHAT-IF endpoint resolves a REAL canonical work from the
single Work authority (a durable ``WorkStore``) by ``work_id`` — the SAME store the Work API reads.
The client never supplies authoritative canonical state for the real-work path; it only names the work.
"""
import tempfile

from fastapi.testclient import TestClient

import src.eureka.universe.server as server
from src.eureka.universe.work_store import WorkStore
from src.eureka.universe.work_model import EurekaWork
from src.eureka.universe.canonical_state import CanonicalWorkState, StructuredFinding, WorkResult
from src.eureka.universe.canonical_identity import canonical_state_fingerprint

# Isolate the durable Work authority to a temp dir (no pollution of the production store). The server
# endpoints + the Scenario work_id resolver both read the SAME ``server.works_db`` (ONE authority).
_STORE_DIR = tempfile.mkdtemp()
server.works_db = WorkStore(_STORE_DIR)
client = TestClient(server.app)

BARE = {"work_id": "W-BARE", "title": "t", "user_intent": "u", "task_category": "c",
        "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}


def _seed_real_work():
    """Insert a REAL CanonicalWorkState into the single (durable) Work authority (server.works_db)."""
    real = CanonicalWorkState(work=EurekaWork(
        work_id="W-REAL", title="Real Work", user_intent="analyze dataset",
        task_category="DESCRIPTOR", problem_statement="Analyze the dataset X"))
    # real, fingerprint-relevant content (Q2 content fingerprint, not metadata)
    real.knowledge.findings.append(StructuredFinding(
        finding_id="F-1", statement="correlation found", finding_type="RELATIONAL",
        evidence_refs=["EVI-1"]))
    real.result = WorkResult(result_id="R-1", work_id="W-REAL", summary="done",
                             status="AVAILABLE", confidence=0.9)
    server.works_db["W-REAL"] = real
    return real


def test_whatif_resolves_real_work_by_id():
    real = _seed_real_work()
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-REAL",
                                                  "work_id": "W-REAL",
                                                  "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 200
    body = r.json()
    # single-authority domain annotation
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["canonical_status"] == "NON_CANONICAL"
    # the WHAT-IF was fed by the REAL canonical content -> its source identity is the Q2 fingerprint
    assert body["source_state_identity"] == canonical_state_fingerprint(real)


def test_real_work_fingerprint_differs_from_bare_work_path():
    # The real-work path reads canonical knowledge/result content; the bare work+acfl path does not.
    # This proves the work_id resolver uses REAL content, not a client-supplied WorkInput.
    real = _seed_real_work()
    real_id = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-REALFP",
                                                        "work_id": "W-REAL",
                                                        "assumptions": [{"delta": 0.1}]}).json()["source_state_identity"]
    bare_id = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-BAREFP",
                                                        "work": BARE,
                                                        "assumptions": [{"delta": 0.1}]}).json()["source_state_identity"]
    assert real_id != bare_id
    assert real_id == canonical_state_fingerprint(real)


def test_work_id_takes_precedence_over_supplied_work():
    # Even if a client smuggles a `work` object, work_id resolves the REAL canonical state.
    real = _seed_real_work()
    body = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-PREC",
                                                     "work_id": "W-REAL",
                                                     "work": BARE,
                                                     "assumptions": [{"delta": 0.1}]}).json()
    assert body["source_state_identity"] == canonical_state_fingerprint(real)


def test_whatif_unknown_work_id_fails_closed():
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-NOPE",
                                                  "work_id": "W-DOES-NOT-EXIST",
                                                  "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 404
    assert r.json()["detail"]["error"] == "WORK_NOT_FOUND"


def test_whatif_requires_a_source():
    # neither work_id nor work -> fail closed (no invented source)
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-NOSRC",
                                                  "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 422


def test_real_work_single_authority_no_second_store():
    # The work_id resolver reads the SAME store as the Work API (single Work authority).
    real = _seed_real_work()
    assert client.get("/api/work/W-REAL/state").status_code == 200
    # and the seeded work is the same object the WHAT-IF resolved
    assert server.works_db["W-REAL"] is real
