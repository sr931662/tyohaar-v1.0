"""Admin service domain — AdminService, constants, helpers, validators, exceptions."""

from __future__ import annotations

from app.services.admin.service import AdminService
from app.services.admin.exceptions import (
    AdminNotFoundError,
    AdminEmailTakenError,
    AdminPasswordTooWeakError,
    AdminLockedError,
    AdminLoginFailedError,
    AdminInvalidTokenError,
    AdminPermissionDeniedError,
    AdminSelfDeactivationError,
    RoleNotFoundError,
    RoleInUseError,
    PermissionNotFoundError,
    PermissionAlreadyAssignedError,
)

__all__ = [
    "AdminService",
    "AdminNotFoundError",
    "AdminEmailTakenError",
    "AdminPasswordTooWeakError",
    "AdminLockedError",
    "AdminLoginFailedError",
    "AdminInvalidTokenError",
    "AdminPermissionDeniedError",
    "AdminSelfDeactivationError",
    "RoleNotFoundError",
    "RoleInUseError",
    "PermissionNotFoundError",
    "PermissionAlreadyAssignedError",
]
