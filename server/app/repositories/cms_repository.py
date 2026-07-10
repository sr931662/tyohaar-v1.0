"""
CMS Repository Aggregate
========================
Provides repository access for:
  - ImportLog
  - ExportLog
  - AutomationRule
  - AutomationLog

All repositories extend BaseRepository and share one AsyncSession via UnitOfWork.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cms.automation_log import AutomationLog
from app.models.cms.automation_rule import AutomationRule
from app.models.cms.export_log import ExportLog
from app.models.cms.import_log import ImportLog
from app.repositories.base import BaseRepository


# ── Import Log Repository ─────────────────────────────────────────────────────

class ImportLogRepository(BaseRepository[ImportLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ImportLog)

    async def find_by_admin(
        self,
        admin_id: uuid.UUID,
        *,
        entity_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> list[ImportLog]:
        conditions = [ImportLog.admin_id == admin_id]
        if entity_type:
            conditions.append(ImportLog.entity_type == entity_type)
        if status:
            conditions.append(ImportLog.status == status)
        return await self.find_many(
            *conditions,
            order_by=ImportLog.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_all_paginated(
        self,
        *,
        entity_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ImportLog], int]:
        conditions: list[Any] = []
        if entity_type:
            conditions.append(ImportLog.entity_type == entity_type)
        if status:
            conditions.append(ImportLog.status == status)

        count_stmt = select(func.count()).select_from(ImportLog)
        data_stmt = (
            select(ImportLog)
            .order_by(ImportLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            count_stmt = count_stmt.where(*conditions)
            data_stmt = data_stmt.where(*conditions)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(data_stmt)).scalars().all()
        return list(rows), total

    async def update_progress(
        self,
        log_id: uuid.UUID,
        *,
        status: str,
        progress_pct: float,
        inserted_rows: int = 0,
        updated_rows: int = 0,
        invalid_rows: int = 0,
        error_summary: dict[str, Any] | None = None,
    ) -> None:
        stmt = (
            update(ImportLog)
            .where(ImportLog.id == log_id)
            .values(
                status=status,
                progress_pct=progress_pct,
                inserted_rows=inserted_rows,
                updated_rows=updated_rows,
                invalid_rows=invalid_rows,
                error_summary=error_summary,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


# ── Export Log Repository ─────────────────────────────────────────────────────

class ExportLogRepository(BaseRepository[ExportLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ExportLog)

    async def find_all_paginated(
        self,
        *,
        admin_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[ExportLog], int]:
        conditions: list[Any] = []
        if admin_id:
            conditions.append(ExportLog.admin_id == admin_id)
        if entity_type:
            conditions.append(ExportLog.entity_type == entity_type)
        if status:
            conditions.append(ExportLog.status == status)

        count_stmt = select(func.count()).select_from(ExportLog)
        data_stmt = (
            select(ExportLog).order_by(ExportLog.created_at.desc()).offset(skip).limit(limit)
        )
        if conditions:
            count_stmt = count_stmt.where(*conditions)
            data_stmt = data_stmt.where(*conditions)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(data_stmt)).scalars().all()
        return list(rows), total

    async def mark_completed(
        self,
        log_id: uuid.UUID,
        *,
        file_storage_path: str,
        download_url: str,
        row_count: int,
        file_size_bytes: int,
        file_content: bytes | None = None,
        mime_type: str | None = None,
    ) -> None:
        from datetime import datetime, timezone
        stmt = (
            update(ExportLog)
            .where(ExportLog.id == log_id)
            .values(
                status="COMPLETED",
                file_storage_path=file_storage_path,
                download_url=download_url,
                row_count=row_count,
                file_size_bytes=file_size_bytes,
                file_content=file_content,
                mime_type=mime_type,
                completed_at=datetime.now(timezone.utc),
            )
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


# ── Automation Rule Repository ────────────────────────────────────────────────

class AutomationRuleRepository(BaseRepository[AutomationRule]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AutomationRule)

    async def find_by_trigger(self, trigger_event: str) -> list[AutomationRule]:
        return await self.find_many(
            AutomationRule.trigger_event == trigger_event,
            AutomationRule.is_active == True,
            order_by=AutomationRule.priority.asc(),
        )

    async def find_all_paginated(
        self,
        *,
        trigger_event: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AutomationRule], int]:
        conditions: list[Any] = []
        if trigger_event:
            conditions.append(AutomationRule.trigger_event == trigger_event)
        if is_active is not None:
            conditions.append(AutomationRule.is_active == is_active)

        count_stmt = select(func.count()).select_from(AutomationRule)
        data_stmt = (
            select(AutomationRule)
            .order_by(AutomationRule.priority.asc(), AutomationRule.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            count_stmt = count_stmt.where(*conditions)
            data_stmt = data_stmt.where(*conditions)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(data_stmt)).scalars().all()
        return list(rows), total

    async def increment_stats(
        self,
        rule_id: uuid.UUID,
        *,
        success: bool,
    ) -> None:
        from datetime import datetime, timezone
        values: dict[str, Any] = {
            "total_executions": AutomationRule.total_executions + 1,
            "last_triggered_at": datetime.now(timezone.utc),
        }
        if success:
            values["successful_executions"] = AutomationRule.successful_executions + 1
        else:
            values["failed_executions"] = AutomationRule.failed_executions + 1

        stmt = (
            update(AutomationRule)
            .where(AutomationRule.id == rule_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def toggle(self, rule_id: uuid.UUID) -> AutomationRule | None:
        rule = await self.get_by_id(rule_id)
        if rule is None:
            return None
        return await self.update(rule, {"is_active": not rule.is_active})


# ── Automation Log Repository ─────────────────────────────────────────────────

class AutomationLogRepository(BaseRepository[AutomationLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AutomationLog)

    async def find_by_rule(
        self,
        rule_id: uuid.UUID,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AutomationLog], int]:
        conditions: list[Any] = [AutomationLog.rule_id == rule_id]
        if status:
            conditions.append(AutomationLog.status == status)

        count_stmt = select(func.count()).select_from(AutomationLog).where(*conditions)
        data_stmt = (
            select(AutomationLog)
            .where(*conditions)
            .order_by(AutomationLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(data_stmt)).scalars().all()
        return list(rows), total

    async def find_all_paginated(
        self,
        *,
        rule_id: uuid.UUID | None = None,
        status: str | None = None,
        entity_type: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AutomationLog], int]:
        conditions: list[Any] = []
        if rule_id:
            conditions.append(AutomationLog.rule_id == rule_id)
        if status:
            conditions.append(AutomationLog.status == status)
        if entity_type:
            conditions.append(AutomationLog.entity_type == entity_type)

        count_stmt = select(func.count()).select_from(AutomationLog)
        data_stmt = (
            select(AutomationLog)
            .order_by(AutomationLog.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if conditions:
            count_stmt = count_stmt.where(*conditions)
            data_stmt = data_stmt.where(*conditions)

        total = (await self._session.execute(count_stmt)).scalar_one()
        rows = (await self._session.execute(data_stmt)).scalars().all()
        return list(rows), total


# ── CMS Repository Aggregate ──────────────────────────────────────────────────

class CMSRepositoryAggregate:
    """Groups all CMS domain sub-repositories under one aggregate."""

    def __init__(self, session: AsyncSession) -> None:
        self.import_logs = ImportLogRepository(session)
        self.export_logs = ExportLogRepository(session)
        self.automation_rules = AutomationRuleRepository(session)
        self.automation_logs = AutomationLogRepository(session)
