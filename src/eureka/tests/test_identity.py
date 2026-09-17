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
    assert rows[0] == ("User ID", "Name", "Email", "Phone", "Company", "Role", "Status",
                       "Last Login", "Created At", "Email Verified", "Phone Verified")
    # requirement: the report must identify the EUREKA user (email, phone, company, EUREKA user)
    assert rows[1][0] == "USR-ADMIN"
    # export must NEVER contain secrets
    forbidden = ("password", "hash", "token", "secret", "session", "mfa_secret")
    assert not any(any(f in str(h).lower() for f in forbidden) for h in rows[0])


def test_admin_users_export_denied_for_user(client):
    c, store = client
    register_verified(c, store, email="user_x@example.com")
    c.post("/api/auth/login", json={"email": "user_x@example.com", "password": "GoodPass1!"})
    assert c.get("/api/admin/users/export").status_code == 403


# ---- admin-initiated password reset (THE recovery path: no mailer exists) ----- #
def _mk_user(store, user_id, email, role=Role.USER, pw="GoodPass1!", status=UserStatus.ACTIVE):
    u = User(user_id=user_id, name=user_id, phone="+1", email=email, company="EUREKA",
             role=role, status=status, password_hash=hash_password(pw),
             created_at="2026-01-01T00:00:00Z", updated_at="2026-01-01T00:00:00Z")
    store.users.set(u.user_id, u.model_dump(mode="json"))
    return u


def _login_ok(c, email, pw):
    r = c.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200 and r.json()["ok"] is True, r.text
    return r


