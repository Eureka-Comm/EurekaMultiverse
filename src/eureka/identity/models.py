"""EUREKA Identity & Access — domain models.

USER IDENTITY is a distinct domain authority (rule 2): it is NOT canonical-state identity, NOT
cognitive authority, NOT CONSTELACIÓN. Every model here is a domain record; nothing here is ever
placed inside the cognitive graph or canonical fingerprint.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from .security import digest_token


class Role(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"


# Role priority for server-side RBAC (higher = more privilege).
ROLE_PRIORITY: Dict[Role, int] = {
    Role.USER: 1,
    Role.ADMIN: 2,
    Role.SUPER_ADMIN: 3,
}


class UserStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INVITED = "INVITED"
    SUSPENDED = "SUSPENDED"
    DISABLED = "DISABLED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"


class AuthEventType(str, Enum):
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    ACCOUNT_DISABLED = "ACCOUNT_DISABLED"
    ACCOUNT_ENABLED = "ACCOUNT_ENABLED"
    ROLE_CHANGED = "ROLE_CHANGED"
    MFA_ENABLED = "MFA_ENABLED"
    MFA_DISABLED = "MFA_DISABLED"
    MFA_FAILED = "MFA_FAILED"


class User(BaseModel):
    user_id: str
    name: str
    phone: str = ""
    email: str
    company: str = ""
    role: Role = Role.USER
    status: UserStatus = UserStatus.PENDING_VERIFICATION
    password_hash: str = ""            # NEVER returned to the client (Argon2id)
    email_verified: bool = False
    phone_verified: bool = False
    mfa_secret: Optional[str] = None   # NEVER returned to the client
    mfa_enabled: bool = False
    created_at: str = ""
    updated_at: str = ""
    last_login_at: Optional[str] = None
    failed_login_count: int = 0
    locked_until: Optional[str] = None

    def public(self) -> "SafeUser":
        """The ONLY user projection exposed over the API (no hash, no secret, no internal counters)."""
        return SafeUser(
            user_id=self.user_id, name=self.name, phone=self.phone, email=self.email,
            company=self.company, role=self.role.value, status=self.status.value,
            email_verified=self.email_verified, phone_verified=self.phone_verified,
            created_at=self.created_at, last_login_at=self.last_login_at,
        )


class SafeUser(BaseModel):
    user_id: str
    name: str
    phone: str
    email: str
    company: str
    role: str
    status: str
    email_verified: bool
    phone_verified: bool
    created_at: str
    last_login_at: Optional[str] = None


class Session(BaseModel):
    session_id: str
    user_id: str
    created_at: str
    expires_at: str
    last_seen_at: str
    revoked_at: Optional[str] = None
    csrf_token: str = ""
    ip: str = ""
    user_agent: str = ""
    mfa_verified: bool = False
    role_at_issue: str = ""   # role snapshot at issue time (server-side, never client)


class AuthEvent(BaseModel):
    event_id: str
    user_id: Optional[str] = None
    event_type: str
    timestamp: str
    success: bool
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ResetToken(BaseModel):
    token_id: str
    token_hash: str            # digest of the plaintext token (never store plaintext)
    user_id: str
    purpose: str = "password_reset"   # password_reset | verify_email
    created_at: str
    expires_at: str
    used: bool = False

    def matches(self, plaintext: str) -> bool:
        from .security import safe_token_cmp
        return safe_token_cmp(self.token_hash, digest_token(plaintext))


class MFAChallenge(BaseModel):
    challenge_id: str
    user_id: str
    created_at: str
    expires_at: str
    used: bool = False


# --------------------------------------------------------------------------- #
# Request contracts. The client NEVER supplies role/status/permissions/authority.
# --------------------------------------------------------------------------- #
class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field("", max_length=32)
    email: str
    company: str = Field("", max_length=200)
    password: str

    # Reject any client-supplied authority fields outright.
    @field_validator("role", "status", "permissions", "is_admin", "authority", check_fields=False)
    @classmethod
    def no_client_authority(cls, v):
        raise ValueError("client-supplied authority is not accepted")

    @field_validator("email")
    @classmethod
    def apply_email_policy(cls, v):
        from .service import normalize_email
        return normalize_email(v)


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class MfaSetupRequest(BaseModel):
    # Admin enables MFA (enrollment yields the shared secret; never logged).
    password: str


class MfaVerifyRequest(BaseModel):
    challenge_id: str
    code: str


class AdminUserUpdateRequest(BaseModel):
    role: Optional[Role] = None
    status: Optional[UserStatus] = None
    @field_validator("role", "status", check_fields=False)
    @classmethod
    def no_extra_authority(cls, v):
        return v


class AdminRoleRequest(BaseModel):
    role: Role


class AdminStatusRequest(BaseModel):
    status: UserStatus
