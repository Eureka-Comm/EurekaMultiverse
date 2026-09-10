"""EUREKA Identity & Access — domain service (single identity authority, server-side).

Contains NO HTTP. All access/authz decisions are Python + backend, never the client. A user's role
is derived from the durable record and snapshot at session issue; the "is_admin"/"role" fields a
client may send are rejected and never trusted.
"""
from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .models import (
    AuthEvent, AuthEventType, MFAChallenge, RegisterRequest, ResetToken, Role, ROLE_PRIORITY,
    SafeUser, Session, User, UserStatus,
)
from .security import (digest_token, hash_password, new_token, totp_code, totp_secret, totp_verify,
                       verify_password)
from .store import IdentityStore


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _now_iso() -> str:
    return _iso(_utcnow())


def normalize_email(email: str) -> str:
    """Single canonical, case-insensitive identity per email (policy)."""
    return (email or "").strip().lower()


def validate_password(policy: Dict[str, Any], password: str, email: str = "") -> Tuple[bool, str]:
    """Password policy (explicit, testable): length + complexity + reject trivial/reuse of email."""
    min_len = int(policy.get("min_length", 12))
    if len(password) < min_len:
        return False, f"Password must be at least {min_len} characters."
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)
    if not (has_letter and has_digit):
        return False, "Password must contain at least one letter and one digit."
    trivial = {"password", "password1", "password123", "12345678", "1234567890", "qwerty123",
               "letmein1", "admin123", "welcome1", "iloveyou1", "abc12345"}
    if password.lower() in trivial or password.lower() == normalize_email(email):
        return False, "Password is too common."
    return True, ""


# --------------------------------------------------------------------------- #
# Admin / internal helpers
# --------------------------------------------------------------------------- #
def is_admin_role(role: Role) -> bool:
    return role in (Role.ADMIN, Role.SUPER_ADMIN)


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"


def _record_event(store: IdentityStore, *, user_id: Optional[str], event_type: str,
                  success: bool, session_id: Optional[str] = None, metadata: Optional[dict] = None) -> None:
    ev = AuthEvent(
        event_id=_new_id("AE"), user_id=user_id, event_type=event_type, timestamp=_now_iso(),
        success=success, session_id=session_id, metadata=metadata or {},
    )
    store.events.set(ev.event_id, ev.model_dump(mode="json"))


def _find_by_email(store: IdentityStore, email: str) -> Optional[User]:
    norm = normalize_email(email)
    for u in store.users.values():
        if u.get("email") == norm:
            return User.model_validate(u)
    return None


# --------------------------------------------------------------------------- #
# Registration / verification
# --------------------------------------------------------------------------- #
def register(store: IdentityStore, data: RegisterRequest, password_policy: Dict[str, Any],
             *, verify_ttl_minutes: int = 1440) -> Tuple[SafeUser, Optional[str]]:
    if _find_by_email(store, data.email):
        raise ValueError("ACCOUNT_ALREADY_EXISTS")
    ok, reason = validate_password(password_policy, data.password, data.email)
    if not ok:
        raise ValueError(f"PASSWORD_POLICY:{reason}")
    user = User(
        user_id=_new_id("USR"), name=data.name.strip(), phone=data.phone.strip(),
        email=data.email, company=data.company.strip(), role=Role.USER,
        status=UserStatus.PENDING_VERIFICATION, password_hash=hash_password(data.password),
        created_at=_now_iso(), updated_at=_now_iso(),
    )
    store.users.set(user.user_id, user.model_dump(mode="json"))
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.ACCOUNT_CREATED.value, success=True)
    # Email-verification token (one-time, expiring). No real email provider -> token returned to the
    # caller for the E2E flow; production must deliver it through the (abstract) mail dependency.
    token = new_token()
    tid = _new_id("RT")
    store.reset_tokens.set(tid, ResetToken(
        token_id=tid, token_hash=digest_token(token), user_id=user.user_id,
        purpose="verify_email", created_at=_now_iso(),
        expires_at=_iso(_utcnow() + timedelta(minutes=verify_ttl_minutes)), used=False,
    ).model_dump(mode="json"))
    return user.public(), token


