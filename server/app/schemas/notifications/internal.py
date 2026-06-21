"""
Notifications domain — internal / admin-only schemas.

Exposes failure details and supports bulk notification operations.
push_notification_token is NEVER included in any schema (device security rule).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, field_validator

from app.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationType,
)
from app.schemas.base import BaseSchema
from app.schemas.notifications.response import NotificationResponse

__all__ = [
    "NotificationInternal",
    "NotificationBatchCreate",
]


class NotificationInternal(NotificationResponse):
    """
    Full notification record for admin ops dashboards and failure investigation.

    Adds failure_reason which is intentionally excluded from customer responses
    because it may contain internal service names and error codes.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    failed_at: datetime | None = None
    failure_reason: str | None = Field(
        default=None,
        description="Channel provider error or internal dispatch failure reason.",
    )
    # Raw data payload in full (no truncation for admin inspection)
    data: dict[str, Any] | None = None


class NotificationBatchCreate(BaseSchema):
    """
    Input schema for bulk notification dispatch operations.

    Used by the campaign service and scheduled reminders to send the same
    notification type to multiple users in a single service call.
    Each recipient gets an individual Notification record created.
    """

    user_ids: list[uuid.UUID] = Field(
        min_length=1,
        max_length=10_000,
        description="List of recipient user UUIDs. Maximum 10,000 per batch.",
    )
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(max_length=200)
    body: str
    action_url: str | None = Field(default=None, max_length=2048)
    image_url: str | None = Field(default=None, max_length=2048)
    data: dict[str, Any] | None = None
    reference_type: str | None = Field(default=None, max_length=100)
    reference_id: uuid.UUID | None = None
    scheduled_at: datetime | None = Field(
        default=None,
        description="Batch scheduled delivery time. None = dispatch immediately.",
    )

    @field_validator("user_ids")
    @classmethod
    def no_duplicate_users(cls, v: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(v) != len(set(v)):
            raise ValueError("user_ids must not contain duplicates.")
        return v
