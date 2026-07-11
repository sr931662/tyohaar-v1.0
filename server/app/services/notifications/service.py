from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import NotificationChannel, NotificationStatus
from app.models.notifications.notification import Notification
from app.schemas.base import CursorPage
from app.schemas.notifications.create import (
    BroadcastCreate,
    NotificationCreate,
    NotificationFromTemplateCreate,
    NotificationTemplateCreate,
)
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


def _status_for_channel(channel: NotificationChannel) -> NotificationStatus:
    """
    IN_APP delivery IS the write to the notifications table — SENT is honest.
    No dispatcher is wired for PUSH/SMS/EMAIL/WHATSAPP yet, so those channels
    must not claim SENT; they stay PENDING until a real gateway is added.
    """
    if channel == NotificationChannel.IN_APP:
        return NotificationStatus.SENT
    return NotificationStatus.PENDING


class NotificationService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    # ── Push dispatch ─────────────────────────────────────────────────────────

    async def _dispatch_push(
        self,
        notification_id: UUID,
        user_id: UUID,
        title: str,
        body: str,
        action_url: str | None = None,
    ) -> None:
        """
        Best-effort FCM dispatch for a PUSH-channel notification that was
        already written to the table as PENDING. Flips it to SENT/FAILED
        based on the outcome. No-ops silently if Firebase isn't configured
        yet — the row just stays PENDING, same as today.
        """
        from app.services.notifications.fcm_client import is_configured, send_push

        if not is_configured():
            return

        async with self._uow() as uow:
            devices = await uow.users.devices.find_by_user(user_id)
            tokens = [
                d.push_notification_token for d in devices
                if d.is_active and d.push_notification_token
            ]
            if not tokens:
                return

            try:
                result = send_push(
                    tokens, title, body,
                    data={"action_url": action_url} if action_url else None,
                )
            except Exception:
                logger.exception("FCM dispatch failed for notification %s", notification_id)
                return

            new_status = NotificationStatus.SENT if result.success_count > 0 else NotificationStatus.FAILED
            notif = await uow.notifications.notifications.get_by_id(notification_id)
            if notif is not None:
                await uow.notifications.notifications.update(notif, {
                    "notification_status": new_status,
                    "sent_at": datetime.now(tz=timezone.utc) if new_status == NotificationStatus.SENT else None,
                })

            for token in result.invalid_tokens:
                device = await uow.users.devices.find_by_token(token)
                if device is not None:
                    await uow.users.devices.update(device, {"is_active": False})

    # ── Email dispatch ────────────────────────────────────────────────────────

    async def _dispatch_email(
        self,
        notification_id: UUID,
        user_id: UUID,
        title: str,
        body: str,
    ) -> None:
        """
        Best-effort SMTP dispatch for an EMAIL-channel notification that was
        already written to the table as PENDING. Flips it to SENT/FAILED
        based on the outcome. No-ops silently if SMTP isn't configured yet —
        the row just stays PENDING, same as today. Mirrors _dispatch_push.
        """
        from app.services.notifications.email_client import is_configured, send_email

        if not is_configured():
            return

        async with self._uow() as uow:
            user = await uow.users.users.get_by_id(user_id)
            if user is None or not user.email:
                return

            new_status = NotificationStatus.FAILED
            try:
                await send_email(
                    to=user.email,
                    subject=title,
                    html_body=f"<div style=\"font-family: sans-serif; font-size: 15px; color: #2A2018;\">{body}</div>",
                    text_body=body,
                )
                new_status = NotificationStatus.SENT
            except Exception:
                logger.exception("Email dispatch failed for notification %s", notification_id)

            notif = await uow.notifications.notifications.get_by_id(notification_id)
            if notif is not None:
                await uow.notifications.notifications.update(notif, {
                    "notification_status": new_status,
                    "sent_at": datetime.now(tz=timezone.utc) if new_status == NotificationStatus.SENT else None,
                })

    # ── Send ──────────────────────────────────────────────────────────────────

    async def send_notification(
        self,
        data: NotificationCreate,
        user_id: UUID | None = None,
    ) -> NotificationResponse:
        recipient_id = user_id or data.user_id
        channel = data.channel
        status = _status_for_channel(channel)
        async with self._uow() as uow:
            notification = await uow.notifications.notifications.create_from_dict({
                "recipient_id": recipient_id,
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
                "notification_status": status,
                "sent_at": datetime.now(tz=timezone.utc) if status == NotificationStatus.SENT else None,
            })
            response = NotificationResponse.model_validate(notification)

        if channel == NotificationChannel.PUSH:
            await self._dispatch_push(notification.id, recipient_id, data.title, data.body, data.action_url)
        elif channel == NotificationChannel.EMAIL:
            await self._dispatch_email(notification.id, recipient_id, data.title, data.body)

        logger.info(
            "dispatch_stub (no real channel configured) user_id=%s notification_id=%s channel=%s status=%s",
            recipient_id,
            notification.id,
            channel,
            status,
        )
        return response

    async def send_from_template(
        self,
        data: NotificationFromTemplateCreate,
    ) -> NotificationResponse:
        async with self._uow() as uow:
            template_obj = await validate_template_exists(data.template_key, uow)
            try:
                title = render_subject(template_obj.title_template, data.context_data)
                body = render_template(template_obj.body_template, data.context_data)
            except Exception as exc:
                raise TemplateRenderError(f"Template render failed: {exc}") from exc

            channel = data.channel
            status = _status_for_channel(channel)
            notification = await uow.notifications.notifications.create_from_dict({
                "recipient_id": data.user_id,
                "template_id": template_obj.id,
                "notification_type": data.notification_type,
                "channel": channel,
                "priority": data.priority,
                "title": title,
                "body": body,
                "reference_type": data.reference_type,
                "reference_id": data.reference_id,
                "notification_status": status,
                "sent_at": datetime.now(tz=timezone.utc) if status == NotificationStatus.SENT else None,
            })
            result = NotificationResponse.model_validate(notification)

        if channel == NotificationChannel.PUSH:
            await self._dispatch_push(notification.id, data.user_id, title, body)
        elif channel == NotificationChannel.EMAIL:
            await self._dispatch_email(notification.id, data.user_id, title, body)

        return result

    async def broadcast_notification(
        self,
        data: BroadcastCreate,
    ) -> int:
        async with self._uow() as uow:
            if data.recipient_ids:
                user_ids = data.recipient_ids
            else:
                from app.models.enums import UserRole
                from app.models.users.user import User

                segment = data.target_segment or "all"
                conditions = [User.deleted_at.is_(None)]
                if segment == "customers":
                    conditions.append(User.role == UserRole.CUSTOMER)
                elif segment == "vendors":
                    conditions.append(User.role == UserRole.VENDOR)
                from sqlalchemy import select
                result = await uow.session.execute(select(User.id).where(*conditions))
                user_ids = [row[0] for row in result.all()]

            status = _status_for_channel(data.channel)
            now = datetime.now(tz=timezone.utc)
            total_sent = 0
            created_by_user: dict[UUID, Notification] = {}

            for i in range(0, len(user_ids), NOTIFICATION_BATCH_SIZE):
                batch = user_ids[i : i + NOTIFICATION_BATCH_SIZE]
                instances = [
                    Notification(
                        recipient_id=uid,
                        notification_type=data.notification_type,
                        channel=data.channel,
                        title=data.title,
                        body=data.body,
                        scheduled_at=data.scheduled_at,
                        notification_status=status,
                        sent_at=now if status == NotificationStatus.SENT else None,
                    )
                    for uid in batch
                ]
                created = await uow.notifications.notifications.bulk_create(instances)
                total_sent += len(created)
                for uid, notif in zip(batch, created):
                    created_by_user[uid] = notif

        if data.channel == NotificationChannel.PUSH:
            await self._dispatch_broadcast_push(created_by_user, data.title, data.body)

        return total_sent

    async def _dispatch_broadcast_push(
        self,
        created_by_user: dict[UUID, Notification],
        title: str,
        body: str,
    ) -> None:
        from app.services.notifications.fcm_client import is_configured, send_push

        if not is_configured() or not created_by_user:
            return

        async with self._uow() as uow:
            user_ids = list(created_by_user.keys())
            token_to_user: dict[str, UUID] = {}
            for i in range(0, len(user_ids), NOTIFICATION_BATCH_SIZE):
                batch = user_ids[i : i + NOTIFICATION_BATCH_SIZE]
                from sqlalchemy import select
                from app.models.users.device import UserDevice
                result = await uow.session.execute(
                    select(UserDevice.push_notification_token, UserDevice.user_id).where(
                        UserDevice.user_id.in_(batch),
                        UserDevice.is_active == True,
                        UserDevice.push_notification_token.isnot(None),
                    )
                )
                for token, uid in result.all():
                    token_to_user[token] = uid

            if not token_to_user:
                return

            try:
                push_result = send_push(list(token_to_user.keys()), title, body)
            except Exception:
                logger.exception("FCM broadcast dispatch failed")
                return

            users_with_success: set[UUID] = set()
            for token, success in push_result.token_success.items():
                if success:
                    users_with_success.add(token_to_user[token])

            now = datetime.now(tz=timezone.utc)
            for uid in users_with_success:
                notif = created_by_user.get(uid)
                if notif is not None:
                    fresh = await uow.notifications.notifications.get_by_id(notif.id)
                    if fresh is not None:
                        await uow.notifications.notifications.update(fresh, {
                            "notification_status": NotificationStatus.SENT,
                            "sent_at": now,
                        })

            for token in push_result.invalid_tokens:
                device = await uow.users.devices.find_by_token(token)
                if device is not None:
                    await uow.users.devices.update(device, {"is_active": False})

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

    async def get_template(self, template_id: UUID) -> NotificationTemplateResponse:
        async with self._uow() as uow:
            template = await uow.notifications.templates.get_by_id(template_id)
            if template is None:
                from app.services.notifications.exceptions import TemplateNotFoundError
                raise TemplateNotFoundError(str(template_id))
            return NotificationTemplateResponse.model_validate(template)

    async def create_template(
        self,
        data: NotificationTemplateCreate,
        admin_id: UUID | None = None,
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
        template_id: UUID,
        data: NotificationTemplateUpdate,
        admin_id: UUID | None = None,
    ) -> NotificationTemplateResponse:
        async with self._uow() as uow:
            template = await uow.notifications.templates.get_by_id(template_id)
            if template is None:
                from app.services.notifications.exceptions import TemplateNotFoundError
                raise TemplateNotFoundError(str(template_id))
            updated = await uow.notifications.templates.update(
                template, data.model_dump(exclude_unset=True)
            )
            return NotificationTemplateResponse.model_validate(updated)

    async def delete_template(self, template_id: UUID, admin_id: UUID | None = None) -> None:
        async with self._uow() as uow:
            template = await uow.notifications.templates.get_by_id(template_id)
            if template is None:
                from app.services.notifications.exceptions import TemplateNotFoundError
                raise TemplateNotFoundError(str(template_id))
            await uow.notifications.templates.update(template, {"is_active": False})