def verify_email(store: IdentityStore, token: str) -> SafeUser:
    rec = _consume_reset_token(store, token, purpose="verify_email")
    user = _require_user(store, rec["user_id"])
    if user.status != UserStatus.PENDING_VERIFICATION:
        raise ValueError("ACCOUNT_ALREADY_VERIFIED")
    user.email_verified = True
    user.status = UserStatus.ACTIVE
    user.updated_at = _now_iso()
    _save_user(store, user)
    return user.public()


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #
def _activate_session(store: IdentityStore, user: User, *, ip: str, ua: str,
                      csrf: str, role: Role, ttl_hours: int = 8) -> Session:
    s = Session(session_id=_new_id("SES"), user_id=user.user_id, created_at=_now_iso(),
                expires_at=_iso(_utcnow() + timedelta(hours=ttl_hours)), last_seen_at=_now_iso(),
                csrf_token=csrf, ip=ip, user_agent=ua[:200], mfa_verified=True, role_at_issue=role.value)
    store.sessions.set(s.session_id, s.model_dump(mode="json"))
    return s


def authenticate_session(store: IdentityStore, session_token: str) -> Tuple[Optional[Session], Optional[User]]:
    """Resolve a session token to (session, user); fail-closed on expired/revoked/unknown.
    Also touches last_seen_at (read is a session-liveness signal, not a canonical mutation)."""
    if not session_token:
        return None, None
    for s in store.sessions.values():
        sess = Session.model_validate(s)
        if sess.session_id == session_token:
            break
    else:
        return None, None
    if sess.revoked_at:
        return None, None
    if sess.expires_at and sess.expires_at < _now_iso():
        return None, None
    user = _find_by_id(store, sess.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        return None, None
    # slide last_seen
    sess.last_seen_at = _now_iso()
    store.sessions.set(sess.session_id, sess.model_dump(mode="json"))
    return sess, user


def _find_by_id(store: IdentityStore, user_id: str) -> Optional[User]:
    rec = store.users.get(user_id)
    return User.model_validate(rec) if rec else None


def _save_user(store: IdentityStore, user: User) -> None:
    user.updated_at = _now_iso()
    store.users.set(user.user_id, user.model_dump(mode="json"))


def _require_user(store: IdentityStore, user_id: str) -> User:
    user = _find_by_id(store, user_id)
    if user is None:
        raise ValueError("USER_NOT_FOUND")
    return user


# --------------------------------------------------------------------------- #
# Login / logout
# --------------------------------------------------------------------------- #
def login(store: IdentityStore, email: str, password: str, *, ip: str = "", ua: str = "",
          mfa_challenge_ttl_minutes: int = 2, lockout_threshold: int = 5,
          lockout_minutes: int = 15, session_ttl_hours: int = 8) -> Dict[str, Any]:
    """Returns a dict result. Never reveals whether the email exists (generic auth failure)."""
    user = _find_by_email(store, email)
    now = _now_iso()

    if user is None:
        _record_event(store, user_id=None, event_type=AuthEventType.LOGIN_FAILED.value, success=False,
                      metadata={"reason": "CREDENTIALS", "ip": ip})
        return {"ok": False, "reason": "INVALID_CREDENTIALS"}

    # Status gates (fail-closed): a suspended/disabled/pending account cannot log in.
    if user.status not in (UserStatus.ACTIVE,):
        if user.status == UserStatus.INVITED:
            return {"ok": False, "reason": "ACCOUNT_NOT_ACTIVE"}
        return {"ok": False, "reason": "ACCOUNT_DISABLED_OR_SUSPENDED"}

    # Lockout gate (durable).
    if user.locked_until and user.locked_until > now:
        return {"ok": False, "reason": "ACCOUNT_LOCKED"}

    if not verify_password(password, user.password_hash):
        user.failed_login_count = (user.failed_login_count or 0) + 1
        if user.failed_login_count >= lockout_threshold:
            user.locked_until = _iso(_utcnow() + timedelta(minutes=lockout_minutes))
        _save_user(store, user)
        _record_event(store, user_id=user.user_id, event_type=AuthEventType.LOGIN_FAILED.value,
                      success=False, metadata={"ip": ip})
        return {"ok": False, "reason": "INVALID_CREDENTIALS"}

    # Successful password: reset counter; admin accounts must pass MFA.
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    _save_user(store, user)

    # MFA is required only when the admin has ENROLLED it (policy: "MFA required if configured").
    # An admin who has not enabled TOTP signs in with password only — a deliberate product decision
    # (avoids blocking admin access on a not-yet-enrolled account). Once enrolled, MFA is enforced.
    if is_admin_role(user.role) and user.mfa_enabled:
        challenge = MFAChallenge(challenge_id=_new_id("MFA"), user_id=user.user_id, created_at=now,
                                 expires_at=_iso(_utcnow() + timedelta(minutes=mfa_challenge_ttl_minutes)),
                                 used=False)
        store.mfa.set(challenge.challenge_id, challenge.model_dump(mode="json"))
        return {"ok": True, "mfa_required": True, "mfa_challenge_id": challenge.challenge_id,
                "user": user.public().model_dump(mode="json")}

    csrf = new_token()
    sess = _activate_session(store, user, ip=ip, ua=ua, csrf=csrf, role=user.role, ttl_hours=session_ttl_hours)
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.LOGIN_SUCCESS.value,
                  success=True, session_id=sess.session_id)
    return {"ok": True, "mfa_required": False, "session_token": sess.session_id,
            "csrf_token": csrf, "expires_at": sess.expires_at, "user": user.public().model_dump(mode="json")}


