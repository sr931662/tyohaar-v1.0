"""
Notifications Controller — send, list, read, preferences, and templates.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import NotificationServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.notifications.create import (
    BroadcastCreate,
    NotificationCreate,
    NotificationFromTemplateCreate,
    NotificationTemplateCreate,
)
from app.schemas.notifications.filters import NotificationFilters
from app.schemas.notifications.response import (
    NotificationPreferencesResponse,
    NotificationResponse,
    NotificationTemplateResponse,
)
from app.schemas.notifications.update import (
    NotificationPreferencesUpdate,
    NotificationTemplateUpdate,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Send ──────────────────────────────────────────────────────────────────────

async def send_notification(
    body: NotificationCreate,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationResponse]:
    result = await service.send_notification(data=body)
    return SuccessResponse(data=result, message="Notification sent.")


async def send_from_template(
    body: NotificationFromTemplateCreate,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationResponse]:
    result = await service.send_from_template(data=body)
    return SuccessResponse(data=result, message="Notification sent.")


async def broadcast_notification(
    body: BroadcastCreate,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[None]:
    await service.broadcast_notification(data=body)
    return SuccessResponse(data=None, message="Broadcast initiated.")


# ── User notifications ────────────────────────────────────────────────────────

async def list_notifications(
    current_user: CurrentUserDep,
    filters: Annotated[NotificationFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: NotificationServiceDep,
) -> CursorPaginatedResponse[NotificationResponse]:
    page = await service.list_notifications(
        user_id=current_user.id, filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def get_notification(
    notification_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationResponse]:
    result = await service.get_notification(
        notification_id=notification_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Notification retrieved.")


async def mark_read(
    notification_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationResponse]:
    result = await service.mark_read(
        notification_id=notification_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Notification marked as read.")


async def mark_all_read(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[None]:
    await service.mark_all_read(user_id=current_user.id)
    return SuccessResponse(data=None, message="All notifications marked as read.")


async def delete_notification(
    notification_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[None]:
    await service.delete_notification(
        notification_id=notification_id, user_id=current_user.id
    )
    return SuccessResponse(data=None, message="Notification deleted.")


async def get_unread_count(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[int]:
    count = await service.get_unread_count(user_id=current_user.id)
    return SuccessResponse(data=count, message="Unread count retrieved.")


# ── Preferences ───────────────────────────────────────────────────────────────

async def get_preferences(
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationPreferencesResponse]:
    result = await service.get_preferences(user_id=current_user.id)
    return SuccessResponse(data=result, message="Preferences retrieved.")


async def update_preferences(
    body: NotificationPreferencesUpdate,
    current_user: CurrentUserDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationPreferencesResponse]:
    result = await service.update_preferences(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Preferences updated.")


# ── Templates ─────────────────────────────────────────────────────────────────

async def list_templates(
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[list[NotificationTemplateResponse]]:
    templates = await service.list_templates()
    return SuccessResponse(data=templates, message="Templates retrieved.")


async def get_template(
    template_id: uuid.UUID,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationTemplateResponse]:
    result = await service.get_template(template_id=template_id)
    return SuccessResponse(data=result, message="Template retrieved.")


async def create_template(
    body: NotificationTemplateCreate,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationTemplateResponse]:
    result = await service.create_template(data=body)
    return SuccessResponse(data=result, message="Template created.")


async def update_template(
    template_id: uuid.UUID,
    body: NotificationTemplateUpdate,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[NotificationTemplateResponse]:
    result = await service.update_template(template_id=template_id, data=body)
    return SuccessResponse(data=result, message="Template updated.")


async def delete_template(
    template_id: uuid.UUID,
    _admin: AdminDep,
    service: NotificationServiceDep,
) -> SuccessResponse[None]:
    await service.delete_template(template_id=template_id)
    return SuccessResponse(data=None, message="Template deleted.")