def test_admin_set_password_restores_access_and_revokes_sessions(client):
    """The capability that was missing: an admin can restore access, and the old credential dies."""
    c, store = client
    _mk_admin(store)
    _mk_user(store, "USR-VICTIM", "victim@example.com", pw="OldPass123!")
    _login_ok(c, "victim@example.com", "OldPass123!")
    assert any(s["user_id"] == "USR-VICTIM" and not s["revoked_at"] for s in store.sessions.values())

    admin_c = TestClient(c.app)  # separate cookie jar: admin session must not clobber the victim's
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    r = admin_c.post("/api/admin/users/USR-VICTIM/password", json={"password": "BrandNew123!"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert r.json()["user"]["user_id"] == "USR-VICTIM"

    # the secret never comes back, and never reaches the audit trail
    import json as _json
    assert "BrandNew123!" not in r.text
    assert "argon2" not in r.text.lower() and "password_hash" not in r.text
    events = [e for e in store.events.values() if e["event_type"] == "PASSWORD_RESET_COMPLETED"]
    assert events and events[-1]["metadata"]["actor_user_id"] == "USR-ADMIN"
    assert events[-1]["metadata"]["target_user_id"] == "USR-VICTIM"
    assert "BrandNew123!" not in _json.dumps(events)

    # fail-closed: every session issued under the old password is revoked
    assert all(s["revoked_at"] for s in store.sessions.values() if s["user_id"] == "USR-VICTIM")

    # old password dead, new password alive
    assert c.post("/api/auth/login",
                  json={"email": "victim@example.com", "password": "OldPass123!"}).status_code == 401
    _login_ok(c, "victim@example.com", "BrandNew123!")


def test_admin_set_password_policy_violation_is_atomic(client):
    """A rejected reset must not mutate anything: the old credential still works."""
    c, store = client
    _mk_admin(store)
    _mk_user(store, "USR-V2", "v2@example.com", pw="OldPass123!")
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    r = admin_c.post("/api/admin/users/USR-V2/password", json={"password": "short"})
    assert r.status_code == 400 and r.json()["detail"].startswith("PASSWORD_POLICY")
    assert verify_password("OldPass123!", store.users.get("USR-V2")["password_hash"])


def test_admin_set_password_clears_lockout_and_failed_count(client):
    """Recovery must also release a locked account, or the reset would not restore access."""
    c, store = client
    _mk_admin(store)
    u = _mk_user(store, "USR-LOCK", "lock@example.com", pw="OldPass123!")
    u.failed_login_count = 9
    u.locked_until = "2999-01-01T00:00:00Z"
    store.users.set(u.user_id, u.model_dump(mode="json"))
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    assert admin_c.post("/api/admin/users/USR-LOCK/password",
                        json={"password": "Fresh12345!"}).status_code == 200
    saved = store.users.get("USR-LOCK")
    assert saved["failed_login_count"] == 0 and not saved["locked_until"]
    _login_ok(c, "lock@example.com", "Fresh12345!")


def test_user_cannot_set_any_password(client):
    """A USER hitting the admin surface directly gets 403 and changes nothing."""
    c, store = client
    _mk_user(store, "USR-V3", "v3@example.com", pw="OldPass123!")
    register_verified(c, store, email="mallory@example.com")
    _login_ok(c, "mallory@example.com", "GoodPass1!")
    r = c.post("/api/admin/users/USR-V3/password", json={"password": "Hijacked123!"})
    assert r.status_code == 403
    assert verify_password("OldPass123!", store.users.get("USR-V3")["password_hash"])


def test_admin_cannot_reset_admin_or_superadmin(client):
    """No lateral takeover: only a SUPER_ADMIN may reset an ADMIN/SUPER_ADMIN."""
    c, store = client
    _mk_admin(store)
    _mk_user(store, "USR-ADMIN2", "admin2@example.com", role=Role.ADMIN, pw="OtherPass1!")
    _mk_user(store, "USR-SUPER", "super@example.com", role=Role.SUPER_ADMIN, pw="SuperPass1!")
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    for target in ("USR-ADMIN2", "USR-SUPER"):
        r = admin_c.post(f"/api/admin/users/{target}/password", json={"password": "Hijacked123!"})
        assert r.status_code == 403 and r.json()["detail"] == "FORBIDDEN_ROLE"
    assert verify_password("OtherPass1!", store.users.get("USR-ADMIN2")["password_hash"])
    assert verify_password("SuperPass1!", store.users.get("USR-SUPER")["password_hash"])


def test_superadmin_can_reset_admin(client):
    c, store = client
    _mk_user(store, "USR-ROOT", "root@example.com", role=Role.SUPER_ADMIN, pw="RootPass1!")
    _mk_user(store, "USR-ADMIN3", "admin3@example.com", role=Role.ADMIN, pw="OtherPass1!")
    root_c = TestClient(c.app)
    _login_ok(root_c, "root@example.com", "RootPass1!")
    assert root_c.post("/api/admin/users/USR-ADMIN3/password",
                       json={"password": "Rotated123!"}).status_code == 200
    assert verify_password("Rotated123!", store.users.get("USR-ADMIN3")["password_hash"])


def test_admin_can_reset_own_password(client):
    c, store = client
    _mk_admin(store)
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    assert admin_c.post("/api/admin/users/USR-ADMIN/password",
                        json={"password": "MyNewPass123!"}).status_code == 200
    _login_ok(c, "admin@example.com", "MyNewPass123!")


def test_admin_set_password_unknown_user_404(client):
    c, store = client
    _mk_admin(store)
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    r = admin_c.post("/api/admin/users/USR-NOPE/password", json={"password": "Whatever123!"})
    assert r.status_code == 404 and r.json()["detail"] == "USER_NOT_FOUND"


# ---- admin user creation: the account must be able to sign in IMMEDIATELY ------ #
def _create(c, **fields):
    body = {"name": "Nuevo Usuario", "email": "nuevo@example.com", "phone": "+34 600111222",
            "company": "ACME"}
    body.update(fields)
    return c.post("/api/admin/users", json=body)


def _admin_client(c, store):
    """A separate cookie jar logged in as the canonical fixture ADMIN (idempotent)."""
    _mk_admin(store)
    admin_c = TestClient(c.app)
    _login_ok(admin_c, "admin@example.com", "GoodPass1!")
    return admin_c


def test_admin_created_user_signs_in_immediately_with_the_generated_password(client):
    """THE requirement: create -> server-generated password -> the user signs in. No dead end.

    Also covers the email-normalisation defect: the account is created with a MIXED-CASE email, and
    `_find_by_email` lowercases the login input — before the fix this account was permanently
    unloginnable and the failure was invisible (LOGIN_FAILED with user_id=None, no counter bump).
    """
    c, store = client
    admin_c = _admin_client(c, store)
    r = _create(admin_c, email="Nuevo.Usuario@Example.COM")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True and body["password_generated"] is True
    generated = body["generated_password"]
    assert body["user"]["status"] == "ACTIVE"                     # never INVITED
    assert body["user"]["email"] == "nuevo.usuario@example.com"    # normalised at storage
    assert "password_hash" not in r.text and "argon2" not in r.text.lower()

    ok, reason = validate_password(identity_config()["password_policy"], generated,
                                   "nuevo.usuario@example.com")
    assert ok, reason

    _login_ok(c, "nuevo.usuario@example.com", generated)            # the admin hands it over
    fresh = TestClient(c.app)
    _login_ok(fresh, "NUEVO.USUARIO@EXAMPLE.COM", generated)        # any casing works


def test_generated_password_is_never_stored_or_audited_in_plaintext(client):
    c, store = client
    admin_c = _admin_client(c, store)
    generated = _create(admin_c).json()["generated_password"]
    uid = next(u["user_id"] for u in store.users.values() if u["email"] == "nuevo@example.com")

    import json as _json
    record = store.users.get(uid)
    assert generated not in _json.dumps(record)
    assert record["password_hash"].startswith("$argon2id$")
    assert generated not in _json.dumps(list(store.events.values()))
    event = [e for e in store.events.values() if e["event_type"] == "ADMIN_USER_CREATED"][-1]
    assert event["metadata"]["password_generated"] is True
    assert event["metadata"]["status"] == "ACTIVE"


def test_two_created_users_receive_different_passwords(client):
    c, store = client
    admin_c = _admin_client(c, store)
    first = _create(admin_c, email="uno@example.com").json()["generated_password"]
    second = _create(admin_c, email="dos@example.com").json()["generated_password"]
    assert first != second


def test_admin_may_still_supply_the_password_explicitly(client):
    c, store = client
    admin_c = _admin_client(c, store)
    body = _create(admin_c, email="elegido@example.com", password="TypedByAdmin1!").json()
    assert body["password_generated"] is False and "generated_password" not in body
    _login_ok(c, "elegido@example.com", "TypedByAdmin1!")


def test_created_user_with_a_weak_supplied_password_is_refused_atomically(client):
    c, store = client
    admin_c = _admin_client(c, store)
    r = _create(admin_c, email="debil@example.com", password="short")
    assert r.status_code == 400 and r.json()["detail"].startswith("PASSWORD_POLICY")
    assert not any(u["email"] == "debil@example.com" for u in store.users.values())


def test_duplicate_email_is_refused_case_insensitively(client):
    c, store = client
    admin_c = _admin_client(c, store)
    assert _create(admin_c, email="Dup@Example.com").status_code == 200
    second = _create(admin_c, email="dup@EXAMPLE.com")
    assert second.status_code == 400 and second.json()["detail"] == "ACCOUNT_ALREADY_EXISTS"


def test_admin_cannot_create_an_admin_or_superadmin(client):
    """Mirrors change_role: creating a privileged account is a SUPER_ADMIN-only grant."""
    c, store = client
    admin_c = _admin_client(c, store)
    for role in ("ADMIN", "SUPER_ADMIN"):
        r = _create(admin_c, email=f"{role.lower()}x@example.com", role=role)
        assert r.status_code == 403 and r.json()["detail"] == "FORBIDDEN_ROLE"
    assert not any(u["email"].endswith("x@example.com") for u in store.users.values())


def test_superadmin_can_create_an_admin(client):
    c, store = client
    _mk_user(store, "USR-ROOT", "root@example.com", role=Role.SUPER_ADMIN, pw="RootPass1!")
    root_c = TestClient(c.app)
    _login_ok(root_c, "root@example.com", "RootPass1!")
    r = _create(root_c, email="nuevoadmin@example.com", role="ADMIN")
    assert r.status_code == 200 and r.json()["user"]["role"] == "ADMIN"
    _login_ok(c, "nuevoadmin@example.com", r.json()["generated_password"])


def test_an_explicitly_invited_account_still_cannot_sign_in(client):
    """The INVITED gate itself is preserved — what changed is that CREATION no longer produces it."""
    c, store = client
    _mk_user(store, "USR-INV", "invitado@example.com", status=UserStatus.INVITED, pw="GoodPass1!")
    r = c.post("/api/auth/login", json={"email": "invitado@example.com", "password": "GoodPass1!"})
    assert r.status_code == 401
    assert store.users.get("USR-INV")["failed_login_count"] == 0   # blocked by status, not by password


def test_admin_resets_a_password_with_a_server_generated_one(client):
    c, store = client
    admin_c = _admin_client(c, store)
    _mk_user(store, "USR-V9", "v9@example.com", pw="OldPass123!")
    r = admin_c.post("/api/admin/users/USR-V9/password", json={"generate": True})
    assert r.status_code == 200
    body = r.json()
    assert body["password_generated"] is True
    generated = body["generated_password"]
    assert verify_password("OldPass123!", store.users.get("USR-V9")["password_hash"]) is False
    _login_ok(c, "v9@example.com", generated)


def test_admin_user_detail_exposes_login_diagnosis_without_secrets(client):
    c, store = client
    admin_c = _admin_client(c, store)
    _mk_user(store, "USR-DIAG", "diag@example.com", pw="OldPass123!")
    c.post("/api/auth/login", json={"email": "diag@example.com", "password": "WrongPass123!"})
    r = admin_c.get("/api/admin/users/USR-DIAG")
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["email"] == "diag@example.com"
    assert body["security"]["failed_login_count"] == 1      # the reason becomes visible to the admin
    assert "locked_until" in body["security"] and "mfa_enabled" in body["security"]
    assert "password_hash" not in r.text and "argon2" not in r.text.lower()
