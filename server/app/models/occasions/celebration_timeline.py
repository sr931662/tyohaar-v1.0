"""
CelebrationTimeline — chronological milestones and system events for a Celebration.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration


class TimelineEventType(str, enum.Enum):
    """
    Category of event recorded on the celebration timeline.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CELEBRATION_CREATED = "celebration_created"
    PACKAGE_SELECTED = "package_selected"
    PACKAGE_BOOKED = "package_booked"
    PAYMENT_RECEIVED = "payment_received"
    INVITATION_SENT = "invitation_sent"
    GUEST_RSVP_RECEIVED = "guest_rsvp_received"
    VENUE_CONFIRMED = "venue_confirmed"
    DECORATION_STARTED = "decoration_started"
    CELEBRATION_COMPLETED = "celebration_completed"
    CHECKLIST_ITEM_DONE = "checklist_item_done"
    NOTE_ADDED = "note_added"
    SYSTEM = "system"
    CUSTOM = "custom"


class CelebrationTimeline(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single event on the celebration's timeline.

    Events can be system-generated (package booked, payment received) or
    customer-added (custom milestone, personal note).

    `occurred_at` is when the event actually happened (not when the row was created).
    `display_order` is a tiebreaker sort key within the same `occurred_at` timestamp.
    `context_data` stores event-specific metadata for rich rendering:
        PACKAGE_BOOKED: {booking_id: '...', package_name: '...', amount: 5000}
        PAYMENT_RECEIVED: {payment_id: '...', amount: 5000, method: 'UPI'}
    """

    __tablename__ = "celebration_timelines"

    __table_args__ = (
        Index("ix_celebration_timelines_celebration_id", "celebration_id"),
        Index("ix_celebration_timelines_occurred_at", "celebration_id", "occurred_at"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Event ─────────────────────────────────────────────────────────────────

    event_type: Mapped[TimelineEventType] = mapped_column(
        SAEnum(TimelineEventType, name="timeline_event_type", native_enum=False),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the event happened (may differ from created_at for backfilled events)",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Tiebreaker sort key when multiple events share the same occurred_at",
    )

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Optional icon to display next to the timeline event in the UI",
    )

    # ── Origin ────────────────────────────────────────────────────────────────

    is_system_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if created automatically by the system (bookings, payments, etc.)",
    )

    context_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Event-specific context for rich rendering (booking_id, amount, etc.)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        back_populates="timeline",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CelebrationTimeline id={self.id} type={self.event_type} "
            f"title={self.title!r}>"
        )
