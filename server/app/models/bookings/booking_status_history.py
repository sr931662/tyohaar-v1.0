"""
BookingStatusHistory — immutable audit log of every booking status transition.

Every status change is recorded here. Rows are never updated or deleted.
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
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BookingStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.users.user import User


class BookingStatusHistory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single immutable record of a booking status transition.

    Rows in this table are APPEND-ONLY — they must never be updated or deleted.
    Together they form a complete audit trail of the booking's lifecycle.

    `old_status` is NULL for the initial CREATED entry (no prior status).
    `changed_by_id` is NULL for system-triggered transitions (payment events, etc.).
    `transitioned_at` is the authoritative timestamp of when the change occurred
    (may differ from `created_at` for backfilled entries).

    `context_data` JSONB stores transition-specific metadata:
        CONFIRMED:         {payment_id: '...'}
        VENDOR_ASSIGNED:   {vendor_count: 3}
        COMPLETED:         {completion_notes: '...'}
        CANCELLED:         {reason: '...', refund_amount: 500}
    """

    __tablename__ = "booking_status_history"

    __table_args__ = (
        Index("ix_booking_status_history_booking_id", "booking_id"),
        Index("ix_booking_status_history_transitioned_at", "booking_id", "transitioned_at"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Transition ────────────────────────────────────────────────────────────

    old_status: Mapped[BookingStatus | None] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=True,
        comment="NULL for the initial CREATED entry",
    )

    new_status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=False,
    )

    # ── Attribution ───────────────────────────────────────────────────────────

    changed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who triggered this transition. NULL for system-triggered changes.",
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable reason for this status change",
    )

    # ── Timestamp ─────────────────────────────────────────────────────────────

    transitioned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the transition actually occurred (authoritative, may differ from created_at)",
    )

    # ── Metadata ──────────────────────────────────────────────────────────────

    context_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Transition-specific context for audit and display purposes",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="status_history",
        lazy="noload",
    )

    changed_by: Mapped[User | None] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<BookingStatusHistory id={self.id} "
            f"{self.old_status} → {self.new_status} at={self.transitioned_at}>"
        )
