"""EUREKA 5.1 — Multi-scenario Result Comparison (evidence aggregation, NOT decision authority).

Aggregates a set of persisted `ScenarioRuntimeResult`s into an explicit, NON_CANONICAL
`ScenarioComparisonResult`. This is read-only evidence for a human decision. It NEVER:
recommends, ranks-by-best, promotes, executes, or converts any hypothetical result to canonical.

Fail-closed on: empty/duplicate ids, missing scenario/result, scenario/result mismatch,
incomparable source identities, and any persisted result carrying canonical authority/scope/status.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from .scenario_repository import ScenarioRepository
from .scenario_foundation import Scenario
from .scenario_runtime import ScenarioRuntimeResult
from .projected_artifact import ArtifactScope, AuthorityClass, CanonicalStatus


class ScenarioComparisonEntry(BaseModel):
    scenario_id: str
    source_state_identity: str
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)
    authority: str = AuthorityClass.PROJECTED.value
    scope: str = ArtifactScope.SCENARIO.value
    canonical_status: str = CanonicalStatus.NON_CANONICAL.value
    provenance: List[str] = Field(default_factory=list)


class MetricDelta(BaseModel):
    metric: str
    scenario_id: str
    value: Optional[float] = None
    baseline_value: Optional[float] = None
    absolute_delta: Optional[float] = None
    relative_delta: Optional[float] = None


class ScenarioComparisonResult(BaseModel):
    comparison_id: str
    scenario_ids: List[str]
    source_state_identity: str
    scenarios: List[ScenarioComparisonEntry] = Field(default_factory=list)
    metric_comparisons: List[MetricDelta] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    scope: str = ArtifactScope.SCENARIO.value
    authority: str = AuthorityClass.PROJECTED.value
    canonical_status: str = CanonicalStatus.NON_CANONICAL.value

    @field_validator("scope")
    @classmethod
    def _scope(cls, v: str) -> str:
        if v != ArtifactScope.SCENARIO.value:
            raise ValueError("comparison must remain SCENARIO (non-canonical)")
        return v

    @field_validator("authority")
    @classmethod
    def _authority(cls, v: str) -> str:
        if v != AuthorityClass.PROJECTED.value:
            raise ValueError("comparison must remain PROJECTED (non-canonical)")
        return v


def _metrics_of(result: ScenarioRuntimeResult) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for pa in result.projected_artifacts:
        for k, v in pa.payload.items():
            if isinstance(v, (int, float)):
                out[k] = float(v)
    return out


def compare_results(repository: ScenarioRepository, scenario_ids: List[str],
                    baseline_scenario_id: Optional[str] = None) -> ScenarioComparisonResult:
    """Aggregate persisted results for the requested scenarios (input order). Read-only."""
    if not scenario_ids:
        raise ValueError("EMPTY_SCENARIO_IDS")
    if len(set(scenario_ids)) != len(scenario_ids):
        raise ValueError("DUPLICATE_SCENARIO_IDS")

    entries: List[ScenarioComparisonEntry] = []
    source_identity: Optional[str] = None

    for sid in scenario_ids:
        sc: Optional[Scenario] = repository.get_scenario(sid)
        if sc is None:
            raise ValueError(f"SCENARIO_NOT_FOUND:{sid}")
        res: Optional[ScenarioRuntimeResult] = repository.get_result(sid)
        if res is None:
            raise ValueError(f"RESULT_NOT_FOUND:{sid}")
        # integrity + authority (fail closed, never correct a persisted authority)
        if res.scenario_id != sid or res.source_state_identity != sc.source_state_identity:
            raise ValueError(f"RESULT_MISMATCH:{sid}")
        if res.scope != ArtifactScope.SCENARIO or res.authority != AuthorityClass.PROJECTED \
                or res.canonical_status != CanonicalStatus.NON_CANONICAL:
            raise ValueError(f"NON_CANONICAL_VIOLATION:{sid}")
        if source_identity is None:
            source_identity = res.source_state_identity
        elif res.source_state_identity != source_identity:
            raise ValueError("INCOMPARABLE_SOURCE_STATE")
        entries.append(ScenarioComparisonEntry(
            scenario_id=sid, source_state_identity=res.source_state_identity,
            assumptions=sc.assumptions, metrics=_metrics_of(res),
            provenance=list(res.provenance),
        ))

    metric_names = sorted({k for e in entries for k in e.metrics})
    base = next((e for e in entries if e.scenario_id == baseline_scenario_id), None)
    deltas: List[MetricDelta] = []
    for name in metric_names:
        for e in entries:
            val = e.metrics.get(name)
            bval = base.metrics.get(name) if (base and name in base.metrics) else None
            abs_delta = (val - bval) if (val is not None and bval is not None) else None
            rel_delta = (abs_delta / bval) if (abs_delta is not None and bval) else None
            deltas.append(MetricDelta(metric=name, scenario_id=e.scenario_id, value=val,
                                      baseline_value=bval, absolute_delta=abs_delta,
                                      relative_delta=rel_delta))

    return ScenarioComparisonResult(
        comparison_id=f"CMP-{uuid.uuid4().hex[:8]}",
        scenario_ids=list(scenario_ids),
        source_state_identity=source_identity or "UNKNOWN",
        scenarios=entries,
        metric_comparisons=deltas,
        provenance=["scenario-comparison"] + [f"scenario:{sid}" for sid in scenario_ids],
        governance={"read_only": True, "non_canonical": True},
    )
