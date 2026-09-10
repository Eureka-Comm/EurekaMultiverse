"""EUREKA Identity & Access — in-memory fixed-window rate limiter (brute-force protection).

Operational (transient) protection on top of the durable per-account lockout. A single mistaken login
is never blocked; a burst across the window is throttled with 429. Keys are only ever (kind, ip) and
(kind, email) — never recorded secrets.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, Tuple


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: Dict[Tuple[str, str], Tuple[float, int]] = {}
        self._lock = threading.Lock()

    def allow(self, kind: str, key: str) -> bool:
        """Return True if the (kind, key) is within the limit for the current window."""
        now = time.time()
        with self._lock:
            nk = (kind, key)
            ts, count = self._hits.get(nk, (0, 0))
            if now - ts > self.window_seconds:
                self._hits[nk] = (now, 1)
                return True
            self._hits[nk] = (ts, count + 1)
            return count < self.max_attempts

    def reset(self, kind: str, key: str) -> None:
        with self._lock:
            self._hits.pop((kind, key), None)

    def hit_count(self, kind: str, key: str) -> int:
        with self._lock:
            return self._hits.get((kind, key), (0, 0))[1]
