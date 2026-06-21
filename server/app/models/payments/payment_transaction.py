"""
PaymentTransaction — append-only ledger of every gateway interaction for a payment.

Covers: authorization, capture, refund, partial refund, chargeback, failure, retry.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, TransactionType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.payment import Payment


class PaymentTransaction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single gateway interaction record within the lifecycle of a payment.

    Transactions are APPEND-ONLY — they record every interaction with the
    payment gateway: authorization, capture, failure, refund attempt, etc.

    `gateway_transaction_id` is the gateway's reference for this specific
    interaction (e.g., Razorpay `pay_xxxxxx` for capture, `rfnd_xxxxxx` for refund).

    `raw_response` stores the full JSON response from the gateway for debugging
    and reconciliation. Never expose this to customers.

    `is_success` is derived from the gateway response and stored for fast queries.
    """

    __tablename__ = "payment_transactions"

    __table_args__ = (
        Index("ix_payment_transactions_payment_id", "payment_id"),
        Index("ix_payment_transactions_type", "payment_id", "transaction_type"),
        Index("ix_payment_transactions_gateway_id", "gateway_transaction_id"),
        CheckConstraint("amount >= 0", name="ck_payment_tx_amount_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Transaction Details ───────────────────────────────────────────────────

    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type", native_enum=False),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount involved in this interaction (capture, refund, etc.)",
    )

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    # ── Gateway Reference ─────────────────────────────────────────────────────

    gateway_transaction_id: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Gateway's own ID for this transaction (pay_xxx, rfnd_xxx, etc.)",
    )

    # ── Result ────────────────────────────────────────────────────────────────

    is_success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    error_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Gateway error code (e.g. 'BAD_REQUEST_ERROR', 'INSUFFICIENT_FUNDS')",
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable error message from the gateway",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When this gateway interaction was initiated",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the gateway confirmed the result",
    )

    processing_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Time from initiation to completion in milliseconds",
    )

    # ── Raw Response (internal only) ──────────────────────────────────────────

    raw_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Full JSON response from the payment gateway. Internal only.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment] = relationship(
        "Payment",
        back_populates="transactions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentTransaction id={self.id} payment_id={self.payment_id} "
            f"type={self.transaction_type} amount={self.amount} ok={self.is_success}>"
        )
