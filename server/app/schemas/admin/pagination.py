"""Paginated response types for the admin domain."""

from __future__ import annotations

from app.schemas.base import CursorPage, OffsetPage
from app.schemas.admin.response import (
    AdminResponse,
    AdminRoleResponse,
    AdminPermissionResponse,
    AuditLogResponse,
)

AdminPage = CursorPage[AdminResponse]
AdminOffsetPage = OffsetPage[AdminResponse]
AdminRolePage = CursorPage[AdminRoleResponse]
AdminPermissionPage = CursorPage[AdminPermissionResponse]
AuditLogPage = CursorPage[AuditLogResponse]
AuditLogOffsetPage = OffsetPage[AuditLogResponse]
