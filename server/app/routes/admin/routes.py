"""
Admin Routes — admin auth, management, roles, permissions, and audit logs.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.admin import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.admin.response import (
    AdminAuditLogResponse,
    AdminPermissionResponse,
    AdminResponse,
    AdminRoleResponse,
)
from app.services.admin.service import AdminTokenResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

# ── Admin auth ────────────────────────────────────────────────────────────────

router.add_api_route(
    "/auth/login",
    ctrl.admin_login,
    methods=["POST"],
    response_model=SuccessResponse[AdminTokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Admin Login",
    description="Authenticate an admin user with email and password. Returns a JWT token pair.",
    operation_id="admin_auth_login",
)

router.add_api_route(
    "/auth/logout",
    ctrl.admin_logout,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Admin Logout",
    description="Invalidate the current admin session. Admin access required.",
    operation_id="admin_auth_logout",
)

router.add_api_route(
    "/auth/me",
    ctrl.verify_admin_token,
    methods=["GET"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Verify Admin Token",
    description="Verify the current admin token and return the authenticated admin's profile.",
    operation_id="admin_auth_verify_token",
)

# ── Permissions (static, must precede /roles/{role_id}/permissions) ───────────

router.add_api_route(
    "/permissions",
    ctrl.list_permissions,
    methods=["GET"],
    response_model=SuccessResponse[list[AdminPermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Permissions (Admin)",
    description="Return all registered permissions. Admin access required.",
    operation_id="admin_list_permissions",
)

router.add_api_route(
    "/permissions",
    ctrl.create_permission,
    methods=["POST"],
    response_model=SuccessResponse[AdminPermissionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Permission (Super Admin)",
    description="Create a new permission record. Super admin access required.",
    operation_id="admin_create_permission",
)

router.add_api_route(
    "/permissions/assign-to-role",
    ctrl.assign_permission_to_role,
    methods=["POST"],
    response_model=SuccessResponse[AdminRoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Permission to Role (Super Admin)",
    description="Grant a permission to a role. Super admin access required.",
    operation_id="admin_assign_permission_to_role",
)

# ── Roles ──────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/roles",
    ctrl.list_roles,
    methods=["GET"],
    response_model=SuccessResponse[list[AdminRoleResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Roles (Admin)",
    description="Return all admin roles. Admin access required.",
    operation_id="admin_list_roles",
)

router.add_api_route(
    "/roles",
    ctrl.create_role,
    methods=["POST"],
    response_model=SuccessResponse[AdminRoleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Role (Super Admin)",
    description="Create a new admin role. Super admin access required.",
    operation_id="admin_create_role",
)

router.add_api_route(
    "/roles/assign",
    ctrl.assign_role_to_admin,
    methods=["POST"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Assign Role to Admin (Super Admin)",
    description="Assign an admin role to an admin user. Super admin access required.",
    operation_id="admin_assign_role_to_admin",
)

router.add_api_route(
    "/roles/{role_id}",
    ctrl.get_role,
    methods=["GET"],
    response_model=SuccessResponse[AdminRoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Role (Admin)",
    description="Return a single admin role by ID. Admin access required.",
    operation_id="admin_get_role",
)

router.add_api_route(
    "/roles/{role_id}",
    ctrl.update_role,
    methods=["PUT"],
    response_model=SuccessResponse[AdminRoleResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Role (Super Admin)",
    description="Update an existing admin role. Super admin access required.",
    operation_id="admin_update_role",
)

router.add_api_route(
    "/roles/{role_id}",
    ctrl.delete_role,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Role (Super Admin)",
    description="Delete an admin role. Super admin access required.",
    operation_id="admin_delete_role",
)

router.add_api_route(
    "/roles/{role_id}/permissions/{permission_id}",
    ctrl.revoke_permission_from_role,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Revoke Permission from Role (Super Admin)",
    description="Remove a permission from a role. Super admin access required.",
    operation_id="admin_revoke_permission_from_role",
)

# ── Audit logs ────────────────────────────────────────────────────────────────

router.add_api_route(
    "/audit-logs/entity/{entity_id}",
    ctrl.get_audit_logs_for_entity,
    methods=["GET"],
    response_model=CursorPaginatedResponse[AdminAuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Audit Logs for Entity (Admin)",
    description="Return paginated audit logs for a specific entity. Pass `entity_type` as a query parameter. Admin access required.",
    operation_id="admin_get_audit_logs_for_entity",
)

router.add_api_route(
    "/audit-logs",
    ctrl.list_audit_logs,
    methods=["GET"],
    response_model=CursorPaginatedResponse[AdminAuditLogResponse],
    status_code=status.HTTP_200_OK,
    summary="List Audit Logs (Admin)",
    description="Return a paginated audit log of all admin actions. Admin access required.",
    operation_id="admin_list_audit_logs",
)

# ── Admin management ──────────────────────────────────────────────────────────

router.add_api_route(
    "/admins",
    ctrl.list_admins,
    methods=["GET"],
    response_model=CursorPaginatedResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="List Admins (Super Admin)",
    description="Return a cursor-paginated list of all admin accounts. Super admin access required.",
    operation_id="admin_list_admins",
)

router.add_api_route(
    "/admins",
    ctrl.create_admin,
    methods=["POST"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Admin (Super Admin)",
    description="Create a new admin account. Super admin access required.",
    operation_id="admin_create_admin",
)

router.add_api_route(
    "/admins/{admin_id}",
    ctrl.get_admin,
    methods=["GET"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Admin (Super Admin)",
    description="Return a single admin account by ID. Super admin access required.",
    operation_id="admin_get_admin",
)

router.add_api_route(
    "/admins/{admin_id}",
    ctrl.update_admin,
    methods=["PUT"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Admin (Super Admin)",
    description="Update an admin account. Super admin access required.",
    operation_id="admin_update_admin",
)

router.add_api_route(
    "/admins/{admin_id}/deactivate",
    ctrl.deactivate_admin,
    methods=["POST"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Deactivate Admin (Super Admin)",
    description="Soft-deactivate an admin account. Super admin access required.",
    operation_id="admin_deactivate_admin",
)

router.add_api_route(
    "/admins/{admin_id}/unlock",
    ctrl.unlock_admin,
    methods=["POST"],
    response_model=SuccessResponse[AdminResponse],
    status_code=status.HTTP_200_OK,
    summary="Unlock Admin (Super Admin)",
    description="Unlock a locked admin account after failed login attempts. Super admin access required.",
    operation_id="admin_unlock_admin",
)

router.add_api_route(
    "/admins/{admin_id}/change-password",
    ctrl.change_admin_password,
    methods=["POST"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Change Admin Password (Super Admin)",
    description="Force a password change for an admin account. Super admin access required.",
    operation_id="admin_change_admin_password",
)

router.add_api_route(
    "/admins/{admin_id}/permissions",
    ctrl.get_admin_permissions,
    methods=["GET"],
    response_model=SuccessResponse[list[AdminPermissionResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Admin Permissions (Admin)",
    description="Return the effective permissions for a specific admin. Admin access required.",
    operation_id="admin_get_admin_permissions",
)
