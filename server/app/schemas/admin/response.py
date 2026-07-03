"""
Admin domain — API response schemas.

Security contract:
  - permissions_override (JSONB) is NEVER included in public AdminResponse
    (internal only; included in AdminInternal).
  - AuditLogResponse (list view) excludes before_state, after_state,
    metadata, and user_agent — too large and too sensitive for list views.
  - AuditLogDetailResponse (single record) includes everything for
    drill-down investigation by authorised admins only.
  - deleted_at is NEVER in any response schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field

from app.schemas.base import IDSchema


class AdminRoleResponse(IDSchema):
    """Public representation of an AdminRole."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    name: str = Field(description="Role display name")
    slug: str = Field(description="URL-safe unique slug")
    description: str | None = Field(default=None, description="Role description")
    is_system: bool = Field(description="True for built-in system roles")
    is_active: bool = Field(description="Whether this role is currently enabled")
    created_at: datetime = Field(description="When this role was created")


class AdminPermissionResponse(IDSchema):
    """Public representation of an AdminPermission definition."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    code: str = Field(description="Permission code in 'resource.action' format")
    name: str = Field(description="Human-readable permission name")
    description: str | None = Field(default=None, description="Permission description")
    module: str = Field(description="Resource module (e.g. 'bookings')")
    action: str = Field(description="Action verb (e.g. 'read', 'write')")
    is_active: bool = Field(description="Whether this permission is enabled")


class AdminResponse(IDSchema):
    """
    Public-safe representation of an Admin account.

    Excludes permissions_override (internal RBAC detail) and deleted_at.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID = Field(description="Associated user account ID")
    full_name: str | None = Field(default=None, description="Display name, from the linked User account")
    email: str | None = Field(default=None, description="Login email, from the linked User account")
    profile_photo_url: str | None = Field(
        default=None, description="Personal avatar, from the linked User's profile"
    )
    role_id: uuid.UUID = Field(description="Assigned admin role ID")
    employee_id: str | None = Field(default=None, description="Internal employee ID")
    department: str | None = Field(default=None, description="Department assignment")
    is_active: bool = Field(description="Whether this admin account is active")
    can_login: bool = Field(description="Whether this admin can log into the panel")
    last_active_at: datetime | None = Field(
        default=None,
        description="Most recent admin panel activity timestamp",
    )
    created_at: datetime = Field(description="When the admin record was created")


class AdminWithRoleResponse(AdminResponse):
    """
    Enriched admin view including role and effective permissions.

    Returned by GET /admin/{id}?expand=role,permissions.
    The permissions list reflects the role's assigned permissions
    (not the permissions_override diff — that is internal).
    """

    role: AdminRoleResponse = Field(description="Full role details")
    permissions: list[AdminPermissionResponse] = Field(
        default_factory=list,
        description="Effective permissions granted by the assigned role",
    )


class AuditLogResponse(IDSchema):
    """
    Lightweight audit log entry for list views.

    Excludes before_state, after_state, metadata, and user_agent which
    are too large and sensitive for paginated list responses. Use
    AuditLogDetailResponse for single-record drill-down.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    actor_id: uuid.UUID = Field(description="Admin who performed the action")
    actor_type: str = Field(description="'admin', 'system', or 'api'")
    action: str = Field(description="Dot-notation action descriptor")
    resource_type: str = Field(description="Entity type affected")
    resource_id: uuid.UUID | None = Field(
        default=None,
        description="Primary key of the affected resource",
    )
    ip_address: str | None = Field(
        default=None,
        description="Actor IP address",
    )
    occurred_at: datetime = Field(description="When the action occurred")
    created_at: datetime = Field(description="When the audit record was persisted")


class AuditLogDetailResponse(AuditLogResponse):
    """
    Full audit log detail for single-record investigative views.

    Authorised admins with 'audit_logs.read' permission may access this.
    Includes before/after state snapshots and full request metadata.
    """

    before_state: dict[str, Any] | None = Field(
        default=None,
        description="Full entity state snapshot before the action",
    )
    after_state: dict[str, Any] | None = Field(
        default=None,
        description="Full entity state snapshot after the action",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Request context metadata (session_id, request_id, etc.)",
    )
    user_agent: str | None = Field(
        default=None,
        description="HTTP User-Agent string from the request",
    )


# Alias consumed by the admin controller
AdminAuditLogResponse = AuditLogResponse
