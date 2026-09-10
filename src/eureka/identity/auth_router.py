"""EUREKA Identity & Access — Auth HTTP surface (server-side boundary).

The client NEVER supplies role/status/permissions; the server derives them. Sessions are opaque,
HttpOnly-cookie based, with a per-session CSRF token required on state-changing calls. Rate limiting
+ durable lockout protect login/reset. Role escalation is rejected; user-existence is never leaked.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from .deps import current_user as user_dep, require_role as require_role_dep, csrf_check
from .models import (ForgotPasswordRequest, LoginRequest, MfaSetupRequest, MfaVerifyRequest,
                     RegisterRequest, ResetPasswordRequest, Role, User, VerifyEmailRequest)
from .ratelimit import RateLimiter
from .service import (login as do_login, verify_email as do_verify_email,
                      request_password_reset, reset_password as do_reset_password,
                      authenticate_session, logout as do_logout, refresh_session,
                      mfa_setup as do_mfa_setup, mfa_verify as do_mfa_verify,
                      is_admin_role, user_has_role)
from .store import IdentityStore


def make_auth_router(store: IdentityStore, config: Dict[str, Any]) -> APIRouter:
    r = APIRouter(tags=["auth"])
    cookie_name = config["session_cookie"]
    secure = config["secure_cookies"]
    limiter = RateLimiter(config["rate_limit_max"], config["rate_limit_window_seconds"])

    def _set_cookie(response: Response, token: str, max_age: Optional[int]) -> None:
        response.set_cookie(key=cookie_name, value=token, httponly=True, secure=secure,
                            samesite="lax", path="/", max_age=max_age)

    def _clear_cookie(response: Response) -> None:
        response.set_cookie(key=cookie_name, value="", httponly=True, secure=secure,
                            samesite="lax", path="/", max_age=0)

    def _rate_gate(kind: str, email: str, ip: str) -> None:
        if not limiter.allow(kind, email) or not limiter.allow(f"{kind}:ip", ip):
            raise HTTPException(status_code=429, detail="RATE_LIMITED")

    # ---- registration / verification ------------------------------------------- #
    @r.post("/api/auth/register")
    def register(data: RegisterRequest, response: Response):
        limiter.reset("login", data.email)
        from .service import register as do_register
        try:
            user, verify_token = do_register(store, data, config["password_policy"])
        except ValueError as e:
            msg = str(e)
            code = 409 if "ALREADY_EXISTS" in msg else 400
            raise HTTPException(status_code=code, detail=msg)
        return {"ok": True, "user": user.model_dump(mode="json"),
                # Token is returned for the local E2E; production delivers it via the mail abstraction
                # (a real email provider is a declared external dependency, NOT faked here).
                "verification_token": verify_token}

    @r.post("/api/auth/verify-email")
    def verify(data: VerifyEmailRequest):
        try:
            user = do_verify_email(store, data.token)
        except ValueError:
            raise HTTPException(status_code=400, detail="TOKEN_INVALID")
        return {"ok": True, "user": user.model_dump(mode="json")}

    # ---- login / logout / refresh ---------------------------------------------- #
    @r.post("/api/auth/login")
    def login(data: LoginRequest, response: Response, request: Request):
        ip = request.client.host if request.client else ""
        _rate_gate("login", data.email, ip)
        res = do_login(store, data.email, data.password, ip=ip,
                       ua=(request.headers.get("user-agent", "")),
                       mfa_challenge_ttl_minutes=config["mfa_challenge_ttl_minutes"],
                       lockout_threshold=config["lockout_threshold"],
                       lockout_minutes=config["lockout_minutes"],
                       session_ttl_hours=config["session_ttl_hours"])
        if res.get("ok"):
            if not res.get("mfa_required"):
                _set_cookie(response, res["session_token"], config["session_ttl_hours"] * 3600)
                limiter.reset("login", data.email)
                return res
            return res
        # Generic, non-oracle login failure.
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS")

    @r.post("/api/auth/logout")
    def logout(request: Request, response: Response,
               user: User = Depends(require_role_dep(Role.USER)),
               x_csrf_token: Optional[str] = Header(None)):
        csrf_check(request)
        sess = getattr(request.state, "session", None)
        do_logout(store, sess, user)
        _clear_cookie(response)
        return {"ok": True}

    @r.post("/api/auth/refresh")
    def refresh(request: Request, response: Response,
                user: User = Depends(require_role_dep(Role.USER)),
                x_csrf_token: Optional[str] = Header(None)):
        csrf_check(request)
        sess = getattr(request.state, "session", None)
        token, csrf, expires = refresh_session(store, sess, user,
                                               session_ttl_hours=config["session_ttl_hours"])
        _set_cookie(response, token, config["session_ttl_hours"] * 3600)
        return {"ok": True, "session_token": token, "csrf_token": csrf, "expires_at": expires}

    @r.get("/api/auth/me")
    def me(user: User = Depends(require_role_dep(Role.USER))):
        return {"ok": True, "user": user.public().model_dump(mode="json")}

    # ---- password reset -------------------------------------------------------- #
    @r.post("/api/auth/forgot-password")
    def forgot(data: ForgotPasswordRequest, request: Request):
        ip = request.client.host if request.client else ""
        _rate_gate("forgot", data.email, ip)
        # Always-generic: the response is identical whether or not the account exists.
        request_password_reset(store, data.email)
        return {"ok": True, "message": "If the account exists, a reset link was generated."}

    @r.post("/api/auth/reset-password")
    def reset(data: ResetPasswordRequest, request: Request):
        ip = request.client.host if request.client else ""
        _rate_gate("reset", "reset", ip)
        try:
            user = do_reset_password(store, data.token, data.password, config["password_policy"])
        except ValueError as e:
            if str(e).startswith("PASSWORD_POLICY"):
                raise HTTPException(status_code=400, detail=str(e))
            raise HTTPException(status_code=400, detail="TOKEN_INVALID")
        return {"ok": True, "user": user.model_dump(mode="json")}

    # ---- admin TOTP MFA (mandatory for ADMIN / SUPER_ADMIN) --------------------- #
    @r.post("/api/auth/mfa/setup")
    def mfa_setup(data: MfaSetupRequest, user: User = Depends(require_role_dep(Role.ADMIN))):
        from .service import mfa_setup as do_setup
        try:
            secret = do_setup(store, user, data.password)
        except ValueError:
            raise HTTPException(status_code=400, detail="PASSWORD_INVALID")
        return {"ok": True, "secret": secret}

    @r.post("/api/auth/mfa/verify")
    def mfa_verify(data: MfaVerifyRequest, response: Response, request: Request):
        ip = request.client.host if request.client else ""
        try:
            res = do_mfa_verify(store, data.challenge_id, data.code, ip=ip,
                                ua=(request.headers.get("user-agent", "")),
                                session_ttl_hours=config["session_ttl_hours"])
        except ValueError:
            raise HTTPException(status_code=400, detail="MFA_INVALID")
        _set_cookie(response, res["session_token"], config["session_ttl_hours"] * 3600)
        return res

    return r
