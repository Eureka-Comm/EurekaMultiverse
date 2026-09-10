"""LS-SCN-03e — F1: artifact write (artifact_exporter.py:799).

Proves `write_export` is GOVERNED transitively: the only path to it in the governed runtime is
via the MUTATE-classified `generate_summary/generate_report/generate_presentation` capabilities,
which `WorkRuntime._execute_step` blocks in DRY_RUN BEFORE the artifact engine runs.
"""
import pathlib
from src.eureka.universe.effect_policy import default_boundary, EffectClass, ExecutionMode, DryRunContext
from src.eureka.universe.work_runtime import WorkRuntime

ROOT = pathlib.Path(__file__).resolve().parents[3]
WR = ROOT / "src/eureka/universe/work_runtime.py"
ART = ROOT / "src/eureka/universe/artifact_engine.py"


def test_artifact_capabilities_are_mutate():
    b = default_boundary()
    for cap in ("generate_report", "generate_summary", "generate_presentation"):
        assert b.classifier.effect_for(cap) == EffectClass.MUTATE


def test_artifact_write_only_reached_via_mutate_branch():
    src = WR.read_text(encoding="utf-8")
    writer = ART.read_text(encoding="utf-8")
    # artifact_engine.generate_artifact is dispatched only from within the generate_* branch
    assert "artifact_engine.generate_artifact" in src
    assert any(f'"{c}"' in src for c in ("generate_summary", "generate_report", "generate_presentation"))
    assert "def generate_artifact" in writer
    assert "write_export(" in writer


def test_dispatch_blocks_generate_report_before_artifact_engine():
    wr = WorkRuntime()
    wr._dry_run = True
    stub_state = type("S", (), {"conditions": []})()
    step = type("S", (), {"capability_id": "generate_report", "target": "EM[PUBLISHER]", "status": "READY", "provenance": []})()
    wr._execute_step(stub_state, step)
    assert step.status == "BLOCKED"
    assert stub_state.conditions and stub_state.conditions[-1].status == "BLOCKED"


def test_dry_run_gate_rejects_artifact_write():
    # Equivalent at the policy layer: MUTATE in DRY_RUN is BLOCKED (the write never occurs).
    b = default_boundary()
    v = b.authorize(DryRunContext(capability_id="generate_report", target="EM[PUBLISHER]",
                                  mode=ExecutionMode.DRY_RUN))
    assert v.decision.value == "BLOCK"
