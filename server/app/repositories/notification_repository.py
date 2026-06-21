"""
Notification repository — Notification and NotificationTemplate.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationChannel, NotificationStatus, NotificationType
from app.models.notifications.notification import Notification
from app.models.notifications.template import NotificationTemplate
from app.repositories.base import BaseRepository


class NotificationTemplateRepository(BaseRepository[NotificationTemplate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, NotificationTemplate)

    async def find_by_key(self, template_key: str) -> list[NotificationTemplate]:
        """Return all channel/language variants for a given template_key."""
        return await self.find_many(
            NotificationTemplate.template_key == template_key,
            NotificationTemplate.is_active == True,  # noqa: E712
        )

    async def find_by_key_and_channel(
        self,
        template_key: str,
        channel: NotificationChannel,
        language: str = "en",
    ) -> NotificationTemplate | None:
        return await self.find_one(
            NotificationTemplate.template_key == template_key,
            NotificationTemplate.channel == channel,
            NotificationTemplate.language == language,
            NotificationTemplate.is_active == True,  # noqa: E712
        )

    async def find_active(self) -> list[NotificationTemplate]:
        return await self.find_many(NotificationTemplate.is_active == True)  # noqa: E712

    async def find_by_category(self, notification_type: NotificationType) -> list[NotificationTemplate]:
        return await self.find_many(
            NotificationTemplate.notification_category == notification_type,
            NotificationTemplate.is_active == True,  # noqa: E712
        )


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def find_by_recipient(
        self,
        recipient_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Notification]:
        return await self.find_many(
            Notification.recipient_id == recipient_id,
            order_by=Notification.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_unread_for_recipient(
        self,
        recipient_id: uuid.UUID,
        *,
        limit: int = 50,
    ) -> list[Notification]:
        return await self.find_many(
            Notification.recipient_id == recipient_id,
            Notification.notification_status.in_([
                NotificationStatus.SENT,
                NotificationStatus.DELIVERED,
            ]),
            Notification.read_at.is_(None),
            order_by=Notification.created_at.desc(),
            limit=limit,
        )

    async def count_unread_for_recipient(self, recipient_id: uuid.UUID) -> int:
        return await self.count(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
            Notification.notification_status.in_([
                NotificationStatus.SENT,
                NotificationStatus.DELIVERED,
            ]),
        )

    async def find_by_status(
        self,
        status: NotificationStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Notification]:
        return await self.find_many(
            Notification.notification_status == status,
            skip=skip,
            limit=limit,
        )

    async def find_pending_delivery(self) -> list[Notification]:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            Notification.notification_status == NotificationStatus.PENDING,
            (Notification.scheduled_at.is_(None)) | (Notification.scheduled_at <= now),
            (Notification.expires_at.is_(None)) | (Notification.expires_at > now),
            order_by=Notification.created_at.asc(),
        )

    async def find_scheduled_before(self, before: datetime) -> list[Notification]:
        return await self.find_many(
            Notification.notification_status == NotificationStatus.PENDING,
            Notification.scheduled_at.is_not(None),
            Notification.scheduled_at <= before,
        )

    async def find_by_channel(
        self,
        channel: NotificationChannel,
        status: NotificationStatus | None = None,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Notification]:
        filters = [Notification.channel == channel]
        if status is not None:
            filters.append(Notification.notification_status == status)
        return await self.find_many(*filters, skip=skip, limit=limit)

    async def find_by_reference(
        self,
        reference_type: str,
        reference_id: uuid.UUID,
    ) -> list[Notification]:
        return await self.find_many(
            Notification.reference_type == reference_type,
            Notification.reference_id == reference_id,
        )

    async def find_by_idempotency_key(self, key: str) -> Notification | None:
        return await self.find_one(Notification.idempotency_key == key)

    async def mark_as_read(self, notification_id: uuid.UUID) -> None:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.read_at.is_(None))
            .values(
                read_at=now,
                notification_status=NotificationStatus.READ,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def mark_batch_as_read(self, notification_ids: list[uuid.UUID]) -> int:
        if not notification_ids:
            return 0
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Notification)
            .where(Notification.id.in_(notification_ids))
            .where(Notification.read_at.is_(None))
            .values(
                read_at=now,
                notification_status=NotificationStatus.READ,
            )
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def find_failed_with_retries(self, max_retry_count: int) -> list[Notification]:
        return await self.find_many(
            Notification.notification_status == NotificationStatus.FAILED,
            Notification.retry_count < max_retry_count,
        )


class NotificationRepositoryAggregate:
    """Groups notification-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.notifications = NotificationRepository(session)
        self.templates = NotificationTemplateRepository(session)
