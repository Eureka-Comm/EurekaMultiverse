"""Human-in-the-loop gate for the evolution loop.

Cap layer 5: nothing becomes an action without explicit human approval. The
gate enforces ONE pending variant at a time (so changes are attributable), and
a proposal can only move PENDING -> APPROVED / REJECTED through the gate, never
by the loop itself.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .ledger import EvolutionLedger
from .proposal import EvolutionProposal, ProposalStatus


class GateError(Exception):
    """Raised when the HITL gate is violated (e.g. a second pending variant)."""


class EvolutionHITLGate:
    def __init__(self, ledger: EvolutionLedger):
        self.ledger = ledger

    def pending(self) -> List[Dict[str, Any]]:
        return self.ledger.pending()

    def propose(self, proposal: EvolutionProposal) -> Dict[str, Any]:
        """Submit a single variant for human approval. Fails if one is already pending."""
        if not isinstance(proposal, EvolutionProposal):
            proposal = EvolutionProposal(**proposal)
        pending = self.pending()
        if pending:
            raise GateError(
                f"Ya hay una variante pendiente de aprobación ({pending[0]['version']}). "
                "El ciclo permite UNA a la vez; aprueba o rechaza antes de proponer otra."
            )
        return self.ledger.register(proposal)

    def approve(self, version: str, note: str = "") -> Dict[str, Any]:
        """Human approves the pending variant.""" 
        self._require_pending(version)
        return self.ledger.set_status(version, ProposalStatus.APPROVED, note=note)

    def reject(self, version: str, note: str = "") -> Dict[str, Any]:
        """Human rejects the pending variant."""
        self._require_pending(version)
        return self.ledger.set_status(version, ProposalStatus.REJECTED, note=note)

    def apply(self, version: str, note: str = "") -> Dict[str, Any]:
        """Mark the (approved) variant as applied."""
        self._require_approved(version)
        return self.ledger.set_status(version, ProposalStatus.APPLIED, note=note)

    def measure(self, version: str, metrics: Dict[str, Any], note: str = "") -> Dict[str, Any]:
        """Record the real measured outcome for an applied variant."""
        self._require_applied(version)
        rec = self.ledger.record_outcome(version, metrics, note=note)
        self.ledger.set_status(version, ProposalStatus.MEASURED, note=note)
        return rec

    # ---- guards ---------------------------------------------------------- #
    def _require_pending(self, version: str) -> Dict[str, Any]:
        p = self.ledger.get(version)
        if p is None:
            raise GateError(f"Variante '{version}' no existe en el ledger.")
        if self.ledger.status_of(version) != ProposalStatus.PENDING.value:
            raise GateError(f"Variante '{version}' ya no está pendiente.")
        return p

    def _require_approved(self, version: str) -> Dict[str, Any]:
        p = self.ledger.get(version)
        if p is None:
            raise GateError(f"Variante '{version}' no existe en el ledger.")
        if self.ledger.status_of(version) != ProposalStatus.APPROVED.value:
            raise GateError(f"Variante '{version}' no está aprobada por el humano.")
        return p

    def _require_applied(self, version: str) -> Dict[str, Any]:
        p = self.ledger.get(version)
        if p is None:
            raise GateError(f"Variante '{version}' no existe en el ledger.")
        if self.ledger.status_of(version) != ProposalStatus.APPLIED.value:
            raise GateError(f"Variante '{version}' no está aplicada.")
        return p
