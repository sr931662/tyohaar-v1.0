"""
PaymentWebhook — persists every incoming payment gateway webhook event.

Never trust webhook delivery: store first, process idempotently.
"""

from __future__ import annotations

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.payment import Payment, PaymentGateway


class PaymentWebhook(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A persisted record of every incoming webhook event from a payment gateway.

    Design principles:
    - STORE FIRST: the raw payload is persisted before any processing begins.
    - IDEMPOTENT: `event_id` is UNIQUE — duplicate webhook deliveries are detected
      and skipped without reprocessing.
    - VERIFIABLE: `is_signature_verified` records whether the HMAC-SHA256 signature
      was valid; unverified events are not processed.

    Processing lifecycle:
    1. Gateway sends webhook → raw_payload saved, is_processed=False
    2. Signature verified → is_signature_verified updated
    3. Service processes event → is_processed=True, processing_result set
    4. On error: processing_error set, retry_count incremented

    `payment_id` is nullable because webhooks may arrive before the local
    Payment record is created (race condition in async systems). The service
    layer links them after the fact.

    `event_id` format varies by gateway:
    - Razorpay: evt_xxxxxxxxxxxxxxxxxx
    - Stripe: evt_xxxxxxxxxxxxxxxxxx
    """

    __tablename__ = "payment_webhooks"

    __table_args__ = (
        UniqueConstraint("event_id", "gateway", name="uq_payment_webhooks_event_gateway"),
        Index("ix_payment_webhooks_payment_id", "payment_id"),
        Index("ix_payment_webhooks_processed", "is_processed", "is_signature_verified"),
        Index("ix_payment_webhooks_event_type", "gateway", "event_type"),
        Index("ix_payment_webhooks_received_at", "received_at"),
    )

    # ── Gateway Identification ────────────────────────────────────────────────

    event_id: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Gateway's unique event ID. Used for idempotent deduplication.",
    )

    gateway: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment=(
            "Which gateway sent this webhook (razorpay, stripe, cashfree, etc.). "
            "Use PaymentGateway enum values from payment.py."
        ),
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Gateway event type e.g. 'payment.captured', 'refund.processed'",
    )

    # ── Link to Payment ───────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Linked after processing. NULL on arrival — race condition "
            "means payment may not exist yet."
        ),
    )

    # ── Verification ──────────────────────────────────────────────────────────

    is_signature_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if HMAC-SHA256 signature was validated against our secret key",
    )

    signature_verification_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Details of the signature verification (algorithm, result, error if any)",
    )

    # ── Payload (immutable) ───────────────────────────────────────────────────

    raw_payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        comment=(
            "Complete webhook payload from the gateway. "
            "Never modified after initial storage — source of truth for reprocessing."
        ),
    )

    # ── Processing ────────────────────────────────────────────────────────────

    is_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the event has been fully processed without error",
    )

    processing_result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Outcome of processing (e.g. {action: 'payment_captured', booking_id: '...'})",
    )

    processing_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail if processing failed",
    )

    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of processing retry attempts made after initial failure",
    )

    # ── Timestamps ────────────────────────────────────────────────────────────

    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Exact timestamp when the HTTP webhook request was received",
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of last successful or failed processing attempt",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment | None] = relationship(
        "Payment",
        back_populates="webhooks",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentWebhook id={self.id} gateway={self.gateway} "
            f"event={self.event_type!r} processed={self.is_processed}>"
        )
