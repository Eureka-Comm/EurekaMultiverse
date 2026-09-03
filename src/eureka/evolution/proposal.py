"""Proposal schema for the supervised evolution loop.

Every proposed variant is an EvolutionProposal. The harness enforces two hard
rules derived from the orchestrator system prompt:

* ONE pending variant at a time (so we can attribute any measured change to a
  single variable, never five at once).
* `requiere_aprobacion_humana` is always True — no proposal becomes an action
  without explicit human approval (cap layer 5).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Literal, List, Optional

from pydantic import BaseModel, Field, field_validator


class ProposalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    MEASURED = "MEASURED"


LayerName = Literal["fuzzy", "estadistica", "cognitiva", "prompt_base"]


class EvolutionProposal(BaseModel):
    """One proposed evolution of the EUREKA engine.

    Fields follow the orchestrator's proposal template verbatim, plus harness
    metadata (id, version, status, timestamps) added by the ledger/gate.
    """

    # --- template fields ---
    version_propuesta: str = Field(..., description="Human-facing label, e.g. 'v2'.")
    capa_afectada: LayerName = Field(..., description="fuzzy | estadistica | cognitiva | prompt_base")
    cambio: str = Field(..., description="Concrete, minimal description of the change.")
    hipotesis: str = Field(..., description="Why this should improve the outcome.")
    metrica_a_observar: str = Field(..., description="The observable metric this variant targets.")
    riesgo: str = Field(..., description="What could break.")
    requiere_aprobacion_humana: bool = True

    # --- optional per-layer detail carried by the reasoner ---
    capa_percepcion: Optional[Dict[str, Any]] = None
    capa_fuzzy: Optional[Dict[str, Any]] = None
    capa_estadistica: Optional[Dict[str, Any]] = None
    capa_cognitiva: Optional[Dict[str, Any]] = None

    # --- harness metadata (managed by the ledger/gate, not by the reasoner) ---
    propuesta_id: Optional[str] = None
    version: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: str = ""
    approved_at: Optional[str] = None

    @field_validator("requiere_aprobacion_humana")
    @classmethod
    def _must_require_human(cls, v: bool) -> bool:
        # Cap layer 5 is a hard gate: no proposal may opt out of human review.
        if v is not None and not v:
            raise ValueError("requiere_aprobacion_humana must be True; the gate is non-negotiable.")
        return True

    @field_validator("cambio", "hipotesis", "metrica_a_observar", "riesgo")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty.")
        return v.strip()

    def stamp(self) -> "EvolutionProposal":
        """Add harness metadata (id + version + timestamp)."""
        if not self.propuesta_id:
            self.propuesta_id = f"PRP-{uuid.uuid4().hex[:8].upper()}"
        if not self.version:
            self.version = self.version_propuesta or f"v{1}"
        if not self.created_at:
            self.created_at = datetime.now().isoformat(timespec="seconds")
        return self


def validate_single_variant(proposals: List[EvolutionProposal]) -> None:
    """Reject a batch that proposes more than one variant at a time."""
    if proposals and len(proposals) > 1:
        raise ValueError(
            "Solo se puede probar UNA variante a la vez. Recibidas: "
            + ", ".join(p.version_propuesta for p in proposals)
        )
