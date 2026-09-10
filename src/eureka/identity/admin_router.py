"""EUREKA Identity & Access — Admin HTTP surface (server-side RBAC).

Every /api/admin/* endpoint authenticates (session cookie) AND authorizes (require_role) server-side.
A USER calling these directly gets 403, never partial data. Reports are DERIVED from AuthEvent — the
single analytics authority — never a second counter.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from .deps import require_role
from .models import AdminRoleRequest, AdminStatusRequest, Role, User
from .service import (admin_create_user, change_role, list_users, login_report, set_status,
                      user_activity)
from .store import IdentityStore
from .models import AuthEvent


class AdminCreateUserRequest(BaseModel):
    name: str
    email: str
    phone: str = ""
    company: str = ""
    role: Role = Role.USER
    password: str


def make_admin_router(store: IdentityStore, config: Dict[str, Any]) -> APIRouter:
    r = APIRouter(tags=["admin"])
    require_admin = require_role(Role.ADMIN)
    require_super = require_role(Role.SUPER_ADMIN)

    @r.get("/api/admin/users")
    def users(limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
              search: str = "", role: Optional[str] = None, status: Optional[str] = None,
              _: User = Depends(require_admin)):
        return list_users(store, search=search, role=role, status=status, limit=limit, offset=offset)

    @r.get("/api/admin/users/export")
    def users_export(_: User = Depends(require_admin)):
        """Real .xlsx export (server-authoritative, admin-gated). Safe fields only — NEVER secrets."""
        import io
        from datetime import datetime, timezone
        from fastapi.responses import Response
        from openpyxl import Workbook

        data = list_users(store, limit=10000)["users"]
        wb = Workbook()
        ws = wb.active
        ws.title = "Users"
        headers = ["Name", "Email", "Phone", "Company", "Role", "Status",
                   "Last Login", "Created At", "Email Verified", "Phone Verified"]
        ws.append(headers)
        for u in data:
            ws.append([
                u.get("name", ""), u.get("email", ""), u.get("phone", ""), u.get("company", ""),
                u.get("role", ""), u.get("status", ""), u.get("last_login_at") or "",
                u.get("created_at") or "", bool(u.get("email_verified")), bool(u.get("phone_verified")),
            ])
        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        filename = f"eureka_users_{datetime.now(timezone.utc).strftime('%Y-%m-%d')}.xlsx"
        return Response(
            content=buf.read(),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @r.get("/api/admin/users/{user_id}")
    def get_user(user_id: str, _: User = Depends(require_admin)):
        from .service import _find_by_id
        u = _find_by_id(store, user_id)
        if u is None:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
        return {"user": u.public().model_dump(mode="json")}

    @r.post("/api/admin/users")
    def create_user(data: AdminCreateUserRequest, actor: User = Depends(require_admin)):
        try:
            u = admin_create_user(store, actor, name=data.name, email=data.email, phone=data.phone,
                                  company=data.company, role=data.role, password=data.password,
                                  password_policy=config["password_policy"])
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "user": u.model_dump(mode="json")}

    @r.post("/api/admin/users/{user_id}/role")
    def role_change(user_id: str, data: AdminRoleRequest, actor: User = Depends(require_admin)):
        try:
            u = change_role(store, actor, user_id, data.role,
                            superadmin_protection=config["superadmin_protection"])
        except ValueError as e:
            code = 400 if "PROTECTED" in str(e) or "EXISTS" in str(e) else 403
            raise HTTPException(status_code=code, detail=str(e))
        return {"ok": True, "user": u.model_dump(mode="json")}

    @r.post("/api/admin/users/{user_id}/status")
    def status_change(user_id: str, data: AdminStatusRequest, actor: User = Depends(require_admin)):
        try:
            u = set_status(store, actor, user_id, data.status)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"ok": True, "user": u.model_dump(mode="json")}

    @r.get("/api/admin/users/{user_id}/activity")
    def activity(user_id: str, _: User = Depends(require_admin)):
        try:
            return user_activity(store, user_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="USER_NOT_FOUND")

    @r.get("/api/admin/reports/logins")
    def report_logins(from_: Optional[str] = Query(None, alias="from"), to_: Optional[str] = Query(None, alias="to"),
                      aggregation: str = Query("day"), user_id: Optional[str] = None,
                      _: User = Depends(require_admin)):
        if aggregation not in ("day", "month"):
            raise HTTPException(status_code=400, detail="AGGREGATION_INVALID")
        if from_ and to_ and from_ > to_:
            raise HTTPException(status_code=400, detail="RANGE_INVALID")
        return login_report(store, from_iso=from_, to_iso=to_, aggregation=aggregation, user_id=user_id)

    @r.get("/api/admin/audit")
    def audit(limit: int = Query(200, ge=1, le=1000), _: User = Depends(require_admin)):
        events = [AuthEvent.model_validate(e).model_dump(mode="json") for e in store.events.values()]
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return {"total": len(events), "events": events[:limit]}

    @r.get("/api/admin/dashboard")
    def dashboard(_: User = Depends(require_admin)):
        from .service import _find_by_id
        users = [User.model_validate(u) for u in store.users.values()]
        active = sum(1 for u in users if u.status.value == "ACTIVE")
        login_events = [AuthEvent.model_validate(e) for e in store.events.values()
                        if e.get("event_type") == "LOGIN_SUCCESS"]
        today = current_day()
        this_month = today[:7]
        return {
            "users": len(users),
            "active_users": active,
            "logins_today": sum(1 for e in login_events if (e.timestamp or "")[:10] == today),
            "logins_this_month": sum(1 for e in login_events if (e.timestamp or "")[:7] == this_month),
            "users_by_company": _count_users_by(store, "company"),
        }

    return r


def current_day() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _count_users_by(store: IdentityStore, field: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for u in store.users.values():
        k = u.get(field) or "UNKNOWN"
        counts[k] = counts.get(k, 0) + 1
    return counts
