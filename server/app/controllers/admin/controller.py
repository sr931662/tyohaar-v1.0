"""
Updated Admin Controller — admin auth, management, roles, permissions, and audit logs.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Request

from app.core.current_user import CurrentUserDep
from app.core.dependencies import AdminServiceDep
from app.core.pagination import CursorPaginationParams, OffsetPaginationParams, get_cursor_pagination, get_offset_pagination
from app.core.permissions import AdminDep, SuperAdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, PaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.admin.create import (
    AdminCreate,
    AdminLoginCreate,
    AdminPasswordChange,
    AdminRoleAssign,
    PermissionAssign,
    PermissionCreate,
    RoleCreate,
)
from app.schemas.admin.response import (
    AdminAuditLogResponse,
    AdminPermissionResponse,
    AdminResponse,
    AdminRoleResponse,
)
from app.schemas.admin.update import AdminUpdate, RoleUpdate
from app.services.admin.service import AdminTokenResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Admin auth ────────────────────────────────────────────────────────────────

async def admin_login(
    body: AdminLoginCreate,
    service: AdminServiceDep,
    request: Request,
) -> SuccessResponse[AdminTokenResponse]:
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else None)
    result = await service.admin_login(email=body.email, password=body.password, ip_address=ip)
    return SuccessResponse(data=result, message="Admin login successful.")


async def admin_logout(
    current_user: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[None]:
    await service.admin_logout(admin_id=current_user.id)
    return SuccessResponse(data=None, message="Logged out.")


async def verify_admin_token(
    current_user: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.get_admin_by_user_id(user_id=current_user.id)
    return SuccessResponse(data=result, message="Token valid.")


# ── Admin management ──────────────────────────────────────────────────────────

async def create_admin(
    body: AdminCreate,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.create_admin(data=body, created_by=current_user.id)
    return SuccessResponse(data=result, message="Admin created.")


async def get_admin(
    admin_id: uuid.UUID,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.get_admin(admin_id=admin_id)
    return SuccessResponse(data=result, message="Admin retrieved.")


async def list_admins(
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> CursorPaginatedResponse[AdminResponse]:
    page = await service.list_admins(cursor=pagination.cursor, limit=pagination.page_size)
    return _cursor_resp(page, pagination.page_size)


async def update_admin(
    admin_id: uuid.UUID,
    body: AdminUpdate,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.update_admin(
        admin_id=admin_id, data=body, updated_by=current_user.id
    )
    return SuccessResponse(data=result, message="Admin updated.")


async def deactivate_admin(
    admin_id: uuid.UUID,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.deactivate_admin(
        admin_id=admin_id, deactivated_by=current_user.id
    )
    return SuccessResponse(data=result, message="Admin deactivated.")


async def change_admin_password(
    admin_id: uuid.UUID,
    body: AdminPasswordChange,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[None]:
    await service.change_admin_password(
        admin_id=admin_id, data=body, changed_by=current_user.id
    )
    return SuccessResponse(data=None, message="Password changed.")


async def unlock_admin(
    admin_id: uuid.UUID,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.unlock_admin(
        admin_id=admin_id, unlocked_by=current_user.id
    )
    return SuccessResponse(data=result, message="Admin unlocked.")


# ── Roles ──────────────────────────────────────────────────────────────────────

async def create_role(
    body: RoleCreate,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminRoleResponse]:
    result = await service.create_role(data=body)
    return SuccessResponse(data=result, message="Role created.")


async def get_role(
    role_id: uuid.UUID,
    _: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminRoleResponse]:
    result = await service.get_role(role_id=role_id)
    return SuccessResponse(data=result, message="Role retrieved.")


async def list_roles(
    _: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[list[AdminRoleResponse]]:
    roles = await service.list_roles()
    return SuccessResponse(data=roles, message="Roles retrieved.")


async def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminRoleResponse]:
    result = await service.update_role(role_id=role_id, data=body)
    return SuccessResponse(data=result, message="Role updated.")


async def delete_role(
    role_id: uuid.UUID,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[None]:
    await service.delete_role(role_id=role_id)
    return SuccessResponse(data=None, message="Role deleted.")


async def assign_role_to_admin(
    body: AdminRoleAssign,
    current_user: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminResponse]:
    result = await service.assign_role_to_admin(data=body, assigned_by=current_user.id)
    return SuccessResponse(data=result, message="Role assigned.")


# ── Permissions ───────────────────────────────────────────────────────────────

async def create_permission(
    body: PermissionCreate,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminPermissionResponse]:
    result = await service.create_permission(data=body)
    return SuccessResponse(data=result, message="Permission created.")


async def list_permissions(
    _: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[list[AdminPermissionResponse]]:
    permissions = await service.list_permissions()
    return SuccessResponse(data=permissions, message="Permissions retrieved.")


async def assign_permission_to_role(
    body: PermissionAssign,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[AdminRoleResponse]:
    result = await service.assign_permission_to_role(data=body)
    return SuccessResponse(data=result, message="Permission assigned to role.")


async def revoke_permission_from_role(
    role_id: uuid.UUID,
    permission_id: uuid.UUID,
    _: SuperAdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[None]:
    await service.revoke_permission_from_role(role_id=role_id, permission_id=permission_id)
    return SuccessResponse(data=None, message="Permission revoked.")


async def get_admin_permissions(
    admin_id: uuid.UUID,
    _: AdminDep,
    service: AdminServiceDep,
) -> SuccessResponse[list[AdminPermissionResponse]]:
    permissions = await service.get_admin_permissions(admin_id=admin_id)
    return SuccessResponse(data=permissions, message="Permissions retrieved.")


# ── Audit logs ────────────────────────────────────────────────────────────────

async def list_audit_logs(
    pagination: Annotated[OffsetPaginationParams, Depends(get_offset_pagination)],
    _: AdminDep,
    service: AdminServiceDep,
) -> PaginatedResponse[AdminAuditLogResponse]:
    result = await service.list_audit_logs(page=pagination.page, page_size=pagination.page_size)
    return result


async def get_audit_logs_for_entity(
    entity_id: uuid.UUID,
    entity_type: str,
    pagination: Annotated[OffsetPaginationParams, Depends(get_offset_pagination)],
    _: AdminDep,
    service: AdminServiceDep,
) -> PaginatedResponse[AdminAuditLogResponse]:
    result = await service.get_audit_logs_for_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        page=pagination.page,
        page_size=pagination.page_size,
    )
    return result
