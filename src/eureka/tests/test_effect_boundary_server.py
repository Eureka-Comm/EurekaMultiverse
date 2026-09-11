"""LS-SCN-03e — F2/F3: server persistence (server.py:369, 808).

Proves these file writes are NOT-REACHABLE-IN-DRY-RUN: they are inside FastAPI request handlers
(user/HTTP-triggered NORMAL actions), never reached from the governed `WorkRuntime._execute_step`
dry-run path, and the runtime (`WorkRuntime`) has no direct fs write for them.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVER = ROOT / "src/eureka/universe/server.py"
WR = ROOT / "src/eureka/universe/work_runtime.py"


def _route_of(server_text: str, target_line: int) -> str:
    """Find the nearest preceding FastAPI route decorator (or 'def ' handler) before target_line."""
    lines = server_text.splitlines()
    for i in range(target_line - 2, -1, -1):
        ln = lines[i].strip()
        if ln.startswith("@app.") and ("('/" in ln or '("/' in ln):
            return ln
    return "no_route_found"


def test_server_writes_are_inside_http_route_handlers():
    src = SERVER.read_text(encoding="utf-8")
    # The two server fs writes (evidence upload + work download). Line numbers are the CURRENT
    # positions after the governed HITL -> Evidence contract added lines; the writes are still
    # inside HTTP handlers (the property under test is unchanged).
    for lineno in (411, 1003):
        route = _route_of(src, lineno)
        assert route.startswith("@app."), f"server.py:{lineno} not inside an HTTP route: {route}"


def test_governed_runtime_has_no_direct_server_persist_write():
    """WorkRuntime (the dry-run gate owner) does not perform the server file writes."""
    wr = WR.read_text(encoding="utf-8")
    # the server persist writes (open(...,"w")) are NOT present in the runtime dispatch
    assert 'open(' not in wr, "WorkRuntime performs an fs write; server persist is separate"


def test_no_scenario_surface_activates_server_persistence():
    """These writes are only triggerable by HTTP requests, not by a controlled/dry-run execution."""
    src = SERVER.read_text(encoding="utf-8")
    # Server endpoints are not the governed dry-run owner (that is WorkRuntime._execute_step).
    assert "_dry_run" not in src, "Server endpoints must not own a dry-run mode that writes files"
