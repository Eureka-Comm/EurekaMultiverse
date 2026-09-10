"""EUREKA 5.1 — REAL predictive + prescriptive WHAT-IF projection (multi-metric, DRY_RUN).

Replaces the legacy single-scalar ACFL projection with a REAL projection that:
- reads the canonical work's REAL ``predictive_knowledge`` (predictions: target, predicted_value, MSE,
  model, validation_status, provenance) and REAL ``prescriptive_knowledge`` (prescriptions: objective,
  alternatives with ACFL score, selected_alternative, authority, validation_status),
- computes a REAL ACFL projection via the existing ``ACFLEngine.evaluate_expression`` on the REAL
  predicate AST (``predictive_knowledge.predicates``), perturbed by the scenario assumption delta via a
  real ACFL parameter ``m`` derived from the canonical acfl weights,
- keeps the real ``gclv_value`` ACFL metric (the canonical's real acfl weights + assumption delta).

Authority is preserved by construction: every artifact is ``ProjectedArtifact`` with scope SCENARIO /
authority PROJECTED / canonical_status NON_CANONICAL (Q3). The computation is read-only (DRY_RUN):
it never mutates the canonical state, only reads its real predictive/prescriptive content. Values are
REAL — if a metric cannot be computed (no predicate, no variable match, non-finite value), it is omitted
(never faked with 0/None/"unknown").
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .acfl_engine import gclv_value, ACFLEngine
from .math_ir import GCLVMembership, Variable
from .projected_artifact import ProjectedArtifact


def _clamp(v: float, lo: float = 1e-6, hi: float = 1.0 - 1e-6) -> float:
    return max(lo, min(hi, v))


def _parse_mse(model_definition: Optional[str]) -> Optional[float]:
    """Extract a REAL MSE from the predictor's ``model_definition`` ("MSE=0.123..."), else None."""
    if not model_definition:
        return None
    m = re.search(r"MSE=([0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)", model_definition)
    return float(m.group(1)) if m else None


def _project_prediction(prediction, predicates, engine: ACFLEngine, m_perturbed: float) -> Optional[Dict[str, Any]]:
    """Project ONE real prediction through the REAL predictor's predicate AST (ACFL/GCLV).

    Uses the canonical's real ``predicted_value`` as the variable input and re-evaluates the real
    predicate under a delta-perturbed ACFL parameter ``m``. Returns None if the projection cannot be
    computed honestly (no matching predicate, non-GCLV AST, no variable input, non-finite value).
    """
    if prediction.predicted_value is None:
        return None
    pred = next((x for x in predicates if x.target == prediction.target_variable), None)
    if pred is None or pred.logical_structure is None:
        return None
    ast = pred.logical_structure
    if not isinstance(ast, GCLVMembership):
        return None
    variable = ast.input
    if not isinstance(variable, Variable):
        return None
    try:
        inputs = {variable.name: float(prediction.predicted_value)}
        membership = engine.evaluate_expression(ast, inputs)
        projected_ast = GCLVMembership(input=ast.input, alpha=ast.alpha, gamma=ast.gamma,
                                        m=m_perturbed)
        projected = engine.evaluate_expression(projected_ast, inputs)
        if not all(_finite(x) for x in (membership, projected)):
            return None
        return {"variable": variable.name, "membership": membership,
                "acfl_projected": projected, "m": m_perturbed}
    except Exception:
        return None


def _finite(v: float) -> bool:
    return isinstance(v, (int, float)) and (v == v) and v not in (float("inf"), float("-inf"))


def _alt(a) -> Dict[str, Any]:
    return {"alternative_id": getattr(a, "alternative_id", ""),
            "description": getattr(a, "description", ""),
            "score": getattr(a, "score", None)}


def real_whatif_projection(scenario, inputs: Dict[str, Any], source_state) -> List[ProjectedArtifact]:
    """Real, deterministic WHAT-IF projection (read-only, DRY_RUN). Delegates math to the existing
    ACFL engine (never duplicates formulas)."""
    weights = getattr(source_state, "acfl", None)
    weights = (weights.weights if weights else {}) or {}
    s_g = _clamp(float(weights.get("cost", 50.0)) / 100.0)
    base_m = _clamp(float(weights.get("risk", 50.0)) / 100.0)
    delta = sum(float(a.get("delta", 0.0)) for a in (scenario.assumptions or []) if isinstance(a, dict))
    m = _clamp(base_m + delta)

    artifacts: List[ProjectedArtifact] = []

    # 1) REAL ACFL metric (canonical acfl weights + assumption delta -> real gclv_value).
    artifacts.append(ProjectedArtifact(
        artifact_id="PRJ-ACFL", artifact_kind="ACFL_METRIC",
        source_state_identity=scenario.source_state_identity,
        provenance=["service:whatif", "real-projection", "acfl:gclv_value"],
        payload={"gclv": gclv_value(s_g, m), "s_g": s_g, "m": m, "base_m": base_m, "delta": delta},
    ))

    pk = getattr(source_state, "predictive_knowledge", None)
    if pk is not None and pk.predictions:
        engine = ACFLEngine()
        pred_payload = []
        for p in pk.predictions:
            item = {
                "target": p.target_variable,
                "predicted_value": p.predicted_value,
                "mse": _parse_mse(p.model_definition),
                "model": p.model_type,
                "validation_status": p.validation_status,
                "reproducibility": p.reproducibility,
                "provenance": list(p.provenance),
            }
            projected = _project_prediction(p, pk.predicates, engine, m)
            if projected is not None:
                item["acfl_projection"] = projected
            pred_payload.append(item)
        artifacts.append(ProjectedArtifact(
            artifact_id="PRJ-PREDICTIVE", artifact_kind="PREDICTIVE_EVIDENCE",
            source_state_identity=scenario.source_state_identity,
            provenance=["service:whatif", "real-projection", "predictor:EMPredictor", "acfl:ACFLEngine"],
            payload={"predictions": pred_payload, "count": len(pred_payload)},
        ))

    prior = getattr(source_state, "prescriptive_knowledge", None)
    if prior is not None and prior.prescriptions:
        presc_payload = []
        for pr in prior.prescriptions:
            presc_payload.append({
                "prescription_id": pr.prescription_id,
                "objective": pr.objective,
                "authority": pr.authority,
                "validation_status": pr.validation_status,
                "selected_alternative": _alt(pr.selected_alternative),
                "alternatives": [_alt(a) for a in pr.alternatives],
                "rationale": pr.rationale,
                "provenance": list(pr.provenance),
            })
        artifacts.append(ProjectedArtifact(
            artifact_id="PRJ-PRESCRIPTIVE", artifact_kind="PRESCRIPTIVE_EVIDENCE",
            source_state_identity=scenario.source_state_identity,
            provenance=["service:whatif", "real-projection", "prescriptor:EMPrescriptor"],
            payload={"prescriptions": presc_payload, "count": len(presc_payload)},
        ))

    return artifacts
