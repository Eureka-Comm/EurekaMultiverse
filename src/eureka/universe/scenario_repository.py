"""EUREKA 5.1 — Bounded Scenario persistence (file-backed JSON, reusing repo convention).

Decision: the repository has NO MongoDB/SQL/repository abstraction. Its established durable
persistence convention is JSON-to-disk (freeze artifacts -> ./generated, evolution ledger ndjson,
artifact export). This block reuses that convention with a small ``ScenarioRepository`` that stores
``Scenario`` + ``ScenarioRuntimeResult`` as JSON. Writes are governed by Q4's ``guarded_dump_json``
(NORMAL + the runtime's canonical-persistence token), so a DRY_RUN/controlled context would be
BLOCKED from persisting.

The repository is STORAGE ONLY. It never converts Scenario -> canonical, never promotes, never
executes, never rewrites authority. ``fail_closed`` on read/validate errors.
"""
from __future__ import annotations

import os
from typing import List, Optional

from .scenario_foundation import Scenario
from .scenario_runtime import ScenarioRuntimeResult
from .scenario_lifecycle import ScenarioLifecycle
from .scenario_decision import ScenarioDecision
from .scenario_execution import ScenarioExecution
from .effect_policy import guarded_dump_json, default_boundary, ExecutionMode, CANONICAL_PERSISTENCE_AUTH


class ScenarioRepository:
    """Minimal, honest JSON-file persistence for Scenario + ScenarioRuntimeResult."""

    def __init__(self, storage_dir: str = "data/scenarios") -> None:
        self.storage_dir = storage_dir
        self._boundary = default_boundary()
        os.makedirs(self.storage_dir, exist_ok=True)

    def _path(self, scenario_id: str, kind: str) -> str:
        return os.path.join(self.storage_dir, ".".join([scenario_id, kind, "json"]))

    # ---- Scenario --------------------------------------------------------- #
    def save_scenario(self, scenario: Scenario) -> None:
        data = scenario.model_dump(mode="json")
        guarded_dump_json(self._boundary, self._path(scenario.scenario_id, "scenario"), data,
                          mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
                          capability_id="scenario.persist", target="fs")

    def get_scenario(self, scenario_id: str) -> Optional[Scenario]:
        path = self._path(scenario_id, "scenario")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            import json
            return Scenario.model_validate(json.load(f))

    # ---- ScenarioRuntimeResult -------------------------------------------- #
    def save_result(self, result: ScenarioRuntimeResult) -> None:
        data = result.model_dump(mode="json")
        guarded_dump_json(self._boundary, self._path(result.scenario_id, "result"), data,
                          mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
                          capability_id="scenario.persist", target="fs")

    def get_result(self, scenario_id: str) -> Optional[ScenarioRuntimeResult]:
        path = self._path(scenario_id, "result")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            import json
            return ScenarioRuntimeResult.model_validate(json.load(f))

    # ---- Lifecycle (status/provenance snapshot; storage-only) --------------- #
    def save_lifecycle(self, lifecycle: ScenarioLifecycle) -> None:
        data = lifecycle.model_dump(mode="json")
        guarded_dump_json(self._boundary, self._path(lifecycle.scenario.scenario_id, "lifecycle"), data,
                          mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
                          capability_id="scenario.persist", target="fs")

    def get_lifecycle(self, scenario_id: str) -> Optional[ScenarioLifecycle]:
        path = self._path(scenario_id, "lifecycle")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            import json
            return ScenarioLifecycle.model_validate(json.load(f))

    # ---- Human Decision (record-only; storage-only) ------------------------ #
    def save_decision(self, decision: ScenarioDecision) -> None:
        data = decision.model_dump(mode="json")
        guarded_dump_json(self._boundary, self._path(decision.scenario_id, "decision"), data,
                          mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
                          capability_id="scenario.persist", target="fs")

    def get_decision(self, scenario_id: str) -> Optional[ScenarioDecision]:
        path = self._path(scenario_id, "decision")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            import json
            return ScenarioDecision.model_validate(json.load(f))

    def list_decisions(self) -> List[ScenarioDecision]:
        """Return all recorded decisions (audit trail), oldest first."""
        import glob
        decisions = []
        for path in sorted(glob.glob(os.path.join(self.storage_dir, "*.decision.json"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    import json
                    decisions.append(ScenarioDecision.model_validate(json.load(f)))
            except Exception:
                pass  # skip corrupt/tampered records (fail-closed on read via get_decision)
        return decisions

    # ---- Governed Execution (real action record; storage-only) ------------- #
    def save_execution(self, execution: ScenarioExecution) -> None:
        data = execution.model_dump(mode="json")
        guarded_dump_json(self._boundary, self._path(execution.scenario_id, "execution"), data,
                          mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
                          capability_id="scenario.persist", target="fs")

    def get_execution(self, scenario_id: str) -> Optional[ScenarioExecution]:
        path = self._path(scenario_id, "execution")
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            import json
            return ScenarioExecution.model_validate(json.load(f))

    def list_executions(self) -> List[ScenarioExecution]:
        """Return all recorded executions (execution audit trail), oldest first."""
        import glob
        executions = []
        for path in sorted(glob.glob(os.path.join(self.storage_dir, "*.execution.json"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    import json
                    executions.append(ScenarioExecution.model_validate(json.load(f)))
            except Exception:
                pass  # skip corrupt/tampered records (fail-closed on read via get_execution)
        return executions
