"""
BookingStatusRecord — current-state analytics snapshot for a booking.

Provides a pre-computed, analytics-friendly view of a booking's present status
without polluting the core Booking table. Updated synchronously by the service
layer on every status transition.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BookingStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking


class BookingStatusRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Denormalized current-status analytics snapshot for a single booking.

    One record per booking (enforced by UNIQUE on booking_id). The service layer
    upserts this record on every booking status change.

    AUTHORITY: This table is DERIVED from Booking and BookingStatusHistory.
    It must never be treated as the authoritative source — always read Booking
    for the canonical status. This record exists solely for:
    - SLA monitoring (overdue bookings, at-risk transitions)
    - Operational dashboards (pending actions, escalations)
    - Analytics (time-in-status, transition throughput)
    - Push alerts (requires_action flag for the ops team)

    SLA deadlines are computed from business policy per status:
        PENDING → CONFIRMED:    30 minutes (vendor assignment window)
        CONFIRMED → IN_PROGRESS: booking's scheduled_date
        IN_PROGRESS → COMPLETED: scheduled_date + 48 hours
    When now() > sla_deadline_at and status hasn't progressed, sla_breached
    is set by the background SLA monitor job, triggering escalation.

    `transition_summary` JSONB accumulates time-in-status data:
        {
          "pending":     12,
          "confirmed":   4320,
          "in_progress": 60
        }
    Values are minutes elapsed in each status, updated on each transition.
    Enables per-status analytics without replaying BookingStatusHistory rows.
    """

    __tablename__ = "booking_status_records"

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_booking_status_records_booking_id"),
        Index("ix_booking_status_records_current_status", "current_status"),
        Index("ix_booking_status_records_sla", "sla_deadline_at", "sla_breached"),
        Index("ix_booking_status_records_requires_action", "requires_action"),
        CheckConstraint(
            "status_duration_minutes >= 0",
            name="ck_booking_status_records_duration_non_negative",
        ),
        CheckConstraint(
            "total_transitions >= 0",
            name="ck_booking_status_records_transitions_non_negative",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        comment="The booking this snapshot belongs to. One record per booking.",
    )

    # ── Current Status ────────────────────────────────────────────────────────

    current_status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=False,
        comment=(
            "Mirrors Booking.booking_status. Updated synchronously on every "
            "status change. Read Booking for the authoritative value."
        ),
    )

    previous_status: Mapped[BookingStatus | None] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=True,
        comment="The status immediately before current_status. NULL for initial state.",
    )

    status_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Timestamp when the booking transitioned into current_status.",
    )

    status_duration_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Time spent in the *previous* status before this transition (minutes). "
            "NULL for the initial PENDING entry."
        ),
    )

    # ── SLA & Escalation ──────────────────────────────────────────────────────

    sla_deadline_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Business-policy deadline for the current status to progress. "
            "NULL when no SLA applies to the current status."
        ),
    )

    sla_breached: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when now() > sla_deadline_at and status has not advanced. "
            "Set by the background SLA monitor; triggers escalation notification."
        ),
    )

    sla_breached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when sla_breached was first set to True.",
    )

    escalated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the booking was escalated to a senior ops member.",
    )

    # ── Pending Action ────────────────────────────────────────────────────────

    requires_action: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when the booking requires an explicit human action "
            "(e.g., vendor assignment, refund approval, cancellation review)."
        ),
    )

    pending_action: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Short description of the required action shown on the ops dashboard.",
    )

    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the ops/admin user assigned to resolve the pending action. "
            "Not a FK to avoid circular dependency with the Admin domain."
        ),
    )

    # ── Transition Analytics ──────────────────────────────────────────────────

    total_transitions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Cumulative count of status transitions this booking has undergone.",
    )

    transition_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Per-status time accumulator: {status_value: total_minutes_spent}. "
            "Updated on each transition. Enables analytics without replaying history. "
            "Example: {pending: 12, confirmed: 4320, in_progress: 60}."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        lazy="noload",
    )

    @property
    def is_sla_at_risk(self) -> bool:
        """True when now() has reached the SLA deadline but breach is not yet recorded."""
        from datetime import timezone
        return (
            self.sla_deadline_at is not None
            and not self.sla_breached
            and datetime.now(timezone.utc) >= self.sla_deadline_at
        )

    def __repr__(self) -> str:
        return (
            f"<BookingStatusRecord booking_id={self.booking_id} "
            f"status={self.current_status} sla_breached={self.sla_breached} "
            f"requires_action={self.requires_action}>"
        )