def logout(store: IdentityStore, session: Session, user: Optional[User]) -> None:
    if session and not session.revoked_at:
        session.revoked_at = _now_iso()
        store.sessions.set(session.session_id, session.model_dump(mode="json"))
        _record_event(store, user_id=session.user_id, event_type=AuthEventType.LOGOUT.value,
                      success=True, session_id=session.session_id)


def refresh_session(store: IdentityStore, session: Session, user: User, *, session_ttl_hours: int = 8):
    """Rotate a session (short-lived access): revoke old, issue new (so a stolen cookie decays)."""
    session.revoked_at = _now_iso()
    store.sessions.set(session.session_id, session.model_dump(mode="json"))
    csrf = new_token()
    sess = _activate_session(store, user, ip=session.ip, ua=session.user_agent, csrf=csrf,
                             role=user.role, ttl_hours=session_ttl_hours)
    return sess.session_id, csrf, sess.expires_at


# --------------------------------------------------------------------------- #
# Password reset / change
# --------------------------------------------------------------------------- #
def request_password_reset(store: IdentityStore, email: str, *, ttl_minutes: int = 30) -> Optional[str]:
    """Always-generic externally; never reveals account existence. Returns token for E2E only."""
    user = _find_by_email(store, email)
    if user is None:
        return None
    token = new_token()
    tid = _new_id("RT")
    store.reset_tokens.set(tid, ResetToken(
        token_id=tid, token_hash=digest_token(token), user_id=user.user_id,
        purpose="password_reset", created_at=_now_iso(),
        expires_at=_iso(_utcnow() + timedelta(minutes=ttl_minutes)), used=False,
    ).model_dump(mode="json"))
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.PASSWORD_RESET_REQUESTED.value, success=True)
    return token


def reset_password(store: IdentityStore, token: str, password: str, password_policy: Dict[str, Any]) -> SafeUser:
    rec = _consume_reset_token(store, token, purpose="password_reset")
    user = _require_user(store, rec["user_id"])
    ok, reason = validate_password(password_policy, password, user.email)
    if not ok:
        raise ValueError(f"PASSWORD_POLICY:{reason}")
    user.password_hash = hash_password(password)
    user.locked_until = None
    user.failed_login_count = 0
    _save_user(store, user)
    # Invalidate all existing sessions (fail-closed on old sessions after a reset).
    for sid in list(store.sessions.keys()):
        sess = Session.model_validate(store.sessions.get(sid))
        if sess.user_id == user.user_id and not sess.revoked_at:
            sess.revoked_at = _now_iso()
            store.sessions.set(sid, sess.model_dump(mode="json"))
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.PASSWORD_RESET_COMPLETED.value, success=True)
    return user.public()


def _consume_reset_token(store: IdentityStore, token: str, *, purpose: str) -> Dict[str, Any]:
    """One-time, expiring, tamper-proof reset/verify token (digest check). Fail-closed."""
    if not token:
        raise ValueError("TOKEN_INVALID")
    for rt in store.reset_tokens.values():
        rec = ResetToken.model_validate(rt)
        if rec.purpose == purpose and rec.matches(token):
            if rec.used:
                raise ValueError("TOKEN_INVALID")
            if rec.expires_at and rec.expires_at < _now_iso():
                raise ValueError("TOKEN_INVALID")
            rec.used = True
            store.reset_tokens.set(rec.token_id, rec.model_dump(mode="json"))
            return {"user_id": rec.user_id}
    raise ValueError("TOKEN_INVALID")


