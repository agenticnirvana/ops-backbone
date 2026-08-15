"""In-memory user directory + profile settings (demo — replace with IdP/DB in production)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel, Field

VALID_ROLES = ("admin", "operator", "viewer")
VALID_THEMES = ("light", "dark")

_DEFAULT_USERS: dict[str, dict[str, Any]] = {
    "operator@agentops.local": {
        "password": "operator123",
        "role": "operator",
        "name": "Ops Operator",
        "timezone": "Asia/Kolkata",
        "notify_hitl": True,
        "notify_pipeline": True,
        "theme_pref": "light",
    },
    "admin@agentops.local": {
        "password": "admin123",
        "role": "admin",
        "name": "Platform Admin",
        "timezone": "UTC",
        "notify_hitl": True,
        "notify_pipeline": True,
        "theme_pref": "dark",
    },
    "viewer@agentops.local": {
        "password": "viewer123",
        "role": "viewer",
        "name": "Read-only Viewer",
        "timezone": "America/New_York",
        "notify_hitl": False,
        "notify_pipeline": False,
        "theme_pref": "light",
    },
}

USERS: dict[str, dict[str, Any]] = deepcopy(_DEFAULT_USERS)


class UserProfile(BaseModel):
    email: str
    role: str
    name: str
    timezone: str = "UTC"
    notify_hitl: bool = True
    notify_pipeline: bool = True
    theme_pref: str = "light"


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    notify_hitl: bool | None = None
    notify_pipeline: bool | None = None
    theme_pref: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class AdminUserCreateRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: str
    name: str = Field(min_length=1, max_length=80)
    timezone: str = "UTC"


class AdminUserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    role: str | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    notify_hitl: bool | None = None
    notify_pipeline: bool | None = None
    theme_pref: str | None = None


def _to_profile(email: str, record: dict[str, Any]) -> UserProfile:
    return UserProfile(
        email=email,
        role=record["role"],
        name=record["name"],
        timezone=record.get("timezone", "UTC"),
        notify_hitl=bool(record.get("notify_hitl", True)),
        notify_pipeline=bool(record.get("notify_pipeline", True)),
        theme_pref=record.get("theme_pref", "light"),
    )


def get_user_record(email: str) -> dict[str, Any] | None:
    return USERS.get(email)


def get_user_profile(email: str) -> UserProfile | None:
    record = get_user_record(email)
    if not record:
        return None
    return _to_profile(email, record)


def verify_password(email: str, password: str) -> bool:
    record = get_user_record(email)
    return bool(record and record["password"] == password)


def update_profile(email: str, body: ProfileUpdateRequest) -> UserProfile:
    record = get_user_record(email)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    if body.name is not None:
        record["name"] = body.name.strip()
    if body.timezone is not None:
        record["timezone"] = body.timezone.strip()
    if body.notify_hitl is not None:
        record["notify_hitl"] = body.notify_hitl
    if body.notify_pipeline is not None:
        record["notify_pipeline"] = body.notify_pipeline
    if body.theme_pref is not None:
        if body.theme_pref not in VALID_THEMES:
            raise HTTPException(status_code=400, detail="theme_pref must be light or dark")
        record["theme_pref"] = body.theme_pref
    return _to_profile(email, record)


def change_password(email: str, body: ChangePasswordRequest) -> None:
    record = get_user_record(email)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    if record["password"] != body.current_password:
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="New password must differ from current password")
    record["password"] = body.new_password


def list_users_public() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for email, record in sorted(USERS.items()):
        rows.append(
            {
                "email": email,
                "role": record["role"],
                "name": record["name"],
                "timezone": record.get("timezone", "UTC"),
                "notify_hitl": bool(record.get("notify_hitl", True)),
                "notify_pipeline": bool(record.get("notify_pipeline", True)),
                "theme_pref": record.get("theme_pref", "light"),
            }
        )
    return rows


def create_user(body: AdminUserCreateRequest) -> dict[str, Any]:
    email = body.email.strip().lower()
    if email in USERS:
        raise HTTPException(status_code=409, detail="User already exists")
    if body.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(VALID_ROLES)}")
    USERS[email] = {
        "password": body.password,
        "role": body.role,
        "name": body.name.strip(),
        "timezone": body.timezone.strip() or "UTC",
        "notify_hitl": body.role != "viewer",
        "notify_pipeline": body.role != "viewer",
        "theme_pref": "light",
    }
    return list_users_public()[-1]


def update_user(email: str, body: AdminUserUpdateRequest) -> dict[str, Any]:
    key = email.strip().lower()
    record = get_user_record(key)
    if not record:
        raise HTTPException(status_code=404, detail="User not found")
    if body.role is not None:
        if body.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"role must be one of: {', '.join(VALID_ROLES)}")
        record["role"] = body.role
    if body.name is not None:
        record["name"] = body.name.strip()
    if body.password is not None:
        record["password"] = body.password
    if body.timezone is not None:
        record["timezone"] = body.timezone.strip()
    if body.notify_hitl is not None:
        record["notify_hitl"] = body.notify_hitl
    if body.notify_pipeline is not None:
        record["notify_pipeline"] = body.notify_pipeline
    if body.theme_pref is not None:
        if body.theme_pref not in VALID_THEMES:
            raise HTTPException(status_code=400, detail="theme_pref must be light or dark")
        record["theme_pref"] = body.theme_pref
    return _to_profile(key, record).model_dump()


def delete_user(email: str, *, actor_email: str) -> None:
    key = email.strip().lower()
    if key == actor_email.strip().lower():
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    if key not in USERS:
        raise HTTPException(status_code=404, detail="User not found")
    if len(USERS) <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last user")
    del USERS[key]


def user_counts_by_role() -> dict[str, int]:
    counts = {role: 0 for role in VALID_ROLES}
    for record in USERS.values():
        role = record.get("role", "viewer")
        counts[role] = counts.get(role, 0) + 1
    return counts
