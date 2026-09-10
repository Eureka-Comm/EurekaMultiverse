"""EUREKA Identity & Access — security primitives.

- Password hashing: Argon2id (argon2-cffi). Never plaintext, never bare SHA-256.
- TOTP (RFC 6238) for admin MFA, implemented with stdlib hmac/hashlib (no external dep).
- Opaque, crypto-random tokens for sessions / reset / verification (database-backed, revocable,
  tamper-proof — no client-decodable JWT with mutable claims).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError

# Argon2id parameters (OWASP-recommended baseline). These are O(seconds) on modern hardware.
_HASHER = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

# --------------------------------------------------------------------------- #
# Passwords
# --------------------------------------------------------------------------- #
def hash_password(password: str, *, app: bool = True) -> str:
    """Return an Argon2id hash string (never returned to the client)."""
    return _HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification; returns False on any mismatch/invalid hash (fail-closed)."""
    try:
        return _HASHER.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, Exception):
        return False


# --------------------------------------------------------------------------- #
# Opaque tokens
# --------------------------------------------------------------------------- #
def new_token(nbytes: int = 32) -> str:
    """Crypto-random opaque token (URL-safe). Never derived from user input."""
    return secrets.token_urlsafe(nbytes)


def digest_token(token: str) -> str:
    """Hash a token for storage (so a DB leak does not expose live credentials)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def safe_token_cmp(a: str, b: str) -> bool:
    """Constant-time comparison for tokens."""
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


# --------------------------------------------------------------------------- #
# TOTP (RFC 6238) — stdlib only; admin MFA
# --------------------------------------------------------------------------- #
def totp_secret() -> str:
    """Generate a base32 TOTP secret (HMAC-SHA1 base32)."""
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii")


def _hmac_sha1(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha1).digest()


def totp_code(secret_b32: str, *, time_step: int = 30, window: int = 1, now: Optional[int] = None) -> str:
    """Return the current TOTP code (6 digits) for a base32 secret (RFC 6238, SHA-1, 6 digits)."""
    key = base64.b32decode(secret_b32.upper())
    counter = (now if now is not None else int(time.time())) // time_step
    msg = struct.pack(">Q", counter)
    digest = _hmac_sha1(key, msg)
    offset = digest[-1] & 0x0F
    binary = (digest[offset] & 0x7F) << 24
    binary |= (digest[offset + 1] & 0xFF) << 16
    binary |= (digest[offset + 2] & 0xFF) << 8
    binary |= digest[offset + 3] & 0xFF
    return str(binary % 1_000_000).zfill(6)


def totp_verify(secret_b32: str, code: str, *, time_step: int = 30, window: int = 1) -> bool:
    """Verify a TOTP code within +-window steps (replay within window tolerated; no storage of codes)."""
    now = int(time.time())
    for delta in range(-window, window + 1):
        expected = totp_code(secret_b32, time_step=time_step, window=window, now=now + delta * time_step)
        if hmac.compare_digest(expected, (code or "").strip()):
            return True
    return False
