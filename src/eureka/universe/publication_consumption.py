"""EUREKA 5.1 — Read-only Published Artifact Consumption (verified, tamper-evident).

Consuming a published artifact means READING the durable publication evidence and VERIFYING it against
the real contract — WITHOUT mutating anything, WITHOUT treating it as a new authoritative state, and
WITHOUT re-executing / re-publishing / re-predicting / re-prescribing.

Verification (reuses the existing publisher integrity mechanism, never a new hash):
- schema: the artifact is a CANONICAL_PUBLICATION_ARTIFACT with the required fields.
- integrity: `canonical_content_signature` (the reused `_freeze_signature`) is re-computed over the
  stored frozen snapshot via `EMPublisher._signature_from_frozen`; a mismatch -> TAMPERED.
- identity/currentness: `canonical_state_identity` vs the CURRENT canonical fingerprint — equal ->
  CURRENT; otherwise HISTORICAL (a valid historical artifact, NOT a corrupted one).
- The published artifact is NOT a second canonical authority; Q2 remains the only canonical-identity
  engine and `_freeze_signature` remains the publication/content identity.

This module is READ-ONLY (composition only): it never writes, never mutates the canonical, and no
GET side-effect. `release` is intentionally OUT of scope here (the repository has no real release /
deliver / ship contract; an invented `status=RELEASED` would be an artificial authority, not real).
"""
from __future__ import annotations

import glob
import json
import os
from typing import Any, Dict, List, Optional

from .canonical_identity import canonical_state_fingerprint
from .publication_model import FrozenResult
from .publisher import EMPublisher

REQUIRED_KEYS = ("artifact_kind", "work_id", "canonical_state_identity",
                 "canonical_content_signature", "frozen_result")


def verify_publication(artifact: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a published artifact dict and return a verification report (read-only, pure)."""
    report: Dict[str, Any] = {
        "artifact_kind": artifact.get("artifact_kind"),
        "work_id": artifact.get("work_id"),
        "canonical_state_identity": artifact.get("canonical_state_identity"),
        "signature": artifact.get("canonical_content_signature"),
        "schema_valid": False,
        "integrity": "UNVERIFIABLE",
        "signature_match": False,
        "publication_status": artifact.get("publication_status"),
    }
    if artifact.get("artifact_kind") != "CANONICAL_PUBLICATION_ARTIFACT":
        return report
    if not all(k in artifact for k in ("work_id", "canonical_state_identity", "canonical_content_signature")):
        return report
    report["schema_valid"] = True

    # Integrity: recompute the reused _freeze_signature over the stored frozen snapshot.
    frozen = artifact.get("frozen_result")
    if frozen:
        try:
            frozen_model = FrozenResult.model_validate(frozen)
            recomputed = EMPublisher._signature_from_frozen(frozen_model)
            report["signature_match"] = recomputed == artifact.get("canonical_content_signature")
            report["integrity"] = "VALID" if report["signature_match"] else "TAMPERED"
        except Exception:
            report["integrity"] = "TAMPERED"   # a frozen snapshot that can't be validated -> not trusted
    return report


def build_publication_consumption(works_db, publisher: EMPublisher, work_id: str) -> Dict[str, Any]:
    """Read-only consumption of the (latest) published artifact for a Work, with verification.

    - Resolves the artifact SERVER-SIDE by work_id (never from a client-supplied filesystem path).
    - Verifies schema + integrity + currentness. Never mutates; never executes.
    - Raises ValueError("WORK_NOT_FOUND") for an unknown work (fail-closed).
    """
    if work_id not in works_db:
        raise ValueError(f"WORK_NOT_FOUND:{work_id}")

    pubdir = publisher.publication_dir
    files = sorted(glob.glob(os.path.join(pubdir, f"{work_id}-*.json")))
    candidates = [os.path.basename(p) for p in files]
    if not files:
        return {"work_id": work_id, "publication": None,
                "verification": {"integrity": "MISSING", "schema_valid": False},
                "candidate_artifacts": candidates}

    latest = files[-1]
    try:
        with open(latest, "r", encoding="utf-8") as f:
            artifact = json.load(f)
    except ValueError:
        # a corrupt artifact (unparseable) must NOT be silently consumed -> fail closed
        return {"work_id": work_id, "publication": None,
                "verification": {"integrity": "TAMPERED", "schema_valid": False,
                                 "message": "artifact is not valid JSON"},
                "candidate_artifacts": candidates}

    verification = verify_publication(artifact)
    # currentness: compare the published canonical identity to the CURRENT canonical fingerprint.
    try:
        current_fp = canonical_state_fingerprint(works_db[work_id])
    except Exception:
        current_fp = None
    verification["currentness"] = ("CURRENT" if artifact.get("canonical_state_identity") == current_fp
                                   else "HISTORICAL")
    verification["revision"] = artifact.get("revision")
    return {"work_id": work_id, "publication": artifact, "verification": verification,
            "candidate_artifacts": candidates}
