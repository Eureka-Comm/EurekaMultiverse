"""EUREKA Identity & Access — FastAPI shared dependencies (single server-side authority).

The identity store + cookie name live on ``app.state`` (set at startup). These dependencies are the
ONLY sanctioned way for any protected route to identify/authorize a caller — there is NO per-endpoint
ad-hoc role check, and NO client-supplied role is ever trusted.
"""
from __future__ import annotations

from typing import Optional
from fastapi import HTTPException, Request

from .models import Role, User
from .service import authenticate_session, user_has_role


def _store(request: Request):
    return request.app.state.identity_store


def _cookie_name(request: Request) -> str:
    return request.app.state.identity_cookie


def current_user(request: Request) -> User:
    store = _store(request)
    token = request.cookies.get(_cookie_name(request))
    sess, user = authenticate_session(store, token)
    if sess is None or user is None:
        raise HTTPException(status_code=401, detail="UNAUTHORIZED")
    request.state.session = sess
    return user


def require_role(min_role: Role):
    def dep(request: Request) -> User:
        user = current_user(request)
        if not user_has_role(user, min_role):
            raise HTTPException(status_code=403, detail="FORBIDDEN")
        return user
    return dep


def csrf_check(request: Request) -> None:
    """Validate the per-session CSRF token header on cookie-authenticated mutations."""
    sess = getattr(request.state, "session", None)
    header = request.headers.get("x-csrf-token", "")
    if sess is None or not sess.csrf_token or header != sess.csrf_token:
        raise HTTPException(status_code=403, detail="CSRF")
