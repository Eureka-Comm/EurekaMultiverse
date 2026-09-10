"""EUREKA 5.1 — Scenario Runtime Transport / API Surface (thin, governed, now persisted).

A thin FastAPI adapter over ``ScenarioService`` (+ bounded ``ScenarioRepository``). Transport is
limited to parse + validate the HTTP shape -> build the canonical domain input -> call
``ScenarioService`` -> serialize. No business logic, no ScenarioRuntime/EffectBoundary/ACFL access,
no persistence invention beyond the file-backed JSON repository, no canonical escalation.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .work_model import EurekaWork
from .canonical_state import CanonicalWorkState
from .scenario_service import ScenarioService
from .scenario_repository import ScenarioRepository
from .scenario_lifecycle import LifecycleTransitionError
from .scenario_decision import ScenarioDecision, DecisionType
from .scenario_execution import ScenarioExecution
from .scenario_observability import AuditProjection


# --------------------------------------------------------------------------- # request models
class WorkInput(BaseModel):
    work_id: str
    title: str
    user_intent: str
    task_category: str = "UNKNOWN"
    problem_statement: str = ""
    acfl_weights: Dict[str, float] = Field(default_factory=lambda: {"cost": 50.0, "risk": 50.0})


class WhatIfRequest(BaseModel):
    scenario_id: str = "SCN-1"
    work: Optional[WorkInput] = None
    work_id: Optional[str] = None
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectRequest(BaseModel):
    work: WorkInput
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)


class CompareRequest(BaseModel):
    scenario_ids: List[str] = Field(default_factory=list)
    baseline_scenario_id: Optional[str] = None


class DecisionRequest(BaseModel):
    # the HUMAN's own inputs only. authority/scope/canonical_status/source_state_identity are derived
    # server-side (never accepted from the client).
    work_id: Optional[str] = None
    work: Optional[WorkInput] = None
    decision_type: DecisionType = DecisionType.CONFIRM
    rationale: str = ""
    human_actor: str = "human"
    selected_artifact_id: Optional[str] = None


class ExecutionRequest(BaseModel):
    # minimal: only the SOURCE reference. The server resolves decision/action/authority/provenance.
    # No authority/execute/promote fields here — the client cannot claim execution authority.
    work_id: Optional[str] = None
    work: Optional[WorkInput] = None


class CompareResponse(BaseModel):
    comparison_id: str
    scenario_ids: List[str]
    source_state_identity: str
    scope: str
    authority: str
    canonical_status: str
    scenarios: List[Dict[str, Any]] = Field(default_factory=list)
    metric_comparisons: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- # response models
class ProjectedArtifactOut(BaseModel):
    artifact_id: str
    artifact_kind: str
    source_state_identity: str
    scope: str
    authority: str
    canonical_status: str
    provenance: List[str] = Field(default_factory=list)
    payload: Dict[str, Any] = Field(default_factory=dict)


class WhatIfResponse(BaseModel):
    scenario_id: str
    source_state_identity: str
    scope: str
    authority: str
    canonical_status: str
    status: str
    provenance: List[str] = Field(default_factory=list)
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)
    projected_artifacts: List[ProjectedArtifactOut] = Field(default_factory=list)


class ScenarioOut(BaseModel):
    scenario_id: str
    source_state_identity: str
    scope: str
    status: str
    assumptions: List[Dict[str, Any]] = Field(default_factory=list)
    provenance: List[str] = Field(default_factory=list)
    governance: Dict[str, Any] = Field(default_factory=dict)


class ScenarioDecisionOut(BaseModel):
    decision_id: str
    scenario_id: str
    lifecycle_state: str
    decision_type: str
    selected_artifact_id: Optional[str] = None
    rationale: str = ""
    human_actor: str = "human"
    scope: str
    authority: str
    canonical_status: str
    source_state_identity: str
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""
    status: str = "RECORDED"


class ScenarioExecutionOut(BaseModel):
    execution_id: str
    scenario_id: str
    decision_id: str
    action_id: str
    source_state_identity: str
    status: str
    scope: str
    authority: str
    canonical_status: str
    governance: Dict[str, Any] = Field(default_factory=dict)
    effect: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[str] = Field(default_factory=list)
    created_at: str = ""


# --------------------------------------------------------------------------- # adapters
def _to_source(work: WorkInput) -> CanonicalWorkState:
    state = CanonicalWorkState(work=EurekaWork(
        work_id=work.work_id, title=work.title, user_intent=work.user_intent,
        task_category=work.task_category, problem_statement=work.problem_statement))
    state.acfl.weights = dict(work.acfl_weights)
    return state


def _to_response(result) -> WhatIfResponse:
    return WhatIfResponse(
        scenario_id=result.scenario_id,
        source_state_identity=result.source_state_identity,
        scope=result.scope.value,
        authority=result.authority.value,
        canonical_status=result.canonical_status.value,
        status=result.status.value,
        provenance=list(result.provenance),
        assumptions=[],
        governance=dict(result.governance),
        projected_artifacts=[
            ProjectedArtifactOut(
                artifact_id=a.artifact_id, artifact_kind=a.artifact_kind,
                source_state_identity=a.source_state_identity, scope=a.scope.value,
                authority=a.authority.value, canonical_status=a.canonical_status.value,
                provenance=list(a.provenance), payload=dict(a.payload),
            ) for a in result.projected_artifacts
        ],
    )


def _to_decision_out(d: ScenarioDecision) -> ScenarioDecisionOut:
    return ScenarioDecisionOut(
        decision_id=d.decision_id, scenario_id=d.scenario_id, lifecycle_state=d.lifecycle_state,
        decision_type=d.decision_type.value, selected_artifact_id=d.selected_artifact_id,
        rationale=d.rationale, human_actor=d.human_actor,
        scope=d.scope.value, authority=d.authority.value, canonical_status=d.canonical_status.value,
        source_state_identity=d.source_state_identity, provenance=list(d.provenance),
        created_at=d.created_at, status=d.status,
    )


def _to_execution_out(e: ScenarioExecution) -> ScenarioExecutionOut:
    return ScenarioExecutionOut(
        execution_id=e.execution_id, scenario_id=e.scenario_id, decision_id=e.decision_id,
        action_id=e.action_id, source_state_identity=e.source_state_identity, status=e.status.value,
        scope=e.scope.value, authority=e.authority.value, canonical_status=e.canonical_status.value,
        governance=dict(e.governance), effect=dict(e.effect),
        provenance=list(e.provenance), created_at=e.created_at,
    )


# --------------------------------------------------------------------------- # router factory
def make_router(service: ScenarioService, work_resolver=None) -> APIRouter:
    router = APIRouter(prefix="/scenario", tags=["scenario"])

    def _handle(default: Exception, status: int = 409) -> HTTPException:
        if isinstance(default, LifecycleTransitionError):
            return HTTPException(status_code=409, detail={"error": "INVALID_TRANSITION", "message": str(default)})
        return HTTPException(status_code=status, detail={"error": str(default)})

    def _resolve_source(req) -> CanonicalWorkState:
        """Resolve the canonical source state. When ``work_id`` is given, the REAL canonical work
        is retrieved server-side (existing authority). The client NEVER supplies authority."""
        if getattr(req, "work_id", None):
            if not work_resolver:
                raise HTTPException(status_code=422, detail={"error": "WORK_RESOLUTION_UNAVAILABLE"})
            state = work_resolver(req.work_id)
            if state is None:
                raise HTTPException(status_code=404, detail={"error": "WORK_NOT_FOUND"})
            return state
        if getattr(req, "work", None) is not None:
            return _to_source(req.work)
        raise HTTPException(status_code=422, detail={"error": "WORK_OR_WORK_ID_REQUIRED"})

    def _decision_error(err: Exception) -> HTTPException:
        # an HTTPException raised earlier (e.g. WORK_NOT_FOUND / WORK_OR_WORK_ID_REQUIRED) propagates
        # unchanged — do NOT fold it into a generic 409.
        if isinstance(err, HTTPException):
            return err
        msg = str(err)
        if msg.startswith("SCENARIO_NOT_FOUND"):
            return HTTPException(status_code=404, detail={"error": msg})
        if msg.startswith("DECISION_NOT_FOUND"):
            return HTTPException(status_code=404, detail={"error": msg})
        if isinstance(err, LifecycleTransitionError):
            return HTTPException(status_code=409, detail={"error": "INVALID_TRANSITION", "message": msg})
        if msg.startswith("REPOSITORY_NOT_CONFIGURED"):
            return HTTPException(status_code=409, detail={"error": msg})
        return _handle(err)

    @router.post("/whatif", response_model=WhatIfResponse)
    def run_whatif(req: WhatIfRequest):
        try:
            source = _resolve_source(req)
            result = service.run_whatif(source, scenario_id=req.scenario_id,
                                        assumptions=req.assumptions)
            return _to_response(result)
        except (RuntimeError, LifecycleTransitionError) as err:
            raise _handle(err)

    @router.get("/decisions", response_model=List[ScenarioDecisionOut])
    def list_decisions():
        try:
            return [_to_decision_out(d) for d in service.list_decisions()]
        except Exception as err:
            raise _decision_error(err)

    @router.get("/executions", response_model=List[ScenarioExecutionOut])
    def list_executions():
        try:
            return [_to_execution_out(e) for e in service.list_executions()]
        except Exception as err:
            raise _decision_error(err)

    @router.get("/{scenario_id}", response_model=ScenarioOut)
    def get_scenario(scenario_id: str):
        sc = service.get_scenario(scenario_id)
        if sc is None:
            raise HTTPException(status_code=404, detail={"error": "SCENARIO_NOT_FOUND"})
        return ScenarioOut(scenario_id=sc.scenario_id, source_state_identity=sc.source_state_identity,
                           scope=sc.scope.value, status=sc.status.value,
                           assumptions=list(sc.assumptions), provenance=list(sc.provenance),
                           governance=dict(sc.governance))

    @router.post("/{scenario_id}/project", response_model=WhatIfResponse)
    def project(scenario_id: str, req: ProjectRequest):
        sc = service.get_scenario(scenario_id)
        if sc is None:
            raise HTTPException(status_code=404, detail={"error": "SCENARIO_NOT_FOUND"})
        try:
            result = service.reproject(sc, _to_source(req.work))
            return _to_response(result)
        except (RuntimeError, LifecycleTransitionError) as err:
            raise _handle(err)

    @router.get("/{scenario_id}/result", response_model=WhatIfResponse)
    def get_result(scenario_id: str):
        result = service.get_result(scenario_id)
        if result is None:
            raise HTTPException(status_code=404, detail={"error": "RESULT_NOT_FOUND"})
        return _to_response(result)

    @router.post("/compare", response_model=CompareResponse)
    def compare(req: CompareRequest):
        try:
            cmp = service.compare(req.scenario_ids, req.baseline_scenario_id)
            return CompareResponse(
                comparison_id=cmp.comparison_id,
                scenario_ids=list(cmp.scenario_ids),
                source_state_identity=cmp.source_state_identity,
                scope=cmp.scope, authority=cmp.authority, canonical_status=cmp.canonical_status,
                scenarios=[e.model_dump(mode="json") for e in cmp.scenarios],
                metric_comparisons=[d.model_dump(mode="json") for d in cmp.metric_comparisons],
                provenance=list(cmp.provenance),
            )
        except ValueError as err:
            msg = str(err)
            if msg.startswith("SCENARIO_NOT_FOUND"):
                raise HTTPException(status_code=404, detail={"error": msg})
            if msg.startswith("INCOMPARABLE_SOURCE_STATE"):
                raise HTTPException(status_code=409, detail={"error": msg})
            if msg.startswith("EMPTY_SCENARIO_IDS") or msg.startswith("DUPLICATE_SCENARIO_IDS"):
                raise HTTPException(status_code=422, detail={"error": msg})
            raise HTTPException(status_code=409, detail={"error": msg})
        except RuntimeError as err:
            raise HTTPException(status_code=409, detail={"error": str(err)})

    @router.post("/{scenario_id}/authorize", response_model=ScenarioDecisionOut)
    def authorize(scenario_id: str, req: DecisionRequest):
        # RECORD-ONLY human decision: REVIEW -> AUTHORIZED. Never executes/promotes/canonicalizes.
        try:
            source = _resolve_source(req)
            d = service.authorize_scenario(scenario_id, source, req.decision_type,
                                           rationale=req.rationale, human_actor=req.human_actor,
                                           selected_artifact_id=req.selected_artifact_id)
            return _to_decision_out(d)
        except Exception as err:
            raise _decision_error(err)

    @router.post("/{scenario_id}/discard", response_model=ScenarioDecisionOut)
    def discard(scenario_id: str, req: DecisionRequest):
        # RECORD-ONLY human decision: REVIEW -> DISCARDED. Never executes/promotes/canonicalizes.
        try:
            source = _resolve_source(req)
            d = service.discard_scenario(scenario_id, source, req.decision_type,
                                         rationale=req.rationale, human_actor=req.human_actor,
                                         selected_artifact_id=req.selected_artifact_id)
            return _to_decision_out(d)
        except Exception as err:
            raise _decision_error(err)

    @router.get("/{scenario_id}/decision", response_model=ScenarioDecisionOut)
    def get_decision(scenario_id: str):
        try:
            d = service.get_decision(scenario_id)
            if d is None:
                raise HTTPException(status_code=404, detail={"error": "DECISION_NOT_FOUND"})
            return _to_decision_out(d)
        except Exception as err:
            raise _decision_error(err)

    @router.post("/{scenario_id}/execute", response_model=ScenarioExecutionOut)
    def execute(scenario_id: str, req: ExecutionRequest):
        # REAL_EXECUTION of the single action a recorded decision authorizes. The server resolves the
        # decision/action/authority/provenance and crosses Q4; the client only names the source.
        try:
            source = _resolve_source(req)
            execution = service.execute_authorized(scenario_id, source)
            if execution.status.value == "SUCCEEDED":
                return _to_execution_out(execution)
            # REJECTED / FAILED -> fail-closed (never a false success)
            raise HTTPException(status_code=409, detail={
                "error": execution.governance.get("reason_code", execution.status.value),
                "message": execution.governance.get("message", ""),
                "execution": _to_execution_out(execution).model_dump(mode="json"),
            })
        except HTTPException:
            raise
        except Exception as err:
            raise _decision_error(err)

    @router.get("/{scenario_id}/execution", response_model=ScenarioExecutionOut)
    def get_execution(scenario_id: str):
        try:
            e = service.get_execution(scenario_id)
            if e is None:
                raise HTTPException(status_code=404, detail={"error": "EXECUTION_NOT_FOUND"})
            return _to_execution_out(e)
        except Exception as err:
            raise _decision_error(err)

    @router.get("/{scenario_id}/audit", response_model=AuditProjection)
    def get_audit(scenario_id: str, work_id: Optional[str] = None):
        # READ-ONLY observability projection (never writes / mutates / authorizes).
        try:
            return service.audit(scenario_id, work_id, work_resolver=work_resolver)
        except ValueError as err:
            msg = str(err)
            if msg.startswith("SCENARIO_NOT_FOUND"):
                raise HTTPException(status_code=404, detail={"error": msg})
            raise _decision_error(err)
        except Exception as err:
            raise _decision_error(err)

    return router


def build_app(storage_dir: str = "data/scenarios") -> FastAPI:
    service = ScenarioService(repository=ScenarioRepository(storage_dir))
    app = FastAPI(title="EUREKA Scenario Runtime", version="0.2")
    app.include_router(make_router(service))
    return app
