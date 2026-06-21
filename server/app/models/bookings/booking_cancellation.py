"""
BookingCancellation — record of a booking cancellation with refund details.

One cancellation per booking (enforced by UNIQUE constraint on booking_id).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CancellationReason, RefundStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.users.user import User


class BookingCancellation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A cancellation record for a booking.

    One record per booking (enforced via UNIQUE on booking_id).
    Captures who cancelled, why, refund eligibility, and processing timeline.

    `policy_version` records which cancellation policy was applied at the time
    (important when policies change over time).

    Refund flow:
    - `refund_eligible`: determined by policy at cancellation time
    - `refund_amount`: calculated by service layer (may be full or partial)
    - `refund_status`: updated as the refund is processed
    - `approved_by_id`: Tyohaar staff who approved the cancellation/refund
    - `processed_at`: when the refund was actually disbursed
    """

    __tablename__ = "booking_cancellations"

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_booking_cancellations_booking_id"),
        Index("ix_booking_cancellations_booking_id", "booking_id"),
        Index("ix_booking_cancellations_cancelled_by_id", "cancelled_by_id"),
        Index("ix_booking_cancellations_refund_status", "refund_status"),
        CheckConstraint("refund_amount >= 0", name="ck_booking_cancellation_refund_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )

    # ── Cancellation Details ──────────────────────────────────────────────────

    cancelled_by_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The user who initiated the cancellation (customer, vendor, or admin)",
    )

    cancellation_reason: Mapped[CancellationReason] = mapped_column(
        SAEnum(CancellationReason, name="cancellation_reason", native_enum=False),
        nullable=False,
    )

    cancellation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Free-text elaboration on the cancellation reason",
    )

    cancelled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exact timestamp when the cancellation was initiated",
    )

    # ── Refund ────────────────────────────────────────────────────────────────

    refund_eligible: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether the customer is eligible for a refund per the policy",
    )

    refund_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Amount to be refunded. NULL until calculated by service layer.",
    )

    refund_status: Mapped[RefundStatus | None] = mapped_column(
        SAEnum(RefundStatus, name="refund_status", native_enum=False),
        nullable=True,
        comment="NULL until a refund is initiated",
    )

    # ── Policy & Approval ─────────────────────────────────────────────────────

    policy_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Cancellation policy version applied (e.g. 'v2024-01')",
    )

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tyohaar staff member who approved this cancellation",
    )

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the refund was actually disbursed",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="cancellation",
        lazy="noload",
    )

    cancelled_by: Mapped[User] = relationship(
        "User",
        foreign_keys=[cancelled_by_id],
        lazy="noload",
    )

    approved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<BookingCancellation booking_id={self.booking_id} "
            f"reason={self.cancellation_reason} refund={self.refund_amount}>"
        )
