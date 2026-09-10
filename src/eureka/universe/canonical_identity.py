"""EUREKA 5.1 — Canonical source-state identity (Q2).

A single, deterministic content fingerprint for ``CanonicalWorkState``.

Identity model (distinct, confirmed against the canonical model):

- ``work_id``        = identity of the *work*  -> NOT part of content identity.
- ``schema_version`` = identity of the *schema* -> NOT part of content identity.
- ``revision``       = evolution/version *counter* -> NOT part of content identity.
- **content fingerprint** = exact *semantic content* identity (canonical outcomes).

This lets us claim: "This Scenario was constructed on exactly this canonical content", and to
detect a STALE source when the current canonical content differs from the saved identity.

The computation is PURE: it never mutates canonical state, never bumps revision, never writes.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Optional


def _dump(value: Any) -> Any:
    """Deterministic JSON-ready value (pydantic models -> dict, else passthrough)."""
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _payload(state) -> dict:
    """Canonical semantic content used for identity. Metadata/version/transient are EXCLUDED."""
    return {
        # work identity (excluded) & schema/revision (excluded) are deliberately omitted.
        "problem": _dump(getattr(state, "problem", None)),
        "knowledge": _dump(getattr(state, "knowledge", None)),
        "predictive_knowledge": _dump(getattr(state, "predictive_knowledge", None)),
        "prescriptive_knowledge": _dump(getattr(state, "prescriptive_knowledge", None)),
        "action_plan": _dump(getattr(state, "action_plan", None)),
        "execution_result": _dump(getattr(getattr(state, "execution_state", None), "result", None)),
        "result": _dump(getattr(state, "result", None)),
        "frozen_result": _dump(getattr(state, "frozen_result", None)),
        "human_decision": _dump(getattr(state, "human_decision", None)),
    }


META_KEYS = ("work_id", "revision", "schema_version")


def _strip_meta(obj):
    """Recursively remove identity-metadata keys (work_id/revision/schema_version) so the
    fingerprint reflects CONTENT, not work/schema/version identity."""
    if isinstance(obj, dict):
        return {k: _strip_meta(v) for k, v in obj.items() if k not in META_KEYS}
    if isinstance(obj, (list, tuple)):
        return [_strip_meta(x) for x in obj]
    return obj


def canonical_state_fingerprint(state) -> str:
    """Deterministic SHA-256 of the canonical semantic content (pure, no mutation)."""
    data = json.dumps(_strip_meta(_payload(state)), sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compare_source_identity(saved_identity: Optional[str], current_state) -> str:
    """Return ``"MATCH"`` if the current state's content identity equals the saved one,
    else ``"STALE"``."""
    current = canonical_state_fingerprint(current_state)
    if saved_identity is None or current != saved_identity:
        return "STALE"
    return "MATCH"
