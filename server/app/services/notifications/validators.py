from __future__ import annotations

from uuid import UUID

from app.models.notifications.notification import Notification
from app.models.notifications.template import NotificationTemplate
from app.repositories.unit_of_work import UnitOfWork
from app.services.notifications.exceptions import (
    NotificationNotFoundError,
    NotificationOwnershipError,
    TemplateNotFoundError,
)


async def validate_template_exists(
    template_key: str,
    uow: UnitOfWork,
) -> NotificationTemplate:
    templates = await uow.notifications.templates.find_by_key(template_key)
    if not templates:
        raise TemplateNotFoundError(template_key)
    return templates[0]


async def validate_notification_owned_by_user(
    notification_id: UUID,
    user_id: UUID,
    uow: UnitOfWork,
) -> Notification:
    notification = await uow.notifications.notifications.get_by_id(notification_id)
    if notification is None:
        raise NotificationNotFoundError(str(notification_id))
    if notification.recipient_id != user_id:
        raise NotificationOwnershipError()
    return notification
