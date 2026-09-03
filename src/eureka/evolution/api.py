"""FastAPI router exposing the supervised evolution loop.

Endpoints let a human drive the HITL gate from the web: propose a single
variant, list history/pending, approve (optionally applying a real, reversible
ACFL weight change to a live EUREKA work), or reject. Every state change is
recorded in the versioned ledger.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException

from .proposal import EvolutionProposal
from .ledger import EvolutionLedger
from .hitl_gate import EvolutionHITLGate, GateError
from .loop_driver import ACFLWeightExecutor, ACFLSignalMeasurer, EvolutionError


def create_evolution_api(
    works_db: Dict[str, Any],
    ledger_path: str = "data/evolution/ledger.ndjson",
    work_provider: Optional[Callable[[str], Any]] = None,
) -> APIRouter:
    router = APIRouter(prefix="/api/evolution", tags=["evolution"])
    ledger = EvolutionLedger(ledger_path)
    gate = EvolutionHITLGate(ledger)

    def _state(work_id: str):
        state = work_provider(work_id) if work_provider else works_db.get(work_id)
        return state

    @router.get("/pending")
    def pending():
        return {"pending": gate.pending()}

    @router.get("/history")
    def history():
        # One entry per proposal, with the EFFECTIVE status (from the latest STATUS
        # record) and its measured outcomes, so the UI can show real evolution state.
        versions = []
        for p in ledger.proposals():
            v = p["version"]
            versions.append({
                "version": v,
                "proposal": p["proposal"],
                "status": ledger.status_of(v),
                "created_at": p.get("created_at"),
                "outcomes": ledger.outcomes(v),
            })
        return {"history": versions}

    @router.get("/{version}")
    def get_one(version: str):
        entry = ledger.get(version)
        if entry is None:
            raise HTTPException(status_code=404, detail=f"Variante '{version}' no existe.")
        return {
            "proposal": entry,
            "status": ledger.status_of(version),
            "outcomes": ledger.outcomes(version),
        }

    @router.post("/propose")
    def propose(payload: Dict[str, Any]):
        try:
            proposal = EvolutionProposal(**payload)
            entry = gate.propose(proposal)
        except (ValueError, GateError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"entry": entry}

    @router.post("/{version}/approve")
    def approve(version: str, apply_work_id: Optional[str] = None):
        try:
            gate.approve(version, note="aprobado por humano vía API")
        except GateError as e:
            raise HTTPException(status_code=400, detail=str(e))

        out: Dict[str, Any] = {"version": version, "status": "APPROVED"}
        if apply_work_id:
            state = _state(apply_work_id)
            if state is None:
                raise HTTPException(status_code=404, detail=f"Work '{apply_work_id}' no encontrado.")
            entry = gate.ledger.get(version)
            if entry is None:
                raise HTTPException(status_code=404, detail=f"Variante '{version}' no existe.")
            proposal = EvolutionProposal(**entry["proposal"])
            weights = (proposal.capa_fuzzy or {}).get("weights")
            if isinstance(weights, dict) and weights:
                try:
                    gate.apply(version, note="ejecución aprobada por humano")
                    applied = ACFLWeightExecutor(lambda: state).apply(proposal, version)
                    metrics = ACFLSignalMeasurer(lambda: state).measure(version, applied)
                    gate.measure(version, metrics, note="medición real del estado de EUREKA")
                    out = {"version": version, "status": "MEASURED", "applied": applied, "metrics": metrics}
                except (GateError, EvolutionError) as e:
                    raise HTTPException(status_code=400, detail=str(e))
            else:
                out["note"] = "aprobada sin acción aplicable (capa_fuzzy.weights ausente)"
        return out

    @router.post("/{version}/reject")
    def reject(version: str):
        try:
            gate.reject(version, note="rechazado por humano vía API")
        except GateError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"version": version, "status": "REJECTED"}

    return router
