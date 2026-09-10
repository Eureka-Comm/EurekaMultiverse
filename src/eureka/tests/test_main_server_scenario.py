"""LS-SCN-MAIN — Scenario API mounted on the SINGLE main FastAPI app."""
import pytest
from fastapi.testclient import TestClient
from src.eureka.universe.server import app

client = TestClient(app)

WORK = {"work_id": "W1", "title": "t", "user_intent": "u", "task_category": "c",
        "problem_statement": "p", "acfl_weights": {"cost": 50.0, "risk": 50.0}}


def test_scenario_router_mounted_on_main_app():
    # the scenario API is reachable on the MAIN server (no separate app)
    r = client.post("/api/scenario/whatif", json={"scenario_id": "SCN-M", "work": WORK,
                                                  "assumptions": [{"delta": 0.1}]})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["canonical_status"] == "NON_CANONICAL"
    assert body["projected_artifacts"][0]["payload"]["m"] == 0.6


def test_main_server_persistence_and_retrieval():
    client.post("/api/scenario/whatif", json={"scenario_id": "SCN-M1", "work": WORK,
                                              "assumptions": [{"delta": 0.1}]})
    assert client.get("/api/scenario/SCN-M1").status_code == 200
    res = client.get("/api/scenario/SCN-M1/result").json()
    assert res["authority"] == "PROJECTED"
    assert res["projected_artifacts"][0]["scope"] == "SCENARIO"


def test_main_server_comparison():
    for sid, delta in (("SCN-A", 0.0), ("SCN-B", 0.1), ("SCN-C", 0.2)):
        client.post("/api/scenario/whatif", json={"scenario_id": sid, "work": WORK,
                                                  "assumptions": [{"delta": delta}]})
    r = client.post("/api/scenario/compare", json={"scenario_ids": ["SCN-A", "SCN-B", "SCN-C"],
                                                   "baseline_scenario_id": "SCN-A"})
    assert r.status_code == 200
    body = r.json()
    assert body["scope"] == "SCENARIO"
    assert body["authority"] == "PROJECTED"
    assert body["scenario_ids"] == ["SCN-A", "SCN-B", "SCN-C"]
    # no recommendation/winner
    for banned in ("best_scenario", "winner", "recommendation", "promote"):
        assert banned not in body


def test_main_server_governance_fail_closed():
    # stale/evil requests must not produce false success
    r = client.post("/api/scenario/compare", json={"scenario_ids": []})
    assert r.status_code == 422
    assert client.get("/api/scenario/NOPE").status_code == 404
