"""
BookingReschedule — records of booking date/time change requests.

Multiple reschedules can be requested per booking.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.users.user import User


class RescheduleStatus(str, enum.Enum):
    """
    Approval lifecycle of a reschedule request.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BookingReschedule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A request to change the date or time of an existing booking.

    Multiple reschedule requests can be submitted for the same booking,
    creating a complete reschedule history.

    `reschedule_fee` is the charge levied for rescheduling per policy.
    `customer_confirmed` tracks whether the customer acknowledged the new
    date/time and any associated fee before the reschedule was applied.

    Policy enforcement (fee calculation, max reschedule count, blackout dates)
    is handled by the service layer — not enforced at the DB level.
    """

    __tablename__ = "booking_reschedules"

    __table_args__ = (
        Index("ix_booking_reschedules_booking_id", "booking_id"),
        Index("ix_booking_reschedules_status", "booking_id", "status"),
        CheckConstraint(
            "new_date >= old_date OR new_date IS NOT NULL",
            name="ck_booking_reschedule_new_date_set",
        ),
        CheckConstraint(
            "reschedule_fee >= 0",
            name="ck_booking_reschedule_fee_non_negative",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
    )

    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The user who requested this reschedule (customer or Tyohaar staff)",
    )

    # ── Date/Time Change ──────────────────────────────────────────────────────

    old_date: Mapped[date] = mapped_column(Date, nullable=False)

    new_date: Mapped[date] = mapped_column(Date, nullable=False)

    old_start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)

    new_start_time: Mapped[time | None] = mapped_column(Time(timezone=False), nullable=True)

    # ── Reason ────────────────────────────────────────────────────────────────

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Fee ───────────────────────────────────────────────────────────────────

    reschedule_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Fee charged for this reschedule per applicable policy",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    status: Mapped[RescheduleStatus] = mapped_column(
        SAEnum(RescheduleStatus, name="reschedule_status", native_enum=False),
        nullable=False,
        default=RescheduleStatus.PENDING_APPROVAL,
    )

    # ── Approval ──────────────────────────────────────────────────────────────

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tyohaar staff who approved or rejected this reschedule",
    )

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Customer Confirmation ─────────────────────────────────────────────────

    customer_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Customer acknowledged the new date and any fee before the change applied",
    )

    customer_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="reschedules",
        lazy="noload",
    )

    requested_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[requested_by_id],
        lazy="noload",
    )

    approved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingReschedule id={self.id} booking_id={self.booking_id} "
            f"{self.old_date} → {self.new_date} status={self.status}>"
        )
