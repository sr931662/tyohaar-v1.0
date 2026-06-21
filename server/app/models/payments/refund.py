"""
Refund — a customer refund request against a captured payment.

Supports full and partial refunds with complete approval workflow.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, RefundStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.payment import Payment
    from app.models.bookings.booking import Booking
    from app.models.users.user import User


class RefundType(str, enum.Enum):
    """
    Whether this refund covers the entire payment or only part of it.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    FULL = "full"
    PARTIAL = "partial"


class RefundReason(str, enum.Enum):
    """
    Business reason for issuing the refund.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CUSTOMER_REQUEST = "customer_request"
    VENDOR_FAILURE = "vendor_failure"
    DUPLICATE_BOOKING = "duplicate_booking"
    EVENT_CANCELLED = "event_cancelled"
    QUALITY_ISSUE = "quality_issue"
    POLICY_EXCEPTION = "policy_exception"
    PAYMENT_ERROR = "payment_error"
    ADMIN_OVERRIDE = "admin_override"


class Refund(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A refund of captured payment funds back to the customer.

    Supports full refunds (entire payment) and partial refunds (subset).
    Multiple partial refunds can exist against the same Payment.

    `gateway_refund_id` is the payment gateway's reference for this refund
    (e.g., Razorpay `rfnd_xxxxxx`). It is set when the gateway confirms initiation.

    Approval workflow:
    1. Customer requests refund (or system auto-triggers on cancellation)
    2. Tyohaar staff reviews and approves (approved_by_id set)
    3. Service layer initiates refund with gateway
    4. Gateway confirms → refund_status updated to COMPLETED

    `booking_id` is denormalized from payment.booking_id for fast admin queries.
    """

    __tablename__ = "refunds"

    __table_args__ = (
        Index("ix_refunds_payment_id", "payment_id"),
        Index("ix_refunds_booking_id", "booking_id"),
        Index("ix_refunds_refund_status", "refund_status"),
        Index("ix_refunds_initiated_by_id", "initiated_by_id"),
        CheckConstraint("amount > 0", name="ck_refund_amount_positive"),
    )

    # ── Context ───────────────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The payment being refunded",
    )

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Denormalized from payment.booking_id for fast admin queries",
    )

    # ── Refund Details ────────────────────────────────────────────────────────

    refund_type: Mapped[RefundType] = mapped_column(
        SAEnum(RefundType, name="refund_type", native_enum=False),
        nullable=False,
    )

    refund_reason: Mapped[RefundReason] = mapped_column(
        SAEnum(RefundReason, name="refund_reason", native_enum=False),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount to be refunded (must be ≤ original payment amount)",
    )

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about the refund decision",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    refund_status: Mapped[RefundStatus] = mapped_column(
        SAEnum(RefundStatus, name="refund_status", native_enum=False),
        nullable=False,
        index=True,
    )

    # ── Gateway ───────────────────────────────────────────────────────────────

    gateway_refund_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Gateway's refund reference e.g. Razorpay rfnd_xxxxxx",
    )

    # ── Workflow Timestamps ───────────────────────────────────────────────────

    initiated_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who initiated the refund (customer self-service or Tyohaar staff)",
    )

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the refund was first requested",
    )

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tyohaar staff member who approved this refund",
    )

    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the refund was confirmed as disbursed by the gateway",
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail if refund_status = FAILED",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment] = relationship(
        "Payment",
        back_populates="refunds",
        lazy="noload",
    )

    booking: Mapped[Booking] = relationship("Booking", lazy="noload")

    initiated_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[initiated_by_id],
        lazy="noload",
    )

    approved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Refund id={self.id} payment_id={self.payment_id} "
            f"type={self.refund_type} amount={self.amount} status={self.refund_status}>"
        )
