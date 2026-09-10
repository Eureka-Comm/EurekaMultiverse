"""EUREKA Identity & Access — package surface.

A distinct domain authority (users/sessions/auth-events/reset-tokens/MFA), durable and restart-safe,
integrated onto the existing EUREKA FastAPI app. Never mixed with canonical identity / cognitive
authority / CONSTELACIÓN.
"""
from __future__ import annotations

from .admin_router import make_admin_router
from .auth_router import make_auth_router
from .config import identity_config
from .store import IdentityStore

__all__ = ["make_auth_router", "make_admin_router", "identity_config", "IdentityStore"]
