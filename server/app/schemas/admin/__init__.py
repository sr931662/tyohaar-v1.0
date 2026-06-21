"""Admin domain schemas — Admin, AdminRole, AdminPermission, AuditLog."""

from __future__ import annotations

from app.schemas.admin.common import PermissionCode
from app.schemas.admin.create import (
    AdminCreate,
    AdminRoleCreate,
    AdminPermissionCreate,
    AdminRolePermissionCreate,
    AuditLogCreate,
)
from app.schemas.admin.update import (
    AdminUpdate,
    AdminRoleUpdate,
    AdminPermissionUpdate,
)
from app.schemas.admin.response import (
    AdminResponse,
    AdminRoleResponse,
    AdminPermissionResponse,
    AuditLogResponse,
    AuditLogDetailResponse,
    AdminWithRoleResponse,
)
from app.schemas.admin.filters import (
    AdminFilters,
    AdminRoleFilters,
    AdminPermissionFilters,
    AuditLogFilters,
)
from app.schemas.admin.pagination import (
    AdminPage,
    AdminOffsetPage,
    AdminRolePage,
    AdminPermissionPage,
    AuditLogPage,
    AuditLogOffsetPage,
)
from app.schemas.admin.internal import (
    AdminInternal,
    AuditLogInternal,
    AdminRoleWithPermissions,
)

__all__ = [
    # common
    "PermissionCode",
    # create
    "AdminCreate",
    "AdminRoleCreate",
    "AdminPermissionCreate",
    "AdminRolePermissionCreate",
    "AuditLogCreate",
    # update
    "AdminUpdate",
    "AdminRoleUpdate",
    "AdminPermissionUpdate",
    # response
    "AdminResponse",
    "AdminRoleResponse",
    "AdminPermissionResponse",
    "AuditLogResponse",
    "AuditLogDetailResponse",
    "AdminWithRoleResponse",
    # filters
    "AdminFilters",
    "AdminRoleFilters",
    "AdminPermissionFilters",
    "AuditLogFilters",
    # pagination
    "AdminPage",
    "AdminOffsetPage",
    "AdminRolePage",
    "AdminPermissionPage",
    "AuditLogPage",
    "AuditLogOffsetPage",
    # internal
    "AdminInternal",
    "AuditLogInternal",
    "AdminRoleWithPermissions",
]
