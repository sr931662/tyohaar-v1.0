"""
AdminService — authentication, CRUD, roles, permissions, and audit log for the admin panel.

Security contract:
- Passwords are stored as HMAC-SHA256 hashes; plaintext is never persisted.
- Session tokens are stored as SHA-256 hashes; only the raw token is returned to the caller.
- AuditLog is IMMUTABLE — write_audit_log wraps the append in try/except so that
  an audit failure never blocks the primary business operation.
- NEVER expose: password_hash, token_hash, deleted_at, account_locked_until internals.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import AdminStatus, AuditAction
from app.schemas.admin import (
    AdminCreate,
    AdminPermissionCreate,
    AdminResponse,
    AdminRoleCreate,
    AdminRoleResponse,
    AdminPermissionResponse,
    AdminUpdate,
    AdminRoleUpdate,
    AdminPermissionUpdate,
    AuditLogFilters,
    AuditLogResponse,
)
from app.schemas.base import CursorPage
from app.services.admin.constants import (
    ADMIN_LOCKOUT_DURATION_MINUTES,
    DEFAULT_PAGE_SIZE,
    MAX_FAILED_LOGIN_ATTEMPTS,
    MAX_PAGE_SIZE,
)
from app.services.admin.exceptions import (
    AdminEmailTakenError,
    AdminInvalidTokenError,
    AdminLoginFailedError,
    AdminLockedError,
    AdminNotFoundError,
    AdminSelfDeactivationError,
    PermissionAlreadyAssignedError,
    PermissionNotFoundError,
    RoleInUseError,
    RoleNotFoundError,
)
from app.core.security import decode_access_token
from app.services.admin.helpers import (
    hash_admin_password,
    verify_admin_password,
)
from app.services.admin.validators import (
    validate_admin_email_unique,
    validate_admin_exists,
    validate_admin_not_locked,
    validate_admin_password_strength,
    validate_permission_exists,
    validate_role_exists,
)
from app.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class AdminTokenResponse:
    """Returned by admin_login — contains the raw (unhashed) session token."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int = 28800  # 8 hours
    admin_id: UUID | None = None


