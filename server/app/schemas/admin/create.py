"""
Admin domain — create (request body) schemas.

Used by POST endpoints to create Admin accounts, roles, permissions,
role-permission assignments, and audit log entries (service-layer only).
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from app.schemas.admin.common import PermissionCode
from app.schemas.base import BaseSchema

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z_]+\.[a-z_]+$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AdminCreate(BaseSchema):
    """
    Payload for granting admin access to an existing user account.

    The referenced user_id must already exist in the users table.
    Roles are validated against active AdminRole records by the service.
    """

    user_id: uuid.UUID = Field(
        description="Existing user account to promote to admin"
    )
    role_id: uuid.UUID = Field(
        description="AdminRole to assign to this admin"
    )
    employee_id: str | None = Field(
        default=None,
        max_length=50,
        description="Internal employee identifier (e.g. HR system ID)",
    )
    department: str | None = Field(
        default=None,
        max_length=100,
        description="Functional department (e.g. 'Operations', 'Finance')",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this admin account is currently active",
    )
    can_login: bool = Field(
        default=True,
        description="Whether this admin is allowed to authenticate to the panel",
    )


class AdminRoleCreate(BaseSchema):
    """
    Payload for creating a new admin role.

    System roles (is_system=True) are protected from deletion. Use
    is_system=False for all custom / client-created roles.
    """

    name: str = Field(
        min_length=2,
        max_length=100,
        description="Human-readable role name (e.g. 'Support Agent')",
    )
    slug: str = Field(
        min_length=2,
        max_length=100,
        description="URL-safe unique slug (e.g. 'support-agent')",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Description of this role's responsibilities",
    )
    is_system: bool = Field(
        default=False,
        description="System roles cannot be deleted; set True only for built-in roles",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not _SLUG_PATTERN.match(v):
            raise ValueError(
                "slug must be lowercase alphanumeric with hyphens (e.g. 'support-agent')"
            )
        return v


class AdminPermissionCreate(BaseSchema):
    """
    Payload for defining a new RBAC permission.

    code must follow 'resource.action' dot notation (e.g. 'users.ban').
    module and action are stored separately for query/filter efficiency.
    """

    code: PermissionCode = Field(
        description="Unique permission code in 'resource.action' format"
    )
    name: str = Field(
        min_length=3,
        max_length=200,
        description="Human-readable name (e.g. 'Ban Users')",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Description of what this permission grants",
    )
    module: str = Field(
        min_length=2,
        max_length=100,
        description="Resource module this permission applies to (e.g. 'users')",
    )
    action: str = Field(
        min_length=2,
        max_length=50,
        description="Action verb (e.g. 'read', 'write', 'ban', 'delete')",
    )

    @field_validator("code")
    @classmethod
    def validate_permission_code(cls, v: str) -> str:
        if not _PERMISSION_CODE_PATTERN.match(v):
            raise ValueError(
                "Permission code must be in 'resource.action' format "
                "(lowercase, dot-separated, e.g. 'bookings.read')"
            )
        return v.lower()

    @field_validator("module", "action")
    @classmethod
    def lowercase_fields(cls, v: str) -> str:
        return v.lower().strip()


class AdminRolePermissionCreate(BaseSchema):
    """
    Payload for assigning a permission to a role (junction record).

    The service layer enforces uniqueness of (role_id, permission_id).
    """

    role_id: uuid.UUID = Field(description="Role to assign the permission to")
    permission_id: uuid.UUID = Field(description="Permission to assign")


class AuditLogCreate(BaseSchema):
    """
    Internal service-layer payload for creating immutable audit log entries.

    This schema is NEVER exposed as a public API endpoint. It is called
    directly by service methods after performing state-changing operations.

    AuditLog records are immutable once created — no update schema exists.
    """

    actor_id: uuid.UUID = Field(
        description="Admin (or system) user who performed the action"
    )
    actor_type: str = Field(
        max_length=50,
        description="Type of actor: 'admin', 'system', or 'api'",
    )
    action: str = Field(
        max_length=200,
        description="Dot-notation action descriptor (e.g. 'booking.status.update')",
    )
    resource_type: str = Field(
        max_length=100,
        description="Entity type affected (e.g. 'booking', 'user', 'vendor')",
    )
    resource_id: uuid.UUID | None = Field(
        default=None,
        description="Primary key of the affected resource",
    )
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
        description="Request context: session_id, request_id, etc.",
    )
    ip_address: str | None = Field(
        default=None,
        max_length=45,
        description="Actor's IP address at action time",
    )
    user_agent: str | None = Field(
        default=None,
        description="HTTP User-Agent string from the request",
    )
    occurred_at: datetime = Field(
        description="Precise timestamp of the action (server time)"
    )


# ── Aliases and additional create schemas ─────────────────────────────────────

class AdminLoginCreate(BaseSchema):
    """Admin panel login credentials."""

    email: str = Field(max_length=255, description="Admin work email address")
    password: str = Field(min_length=8, description="Admin password")


class AdminPasswordChange(BaseSchema):
    """Payload for changing an admin's password."""

    old_password: str = Field(description="Current password for verification")
    new_password: str = Field(min_length=8, description="New password to set")


class AdminRoleAssign(BaseSchema):
    """Payload for assigning a role to an admin."""

    admin_id: uuid.UUID = Field(description="Admin account to update")
    role_id: uuid.UUID = Field(description="Role to assign")


class PermissionAssign(BaseSchema):
    """Payload for assigning a permission to a role."""

    role_id: uuid.UUID = Field(description="Role to grant the permission to")
    permission_id: uuid.UUID = Field(description="Permission to assign")


# Short-name aliases consumed by the admin controller
PermissionCreate = AdminPermissionCreate
RoleCreate = AdminRoleCreate
