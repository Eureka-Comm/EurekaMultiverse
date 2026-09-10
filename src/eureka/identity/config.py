"""EUREKA Identity & Access — runtime configuration (env-driven, no secrets in source)."""
from __future__ import annotations

import os
from typing import Any, Dict


def identity_config() -> Dict[str, Any]:
    """Build the identity/auth runtime config from the environment. Production must set these."""
    return {
        # Storage
        "storage_dir": os.getenv("EUREKA_IDENTITY_STORAGE_DIR", "data/identity"),
        # Sessions
        "session_ttl_hours": int(os.getenv("EUREKA_SESSION_TTL_HOURS", "8")),
        # Passwords
        "password_policy": {
            "min_length": int(os.getenv("EUREKA_PASSWORD_MIN_LENGTH", "12")),
        },
        # Lockout (durable, per-account)
        "lockout_threshold": int(os.getenv("EUREKA_LOCKOUT_THRESHOLD", "5")),
        "lockout_minutes": int(os.getenv("EUREKA_LOCKOUT_MINUTES", "15")),
        # MFA
        "mfa_challenge_ttl_minutes": int(os.getenv("EUREKA_MFA_CHALLENGE_TTL_MINUTES", "2")),
        # Rate limiting (in-memory fixed-window)
        "rate_limit_max": int(os.getenv("EUREKA_RATE_LIMIT_MAX", "8")),
        "rate_limit_window_seconds": int(os.getenv("EUREKA_RATE_LIMIT_WINDOW_SECONDS", "900")),
        # Cookies
        "secure_cookies": os.getenv("EUREKA_SECURE_COOKIES", "false").lower() == "true",
        "session_cookie": os.getenv("EUREKA_SESSION_COOKIE", "eureka_sid"),
        # Admin
        "superadmin_protection": True,
    }
