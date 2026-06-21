"""
Notifications domain — update (patch) schemas.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from app.models.enums import NotificationStatus
from app.schemas.base import BaseSchema

__all__ = [
    "NotificationUpdate",
    "NotificationTemplateUpdate",
]


class NotificationUpdate(BaseSchema):
    """
    Partial update for a notification dispatch record.

    Used by the channel adapters to record delivery outcomes
    and by the mobile client to mark in-app notifications as read.
    """

    status: NotificationStatus | None = Field(
        default=None,
        description="Updated lifecycle status of the dispatch attempt.",
    )
    sent_at: datetime | None = Field(
        default=None,
        description="Timestamp when the notification was handed off to the channel provider.",
    )
    delivered_at: datetime | None = Field(
        default=None,
        description="Timestamp when delivery was confirmed by the channel provider.",
    )
    read_at: datetime | None = Field(
        default=None,
        description="Timestamp when the user opened or read the notification.",
    )
    failed_at: datetime | None = Field(
        default=None,
        description="Timestamp when the dispatch attempt permanently failed.",
    )
    failure_reason: str | None = Field(
        default=None,
        max_length=1000,
        description="Error message or provider rejection reason.",
    )
    is_read: bool | None = Field(
        default=None,
        description="Boolean read flag for in-app notification inbox.",
    )


class NotificationTemplateUpdate(BaseSchema):
    """
    Admin patch schema for notification template content.

    notification_type, channel, and language are immutable after creation —
    they form the lookup key. Create a new template to change the key.
    """

    title_template: str | None = Field(
        default=None,
        max_length=300,
        description="Updated Jinja2 title template.",
    )
    body_template: str | None = Field(
        default=None,
        description="Updated Jinja2 body template.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Toggle template activation without deletion.",
    )


class NotificationPreferencesUpdate(BaseSchema):
    """Customer: update notification channel opt-in/opt-out preferences."""

    email_enabled: bool | None = None
    sms_enabled: bool | None = None
    push_enabled: bool | None = None
    in_app_enabled: bool | None = None
    marketing_enabled: bool | None = None
    transactional_enabled: bool | None = None
