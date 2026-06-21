"""
Admin domain — update (PATCH request body) schemas.

All fields are optional; only provided fields are applied.
AuditLog records are immutable — no update schema exists for them.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema

_SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class AdminUpdate(BaseSchema):
    """
    Partial update payload for an Admin record.

    permissions_override is a JSONB blob for custom permission grants or
    revocations that differ from the base role. The service merges this
    with the role's effective permission set at authorisation time.
    """

    role_id: uuid.UUID | None = Field(
        default=None,
        description="New role to assign; clears role-level permissions",
    )
    employee_id: str | None = Field(
        default=None,
        max_length=50,
        description="Updated employee identifier",
    )
    department: str | None = Field(
        default=None,
        max_length=100,
        description="Updated department assignment",
    )
    is_active: bool | None = Field(
        default=None,
        description="Activate or deactivate this admin account",
    )
    can_login: bool | None = Field(
        default=None,
        description="Allow or block panel login for this admin",
    )
    permissions_override: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Custom permission overrides beyond the base role. "
            "Keys are permission codes; values are True (grant) or False (revoke)."
        ),
    )


class AdminRoleUpdate(BaseSchema):
    """
    Partial update payload for an AdminRole.

    is_system cannot be changed via this schema — system flag is set
    only at creation time to prevent accidental unlocking of system roles.
    """

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Updated role display name",
    )
    slug: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
        description="Updated URL-safe slug",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated role description",
    )
    is_active: bool | None = Field(
        default=None,
        description="Enable or disable this role",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str | None) -> str | None:
        if v is not None and not _SLUG_PATTERN.match(v):
            raise ValueError(
                "slug must be lowercase alphanumeric with hyphens (e.g. 'support-agent')"
            )
        return v


class AdminPermissionUpdate(BaseSchema):
    """
    Partial update payload for an AdminPermission.

    code and module/action cannot be changed after creation — update
    is_active to False and create a new permission if the code changes.
    """

    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=200,
        description="Updated human-readable permission name",
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated description",
    )
    is_active: bool | None = Field(
        default=None,
        description="Enable or disable this permission definition",
    )


# Short-name alias consumed by the admin controller
RoleUpdate = AdminRoleUpdate
