"""EUREKA 5.1 — Durable Work Authority (ONE authority, restart-safe).

The Work authority has historically been an in-memory ``works_db`` dict. This module transitions the
SAME authority to a durable, file-backed store WITHOUT changing the concept (there is still exactly
ONE Work authority). All existing mutations/reads keep working because ``WorkStore`` is dict-like
(``get`` / ``__getitem__`` / ``__setitem__`` / ``__contains__`` / ``keys`` / ``len``), so the server
endpoints, the Scenario ``work_id`` resolver and the evolution API keep routing through the SAME
object.

Design:
- STORAGE ONLY, one authority: no second store, no new API, no second server.
- Persistence convention: JSON per work under ``data/works`` (the repo's existing file-backed convention).
- Load validates via the REAL ``CanonicalWorkState`` schema (fail-closed on corrupt; never fabricate).
- Writes are Q4-gated (``EffectBoundary``/``authorize_write``, capability ``work.persist``, NORMAL +
  the canonical-runtime authorization) AND atomic (temp + ``os.replace``), so a crash cannot corrupt a work.
- Lazy load on access; the store does not eagerly load on startup (a corrupt work is detected on access
  and raises, so it is never silently treated as absent).
- Q2 remains the ONLY identity engine: loading rebuilds the same semantic ``CanonicalWorkState``, and its
  ``canonical_state_fingerprint`` is unchanged (verified by round-trip).
"""
from __future__ import annotations

import json
import os
from typing import Dict, Iterator, List, Optional

from .canonical_state import CanonicalWorkState
from .effect_policy import (default_boundary, ExecutionMode, EffectBoundary, EffectClass,
                            BoundaryDecision, PolicyError, CANONICAL_PERSISTENCE_AUTH)


class CorruptWorkError(RuntimeError):
    """Raised when a durable Work record exists but fails schema validation (fail-closed)."""
    def __init__(self, work_id: str, detail: str):
        super().__init__(f"CORRUPT_WORK: {work_id}: {detail}")
        self.work_id = work_id
        self.detail = detail


class WorkStore:
    """Durable, dict-like Work authority backed by per-work JSON files.

    The in-memory ``_cache`` is a read/write look-aside; the durable truth is on disk. ``work_id`` is
    stable and is the identity of the Work (never re-derived from memory address / process id).
    """

    def __init__(self, storage_dir: str = "data/works", boundary: Optional[EffectBoundary] = None) -> None:
        self.storage_dir = storage_dir
        self._boundary = boundary or default_boundary()
        self._cache: Dict[str, CanonicalWorkState] = {}
        os.makedirs(self.storage_dir, exist_ok=True)

    # ---- pathing ----------------------------------------------------------- #
    def _path(self, work_id: str) -> str:
        return os.path.join(self.storage_dir, f"{work_id}.json")

    # ---- durable write / read (Q4-gated + atomic) -------------------------- #
    def _persist(self, canonical: CanonicalWorkState) -> None:
        work_id = canonical.work.work_id
        data = canonical.model_dump(mode="json")
        verdict = self._boundary.authorize_write(
            EffectClass.MUTATE, mode=ExecutionMode.NORMAL, authorization=CANONICAL_PERSISTENCE_AUTH,
            target="fs", capability_id="work.persist")
        if verdict.decision == BoundaryDecision.BLOCK:
            raise PolicyError(verdict.reason_code, verdict.message)
        path = self._path(work_id)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)  # atomic replacement (no partial/corrupt work on crash)

    def _load(self, work_id: str) -> Optional[CanonicalWorkState]:
        if work_id in self._cache:
            return self._cache[work_id]
        path = self._path(work_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            canonical = CanonicalWorkState.model_validate(data)  # schema validation (fail-closed)
        except PolicyError:
            raise
        except Exception as e:
            raise CorruptWorkError(work_id, str(e)) from e
        self._cache[work_id] = canonical
        return canonical

    # ---- dict-like interface (preserves the existing ONE-authority calls) -- #
    def get(self, work_id: str, default=None) -> Optional[CanonicalWorkState]:
        canonical = self._load(work_id)
        return canonical if canonical is not None else default

    def __getitem__(self, work_id: str) -> CanonicalWorkState:
        canonical = self._load(work_id)
        if canonical is None:
            raise KeyError(work_id)
        return canonical

    def __setitem__(self, work_id: str, canonical: CanonicalWorkState) -> None:
        # The durable truth is the canonical's own work_id; write-through to disk + cache.
        self._persist(canonical)
        self._cache[canonical.work.work_id] = canonical

    def __delitem__(self, work_id: str) -> None:
        self._cache.pop(work_id, None)
        if os.path.exists(self._path(work_id)):
            os.remove(self._path(work_id))

    def __contains__(self, work_id: str) -> bool:
        canonical = self._load(work_id)   # raises on corrupt (fail-closed, never treated as absent)
        return canonical is not None

    def __len__(self) -> int:
        return len(self.list())

    def __iter__(self) -> Iterator[str]:
        return iter(self.list())

    def keys(self) -> List[str]:
        return self.list()

    def items(self):
        for w_id in self.list():
            yield w_id, self[w_id]

    def list(self) -> List[str]:
        import glob
        return sorted(os.path.splitext(os.path.basename(p))[0]
                      for p in glob.glob(os.path.join(self.storage_dir, "*.json")))

    def cache_keys(self) -> List[str]:
        return list(self._cache.keys())
