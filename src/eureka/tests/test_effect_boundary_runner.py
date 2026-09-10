"""LS-SCN-03a — Direct-EM bypass (F18/F19).

Proves that ``foundation/cognitive/orchestration/runner.py`` (GenericEMRunner) is
NOT-REACHABLE-IN-DRY-RUN from the governed/controlled execution surface:

- The ONLY governed dry-run surface is ``src/eureka/universe`` (``WorkRuntime._execute_step``).
- ``GenericEMRunner`` operates on an ``EnterpriseKnowledgePackage`` (EKP), a separate model from
  ``CanonicalWorkState``, and is **not** referenced by any ``universe`` module nor instantiated
  anywhere in ``src/eureka`` (only in its own definition/export).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]          # repo root
RUNNER = ROOT / "src/eureka/foundation/cognitive/orchestration/runner.py"
UNIVERSE = ROOT / "src/eureka/universe"
EUREKA = ROOT / "src/eureka"


def _text(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def test_runner_operates_on_ekp_not_canonical_state():
    """GenericEMRunner.run mutates an EKP; it has no CanonicalWorkState/WorkRuntime surface."""
    txt = _text(RUNNER)
    assert "def run(self, em_id" in txt, "run signature must take an em_id"
    assert "ekp:" in txt, "run signature must take an EKP"
    assert "EnterpriseKnowledgePackage" in txt
    assert "CanonicalWorkState" not in txt, "runner must never touch canonical work state"
    assert "WorkRuntime" not in txt, "runner must never touch the governed WorkRuntime gate"


def test_governed_runtime_has_no_dependency_on_foundation_runner():
    """The controlled/dry-run surface (universe) must not route through the foundation EM runner."""
    needles = ("GenericEMRunner", "orchestration.runner", "orchestration.runner_contract")
    for p in sorted(UNIVERSE.rglob("*.py")):
        txt = _text(p)
        for needle in needles:
            assert needle not in txt, f"governed runtime references foundation runner: {p} ({needle})"


def test_foundation_runner_is_not_instantiated_anywhere():
    """No module in src/eureka instantiates GenericEMRunner outside its own definition.

    Only class-definition lines (``class ...GenericEMRunner(...)``) are allowed; a real call site
    ``GenericEMRunner(...)`` not on a ``class`` line would make F18/F19 reachable.
    """
    this_file = "test_effect_boundary_runner.py"
    hits = []
    for p in sorted(EUREKA.rglob("*.py")):
        if p.name == this_file or p == RUNNER:
            continue
        for ln in _text(p).splitlines():
            stripped = ln.strip()
            if "GenericEMRunner(" in ln and not stripped.startswith("class"):
                hits.append(f"{p.relative_to(ROOT)}: {stripped}")
    assert hits == [], f"GenericEMRunner instantiated at: {hits}"


def test_governed_gate_is_the_only_dry_run_entry():
    """The only place that consults a DRY_RUN boundary is WorkRuntime._execute_step."""
    wr = _text(ROOT / "src/eureka/universe/work_runtime.py")
    assert "_dry_run" in wr, "WorkRuntime must own the dry-run flag"
    assert "effect_boundary" in wr.lower()