class AdminService(BaseService):
    def __init__(
        self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
    ) -> None:
        super().__init__(session_factory)

    # ── Authentication ────────────────────────────────────────────────────────

    async def admin_login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
    ) -> AdminTokenResponse:
        try:
            async with self._uow() as uow:
                # Look up user by email first (credentials live on User, not Admin)
                user = await uow.users.users.find_by_email(email)
                if user is None:
                    raise AdminLoginFailedError("Invalid email or password.")

                admin = await uow.admin.admins.find_by_user(user.id)
                if admin is None:
                    raise AdminLoginFailedError("Invalid email or password.")

                validate_admin_not_locked(admin)

                stored_hash = getattr(user, "password_hash", None) or ""
                if not verify_admin_password(password, stored_hash):
                    await uow.admin.admins.increment_failed_login(admin.id)
                    new_count = admin.failed_login_count + 1
                    if new_count >= MAX_FAILED_LOGIN_ATTEMPTS:
                        locked_until = datetime.now(tz=timezone.utc) + timedelta(
                            minutes=ADMIN_LOCKOUT_DURATION_MINUTES
                        )
                        await uow.admin.admins.update(
                            admin,
                            {
                                "account_locked_until": locked_until,
                                "failed_login_count": new_count,
                            },
                        )
                    await uow.commit()
                    raise AdminLoginFailedError("Invalid email or password.")

                # Successful login — reset counters and record last login
                await uow.admin.admins.reset_failed_login(admin.id)
                await uow.admin.admins.update_last_login(admin.id, ip_address=ip_address)

                admin_id = admin.id
                admin_user_id = admin.user_id

                await uow.commit()
        except (AdminLoginFailedError, AdminLockedError):
            raise
        except Exception as exc:
            logger.error("admin_login DB error for %s: %s", email, exc)
            raise AdminLoginFailedError("Login service temporarily unavailable. Please try again.") from exc

        # Issue a real, revocable session (access + refresh token pair) via the
        # shared AuthService rather than a bare stateless JWT, so admin sessions
        # can be silently refreshed the same way vendor/customer sessions are.
        from app.models.enums import LoginMethod
        from app.services.auth.service import AuthService

        tokens = await AuthService().create_session_for_user_id(
            admin_user_id, ip_address=ip_address, login_method=LoginMethod.EMAIL_PASSWORD
        )

        await self.write_audit_log(
            admin_id=admin_id,
            action=AuditAction.LOGIN,
            entity_type="admin",
            entity_id=str(admin_id),
            changes=None,
            ip_address=ip_address,
            user_agent=None,
        )

        return AdminTokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        )

    async def admin_logout(self, admin_id: UUID) -> None:
        # JWT is stateless — client discards the token on logout.
        await self.write_audit_log(
            admin_id=admin_id,
            action=AuditAction.LOGOUT,
            entity_type="admin",
            entity_id=str(admin_id),
            changes=None,
            ip_address=None,
            user_agent=None,
        )

    async def verify_admin_token(self, token: str) -> AdminResponse:
        user_id_str = decode_access_token(token)
        if user_id_str is None:
            raise AdminInvalidTokenError("Admin session token is invalid or expired.")
        async with self._uow() as uow:
            from uuid import UUID as _UUID
            user_id = _UUID(user_id_str)
            admin = await uow.admin.admins.find_by_user(user_id)
            if admin is None:
                raise AdminInvalidTokenError("Admin account not found for this token.")
            return AdminResponse.model_validate(admin)

    # ── Admin CRUD ────────────────────────────────────────────────────────────

    async def create_admin(
        self,
        data: AdminCreate,
        created_by_id: UUID,
    ) -> AdminResponse:
        async with self._uow() as uow:
            await validate_admin_email_unique(data.work_email, uow)

            if data.role_id:
                await validate_role_exists(data.role_id, uow)

            payload = data.model_dump(exclude_unset=True)
            admin = await uow.admin.admins.create(payload)
            await uow.commit()
            result = AdminResponse.model_validate(admin)

        await self.write_audit_log(
            admin_id=created_by_id,
            action=AuditAction.CREATE,
            entity_type="admin",
            entity_id=str(admin.id),
            changes={"user_id": str(data.user_id), "role_id": str(data.role_id)},
            ip_address=None,
            user_agent=None,
        )
        return result

    async def get_admin(self, admin_id: UUID) -> AdminResponse:
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            return AdminResponse.model_validate(admin)

    async def get_admin_by_user_id(self, user_id: UUID) -> AdminResponse:
        async with self._uow() as uow:
            admin = await uow.admin.admins.find_by_user(user_id)
            if admin is None:
                raise AdminNotFoundError(f"Admin not found for user {user_id}.")

            response = AdminResponse.model_validate(admin)
            user = await uow.users.users.get_with_profile(user_id)
            if user is not None:
                response.full_name = user.full_name
                response.email = user.email
                profile = getattr(user, "profile", None)
                response.profile_photo_url = getattr(profile, "profile_photo_url", None)
            return response

    async def list_admins(
        self,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> CursorPage[AdminResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            admins = await uow.admin.admins.find_many(
                order_by=None,
                skip=0,
                limit=limit,
            )
            items = [AdminResponse.model_validate(a) for a in admins]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def update_admin(
        self,
        admin_id: UUID,
        data: AdminUpdate,
        updated_by_id: UUID,
    ) -> AdminResponse:
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            payload = data.model_dump(exclude_unset=True)
            updated = await uow.admin.admins.update(admin, payload)
            await uow.commit()
            result = AdminResponse.model_validate(updated)

        await self.write_audit_log(
            admin_id=updated_by_id,
            action=AuditAction.UPDATE,
            entity_type="admin",
            entity_id=str(admin_id),
            changes=payload,
            ip_address=None,
            user_agent=None,
        )
        return result

    async def deactivate_admin(
        self,
        admin_id: UUID,
        deactivated_by_id: UUID,
    ) -> None:
        if admin_id == deactivated_by_id:
            raise AdminSelfDeactivationError(
                "Admins cannot deactivate their own account."
            )
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            await uow.admin.admins.update(
                admin, {"admin_status": AdminStatus.DEACTIVATED}
            )
            await uow.commit()

        await self.write_audit_log(
            admin_id=deactivated_by_id,
            action=AuditAction.UPDATE,
            entity_type="admin",
            entity_id=str(admin_id),
            changes={"admin_status": AdminStatus.DEACTIVATED.value},
            ip_address=None,
            user_agent=None,
        )

    async def change_admin_password(
        self,
        admin_id: UUID,
        old_password: str,
        new_password: str,
    ) -> None:
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            user = await uow.users.users.get_by_id(admin.user_id)
            if user is None or not verify_admin_password(
                old_password, getattr(user, "password_hash", "")
            ):
                raise AdminLoginFailedError("Current password is incorrect.")
            validate_admin_password_strength(new_password)
            new_hash = hash_admin_password(new_password)
            await uow.users.users.update(user, {"password_hash": new_hash})
            await uow.commit()

        await self.write_audit_log(
            admin_id=admin_id,
            action=AuditAction.UPDATE,
            entity_type="admin",
            entity_id=str(admin_id),
            changes={},
            ip_address=None,
            user_agent=None,
        )

    # ── Roles ─────────────────────────────────────────────────────────────────

    async def create_role(
        self,
        data: AdminRoleCreate,
        created_by_id: UUID,
    ) -> AdminRoleResponse:
        async with self._uow() as uow:
            role = await uow.admin.roles.create(data.model_dump(exclude_unset=True))
            await uow.commit()
            result = AdminRoleResponse.model_validate(role)

        await self.write_audit_log(
            admin_id=created_by_id,
            action=AuditAction.CREATE,
            entity_type="admin_role",
            entity_id=str(role.id),
            changes={"name": data.name, "slug": data.slug},
            ip_address=None,
            user_agent=None,
        )
        return result

    async def get_role(self, role_id: UUID) -> AdminRoleResponse:
        async with self._uow() as uow:
            role = await uow.admin.roles.get_with_permissions(role_id)
            if role is None:
                raise RoleNotFoundError("AdminRole", str(role_id))
            return AdminRoleResponse.model_validate(role)

    async def list_roles(self) -> list[AdminRoleResponse]:
        async with self._uow() as uow:
            roles = await uow.admin.roles.find_active()
            return [AdminRoleResponse.model_validate(r) for r in roles]

    async def update_role(
        self,
        role_id: UUID,
        data: AdminRoleUpdate,
        updated_by_id: UUID,
    ) -> AdminRoleResponse:
        async with self._uow() as uow:
            role = await validate_role_exists(role_id, uow)
            payload = data.model_dump(exclude_unset=True)
            updated = await uow.admin.roles.update(role, payload)
            await uow.commit()
            result = AdminRoleResponse.model_validate(updated)

        await self.write_audit_log(
            admin_id=updated_by_id,
            action=AuditAction.UPDATE,
            entity_type="admin_role",
            entity_id=str(role_id),
            changes=payload,
            ip_address=None,
            user_agent=None,
        )
        return result

    async def delete_role(self, role_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            role = await validate_role_exists(role_id, uow)
            assigned = await uow.admin.admins.find_by_role(role_id, limit=1)
            if assigned:
                raise RoleInUseError(
                    f"Role '{role.name}' cannot be deleted while admins are assigned to it."
                )
            await uow.admin.roles.delete(role)
            await uow.commit()

        await self.write_audit_log(
            admin_id=admin_id,
            action=AuditAction.DELETE,
            entity_type="admin_role",
            entity_id=str(role_id),
            changes={"name": role.name},
            ip_address=None,
            user_agent=None,
        )

    async def assign_role_to_admin(
        self,
        admin_id: UUID,
        role_id: UUID,
        assigned_by_id: UUID,
    ) -> AdminResponse:
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            await validate_role_exists(role_id, uow)
            updated = await uow.admin.admins.update(admin, {"role_id": role_id})
            await uow.commit()
            result = AdminResponse.model_validate(updated)

        await self.write_audit_log(
            admin_id=assigned_by_id,
            action=AuditAction.ASSIGN,
            entity_type="admin",
            entity_id=str(admin_id),
            changes={"role_id": str(role_id)},
            ip_address=None,
            user_agent=None,
        )
        return result

    # ── Permissions ───────────────────────────────────────────────────────────

    async def create_permission(
        self,
        data: AdminPermissionCreate,
        created_by_id: UUID,
    ) -> AdminPermissionResponse:
        async with self._uow() as uow:
            perm = await uow.admin.permissions.create(
                data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            result = AdminPermissionResponse.model_validate(perm)

        await self.write_audit_log(
            admin_id=created_by_id,
            action=AuditAction.CREATE,
            entity_type="admin_permission",
            entity_id=str(perm.id),
            changes={"code": data.code},
            ip_address=None,
            user_agent=None,
        )
        return result

    async def list_permissions(self) -> list[AdminPermissionResponse]:
        async with self._uow() as uow:
            perms = await uow.admin.permissions.find_active()
            return [AdminPermissionResponse.model_validate(p) for p in perms]

    async def assign_permission_to_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        assigned_by_id: UUID,
    ) -> AdminRoleResponse:
        async with self._uow() as uow:
            role = await validate_role_exists(role_id, uow)
            await validate_permission_exists(permission_id, uow)

            existing = await uow.admin.role_permissions.find_grant(
                role_id, permission_id
            )
            if existing is not None:
                raise PermissionAlreadyAssignedError(
                    "Permission is already assigned to this role."
                )

            await uow.admin.role_permissions.create(
                {"role_id": role_id, "permission_id": permission_id}
            )
            await uow.commit()

            updated_role = await uow.admin.roles.get_with_permissions(role_id)
            result = AdminRoleResponse.model_validate(updated_role)

        await self.write_audit_log(
            admin_id=assigned_by_id,
            action=AuditAction.ASSIGN,
            entity_type="admin_role",
            entity_id=str(role_id),
            changes={"permission_id": str(permission_id)},
            ip_address=None,
            user_agent=None,
        )
        return result

    async def revoke_permission_from_role(
        self,
        role_id: UUID,
        permission_id: UUID,
        admin_id: UUID,
    ) -> AdminRoleResponse:
        async with self._uow() as uow:
            role = await validate_role_exists(role_id, uow)
            grant = await uow.admin.role_permissions.find_grant(role_id, permission_id)
            if grant is None:
                raise PermissionNotFoundError(
                    "Permission is not assigned to this role."
                )
            await uow.admin.role_permissions.delete(grant)
            await uow.commit()

            updated_role = await uow.admin.roles.get_with_permissions(role_id)
            result = AdminRoleResponse.model_validate(updated_role)

        await self.write_audit_log(
            admin_id=admin_id,
            action=AuditAction.REVOKE,
            entity_type="admin_role",
            entity_id=str(role_id),
            changes={"permission_id": str(permission_id)},
            ip_address=None,
            user_agent=None,
        )
        return result

    async def get_admin_permissions(self, admin_id: UUID) -> list[str]:
        """Return flat list of permission codes for the admin's assigned role."""
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            permissions = await uow.admin.permissions.find_for_role(admin.role_id)
            return [p.code for p in permissions]

    # ── Audit Log (IMMUTABLE — append-only) ───────────────────────────────────

    async def write_audit_log(
        self,
        admin_id: UUID | None,
        action: str,
        entity_type: str,
        entity_id: str | None,
        changes: dict[str, Any] | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        """
        Append an AuditLog record.  Fire-and-forget: if the write fails the error
        is logged but NOT re-raised so audit never blocks a business operation.
        """
        try:
            async with self._uow() as uow:
                await uow.admin.audit_logs.create_from_dict(
                    {
                        "actor_id": admin_id,
                        "actor_type": "admin" if admin_id else "system",
                        "action": action,
                        "entity_type": entity_type,
                        "entity_id": entity_id,
                        "after_value": changes,
                        "ip_address": ip_address,
                        "user_agent": user_agent,
                        "is_successful": True,
                    }
                )
                await uow.commit()
        except Exception as exc:
            logger.error(
                "Audit log write failed — action=%s entity=%s:%s error=%s",
                action,
                entity_type,
                entity_id,
                exc,
            )

    async def list_audit_logs(
        self,
        filters: AuditLogFilters,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> CursorPage[AuditLogResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            logs = await uow.admin.audit_logs.find_many(
                order_by=None,
                skip=0,
                limit=limit,
            )
            items = [AuditLogResponse.model_validate(lg) for lg in logs]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_audit_logs_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        cursor: str | None = None,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> CursorPage[AuditLogResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            logs = await uow.admin.audit_logs.find_for_entity(
                entity_type=entity_type,
                entity_id=entity_id,
                limit=limit,
            )
            items = [AuditLogResponse.model_validate(lg) for lg in logs]
            return CursorPage(items=items, has_more=len(items) == limit)

    # ── Account Unlock ────────────────────────────────────────────────────────

    async def unlock_admin(
        self,
        admin_id: UUID,
        unlocked_by_id: UUID,
    ) -> AdminResponse:
        async with self._uow() as uow:
            admin = await validate_admin_exists(admin_id, uow)
            updated = await uow.admin.admins.update(
                admin,
                {
                    "failed_login_count": 0,
                    "account_locked_until": None,
                },
            )
            await uow.commit()
            result = AdminResponse.model_validate(updated)

        await self.write_audit_log(
            admin_id=unlocked_by_id,
            action=AuditAction.UPDATE,
            entity_type="admin",
            entity_id=str(admin_id),
            changes={"failed_login_count": 0, "account_locked_until": None},
            ip_address=None,
            user_agent=None,
        )
        return result
