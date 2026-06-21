"""
Notifications domain — filter query parameter schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import Field

from app.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.schemas.base import BaseSchema

__all__ = [
    "NotificationFilters",
]


class NotificationFilters(BaseSchema):
    """
    Filter parameters for notification history and admin dispatch monitoring.

    All fields are optional. The standard customer endpoint pre-filters on
    the authenticated user_id at the router level.
    """

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Filter notifications belonging to a specific user (admin use).",
    )
    notification_type: NotificationType | None = Field(
        default=None,
        description="Filter by semantic notification type.",
    )
    channel: NotificationChannel | None = Field(
        default=None,
        description="Filter by delivery channel.",
    )
    status: NotificationStatus | None = Field(
        default=None,
        description="Filter by dispatch lifecycle status.",
    )
    is_read: bool | None = Field(
        default=None,
        description="True = unread only; False = read only; None = all (in-app inbox).",
    )
    priority: NotificationPriority | None = Field(
        default=None,
        description="Filter by dispatch priority.",
    )
    from_date: datetime | None = Field(
        default=None,
        description="Include only notifications created at or after this timestamp.",
    )
    to_date: datetime | None = Field(
        default=None,
        description="Include only notifications created at or before this timestamp.",
    )
    reference_type: str | None = Field(
        default=None,
        max_length=100,
        description="Filter by related entity type, e.g. 'booking'.",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="Filter by specific related entity UUID.",
    )
