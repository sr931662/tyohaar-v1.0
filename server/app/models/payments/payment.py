"""
Payment — the master payment record for a booking.

A single Payment captures the full customer obligation for one Booking.
Multiple PaymentAttempts track checkout retries; PaymentTransactions track
every gateway interaction; PaymentSplits describe settlement allocation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, PaymentMethod, PaymentStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.bookings.booking import Booking
    from app.models.users.user import User
    from app.models.payments.payment_transaction import PaymentTransaction
    from app.models.payments.payment_split import PaymentSplit
    from app.models.payments.refund import Refund
    from app.models.payments.payment_attempt import PaymentAttempt
    from app.models.payments.payment_webhook import PaymentWebhook


class PaymentGateway(str, enum.Enum):
    """
    Payment gateway used to process a payment.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    CASHFREE = "cashfree"
    PHONEPE = "phonepe"
    PAYTM = "paytm"
    OFFLINE = "offline"    # Cash/cheque/bank transfer collected by Tyohaar staff


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Master payment record representing the full financial obligation for a booking.

    Lifecycle:
    1. Payment created when customer initiates checkout (status=PENDING)
    2. Customer attempts payment → PaymentAttempt(s) logged
    3. Gateway processes → PaymentTransaction records created
    4. Gateway captures → payment_status=COMPLETED, captured_at set
    5. Settlement scheduled → PaymentSplit records created, settled_at set
    6. Refund requested → Refund record created

    `payment_number` is a human-readable identifier shown on receipts (e.g., PAY-2024-001234).
    It is UNIQUE and customer-facing.

    Gateway fields:
    - `gateway_order_id`: ID of the order created in the gateway (before payment)
    - `gateway_payment_id`: ID of the completed payment in the gateway
    - `gateway_signature`: HMAC signature provided by gateway after capture

    Financial invariant (enforced by service layer):
        subtotal - discount_amount + tax_amount + platform_fee = final_amount
    """

    __tablename__ = "payments"

    __table_args__ = (
        UniqueConstraint("payment_number", name="uq_payments_payment_number"),
        Index("ix_payments_booking_id", "booking_id"),
        Index("ix_payments_payer_id", "payer_id"),
        Index("ix_payments_payment_status", "payment_status"),
        Index("ix_payments_gateway_order_id", "gateway_order_id"),
        Index("ix_payments_gateway_payment_id", "gateway_payment_id"),
        CheckConstraint("subtotal >= 0", name="ck_payment_subtotal_non_negative"),
        CheckConstraint("discount_amount >= 0", name="ck_payment_discount_non_negative"),
        CheckConstraint("tax_amount >= 0", name="ck_payment_tax_non_negative"),
        CheckConstraint("platform_fee >= 0", name="ck_payment_platform_fee_non_negative"),
        CheckConstraint("final_amount >= 0", name="ck_payment_final_amount_non_negative"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    payment_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Human-readable receipt reference e.g. PAY-2024-001234",
    )

    # ── Context ───────────────────────────────────────────────────────────────

    booking_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The booking this payment is for",
    )

    payer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer making the payment",
    )

    # ── Currency & Amounts ────────────────────────────────────────────────────

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Package/item price before discounts and taxes",
    )

    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total discount applied (coupon, promotional, etc.)",
    )

    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Total GST collected (CGST + SGST or IGST)",
    )

    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Tyohaar convenience/platform fee charged to the customer",
    )

    final_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total amount due: subtotal - discount + tax + platform_fee",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    payment_status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        SAEnum(PaymentMethod, name="payment_method", native_enum=False),
        nullable=True,
        comment="Set after the customer selects a method at checkout",
    )

    # ── Gateway ───────────────────────────────────────────────────────────────

    gateway: Mapped[PaymentGateway | None] = mapped_column(
        SAEnum(PaymentGateway, name="payment_gateway", native_enum=False),
        nullable=True,
        comment="Which payment gateway processed this payment",
    )

    gateway_order_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Gateway order ID created before customer pays (e.g. Razorpay order_xxxxxxxx)",
    )

    gateway_payment_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Gateway payment ID after successful capture (e.g. Razorpay pay_xxxxxxxx)",
    )

    gateway_signature: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "HMAC-SHA256 signature from the gateway verifying payment authenticity. "
            "Checkout-flow signatures (order_id|payment_id) are verified against "
            "our key_secret; inbound webhook payloads are verified separately "
            "against our webhook_secret. Either scheme marks the payment COMPLETED."
        ),
    )

    # ── Timestamps ────────────────────────────────────────────────────────────

    captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the gateway confirmed funds were captured",
    )

    settled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the settlement batch for this payment was processed",
    )

    failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When payment was definitively marked as failed (all retries exhausted)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    booking: Mapped[Booking] = relationship(
        "Booking",
        back_populates="payments",
        lazy="noload",
    )

    payer: Mapped[User] = relationship("User", lazy="noload")

    transactions: Mapped[List[PaymentTransaction]] = relationship(
        "PaymentTransaction",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    splits: Mapped[List[PaymentSplit]] = relationship(
        "PaymentSplit",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    refunds: Mapped[List[Refund]] = relationship(
        "Refund",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    attempts: Mapped[List[PaymentAttempt]] = relationship(
        "PaymentAttempt",
        back_populates="payment",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    webhooks: Mapped[List[PaymentWebhook]] = relationship(
        "PaymentWebhook",
        back_populates="payment",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Payment id={self.id} number={self.payment_number!r} "
            f"amount={self.final_amount} status={self.payment_status}>"
        )
