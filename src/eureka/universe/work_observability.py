"""EUREKA 5.1 — Read-only CANONICAL work observability projection.

Composes, from the EXISTING authorities (WorkStore + EM Publisher + publication consumption), a single
READ-ONLY view of the canonical chain: WORK → EXECUTION → RESULT → PUBLISH → PUBLISHED ARTIFACT →
INTEGRITY VERIFICATION → CURRENT / HISTORICAL.

It is a READ MODEL only:
- never writes, never mutates the canonical, never executes/authorizes/publishes/freezes;
- every stage is tagged RECORDED / DERIVED / NOT_RECORDED (honest absence, never invented);
- the canonical identity is Q2 (`canonical_state_fingerprint`), the publication identity is the reused
  `_freeze_signature`; nothing new is made an authority;
- a `TAMPERED` artifact is reported as NOT trustworthy; a `HISTORICAL` artifact is reported as VALID
  historical evidence (NOT corrupt). These are distinct properties.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .canonical_identity import canonical_state_fingerprint
from .publication_consumption import build_publication_consumption
from .work_store import CorruptWorkError


# The CONTRACTUAL cognitive pipeline: the EM architecture order EUREKA defines. This is a READ-ONLY
# architectural constant (contract), NOT observed data. The OBSERVED pipeline (em_pipeline statuses +
# cognitive_trace) is derived from the real canonical state and may differ (NOT_OBSERVED stages).
CONTRACTUAL_PIPELINE = [
    "EM Core", "EM Structurer", "EM Descriptor", "EM Predictor",
    "EM Prescriptor", "EM Actioner", "EM Installer", "EM Publisher",
]


class WorkAuditStage(BaseModel):
    stage: str                                  # WORK / EXECUTION / RESULT / PUBLISH / CONSUMPTION
    status: str                                 # RECORDED / DERIVED / NOT_RECORDED
    authority: str = "CANONICAL"
    details: Dict[str, Any] = Field(default_factory=dict)
    provenance: List[str] = Field(default_factory=list)


class WorkAuditProjection(BaseModel):
    work_id: str
    canonical_state_identity: str               # Q2 fingerprint (server-derived, not client)
    revision: Optional[int] = None
    status: Optional[str] = None
    stages: List[WorkAuditStage] = Field(default_factory=list)
    execution: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    publication: Optional[Dict[str, Any]] = None
    consumption: Optional[Dict[str, Any]] = None
    # COGNITIVE OBSERVATORY (read-only, derived from real canonical state):
    contractual_pipeline: List[str] = Field(default_factory=list)   # CONTRACTUAL EM order (constant)
    em_pipeline: List[Dict[str, Any]] = Field(default_factory=list)  # OBSERVED per-EM statuses
    cognitive_trace: List[Dict[str, Any]] = Field(default_factory=list)  # runtime_metadata (provider/model/status/latency)
    provenance: List[str] = Field(default_factory=list)


def build_work_audit(works_db, publisher, work_id: str) -> WorkAuditProjection:
    """Assemble the read-only canonical work audit (fail-closed on unknown / corrupt work)."""
    try:
        known = work_id in works_db     # may raise CorruptWorkError (fail-closed, never silent)
    except CorruptWorkError as e:
        # A corrupt WorkStore record must NOT be silently treated as absent or fabricated. The
        # observatory reports it honestly as corrupt/unobservable (read-only, no invention).
        return WorkAuditProjection(
            work_id=work_id,
            canonical_state_identity="", status="CORRUPT",
            stages=[WorkAuditStage(stage="WORK", status="NOT_RECORDED", authority="CANONICAL",
                                   details={"corruption": str(e)},
                                   provenance=["work-authority", f"work_id:{work_id}"])],
            provenance=["work-authority", f"work_id:{work_id}", "corrupt"],
        )
    if not known:
        raise ValueError(f"WORK_NOT_FOUND:{work_id}")
    work = works_db[work_id]

    identity = canonical_state_fingerprint(work)
    execution = (work.execution_state.model_dump(mode="json") if work.execution_state else None)
    result = (work.result.model_dump(mode="json") if work.result else None)
    publication = None
    if work.publication_state:
        publication = {
            "publication_state": work.publication_state.model_dump(mode="json"),
            "frozen_result": (work.frozen_result.model_dump(mode="json") if work.frozen_result else None),
        }
    consumption = None
    if work.publication_state:
        consumption = build_publication_consumption(works_db, publisher, work_id)

    stages = [
        WorkAuditStage(stage="WORK", status="RECORDED", authority="CANONICAL",
                       details={"revision": getattr(work, "revision", None),
                                "status": getattr(work, "status", None)},
                       provenance=["work-authority", f"work_id:{work_id}"]),
        WorkAuditStage(stage="EXECUTION",
                       status="RECORDED" if execution else "NOT_RECORDED",
                       authority="CANONICAL",
                       details={"status": (work.execution_state.status if work.execution_state else None),
                                "result_status": (work.execution_state.result.status
                                                  if work.execution_state and work.execution_state.result else None)},
                       provenance=list(getattr(work.execution_state, "provenance", []) or [])),
        WorkAuditStage(stage="RESULT", status="RECORDED" if result else "NOT_RECORDED",
                       authority="CANONICAL", provenance=list(getattr(work.result, "provenance", []) or [])),
        WorkAuditStage(stage="PUBLISH",
                       status="RECORDED" if publication else "NOT_RECORDED",
                       authority="PUBLISHED",
                       details={"status": (work.publication_state.status if work.publication_state else None),
                                "publication_count": len(getattr(work.publication_state, "publications", []) or [])},
                       provenance=list(getattr(work.frozen_result, "provenance", []) or [])),
        WorkAuditStage(stage="CONSUMPTION",
                       status="RECORDED" if consumption and consumption.get("publication") else "NOT_RECORDED",
                       authority="OBSERVED",
                       details=(consumption.get("verification", {}) if consumption else {})),
    ]

    provenance = ["work-authority", f"work_id:{work_id}", f"source:{identity}"]
    if work.frozen_result:
        provenance += list(work.frozen_result.provenance or [])
    if work.publication_state:
        provenance += list(getattr(work.publication_state, "provenance", []) or [])

    return WorkAuditProjection(
        work_id=work_id,
        canonical_state_identity=identity,
        revision=getattr(work, "revision", None),
        status=getattr(work, "status", None),
        stages=stages,
        execution=execution,
        result=result,
        publication=publication,
        consumption={"verification": consumption.get("verification", {}),
                     "candidate_artifacts": consumption.get("candidate_artifacts", [])} if consumption else None,
        # COGNITIVE OBSERVATORY (real canonical state, read-only)
        contractual_pipeline=list(CONTRACTUAL_PIPELINE),
        em_pipeline=[e.model_dump(mode="json") for e in (getattr(work, "em_pipeline", None) or [])],
        cognitive_trace=[m.model_dump(mode="json") for m in (getattr(work, "runtime_metadata", None) or [])],
        provenance=provenance,
    )
