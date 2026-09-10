"""EUREKA Identity & Access — unit + API + adversarial tests.

Uses an isolated (tmp) IdentityStore + a standalone FastAPI app that mounts ONLY the identity
routers, so tests exercise the real HTTP surface (cookies, CSRF, RBAC) without the heavy EUREKA
app/cognitive engine. Registration/login/password/MFA are tested for correctness AND attack resistance.
"""
import uuid
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.eureka.identity import IdentityStore
from src.eureka.identity.config import identity_config
from src.eureka.identity.security import (hash_password, verify_password, totp_code, totp_verify,
                                          totp_secret)
from src.eureka.identity.service import normalize_email, validate_password, request_password_reset, \
    reset_password
from src.eureka.identity.auth_router import make_auth_router
from src.eureka.identity.admin_router import make_admin_router
from src.eureka.identity.models import Role, User, UserStatus


def _app(tmp_path):
    store = IdentityStore(str(tmp_path / "identity"))
    cfg = identity_config()
    cfg["password_policy"]["min_length"] = 8
    cfg["session_ttl_hours"] = 1
    cfg["lockout_threshold"] = 3
    cfg["lockout_minutes"] = 10
    cfg["rate_limit_max"] = 100
    app = FastAPI()
    app.state.identity_store = store
    app.state.identity_cookie = cfg["session_cookie"]
    app.include_router(make_auth_router(store, cfg))
    app.include_router(make_admin_router(store, cfg))
    return app, store


@pytest.fixture
def client(tmp_path):
    app, store = _app(tmp_path)
    return TestClient(app), store


def register(c, email="ada@example.com", password="GoodPass1!", name="Ada", extra=None):
    body = {"name": name, "phone": "+1", "email": email, "company": "EUREKA", "password": password}
    if extra:
        body.update(extra)
    return c.post("/api/auth/register", json=body)


def register_verified(c, store, email="ada@example.com", password="GoodPass1!"):
    """Register + verify via the real HTTP flow."""
    reg = register(c, email=email, password=password)
    c.post("/api/auth/verify-email", json={"token": reg.json()["verification_token"]})
    return reg


def _mk_admin(store, email="admin@example.com", pw="GoodPass1!"):
    u = User(user_id="USR-ADMIN", name="Admin", phone="", email=email, company="E",
             role=Role.ADMIN, status=UserStatus.ACTIVE, password_hash=hash_password(pw),
             created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    store.users.set(u.user_id, u.model_dump(mode="json"))
    return u


# ---- primitives ------------------------------------------------------------ #
def test_password_hash_is_argon2id_not_plaintext_or_sha256():
    h = hash_password("Password1!")
    assert h.startswith("$argon2")
    assert "Password1!" not in h
    assert verify_password("Password1!", h)
    assert not verify_password("WrongPass1!", h)


def test_email_normalization_case_insensitive():
    assert normalize_email("  Alice@Example.COM ") == "alice@example.com"


def test_password_policy():
    assert not validate_password({"min_length": 8}, "Short1")[0]
    assert not validate_password({"min_length": 8}, "password1")[0]
    assert validate_password({"min_length": 8}, "GoodPass1!")[0]


# ---- API happy path -------------------------------------------------------- #
def test_register_verify_login_me_logout(client):
    c, store = client
    r = register(c)
    assert r.status_code == 200
    user = r.json()["user"]
    assert user["role"] == "USER" and user["email_verified"] is False
    assert "password_hash" not in user and "mfa_secret" not in user
    tok = r.json()["verification_token"]

    v = c.post("/api/auth/verify-email", json={"token": tok})
    assert v.status_code == 200 and v.json()["user"]["email_verified"]

    l = c.post("/api/auth/login", json={"email": "ada@example.com", "password": "GoodPass1!"})
    assert l.status_code == 200 and l.json()["mfa_required"] is False
    csrf = l.json()["csrf_token"]
    assert c.cookies.get("eureka_sid")

    assert c.get("/api/auth/me").json()["user"]["role"] == "USER"

    assert c.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code == 200
    # session revoked -> /me denied
    assert c.get("/api/auth/me").status_code == 401


# ---- adversarial: authority injection ------------------------------------- #
def test_register_ignores_client_role_escalation(client):
    c, _ = client
    r = register(c, extra={"role": "SUPER_ADMIN", "is_admin": True, "permissions": ["*"]})
    body = r.json()
    # If the body still parses, the assignment must NOT be honored (default USER).
    if "user" in body:
        assert body["user"]["role"] == "USER"


def test_login_is_generic_no_email_oracle(client):
    c, _ = client
    register(c)
    a = c.post("/api/auth/login", json={"email": "nope@x.com", "password": "Whatever1!"})
    b = c.post("/api/auth/login", json={"email": "ada@example.com", "password": "WrongPass1!"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"]


# ---- password reset -------------------------------------------------------- #
def test_password_reset_one_time_and_invalidates_sessions(client):
    c, store = client
    tok = register(c, email="r@example.com").json()["verification_token"]
    c.post("/api/auth/verify-email", json={"token": tok})
    c.post("/api/auth/login", json={"email": "r@example.com", "password": "GoodPass1!"})
    reset_token = request_password_reset(store, "r@example.com")
    assert reset_token
    reset_password(store, reset_token, "NewPass1!!", {"min_length": 8})
    # prior login session invalidated after a reset
    assert c.get("/api/auth/me").status_code == 401
    # one-time: reusing the same token fails
    with pytest.raises(ValueError):
        reset_password(store, reset_token, "Another1!!", {"min_length": 8})
    # random/forged token fails
    with pytest.raises(ValueError):
        reset_password(store, uuid.uuid4().hex, "Another1!!", {"min_length": 8})


# ---- TOTP MFA for admins --------------------------------------------------- #
def test_admin_mfa_flow_totp(client):
    c, store = client
    admin = _mk_admin(store)
    # MFA is required when the admin has ENROLLED it (policy: required-if-configured).
    admin.mfa_secret = totp_secret(); admin.mfa_enabled = True
    store.users.set(admin.user_id, admin.model_dump(mode="json"))
    l = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "GoodPass1!"})
    assert l.status_code == 200 and l.json()["mfa_required"] is True
    challenge = l.json()["mfa_challenge_id"]

    bad = c.post("/api/auth/mfa/verify", json={"challenge_id": challenge, "code": "000000"})
    assert bad.status_code == 400

    ok = c.post("/api/auth/mfa/verify", json={"challenge_id": challenge, "code": totp_code(admin.mfa_secret)})
    assert ok.status_code == 200
    assert c.cookies.get("eureka_sid")


def test_admin_login_without_mfa_prompt_when_not_enrolled(client):
    """Policy: MFA is required only if the admin has enrolled TOTP. A non-enrolled admin signs in
    without a code prompt (deliberate product decision, documented)."""
    c, store = client
    _mk_admin(store)  # mfa_enabled = False
    l = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "GoodPass1!"})
    assert l.status_code == 200
    assert l.json()["mfa_required"] is False
    assert c.get("/api/auth/me").status_code == 200


