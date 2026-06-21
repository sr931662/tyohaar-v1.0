"""Admin service validators — raise domain exceptions on constraint violations."""

from __future__ import annotations

import re
from uuid import UUID

from app.models.admin.admin import Admin
from app.models.admin.permission import AdminPermission
from app.models.admin.role import AdminRole
from app.repositories.unit_of_work import UnitOfWork
from app.services.admin.constants import MIN_ADMIN_PASSWORD_LENGTH
from app.services.admin.exceptions import (
    AdminEmailTakenError,
    AdminLockedError,
    AdminNotFoundError,
    AdminPasswordTooWeakError,
    AdminPermissionDeniedError,
    PermissionNotFoundError,
    RoleNotFoundError,
)

_SPECIAL_CHAR_RE = re.compile(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]")


async def validate_admin_exists(admin_id: UUID, uow: UnitOfWork) -> Admin:
    """Fetch the Admin by PK; raise AdminNotFoundError if absent."""
    admin = await uow.admin.admins.get_by_id(admin_id)
    if admin is None:
        raise AdminNotFoundError("Admin", str(admin_id))
    return admin


async def validate_admin_email_unique(
    email: str,
    uow: UnitOfWork,
    exclude_id: UUID | None = None,
) -> None:
    """
    Raise AdminEmailTakenError if *email* is already assigned to a different admin.
    When *exclude_id* is provided, the admin with that id is exempt (for updates).
    """
    existing = await uow.admin.admins.find_by_work_email(email)
    if existing is None:
        return
    if exclude_id is not None and existing.id == exclude_id:
        return
    raise AdminEmailTakenError(
        f"Work email '{email}' is already associated with another admin."
    )


def validate_admin_password_strength(password: str) -> None:
    """
    Raise AdminPasswordTooWeakError unless the password meets all requirements:
    - At least MIN_ADMIN_PASSWORD_LENGTH characters
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    errors: list[str] = []
    if len(password) < MIN_ADMIN_PASSWORD_LENGTH:
        errors.append(
            f"Password must be at least {MIN_ADMIN_PASSWORD_LENGTH} characters."
        )
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter.")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one digit.")
    if not _SPECIAL_CHAR_RE.search(password):
        errors.append("Password must contain at least one special character.")
    if errors:
        raise AdminPasswordTooWeakError(" ".join(errors))


def validate_admin_not_locked(admin: Admin) -> None:
    """Raise AdminLockedError if the admin account is currently locked."""
    if admin.is_locked:
        locked_until = (
            admin.account_locked_until.isoformat()
            if admin.account_locked_until
            else None
        )
        raise AdminLockedError(
            "Admin account is temporarily locked due to too many failed login attempts.",
            locked_until=locked_until,
        )


async def validate_role_exists(role_id: UUID, uow: UnitOfWork) -> AdminRole:
    """Fetch the AdminRole by PK; raise RoleNotFoundError if absent."""
    role = await uow.admin.roles.get_by_id(role_id)
    if role is None:
        raise RoleNotFoundError("AdminRole", str(role_id))
    return role


async def validate_permission_exists(
    permission_id: UUID, uow: UnitOfWork
) -> AdminPermission:
    """Fetch the AdminPermission by PK; raise PermissionNotFoundError if absent."""
    permission = await uow.admin.permissions.get_by_id(permission_id)
    if permission is None:
        raise PermissionNotFoundError("AdminPermission", str(permission_id))
    return permission


async def validate_admin_has_permission(
    admin_id: UUID,
    permission_code: str,
    uow: UnitOfWork,
) -> None:
    """
    Raise AdminPermissionDeniedError if the admin's role does not include
    the given *permission_code*.
    """
    permissions = await uow.admin.permissions.find_for_role(
        (await validate_admin_exists(admin_id, uow)).role_id
    )
    codes = [p.code for p in permissions]
    if permission_code not in codes:
        raise AdminPermissionDeniedError(
            f"Admin does not have permission '{permission_code}'."
        )