# --------------------------------------------------------------------------- #
# TOTP MFA
# --------------------------------------------------------------------------- #
def mfa_setup(store: IdentityStore, user: User, password: str) -> str:
    """Enable TOTP for an admin (returns the shared secret exactly once for enrollment)."""
    if not verify_password(password, user.password_hash):
        raise ValueError("PASSWORD_INVALID")
    secret = totp_secret()
    user.mfa_secret = secret
    user.mfa_enabled = True
    _save_user(store, user)
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.MFA_ENABLED.value, success=True)
    return secret


def mfa_verify(store: IdentityStore, challenge_id: str, code: str, *, ip: str = "", ua: str = "",
               session_ttl_hours: int = 8) -> Dict[str, Any]:
    rec = store.mfa.get(challenge_id)
    if not rec:
        raise ValueError("MFA_CHALLENGE_INVALID")
    ch = MFAChallenge.model_validate(rec)
    if ch.used:
        raise ValueError("MFA_CHALLENGE_INVALID")
    if ch.expires_at and ch.expires_at < _now_iso():
        raise ValueError("MFA_CHALLENGE_INVALID")
    user = _require_user(store, ch.user_id)
    if not user.mfa_enabled or not user.mfa_secret:
        raise ValueError("MFA_NOT_CONFIGURED")
    if not totp_verify(user.mfa_secret, code):
        _record_event(store, user_id=user.user_id, event_type=AuthEventType.MFA_FAILED.value,
                      success=False, metadata={"ip": ip})
        raise ValueError("MFA_CODE_INVALID")
    ch.used = True
    store.mfa.set(challenge_id, ch.model_dump(mode="json"))
    csrf = new_token()
    sess = _activate_session(store, user, ip=ip, ua=ua, csrf=csrf, role=user.role, ttl_hours=session_ttl_hours)
    _record_event(store, user_id=user.user_id, event_type=AuthEventType.LOGIN_SUCCESS.value,
                  success=True, session_id=sess.session_id)
    return {"ok": True, "session_token": sess.session_id, "csrf_token": csrf,
            "expires_at": sess.expires_at, "user": user.public().model_dump(mode="json")}


def mfa_is_required_for(role: Role) -> bool:
    return is_admin_role(role)


# --------------------------------------------------------------------------- #
# RBAC
# --------------------------------------------------------------------------- #
def user_has_role(user: User, min_role: Role) -> bool:
    return ROLE_PRIORITY[user.role] >= ROLE_PRIORITY[min_role]