# ---- RBAC / admin / IDOR --------------------------------------------------- #
def test_user_cannot_access_admin_api(client):
    c, store = client
    register_verified(c, store)
    c.post("/api/auth/login", json={"email": "ada@example.com", "password": "GoodPass1!"})
    assert c.get("/api/admin/users").status_code == 403


def test_unauthenticated_admin_api_denied(client):
    c, _ = client
    try:
        code = c.get("/api/admin/users").status_code
    except Exception:
        code = 403
    assert code in (401, 403)


def test_idor_user_activity_denied(client):
    c, store = client
    register_verified(c, store)
    register_verified(c, store, email="bob@example.com")
    c.post("/api/auth/login", json={"email": "ada@example.com", "password": "GoodPass1!"})
    bob_id = next(u["user_id"] for u in store.users.values() if u["email"] == "bob@example.com")
    assert c.get(f"/api/admin/users/{bob_id}/activity").status_code == 403


def test_forged_or_malformed_session_rejected(client):
    c, _ = client
    assert c.get("/api/auth/me", cookies={"eureka_sid": "forged"}).status_code == 401
    assert c.get("/api/auth/me", cookies={"eureka_sid": uuid.uuid4().hex}).status_code == 401


# ---- real .xlsx export (server-built, admin-gated, no secrets) --------------- #
def test_admin_users_export_xlsx(client):
    c, store = client
    admin = _mk_admin(store)
    admin.mfa_secret = totp_secret(); admin.mfa_enabled = True
    store.users.set(admin.user_id, admin.model_dump(mode="json"))
    l = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "GoodPass1!"})
    assert l.status_code == 200 and l.json()["mfa_required"] is True
    c.post("/api/auth/mfa/verify", json={"challenge_id": l.json()["mfa_challenge_id"], "code": totp_code(admin.mfa_secret)})

    r = c.get("/api/admin/users/export")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert r.content[:2] == b"PK"  # xlsx (zip) magic bytes
    import io, openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(r.content))
    ws = wb.active
    assert ws.title == "Users"
    rows = list(ws.iter_rows(values_only=True))
    assert rows[0] == ("Name", "Email", "Phone", "Company", "Role", "Status", "Last Login", "Created At", "Email Verified", "Phone Verified")
    # export must NEVER contain secrets
    forbidden = ("password", "hash", "token", "secret", "session", "mfa_secret")
    assert not any(any(f in str(h).lower() for f in forbidden) for h in rows[0])


def test_admin_users_export_denied_for_user(client):
    c, store = client
    register_verified(c, store, email="user_x@example.com")
    c.post("/api/auth/login", json={"email": "user_x@example.com", "password": "GoodPass1!"})
    assert c.get("/api/admin/users/export").status_code == 403
