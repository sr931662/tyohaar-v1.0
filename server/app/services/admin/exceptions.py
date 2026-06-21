"""Admin domain service exceptions."""

from __future__ import annotations

from app.services.exceptions import (
    AccountLockedError,
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionError,
    ValidationError,
)


class AdminNotFoundError(NotFoundError):
    """Raised when the requested admin account does not exist."""


class AdminEmailTakenError(ConflictError):
    """Raised when a work_email is already associated with another admin."""


class AdminPasswordTooWeakError(ValidationError):
    """Raised when a proposed admin password fails strength requirements."""


class AdminLockedError(AccountLockedError):
    """Raised when an admin account is locked due to excessive failed logins."""


class AdminLoginFailedError(AuthenticationError):
    """Raised when admin login credentials are invalid."""


class AdminInvalidTokenError(AuthenticationError):
    """Raised when an admin session token is missing, expired, or invalid."""


class AdminPermissionDeniedError(PermissionError):
    """Raised when an admin lacks the required permission for an operation."""


class AdminSelfDeactivationError(BusinessRuleError):
    """Raised when an admin attempts to deactivate their own account."""


class RoleNotFoundError(NotFoundError):
    """Raised when the requested AdminRole does not exist."""


class RoleInUseError(ConflictError):
    """Raised when attempting to delete a role that still has admins assigned to it."""


class PermissionNotFoundError(NotFoundError):
    """Raised when the requested AdminPermission does not exist."""


class PermissionAlreadyAssignedError(ConflictError):
    """Raised when a permission is already assigned to the target role."""
