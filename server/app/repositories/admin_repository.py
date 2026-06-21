"""
Admin repository — Admin, AdminRole, AdminPermission, AdminRolePermission, AuditLog.

AuditLog is IMMUTABLE (append-only). Only create() is permitted.
Never call update(), soft_delete(), delete(), bulk_update(), or bulk_delete()
on AuditLogRepository.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.admin.admin import Admin
from app.models.admin.audit_log import AuditLog
from app.models.admin.permission import AdminPermission
from app.models.admin.role import AdminRole
from app.models.admin.role_permission import AdminRolePermission
from app.models.enums import AdminDepartment, AdminStatus, AuditAction, PermissionAction, PermissionResource
from app.repositories.base import BaseRepository, RepositoryError


class AdminRoleRepository(BaseRepository[AdminRole]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AdminRole)

    async def find_by_slug(self, slug: str) -> AdminRole | None:
        return await self.find_one(AdminRole.slug == slug)

    async def find_system_roles(self) -> list[AdminRole]:
        return await self.find_many(AdminRole.is_system == True)  # noqa: E712

    async def find_super_admin_roles(self) -> list[AdminRole]:
        return await self.find_many(AdminRole.is_super_admin == True)  # noqa: E712

    async def find_active(self) -> list[AdminRole]:
        return await self.find_many(
            AdminRole.is_active == True,  # noqa: E712
            order_by=AdminRole.priority_rank.asc(),
        )

    async def get_with_permissions(self, role_id: uuid.UUID) -> AdminRole | None:
        return await self.get_by_id(
            role_id,
            options=[
                selectinload(AdminRole.permissions).selectinload(AdminRolePermission.permission),
            ],
        )


class AdminPermissionRepository(BaseRepository[AdminPermission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AdminPermission)

    async def find_by_code(self, code: str) -> AdminPermission | None:
        return await self.find_one(AdminPermission.code == code)

    async def find_by_resource(self, resource: PermissionResource) -> list[AdminPermission]:
        return await self.find_many(AdminPermission.resource == resource)

    async def find_by_resource_and_action(
        self,
        resource: PermissionResource,
        action: PermissionAction,
    ) -> AdminPermission | None:
        return await self.find_one(
            AdminPermission.resource == resource,
            AdminPermission.action == action,
        )

    async def find_active(self) -> list[AdminPermission]:
        return await self.find_many(AdminPermission.is_active == True)  # noqa: E712

    async def find_for_role(self, role_id: uuid.UUID) -> list[AdminPermission]:
        stmt = (
            select(AdminPermission)
            .join(
                AdminRolePermission,
                AdminRolePermission.permission_id == AdminPermission.id,
            )
            .where(AdminRolePermission.role_id == role_id)
            .where(AdminPermission.is_active == True)  # noqa: E712
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class AdminRolePermissionRepository(BaseRepository[AdminRolePermission]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AdminRolePermission)

    async def find_by_role(self, role_id: uuid.UUID) -> list[AdminRolePermission]:
        return await self.find_many(
            AdminRolePermission.role_id == role_id,
            options=[selectinload(AdminRolePermission.permission)],
        )

    async def find_grant(
        self,
        role_id: uuid.UUID,
        permission_id: uuid.UUID,
    ) -> AdminRolePermission | None:
        return await self.find_one(
            AdminRolePermission.role_id == role_id,
            AdminRolePermission.permission_id == permission_id,
        )

    async def revoke_all_for_role(self, role_id: uuid.UUID) -> int:
        return await self.bulk_delete(
            [rp.id for rp in await self.find_by_role(role_id)]
        )

    async def revoke_permission_from_roles(self, permission_id: uuid.UUID) -> int:
        from sqlalchemy import delete as sa_delete
        stmt = (
            sa_delete(AdminRolePermission)
            .where(AdminRolePermission.permission_id == permission_id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount


class AdminRepository(BaseRepository[Admin]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Admin)

    async def find_by_user(self, user_id: uuid.UUID) -> Admin | None:
        return await self.find_one(Admin.user_id == user_id)

    async def find_by_employee_id(self, employee_id: str) -> Admin | None:
        return await self.find_one(Admin.employee_id == employee_id)

    async def find_by_work_email(self, work_email: str) -> Admin | None:
        return await self.find_one(Admin.work_email == work_email)

    async def find_by_status(
        self,
        status: AdminStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Admin]:
        return await self.find_many(
            Admin.admin_status == status,
            skip=skip,
            limit=limit,
        )

    async def find_active(self, *, skip: int = 0, limit: int = 100) -> list[Admin]:
        return await self.find_many(
            Admin.admin_status == AdminStatus.ACTIVE,
            skip=skip,
            limit=limit,
        )

    async def find_by_department(
        self,
        department: AdminDepartment,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Admin]:
        return await self.find_many(
            Admin.department == department,
            Admin.admin_status == AdminStatus.ACTIVE,
            skip=skip,
            limit=limit,
        )

    async def find_by_role(
        self,
        role_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Admin]:
        return await self.find_many(
            Admin.role_id == role_id,
            skip=skip,
            limit=limit,
        )

    async def find_direct_reports(self, admin_id: uuid.UUID) -> list[Admin]:
        return await self.find_many(Admin.reporting_to_id == admin_id)

    async def find_locked(self) -> list[Admin]:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(Admin.account_locked_until > now)

    async def get_with_role(self, admin_id: uuid.UUID) -> Admin | None:
        return await self.get_by_id(
            admin_id,
            options=[
                selectinload(Admin.role).selectinload(AdminRole.permissions),
            ],
        )

    async def get_with_audit_logs(
        self,
        admin_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> Admin | None:
        return await self.get_by_id(
            admin_id,
            options=[selectinload(Admin.audit_logs)],
        )

    async def increment_failed_login(self, admin_id: uuid.UUID) -> None:
        stmt = (
            update(Admin)
            .where(Admin.id == admin_id)
            .values(failed_login_count=Admin.failed_login_count + 1)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def reset_failed_login(self, admin_id: uuid.UUID) -> None:
        stmt = (
            update(Admin)
            .where(Admin.id == admin_id)
            .values(failed_login_count=0, account_locked_until=None)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def update_last_login(
        self,
        admin_id: uuid.UUID,
        ip_address: str | None = None,
    ) -> None:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Admin)
            .where(Admin.id == admin_id)
            .values(last_login_at=now, last_login_ip=ip_address, last_active_at=now)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def update_last_active(self, admin_id: uuid.UUID) -> None:
        from datetime import datetime, timezone
        stmt = (
            update(Admin)
            .where(Admin.id == admin_id)
            .values(last_active_at=datetime.now(tz=timezone.utc))
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def count_by_department(self) -> dict[str, int]:
        stmt = (
            select(Admin.department, func.count().label("count"))
            .where(Admin.deleted_at.is_(None))
            .where(Admin.admin_status == AdminStatus.ACTIVE)
            .group_by(Admin.department)
        )
        result = await self._session.execute(stmt)
        return {str(row.department): row.count for row in result.all()}


class AuditLogRepository(BaseRepository[AuditLog]):
    """
    IMMUTABLE: only create() is permitted.
    The audit_logs table has no UPDATE or DELETE privileges in production.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)

    # Disable mutating operations for the immutable audit log.

    async def update(self, instance: AuditLog, data: dict) -> AuditLog:  # type: ignore[override]
        raise RepositoryError("AuditLog is immutable — updates are not permitted.")

    async def delete(self, instance: AuditLog) -> None:  # type: ignore[override]
        raise RepositoryError("AuditLog is immutable — deletes are not permitted.")

    async def soft_delete(self, instance: AuditLog) -> None:  # type: ignore[override]
        raise RepositoryError("AuditLog is immutable — soft deletes are not permitted.")

    async def bulk_update(self, ids: list[uuid.UUID], data: dict) -> int:  # type: ignore[override]
        raise RepositoryError("AuditLog is immutable — bulk updates are not permitted.")

    async def bulk_delete(self, ids: list[uuid.UUID]) -> int:  # type: ignore[override]
        raise RepositoryError("AuditLog is immutable — bulk deletes are not permitted.")

    # ── Queries ───────────────────────────────────────────────────────────────

    async def find_by_actor(
        self,
        actor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.actor_id == actor_id,
            order_by=AuditLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.entity_type == entity_type,
            AuditLog.entity_id == entity_id,
            order_by=AuditLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_action(
        self,
        action: AuditAction,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.action == action,
            order_by=AuditLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_sensitive(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.is_sensitive == True,  # noqa: E712
            order_by=AuditLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_failed_actions(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.is_successful == False,  # noqa: E712
            order_by=AuditLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_request_id(self, request_id: str) -> list[AuditLog]:
        return await self.find_many(AuditLog.request_id == request_id)

    async def find_in_range(
        self,
        start: datetime,
        end: datetime,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.created_at >= start,
            AuditLog.created_at <= end,
            order_by=AuditLog.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_session(self, session_id: uuid.UUID) -> list[AuditLog]:
        return await self.find_many(
            AuditLog.session_id == session_id,
            order_by=AuditLog.created_at.asc(),
        )


class AdminRepositoryAggregate:
    """Groups all admin-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.admins = AdminRepository(session)
        self.roles = AdminRoleRepository(session)
        self.permissions = AdminPermissionRepository(session)
        self.role_permissions = AdminRolePermissionRepository(session)
        self.audit_logs = AuditLogRepository(session)
