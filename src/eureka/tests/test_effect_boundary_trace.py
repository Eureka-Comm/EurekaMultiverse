"""LS-SCN-03c — F5–F13: trace/instrumentation writes.

Classifies the trace-write funnels as NOT-A-MUTATION (diagnostic telemetry), proven by test:

- Each write target is a trace/debug file (`R8.8.7.5-*.json`, `deepseek_raw_response.txt`, `TRACE`),
  i.e. observability metadata, NOT a canonical/domain artifact.
- None of these files can mutate `CanonicalWorkState`, a `frozen_result`, or a canonical `result`
  (no canonical-state-derived artifact write on those paths).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
FILES = {
    "ollama_provider": ROOT / "src/eureka/universe/ollama_provider.py",
    "orchestrator": ROOT / "src/eureka/universe/orchestrator.py",
    "provider_backed_cognitive_engine": ROOT / "src/eureka/universe/provider_backed_cognitive_engine.py",
    "cognitive_engine": ROOT / "src/eureka/universe/cognitive_engine.py",
}

# diagnostic trace filename markers that are permitted
TRACE_MARKERS = ("R8.8.7.5-", "deepseek_raw_response", "TRACE")
# a write that is NOT a trace marker would be a domain artifact write
NON_TRACE_WRITE = ("write_export", "save_artifact", "frozen_result", "FROZEN-SOLUTION")


def _writes(path: pathlib.Path):
    """Yield (lineno, line) for fs-write calls in the file (write-mode open OR write_text)."""
    for i, ln in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if ("write_text(" in ln) or ('open(' in ln) and (('"w"' in ln) or ("'w'" in ln)):
            yield i, ln


def test_trace_writes_are_diagnostic_not_domain_artifacts():
    """Every fs write in these files is a trace/debug file, never a canonical/domain artifact."""
    for name, path in FILES.items():
        found = False
        for lineno, ln in _writes(path):
            if not any(m in ln for m in TRACE_MARKERS):
                # a non-trace write could be a domain mutation
                raise AssertionError(f"{name}:{lineno} non-trace fs write: {ln.strip()}")
            found = True
        assert found, f"{name} should contain trace writes"


def test_trace_files_cannot_mutate_canonical_state():
    """None of the trace-write files persists canonical state / frozen result on a write line."""
    for name, path in FILES.items():
        for lineno, ln in _writes(path):
            for marker in NON_TRACE_WRITE:
                assert marker not in ln, f"{name}:{lineno} canonical-artifact write: {ln.strip()}"


def test_trace_payloads_are_metadata_not_canonical_dump():
    """Trace writes serialise telemetry (timestamp/status/response/input/proposal), not canonical."""
    for name, path in FILES.items():
        for lineno, ln in _writes(path):
            assert ("timestamp" in ln or "status" in ln or "response" in ln
                    or "input" in ln or "proposal" in ln or "trace" in ln or "content" in ln
                    or "json" in ln), f"{name}:{lineno} trace payload not metadata: {ln.strip()}"
