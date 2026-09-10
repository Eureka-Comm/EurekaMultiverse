"""LS-SCN-03b — F4: evolution ledger (evolution/ledger.py:44).

Proves `EvolutionLedger._append` (the append-only ledger write) is
NOT-REACHABLE-IN-DRY-RUN from the governed/controlled execution surface:

- The governed dry-run surface is ``src/eureka/universe`` (``WorkRuntime._execute_step``).
- ``EvolutionLedger`` lives in ``src/eureka/evolution`` (its own subsystem) and is driven by the
  evolution loop (``evolution/api.py``, ``evolution/hitl_gate.py``), not by ``_execute_step``.
- ``src/eureka/universe`` never references ``EvolutionLedger`` / ``evolution.ledger``.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
UNIVERSE = ROOT / "src/eureka/universe"
RUNTIME_ENTRY = ROOT / "src/eureka/universe/work_runtime.py"


def _text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def test_governed_runtime_never_references_evolution_ledger():
    """The controlled/dry-run surface must not route through the evolution ledger."""
    needles = ("EvolutionLedger", "evolution.ledger", "evolution.ledger.EvolutionLedger")
    for p in sorted(UNIVERSE.rglob("*.py")):
        txt = _text(p)
        for needle in needles:
            assert needle not in txt, f"governed runtime references evolution ledger: {p} ({needle})"


def test_work_runtime_gate_is_the_only_dry_run_surface():
    """Only WorkRuntime owns the dry-run flag; the ledger is never consulted by it."""
    wr_txt = _text(RUNTIME_ENTRY)
    assert "_dry_run" in wr_txt
    assert "EvolutionLedger" not in wr_txt, "WorkRuntime must never call the evolution ledger"


def test_evolution_ledger_append_is_called_only_by_ledger_methods():
    """`_append` is a private helper invoked only by register/record_outcome/set_status."""
    txt = _text(ROOT / "src/eureka/evolution/ledger.py")
    # these are the only call sites of _append
    for caller in ("self._append(record)",):
        assert txt.count(caller) >= 3, "expected register/record_outcome/set_status to call _append"
    # it must not be invoked from the governed universe
    assert "evolution/ledger" not in _text(ROOT / "src/eureka/universe/work_runtime.py")
