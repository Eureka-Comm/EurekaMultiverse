"""EUREKA Identity & Access — durable storage (ONE identity authority, restart-safe).

Follows the repo's file-backed JSON convention (mirrors WorkStore): each collection is a JSON file
under ``data/identity`` written atomically (temp + ``os.replace``). Lazy load on access; a corrupt
record is reported fail-closed (``CorruptIdentityError``), never silently treated as absent.
Identity is a SEPARATE domain authority — it never writes into ``data/works`` or canonical state.
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional


class CorruptIdentityError(RuntimeError):
    def __init__(self, collection: str, detail: str):
        super().__init__(f"CORRUPT_IDENTITY:{collection}: {detail}")
        self.collection = collection
        self.detail = detail


class _JsonCollection:
    def __init__(self, dir: str, name: str):
        self.path = os.path.join(dir, f"{name}.json")
        self._cache: Optional[Dict[str, Any]] = None

    def _load(self) -> Dict[str, Any]:
        if self._cache is not None:
            return self._cache
        if not os.path.exists(self.path):
            self._cache = {}
            return self._cache
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CorruptIdentityError(self.path, str(e)) from e
        if not isinstance(data, dict):
            raise CorruptIdentityError(self.path, "expected a JSON object")
        self._cache = data
        return self._cache

    def _save(self) -> None:
        data = self._load()
        tmp = f"{self.path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, self.path)

    def get(self, key: str, default=None):
        return self._load().get(key, default)

    def keys(self) -> List[str]:
        return list(self._load().keys())

    def values(self) -> list:
        return list(self._load().values())

    def items(self):
        return self._load().items()

    def contains(self, key: str) -> bool:
        return key in self._load()

    def set(self, key: str, value: Any) -> None:
        self._load()[key] = value
        self._save()

    def delete(self, key: str) -> None:
        coll = self._load()
        coll.pop(key, None)
        self._save()

    def __len__(self) -> int:
        return len(self._load())


class IdentityStore:
    """Durable Identity & Access authority (users/sessions/events/tokens/mfa)."""

    def __init__(self, storage_dir: str = "data/identity") -> None:
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.users = _JsonCollection(storage_dir, "users")
        self.sessions = _JsonCollection(storage_dir, "sessions")
        self.events = _JsonCollection(storage_dir, "auth_events")
        self.reset_tokens = _JsonCollection(storage_dir, "reset_tokens")
        self.mfa = _JsonCollection(storage_dir, "mfa_challenges")

    def flush_reload(self) -> None:
        """Drop in-memory caches so a re-open re-reads disk (used by restart tests)."""
        for coll in (self.users, self.sessions, self.events, self.reset_tokens, self.mfa):
            coll._cache = None
