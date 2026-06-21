"""Filter/query-parameter schemas for admin domain list endpoints."""

from __future__ import annotations

import uuid
from pydantic import Field
from app.schemas.base import BaseSchema


class AdminFilters(BaseSchema):
    """Query parameters for listing admin users."""

    role_id: uuid.UUID | None = None
    department: str | None = None
    is_active: bool | None = None
    can_login: bool | None = None
    search: str | None = Field(default=None, description="Search by employee_id or username")


class AdminRoleFilters(BaseSchema):
    """Query parameters for listing admin roles."""

    is_active: bool | None = None
    is_system: bool | None = None
    search: str | None = None


class AdminPermissionFilters(BaseSchema):
    """Query parameters for listing admin permissions."""

    module: str | None = None
    action: str | None = None
    is_active: bool | None = None
    search: str | None = None


class AuditLogFilters(BaseSchema):
    """Query parameters for listing audit log entries."""

    actor_id: uuid.UUID | None = None
    actor_type: str | None = None
    action: str | None = Field(default=None, description="Partial match on action string")
    resource_type: str | None = None
    resource_id: uuid.UUID | None = None
    from_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter occurred_at >= from_date (YYYY-MM-DD)",
    )
    to_date: str | None = Field(
        default=None,
        pattern=r"^\d{4}-\d{2}-\d{2}$",
        description="Filter occurred_at <= to_date (YYYY-MM-DD)",
    )
    ip_address: str | None = None
