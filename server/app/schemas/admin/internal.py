"""Internal/full-detail admin schemas for service-layer and privileged endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from app.schemas.base import BaseSchema


class AdminInternal(BaseSchema):
    """
    Full admin record including permissions_override and soft-delete.
    Only for super-admin service operations.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    employee_id: str | None = None
    department: str | None = None
    is_active: bool
    can_login: bool
    last_active_at: datetime | None = None
    permissions_override: dict[str, Any] | None = None  # INTERNAL — custom permission overrides
    deleted_at: datetime | None = None  # INTERNAL — soft-delete
    created_at: datetime
    updated_at: datetime


class AuditLogInternal(BaseSchema):
    """
    Full audit log record including before/after state and request metadata.
    Only accessible to super-admin and audit report endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    actor_id: uuid.UUID
    actor_type: str
    action: str
    resource_type: str
    resource_id: uuid.UUID | None = None
    before_state: dict[str, Any] | None = None  # INTERNAL — full state diff
    after_state: dict[str, Any] | None = None   # INTERNAL — full state diff
    metadata: dict[str, Any] | None = None      # INTERNAL — request context
    ip_address: str | None = None
    user_agent: str | None = None
    occurred_at: datetime
    created_at: datetime


class AdminRoleWithPermissions(BaseSchema):
    """Admin role with all its assigned permissions expanded."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_system: bool
    is_active: bool
    permission_codes: list[str]  # e.g. ["bookings.read", "vendors.write"]
    created_at: datetime