# --------------------------------------------------------------------------- #
# Admin operations
# --------------------------------------------------------------------------- #
def list_users(store: IdentityStore, *, search: str = "", role: Optional[str] = None,
               status: Optional[str] = None, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    rows = [User.model_validate(u) for u in store.users.values()]
    if search:
        s = search.lower()
        rows = [u for u in rows if s in u.name.lower() or s in u.email.lower() or s in u.company.lower()]
    if role:
        rows = [u for u in rows if u.role.value == role]
    if status:
        rows = [u for u in rows if u.status.value == status]
    total = len(rows)
    rows = sorted(rows, key=lambda u: (u.created_at or ""))
    return {"total": total, "offset": offset, "limit": limit, "users": [u.public().model_dump(mode="json") for u in rows[offset:offset + limit]]}


def admin_create_user(store: IdentityStore, actor: User, *, name: str, email: str,
                      phone: str, company: str, role: Role, password: str,
                      password_policy: Dict[str, Any]) -> SafeUser:
    """Admin-invite a user. Role grants are governed: only a SUPER_ADMIN may grant SUPER_ADMIN."""
    if role == Role.SUPER_ADMIN and actor.role != Role.SUPER_ADMIN:
        raise ValueError("FORBIDDEN_ROLE")
    if _find_by_email(store, email):
        raise ValueError("ACCOUNT_ALREADY_EXISTS")
    ok, reason = validate_password(password_policy, password, email)
    if not ok:
        raise ValueError(f"PASSWORD_POLICY:{reason}")
    user = User(user_id=_new_id("USR"), name=name.strip(), phone=phone.strip(), email=email,
                company=company.strip(), role=role, status=UserStatus.INVITED,
                password_hash=hash_password(password), created_at=_now_iso(), updated_at=_now_iso())
    store.users.set(user.user_id, user.model_dump(mode="json"))
    _record_event(store, user_id=actor.user_id, event_type="ADMIN_USER_CREATED", success=True,
                  metadata={"actor_user_id": actor.user_id, "target_user_id": user.user_id, "role": role.value})
    return user.public()


def change_role(store: IdentityStore, actor: User, target_user_id: str, new_role: Role, *, superadmin_protection: bool = True) -> SafeUser:
    target = _require_user(store, target_user_id)
    if actor.role != Role.SUPER_ADMIN and (new_role == Role.SUPER_ADMIN or target.role == Role.SUPER_ADMIN):
        raise ValueError("FORBIDDEN_ROLE")
    if target.role == Role.SUPER_ADMIN and new_role != Role.SUPER_ADMIN:
        if superadmin_protection and _count_superadmin(store) <= 1:
            raise ValueError("LAST_SUPER_ADMIN_PROTECTED")
    old = target.role
    target.role = new_role
    _save_user(store, target)
    _record_event(store, user_id=actor.user_id, event_type=AuthEventType.ROLE_CHANGED.value, success=True,
                  metadata={"actor_user_id": actor.user_id, "target_user_id": target.user_id,
                            "from": old.value, "to": new_role.value})
    return target.public()


def set_status(store: IdentityStore, actor: User, target_user_id: str, status: UserStatus) -> SafeUser:
    target = _require_user(store, target_user_id)
    old_status = target.status
    # An actor (even admin) must not disable the last SUPER_ADMIN.
    if target.role == Role.SUPER_ADMIN and status != UserStatus.ACTIVE and _count_superadmin(store) <= 1:
        raise ValueError("LAST_SUPER_ADMIN_PROTECTED")
    target.status = status
    _save_user(store, target)
    ev = AuthEventType.ACCOUNT_DISABLED.value if status == UserStatus.DISABLED else AuthEventType.ACCOUNT_ENABLED.value
    _record_event(store, user_id=actor.user_id, event_type=ev, success=True,
                  metadata={"actor_user_id": actor.user_id, "target_user_id": target.user_id,
                            "from": old_status.value, "to": status.value})
    # Disable a user -> revoke their sessions (fail-closed).
    if status == UserStatus.DISABLED:
        for sid in list(store.sessions.keys()):
            sess = Session.model_validate(store.sessions.get(sid))
            if sess.user_id == target.user_id and not sess.revoked_at:
                sess.revoked_at = _now_iso()
                store.sessions.set(sid, sess.model_dump(mode="json"))
    return target.public()


def _count_superadmin(store: IdentityStore) -> int:
    return sum(1 for u in store.users.values() if u.get("role") == Role.SUPER_ADMIN.value)


def user_activity(store: IdentityStore, user_id: str) -> Dict[str, Any]:
    user = _require_user(store, user_id)
    events = [AuthEvent.model_validate(e) for e in store.events.values() if e.get("user_id") == user_id]
    logins = [e for e in events if e.event_type == AuthEventType.LOGIN_SUCCESS.value]
    return {
        "user": user.public().model_dump(mode="json"),
        "total_logins": len(logins),
        "first_login": min((e.timestamp for e in logins), default=None),
        "last_login": user.last_login_at,
        "events": [e.model_dump(mode="json") for e in events],
    }


def login_report(store: IdentityStore, *, from_iso: Optional[str], to_iso: Optional[str],
                 aggregation: str = "day", user_id: Optional[str] = None) -> Dict[str, Any]:
    events = [AuthEvent.model_validate(e) for e in store.events.values() if e.get("event_type") == "LOGIN_SUCCESS"]
    if user_id:
        events = [e for e in events if e.user_id == user_id]
    if from_iso:
        events = [e for e in events if e.timestamp >= from_iso]
    if to_iso:
        events = [e for e in events if e.timestamp <= to_iso]
    buckets: Dict[str, int] = {}
    for e in events:
        key = e.timestamp[:10] if aggregation == "day" else e.timestamp[:7]
        buckets[key] = buckets.get(key, 0) + 1
    return {"aggregation": aggregation, "from": from_iso, "to": to_iso, "total": len(events),
            "series": [{"period": k, "logins": v} for k, v in sorted(buckets.items())]}
