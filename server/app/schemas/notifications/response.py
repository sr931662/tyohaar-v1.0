"""
Notifications domain — response (output) schemas.

Security: failure_reason is excluded from NotificationResponse (customer view).
It is only available in NotificationInternal for admin/ops use.
push_notification_token is NEVER included in any response schema.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict

from app.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.schemas.base import BaseSchema

__all__ = [
    "NotificationResponse",
    "NotificationTemplateResponse",
]


class NotificationResponse(BaseSchema):
    """
    Customer-facing notification record for the in-app notification inbox.

    Excludes failure_reason (internal ops detail) and the raw data payload
    is included because clients need it for deep-link routing.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    user_id: uuid.UUID
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    status: NotificationStatus
    title: str
    body: str
    action_url: str | None = None
    image_url: str | None = None
    data: dict[str, Any] | None = None
    reference_type: str | None = None
    reference_id: uuid.UUID | None = None
    scheduled_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    read_at: datetime | None = None
    is_read: bool
    created_at: datetime


class NotificationTemplateResponse(BaseSchema):
    """
    Notification template record returned in admin template management endpoints.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    notification_type: NotificationType
    channel: NotificationChannel
    title_template: str
    body_template: str
    is_active: bool
    language: str
    created_at: datetime


class NotificationPreferencesResponse(BaseSchema):
    """Customer notification preferences for each channel."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: uuid.UUID
    email_enabled: bool = True
    sms_enabled: bool = True
    push_enabled: bool = True
    in_app_enabled: bool = True
    marketing_enabled: bool = False
    transactional_enabled: bool = True
