"""
FastAPI authorization dependencies — role and ownership enforcement.

Usage in route handlers
-----------------------
    from app.core.permissions import AdminDep, require_roles

    @router.delete("/users/{user_id}")
    async def delete_user(admin: AdminDep) -> None: ...

    @router.get("/vendor/dashboard")
    async def vendor_dashboard(
        vendor: Annotated[UserResponse, Depends(require_roles(UserRole.VENDOR))],
    ) -> ...: ...

These dependencies enforce *who* may call a route. They do not perform any
business logic — they only gate access based on the resolved current user.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from app.core.current_user import CurrentUserDep, get_current_user
from app.models.enums import UserRole
from app.schemas.users.response import UserResponse


def _require(allowed: frozenset[UserRole]) -> Callable[..., UserResponse]:
    """Internal factory that creates a role-checking dependency."""

    async def _dep(current_user: CurrentUserDep) -> UserResponse:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource.",
            )
        return current_user

    return _dep


# ── Named role dependencies ───────────────────────────────────────────────────

async def require_admin(current_user: CurrentUserDep) -> UserResponse:
    """Dependency — requires ADMIN or SUPER_ADMIN role."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current_user


async def require_super_admin(current_user: CurrentUserDep) -> UserResponse:
    """Dependency — requires SUPER_ADMIN role exclusively."""
    if current_user.role is not UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super-admin access required.",
        )
    return current_user


async def require_vendor(current_user: CurrentUserDep) -> UserResponse:
    """Dependency — requires VENDOR role."""
    if current_user.role is not UserRole.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required.",
        )
    return current_user


async def require_customer(current_user: CurrentUserDep) -> UserResponse:
    """Dependency — requires CUSTOMER role."""
    if current_user.role is not UserRole.CUSTOMER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer access required.",
        )
    return current_user


async def require_staff(current_user: CurrentUserDep) -> UserResponse:
    """Dependency — requires ADMIN, SUPER_ADMIN, or SUPPORT role."""
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.SUPPORT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required.",
        )
    return current_user


# ── Composable factory ────────────────────────────────────────────────────────

def require_roles(*roles: UserRole) -> Callable[..., UserResponse]:
    """
    Factory — returns a dependency that accepts any of the given roles.

    Example:
        @router.get("/mixed")
        async def mixed(
            user: Annotated[UserResponse, Depends(require_roles(UserRole.ADMIN, UserRole.VENDOR))],
        ) -> ...: ...
    """
    allowed = frozenset(roles)
    return _require(allowed)


# ── Ownership enforcement ─────────────────────────────────────────────────────

def require_ownership(path_param: str = "user_id") -> Callable[..., None]:
    """
    Factory — returns a dependency that verifies the authenticated user owns
    the resource identified by a UUID path parameter.

    ADMIN and SUPER_ADMIN roles bypass the ownership check.

    Example:
        @router.get("/users/{user_id}/profile")
        async def get_profile(
            _: Annotated[None, Depends(require_ownership("user_id"))],
            user_id: uuid.UUID,
        ) -> ...: ...
    """

    async def _dep(
        current_user: CurrentUserDep,
        resource_owner_id: uuid.UUID = Path(alias=path_param),
    ) -> None:
        if current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
            return
        if current_user.id != resource_owner_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only access your own resources.",
            )

    return _dep


# ── Vendor-entity resolution ───────────────────────────────────────────────────

async def resolve_vendor_id_for_user(current_user: UserResponse) -> uuid.UUID:
    """
    Resolve the Vendor business-entity id owned by *current_user*.

    Plain async function (not a FastAPI dependency) so call sites that need
    to branch on role themselves — e.g. an endpoint shared between vendors
    and admins — can call it directly instead of going through `Depends`.
    """
    if current_user.role is not UserRole.VENDOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vendor access required.",
        )

    from app.repositories.unit_of_work import UnitOfWork

    async with UnitOfWork() as uow:
        vendor = await uow.vendors.vendors.find_by_user(current_user.id)
        if vendor is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No vendor profile exists for this account yet.",
            )
        return vendor.id


async def get_current_vendor_id(current_user: CurrentUserDep) -> uuid.UUID:
    """
    Dependency — resolves the Vendor business-entity id owned by the
    authenticated user.

    `current_user.id` is the User row's id, but Package/Booking/etc. all
    store the Vendor row's id as `vendor_id` (a distinct primary key). Every
    vendor-scoped write must use this, not `current_user.id` directly.
    """
    return await resolve_vendor_id_for_user(current_user)


# ── Admin-entity resolution ─────────────────────────────────────────────────────

async def get_current_admin_id(current_user: CurrentUserDep) -> uuid.UUID:
    """
    Dependency — resolves the Admin business-entity id owned by the
    authenticated user.

    `current_user.id` is the User row's id, but tables that record "which
    admin did this" (e.g. cms_import_logs.admin_id, cms_export_logs.admin_id)
    have a foreign key to `admins.id` — a distinct primary key — not to
    `users.id`. Passing current_user.id there directly fails with a foreign
    key violation.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )

    from app.repositories.unit_of_work import UnitOfWork

    async with UnitOfWork() as uow:
        admin = await uow.admin.admins.find_by_user(current_user.id)
        if admin is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No admin profile exists for this account yet.",
            )
        return admin.id


# ── Typed aliases ─────────────────────────────────────────────────────────────

AdminDep = Annotated[UserResponse, Depends(require_admin)]
SuperAdminDep = Annotated[UserResponse, Depends(require_super_admin)]
VendorDep = Annotated[UserResponse, Depends(require_vendor)]
CustomerDep = Annotated[UserResponse, Depends(require_customer)]
StaffDep = Annotated[UserResponse, Depends(require_staff)]
CurrentVendorIdDep = Annotated[uuid.UUID, Depends(get_current_vendor_id)]
CurrentAdminIdDep = Annotated[uuid.UUID, Depends(get_current_admin_id)]
