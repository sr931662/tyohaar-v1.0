"""
Notifications domain — create (input) schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field, HttpUrl, field_validator

from app.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.schemas.base import BaseSchema

__all__ = [
    "NotificationCreate",
    "NotificationTemplateCreate",
]


class NotificationCreate(BaseSchema):
    """
    Service-layer input for creating a single notification record.

    Used by the notification dispatch service, NOT by public HTTP endpoints.
    The service layer resolves the template, renders the body, and then
    creates a record via this schema before dispatching to the channel adapter.
    """

    user_id: uuid.UUID = Field(description="Recipient user UUID.")
    notification_type: NotificationType = Field(
        description="Semantic type drives template selection and client routing.",
    )
    channel: NotificationChannel = Field(
        description="Delivery channel: PUSH, SMS, EMAIL, WHATSAPP, or IN_APP.",
    )
    priority: NotificationPriority = Field(
        default=NotificationPriority.NORMAL,
        description="Dispatch priority; CRITICAL notifications bypass batching.",
    )
    title: str = Field(
        max_length=200,
        description="Notification title / subject line.",
    )
    body: str = Field(
        description="Full notification body text (plain text or HTML for EMAIL).",
    )
    action_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Deep link or web URL opened when the user taps the notification.",
    )
    image_url: str | None = Field(
        default=None,
        max_length=2048,
        description="Rich media image URL for push / in-app notifications.",
    )
    data: dict[str, Any] | None = Field(
        default=None,
        description="Structured JSON payload forwarded to the client app (e.g. booking_id).",
    )
    reference_type: str | None = Field(
        default=None,
        max_length=100,
        description="Entity type this notification relates to, e.g. 'booking'.",
    )
    reference_id: uuid.UUID | None = Field(
        default=None,
        description="UUID of the related entity.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Future timestamp to schedule deferred delivery. None = send immediately.",
    )

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Notification title must not be blank.")
        return v


class NotificationTemplateCreate(BaseSchema):
    """
    Admin input for creating a Jinja2 notification template.

    Templates are keyed on (notification_type, channel, language) —
    the notification service looks up the matching template at dispatch time.
    Variable placeholders use Jinja2 syntax: {{ booking_number }}.
    """

    notification_type: NotificationType
    channel: NotificationChannel
    title_template: str = Field(
        max_length=300,
        description="Jinja2 template for the notification title/subject.",
    )
    body_template: str = Field(
        description="Jinja2 template for the full notification body.",
    )
    language: str = Field(
        default="en",
        max_length=10,
        pattern=r"^[a-z]{2}(-[A-Z]{2})?$",
        description="BCP-47 language tag, e.g. 'en', 'hi', 'ta'.",
    )
    is_active: bool = Field(
        default=True,
        description="Inactive templates are skipped during dispatch.",
    )


class BroadcastCreate(BaseSchema):
    """Admin: send a broadcast notification to a group of users."""

    title: str = Field(max_length=300, description="Broadcast notification title.")
    body: str = Field(description="Broadcast notification body.")
    notification_type: NotificationType = Field(default=NotificationType.SYSTEM)
    channel: NotificationChannel = Field(default=NotificationChannel.IN_APP)
    target_segment: str | None = Field(
        default="all",
        description="'all', 'customers', or 'vendors'. Ignored when recipient_ids is set.",
    )
    recipient_ids: list[uuid.UUID] | None = Field(
        default=None,
        description="Explicit list of user UUIDs to notify. Overrides target_segment.",
    )
    scheduled_at: datetime | None = Field(
        default=None,
        description="Optional future time to deliver; None means immediate.",
    )
    metadata: dict[str, Any] | None = None


class NotificationFromTemplateCreate(BaseSchema):
    """Trigger a templated notification for a specific user and event."""

    user_id: uuid.UUID = Field(description="Recipient user ID.")
    template_key: str = Field(description="Key of the NotificationTemplate to render and send.")
    notification_type: NotificationType
    channel: NotificationChannel
    language: str = Field(default="en", max_length=10)
    context_data: dict[str, Any] = Field(
        default_factory=dict,
        description="Template variable values injected into the Jinja2 template.",
    )
    reference_id: uuid.UUID | None = None
    reference_type: str | None = Field(default=None, max_length=100)
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
