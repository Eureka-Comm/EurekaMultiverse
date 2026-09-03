"""Evolution loop driver: PERCEBE -> RAZONA (capas 1-4) -> PROPONE -> GATE -> EJECUTA & MIDE -> REGISTRA.

The loop never applies a change on its own: it proposes a single versioned
variant and stops at the human gate. Only after a human approves does
`on_approve` execute + measure + log, so every recorded version carries a real,
attributable outcome.

Execution is deliberately scoped to reversible, real EUREKA knobs (ACFL weights /
feasible_only). Arbitrary code-generation from an LLM proposal is intentionally
NOT wired here — per the hard limits, that requires per-proposal explicit
approval and is a separate concern.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

from .hitl_gate import EvolutionHITLGate
from .proposal import EvolutionProposal, validate_single_variant
from .prompt_base import ORCHESTRATOR_SYSTEM_PROMPT, build_perception_input, render_perception


class EvolutionError(Exception):
    """Raised when the loop cannot proceed (e.g. a malformed reasoner output)."""


# --- Reasoner -------------------------------------------------------------- #
class StubReasoner:
    """Deterministic reasoner for tests; returns a fixed proposal."""

    def __init__(self, proposal: EvolutionProposal):
        self.proposal = proposal

    def reason(self, perception: Dict[str, Any]) -> EvolutionProposal:
        out = self.proposal.model_copy(deep=True)
        out.capa_percepcion = perception
        return out


class DeepSeekReasoner:
    """Production reasoner: calls the orchestrator prompt and parses the proposal JSON.

    `complete_fn(messages: List[Dict[str,str]]) -> str` is injected so the harness
    stays decoupled from a concrete provider. It must return the proposal JSON
    object following the orchestrator template.
    """

    def __init__(self, complete_fn: Callable[[List[Dict[str, str]]], str]):
        self.complete_fn = complete_fn

    def reason(self, perception: Dict[str, Any]) -> EvolutionProposal:
        user = (
            "PERCEPCIÓN ACTUAL (capa 1, sin interpretar):\n" + render_perception(perception) +
            "\n\nRazona en capas (1-4) y propón EXACTAMENTE UNA variante de mejora. "
            "Devuelve únicamente el objeto JSON de la plantilla de propuesta."
        )
        raw = self.complete_fn([
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ])
        return self._parse(raw)

    def _parse(self, raw: str) -> EvolutionProposal:
        text = raw.strip()
        # Tolerate code fences.
        if text.startswith("```"):
            text = text.split("```")[1] if "```" in text[3:] else text
            text = text.lstrip("json").strip()
        obj = json.loads(text)
        return EvolutionProposal(**obj)


# --- Executor / measurer (real, reversible EUREKA knobs) ------------------- #
class ACFLWeightExecutor:
    """Applies a real, reversible ACFL weight change to a EUREKA canonical state."""

    def __init__(self, state_provider: Callable[[], Any]):
        self.state_provider = state_provider

    def apply(self, proposal: EvolutionProposal, version: str) -> Dict[str, Any]:
        state = self.state_provider()
        fuzzy = proposal.capa_fuzzy or {}
        new_weights = fuzzy.get("weights")
        if not isinstance(new_weights, dict) or not new_weights:
            raise EvolutionError(
                "La propuesta no trae capa_fuzzy.weights aplicable; no se aplica ningún cambio real."
            )
        before = dict(getattr(state.acfl, "weights", {}) or {})
        state.acfl.weights.update(new_weights)
        return {
            "applied": True,
            "version": version,
            "target": "acfl.weights",
            "weights_before": before,
            "weights_after": dict(state.acfl.weights),
        }


class ACFLSignalMeasurer:
    """Measures real signals from the EUREKA state after a change."""

    def __init__(self, state_provider: Callable[[], Any]):
        self.state_provider = state_provider

    def measure(self, version: str, applied: Dict[str, Any]) -> Dict[str, Any]:
        state = self.state_provider()
        acfl = getattr(state, "acfl", None) or {}
        return {
            "weights": dict(getattr(acfl, "weights", {}) or {}),
            "num_criteria": len(getattr(acfl, "criteria", []) or []),
            "num_alternatives": len(getattr(acfl, "alternatives", []) or [])
                               or len(getattr(acfl, "normalized_scores", {}) or {}),
            "has_scores": bool(getattr(acfl, "normalized_scores", {}) or {}),
            "frontier": list(getattr(acfl, "frontier", []) or []),
        }


# --- Loop ------------------------------------------------------------------ #
class EvolutionLoop:
    """Coordinates the supervised cycle. Stops at the gate after PROPOSE."""

    def __init__(self, reasoner, gate: EvolutionHITLGate,
                 executor: Optional[Any] = None, measurer: Optional[Any] = None):
        self.reasoner = reasoner
        self.gate = gate
        self.executor = executor
        self.measurer = measurer

    def cycle(self, perception_raw: Dict[str, Any]) -> Dict[str, Any]:
        runs: List[Dict[str, Any]] = []
        perception = build_perception_input(perception_raw)

        # RAZONAR (capas 1-4): produce UNA propuesta.
        proposal = self.reasoner.reason(perception)
        if not isinstance(proposal, EvolutionProposal):
            raise EvolutionError("El reasoner debe devolver un EvolutionProposal.")
        # Cap 5: asegura una sola variante (nunca cinco a la vez).
        validate_single_variant([proposal])
        proposal.capa_percepcion = perception

        # PROPONER: entra al gate humano.
        return self.gate.propose(proposal)

    def on_approve(self, version: str, perception_raw: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """After human approval: EJECUTAR -> MEDIR -> REGISTRAR (both real and reversible)."""
        if self.executor is None:
            raise EvolutionError("No se configuró executor; no se ejecuta ningún cambio.")
        if self.measurer is None:
            raise EvolutionError("No se configuró measurer; no se puede medir.")

        proposal_entry = self.gate.ledger.get(version)
        if proposal_entry is None:
            raise EvolutionError(f"Variante '{version}' no encontrada.")
        proposal = EvolutionProposal(**proposal_entry["proposal"])

        self.gate.apply(version, note="ejecución aprobada por humano")
        applied = self.executor.apply(proposal, version)
        metrics = self.measurer.measure(version, applied)
        self.gate.measure(version, metrics, note="medición real del estado de EUREKA")
        return {"version": version, "applied": applied, "metrics": metrics}
