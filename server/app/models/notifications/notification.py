"""
Notification — a single notification instance dispatched (or scheduled) for a user.

Each row is an immutable record of intent + delivery outcome for one recipient,
one channel, and one event. Multiple channels for the same event produce multiple rows.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.notifications.template import NotificationTemplate


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A notification dispatched (or pending dispatch) to a single user on a single channel.

    Architecture:
    - One row per recipient × channel combination.
    - If "booking_confirmed" should be sent via Push + SMS + Email, the service
      creates three Notification rows sharing the same reference_type/reference_id.
    - The template_id links to the rendered source template (nullable for ad-hoc).

    Delivery state machine (notification_status):
        PENDING → SENT → DELIVERED → READ
                       ↘ FAILED (retry_count < max_retries → back to PENDING)

    Idempotency:
        `idempotency_key` is an optional caller-provided stable key. The service
        layer performs an upsert on (idempotency_key) when set, preventing duplicate
        notifications from multiple publish events (e.g., webhook retries).

    Scheduling:
        `scheduled_at` is set for future delivery. The dispatcher skips rows where
        NOW() < scheduled_at. `expires_at` causes the dispatcher to skip overdue
        notifications that are no longer actionable (e.g., event reminders after the event).

    Deep linking:
        `deep_link` carries the mobile URI scheme e.g. "tyohaar://bookings/{id}".
        `action_url` is the web fallback. `action_label` is the CTA button text.

    `device_token_snapshot` stores the FCM/APNS token at send time.
    Tokens rotate; this snapshot lets support diagnose delivery failures
    even after the token has changed.

    `reference_type` + `reference_id` form a polymorphic pointer to the triggering entity:
        - "booking"     → bookings.id
        - "payment"     → payments.id
        - "celebration" → celebrations.id
        - "membership"  → user_memberships.id
        - "system"      → NULL
    """

    __tablename__ = "notifications"

    __table_args__ = (
        Index("ix_notifications_recipient_id", "recipient_id"),
        Index("ix_notifications_recipient_status", "recipient_id", "notification_status"),
        Index("ix_notifications_recipient_channel", "recipient_id", "channel"),
        Index("ix_notifications_scheduled_at", "scheduled_at"),
        Index("ix_notifications_reference", "reference_type", "reference_id"),
        Index("ix_notifications_idempotency_key", "idempotency_key", unique=True),
        Index("ix_notifications_created_at", "created_at"),
    )

    # ── Recipients ────────────────────────────────────────────────────────────

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="User who will receive this notification.",
    )

    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "User or admin who triggered this notification. "
            "NULL for system-generated notifications."
        ),
    )

    # ── Template ──────────────────────────────────────────────────────────────

    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("notification_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Source template used to render title/body. "
            "NULL for ad-hoc programmatic notifications."
        ),
    )

    # ── Classification ────────────────────────────────────────────────────────

    notification_type: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type", native_enum=False),
        nullable=False,
    )

    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, name="notification_channel", native_enum=False),
        nullable=False,
        comment="Delivery channel for this specific notification row.",
    )

    priority: Mapped[NotificationPriority] = mapped_column(
        SAEnum(NotificationPriority, name="notification_priority", native_enum=False),
        nullable=False,
        default=NotificationPriority.NORMAL,
    )

    # ── Content ───────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Rendered notification title (after template variable substitution).",
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full rendered notification body.",
    )

    short_body: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment="Concise body for SMS or push preview (≤160 chars). Falls back to body if NULL.",
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Rich notification image URL (for push rich media, email header image).",
    )

    # ── Action / Deep Link ────────────────────────────────────────────────────

    deep_link: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Mobile URI scheme e.g. 'tyohaar://bookings/{id}' for push tap action.",
    )

    action_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="CTA button label e.g. 'View Booking', 'Pay Now', 'Track Order'.",
    )

    action_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Web URL for the CTA button (email / web push fallback to deep_link).",
    )

    # ── Source Reference (polymorphic) ────────────────────────────────────────

    reference_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Entity type that triggered this notification: booking, payment, celebration, etc.",
    )

    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the triggering entity. Not a FK to allow cross-domain flexibility.",
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Future delivery time. NULL = send immediately. "
            "The dispatcher skips rows where scheduled_at > NOW()."
        ),
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Stale-after timestamp. Dispatcher skips delivery if NOW() > expires_at. "
            "Example: event reminder expires after the event date."
        ),
    )

    # ── Idempotency ───────────────────────────────────────────────────────────

    idempotency_key: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        unique=True,
        comment=(
            "Optional caller-supplied deduplication key (UNIQUE). "
            "Format: '{event_type}:{reference_id}:{channel}'. "
            "Prevents duplicate sends on webhook retries."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────

    notification_status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(NotificationStatus, name="notification_status", native_enum=False),
        nullable=False,
        default=NotificationStatus.PENDING,
    )

    # ── Delivery Timestamps ───────────────────────────────────────────────────

    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the notification was handed off to the delivery provider.",
    )

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When delivery to the device/inbox was confirmed by the provider.",
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user opened or acknowledged the notification.",
    )

    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user explicitly dismissed or cleared the notification.",
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the most recent delivery failure.",
    )

    # ── Retry ─────────────────────────────────────────────────────────────────

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of delivery attempts made after the initial send.",
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Last failure message from the provider (e.g. 'InvalidToken', 'Unsubscribed').",
    )

    # ── Provider Context ──────────────────────────────────────────────────────

    device_token_snapshot: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "FCM/APNS token captured at send time. Tokens rotate; this snapshot "
            "enables post-mortem debugging of delivery failures."
        ),
    )

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Provider-specific context: FCM message ID, SES message ID, "
            "Twilio SID, campaign tags, A/B variant, etc."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    recipient: Mapped[User] = relationship(
        "User",
        foreign_keys=[recipient_id],
        lazy="noload",
    )

    sender: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[sender_id],
        lazy="noload",
    )

    template: Mapped[NotificationTemplate | None] = relationship(
        "NotificationTemplate",
        back_populates="notifications",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Notification id={self.id} type={self.notification_type} "
            f"channel={self.channel} status={self.notification_status}>"
        )
