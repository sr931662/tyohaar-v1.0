"""
NotificationTemplate — reusable content templates for all notification channels.

One logical template_key can have separate rows for each channel and language,
enabling the same event (e.g. "booking_confirmed") to produce appropriately
formatted content for Push, SMS, Email, and WhatsApp from a single key.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import NotificationChannel, NotificationType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notifications.notification import Notification


class NotificationTemplate(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A versioned, channel-specific notification content template.

    Multi-channel reuse:
        The same `template_key` (e.g. "booking_confirmed") maps to multiple rows,
        one per channel. The notification service selects the correct row by
        (template_key, channel, language, version):

            template_key="booking_confirmed", channel=PUSH,  language="en", version=1
            template_key="booking_confirmed", channel=SMS,   language="en", version=1
            template_key="booking_confirmed", channel=EMAIL, language="en", version=1
            template_key="booking_confirmed", channel=PUSH,  language="hi", version=1

    Localization:
        `language` is a BCP-47 tag ("en", "hi", "ta", etc.). To add a new language,
        insert a new row with the same template_key/channel/version and the new language.

    A/B testing:
        Increment `version` to create a test variant. Both version=1 and version=2
        can be active simultaneously; the service layer picks the variant per user.

    Template syntax:
        `title_template` and `body_template` use Jinja2/Mustache placeholders,
        e.g. "Your booking {{booking_number}} is confirmed!" The `variables` JSONB
        documents the expected context dict so callers know what to pass.

    `variables` JSONB structure:
        {
          "booking_number": {"type": "string", "description": "Human-readable booking ID"},
          "customer_name":  {"type": "string", "description": "Customer first name"},
          "event_date":     {"type": "string", "description": "Formatted celebration date"}
        }

    `category` is the NotificationType this template belongs to, enabling the
    notification service to auto-select the right template from a type+channel pair.
    """

    __tablename__ = "notification_templates"

    __table_args__ = (
        UniqueConstraint(
            "template_key", "channel", "language", "version",
            name="uq_notification_templates_key_channel_lang_ver",
        ),
        Index("ix_notification_templates_key", "template_key"),
        Index("ix_notification_templates_channel", "channel"),
        Index("ix_notification_templates_category", "notification_category"),
        Index("ix_notification_templates_active", "is_active"),
        CheckConstraint("version >= 1", name="ck_notification_templates_version_min"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    template_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment=(
            "Machine-readable identifier for this notification event. "
            "Same key across all channels and languages. "
            "Examples: booking_confirmed, payment_successful, membership_activated."
        ),
    )

    # ── Targeting ─────────────────────────────────────────────────────────────

    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(NotificationChannel, name="notification_channel", native_enum=False),
        nullable=False,
        comment="Which delivery channel this variant is designed for.",
    )

    language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        comment="BCP-47 language tag. Default 'en'. Add rows for 'hi', 'ta', etc.",
    )

    version: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment="Template version. Increment for A/B variants or content revisions.",
    )

    # ── Category ──────────────────────────────────────────────────────────────

    notification_category: Mapped[NotificationType] = mapped_column(
        SAEnum(NotificationType, name="notification_type", native_enum=False),
        nullable=False,
        comment=(
            "The notification event type this template handles. "
            "Enables auto-selection by (notification_category, channel, language)."
        ),
    )

    # ── Content ───────────────────────────────────────────────────────────────

    title_template: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment=(
            "Jinja2/Mustache title template. "
            "Example: 'Booking {{booking_number}} Confirmed!'."
        ),
    )

    body_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Full notification body template. Used for push body, email body, WhatsApp message. "
            "For SMS, short_body_template is used if present."
        ),
    )

    short_body_template: Mapped[str | None] = mapped_column(
        String(320),
        nullable=True,
        comment=(
            "Concise body template for SMS (≤160 chars after rendering) and "
            "push notification preview text. Falls back to body_template if NULL."
        ),
    )

    # ── Variable Schema ───────────────────────────────────────────────────────

    variables: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Documentation of template variables: {var_name: {type, description, required}}. "
            "Used for validation and auto-completion in the admin panel."
        ),
    )

    # ── Metadata ──────────────────────────────────────────────────────────────

    description: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Internal description of what this template is for and when it fires.",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inactive templates are ignored by the notification service.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    notifications: Mapped[List[Notification]] = relationship(
        "Notification",
        back_populates="template",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<NotificationTemplate key={self.template_key!r} "
            f"channel={self.channel} lang={self.language} v{self.version}>"
        )
