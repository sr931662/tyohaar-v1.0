from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import NotificationStatus
from app.models.notifications.notification import Notification
from app.schemas.base import CursorPage
from app.schemas.notifications.create import NotificationCreate, NotificationTemplateCreate
from app.schemas.notifications.filters import NotificationFilters
from app.schemas.notifications.response import NotificationResponse, NotificationTemplateResponse
from app.schemas.notifications.update import NotificationTemplateUpdate
from app.services.base import BaseService
from app.services.notifications.constants import NOTIFICATION_BATCH_SIZE
from app.services.notifications.exceptions import (
    TemplateKeyExistsError,
    TemplateRenderError,
)
from app.services.notifications.helpers import render_subject, render_template
from app.services.notifications.validators import (
    validate_notification_owned_by_user,
    validate_template_exists,
)

logger = logging.getLogger(__name__)


class NotificationService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    # ── Send ──────────────────────────────────────────────────────────────────

    async def send_notification(
        self,
        user_id: UUID,
        data: NotificationCreate,
    ) -> NotificationResponse:
        channel = data.channel
        async with self._uow() as uow:
            notification = await uow.notifications.notifications.create_from_dict({
                "recipient_id": user_id,
                "notification_type": data.notification_type,
                "channel": channel,
                "priority": data.priority,
                "title": data.title,
                "body": data.body,
                "action_url": data.action_url,
                "image_url": data.image_url,
                "reference_type": data.reference_type,
                "reference_id": data.reference_id,
                "scheduled_at": data.scheduled_at,
                "notification_status": NotificationStatus.SENT,
                "sent_at": datetime.now(tz=timezone.utc),
            })
            response = NotificationResponse.model_validate(notification)

        logger.info(
            "push_stub user_id=%s notification_id=%s channel=%s",
            user_id,
            notification.id,
            channel,
        )
        return response

    async def send_from_template(
        self,
        user_id: UUID,
        template_key: str,
        context: dict,
        channels: list[str] | None = None,
    ) -> NotificationResponse:
        async with self._uow() as uow:
            template_obj = await validate_template_exists(template_key, uow)
            try:
                title = render_subject(template_obj.title_template, context)
                body = render_template(template_obj.body_template, context)
            except Exception as exc:
                raise TemplateRenderError(f"Template render failed: {exc}") from exc

            channel = template_obj.channel
            notification = await uow.notifications.notifications.create_from_dict({
                "recipient_id": user_id,
                "template_id": template_obj.id,
                "notification_type": template_obj.notification_category,
                "channel": channel,
                "title": title,
                "body": body,
                "notification_status": NotificationStatus.SENT,
                "sent_at": datetime.now(tz=timezone.utc),
            })
            return NotificationResponse.model_validate(notification)

    async def broadcast_notification(
        self,
        user_ids: list[UUID],
        template_key: str,
        context: dict,
    ) -> int:
        async with self._uow() as uow:
            template_obj = await validate_template_exists(template_key, uow)
            try:
                title = render_subject(template_obj.title_template, context)
                body = render_template(template_obj.body_template, context)
            except Exception as exc:
                raise TemplateRenderError(f"Template render failed: {exc}") from exc

            now = datetime.now(tz=timezone.utc)
            total_sent = 0

            for i in range(0, len(user_ids), NOTIFICATION_BATCH_SIZE):
                batch = user_ids[i : i + NOTIFICATION_BATCH_SIZE]
                instances = [
                    Notification(
                        recipient_id=uid,
                        template_id=template_obj.id,
                        notification_type=template_obj.notification_category,
                        channel=template_obj.channel,
                        title=title,
                        body=body,
                        notification_status=NotificationStatus.SENT,
                        sent_at=now,
                    )
                    for uid in batch
                ]
                created = await uow.notifications.notifications.bulk_create(instances)
                total_sent += len(created)

            return total_sent

    # ── Read / Manage ─────────────────────────────────────────────────────────

    async def list_notifications(
        self,
        user_id: UUID,
        filters: NotificationFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[NotificationResponse]:
        async with self._uow() as uow:
            page = await uow.notifications.notifications.cursor_paginate(
                Notification.recipient_id == user_id,
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[NotificationResponse.model_validate(n) for n in page.items],
                next_cursor=page.next_cursor,
                page_size=page.page_size,
            )

    async def get_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> NotificationResponse:
        async with self._uow() as uow:
            notification = await validate_notification_owned_by_user(
                notification_id, user_id, uow
            )
            return NotificationResponse.model_validate(notification)

    async def mark_read(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> NotificationResponse:
        async with self._uow() as uow:
            notification = await validate_notification_owned_by_user(
                notification_id, user_id, uow
            )
            await uow.notifications.notifications.mark_as_read(notification_id)
            # Re-fetch to get updated fields
            updated = await uow.notifications.notifications.get_by_id(notification_id)
            return NotificationResponse.model_validate(updated)

    async def mark_all_read(self, user_id: UUID) -> int:
        async with self._uow() as uow:
            unread = await uow.notifications.notifications.find_unread_for_recipient(
                user_id, limit=500
            )
            if not unread:
                return 0
            ids = [n.id for n in unread]
            count = await uow.notifications.notifications.mark_batch_as_read(ids)
            return count

    async def delete_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            notification = await validate_notification_owned_by_user(
                notification_id, user_id, uow
            )
            await uow.notifications.notifications.delete(notification)

    async def get_unread_count(self, user_id: UUID) -> int:
        async with self._uow() as uow:
            return await uow.notifications.notifications.count_unread_for_recipient(user_id)

    # ── Preferences ───────────────────────────────────────────────────────────

    async def get_preferences(self, user_id: UUID) -> object:
        # NotificationPreference model handled via user repository aggregate
        # Return a stub dict until a dedicated preferences schema is wired
        async with self._uow() as uow:
            prefs = await uow.users.preferences.get_by_user(user_id) \
                if hasattr(uow.users, "preferences") else None
            if prefs is None:
                return {"user_id": str(user_id), "push_enabled": True, "email_enabled": True, "sms_enabled": True}
            try:
                from app.schemas.notifications.response import NotificationPreferenceResponse
                return NotificationPreferenceResponse.model_validate(prefs)
            except Exception:
                return prefs

    async def update_preferences(self, user_id: UUID, data: object) -> object:
        async with self._uow() as uow:
            if hasattr(uow.users, "preferences"):
                existing = await uow.users.preferences.get_by_user(user_id)
                update_dict = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else {}
                if existing is None:
                    prefs = await uow.users.preferences.create_from_dict(
                        {"user_id": user_id, **update_dict}
                    )
                else:
                    prefs = await uow.users.preferences.update(existing, update_dict)
                try:
                    from app.schemas.notifications.response import NotificationPreferenceResponse
                    return NotificationPreferenceResponse.model_validate(prefs)
                except Exception:
                    return prefs
            return {"user_id": str(user_id)}

    # ── Template Management (admin) ───────────────────────────────────────────

    async def list_templates(self) -> list[NotificationTemplateResponse]:
        async with self._uow() as uow:
            templates = await uow.notifications.templates.find_active()
            return [NotificationTemplateResponse.model_validate(t) for t in templates]

    async def get_template(self, template_key: str) -> NotificationTemplateResponse:
        async with self._uow() as uow:
            template = await validate_template_exists(template_key, uow)
            return NotificationTemplateResponse.model_validate(template)

    async def create_template(
        self,
        data: NotificationTemplateCreate,
        admin_id: UUID,
    ) -> NotificationTemplateResponse:
        async with self._uow() as uow:
            template_key_value = (
                str(data.notification_type.value)
                if hasattr(data.notification_type, "value")
                else str(data.notification_type)
            )
            existing = await uow.notifications.templates.find_by_key_and_channel(
                template_key=template_key_value,
                channel=data.channel,
                language=data.language,
            )
            if existing is not None:
                raise TemplateKeyExistsError()

            template = await uow.notifications.templates.create_from_dict({
                "template_key": template_key_value,
                "channel": data.channel,
                "language": data.language,
                "notification_category": data.notification_type,
                "title_template": data.title_template,
                "body_template": data.body_template,
                "is_active": data.is_active,
                "version": 1,
            })
            return NotificationTemplateResponse.model_validate(template)

    async def update_template(
        self,
        template_key: str,
        data: NotificationTemplateUpdate,
        admin_id: UUID,
    ) -> NotificationTemplateResponse:
        async with self._uow() as uow:
            template = await validate_template_exists(template_key, uow)
            updated = await uow.notifications.templates.update(
                template, data.model_dump(exclude_unset=True)
            )
            return NotificationTemplateResponse.model_validate(updated)

    async def delete_template(self, template_key: str, admin_id: UUID) -> None:
        async with self._uow() as uow:
            template = await validate_template_exists(template_key, uow)
            await uow.notifications.templates.update(template, {"is_active": False})
