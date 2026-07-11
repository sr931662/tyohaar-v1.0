"""
CelebrationGuestHistory — append-only audit trail of guest lifecycle events.

CelebrationGuest only stores current-state columns (rsvp_status,
invitation_opened_at, etc.) with no record of prior transitions. This table
gives customers a real "History" view of what happened with their guest
list (invited, opened the invite, RSVP'd, changed their RSVP, checked in)
instead of just the current snapshot.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import GuestHistoryEventType, RSVPStatus
from app.models.mixins import UUIDPrimaryKeyMixin


class CelebrationGuestHistory(UUIDPrimaryKeyMixin, Base):
    """A single immutable record of a guest lifecycle event."""

    __tablename__ = "celebration_guest_history"

    __table_args__ = (
        Index("ix_celebration_guest_history_guest_id", "celebration_guest_id"),
        # celebration_id is denormalized so per-celebration history can be
        # queried without joining through celebration_guests for every row.
        Index("ix_celebration_guest_history_celebration_id", "celebration_id", "occurred_at"),
    )

    celebration_guest_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebration_guests.id", ondelete="CASCADE"),
        nullable=False,
    )

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    event_type: Mapped[GuestHistoryEventType] = mapped_column(
        SAEnum(GuestHistoryEventType, name="guest_history_event_type", native_enum=False),
        nullable=False,
    )

    previous_status: Mapped[RSVPStatus | None] = mapped_column(
        SAEnum(RSVPStatus, name="rsvp_status", native_enum=False),
        nullable=True,
        comment="Only set for RSVP_CHANGED events",
    )

    new_status: Mapped[RSVPStatus | None] = mapped_column(
        SAEnum(RSVPStatus, name="rsvp_status", native_enum=False),
        nullable=True,
        comment="Only set for RSVP_CHANGED events",
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<CelebrationGuestHistory guest_id={self.celebration_guest_id} "
            f"event={self.event_type}>"
        )
