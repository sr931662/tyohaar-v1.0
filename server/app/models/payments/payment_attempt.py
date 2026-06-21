"""
PaymentAttempt — records every checkout attempt for a payment, including failures.

Enables retry analytics, fraud detection, and UX debugging.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.payment import Payment


class PaymentAttemptStatus(str, enum.Enum):
    """
    Outcome status of a single payment checkout attempt.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    INITIATED = "initiated"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class PaymentAttempt(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single customer checkout attempt for a payment.

    Multiple attempts exist for the same Payment when the customer retries
    after a failure (network error, bank decline, timeout, etc.).

    `attempt_number` starts at 1 and increments per payment.
    `processing_duration_ms` measures gateway round-trip time for SLA monitoring.

    `device_info` JSONB structure:
        {
          "platform": "android",
          "os_version": "14",
          "app_version": "2.1.0",
          "device_model": "Pixel 8",
          "network_type": "4G"
        }

    `gateway_response` stores the raw error or success response from the gateway.
    This is INTERNAL and must never be exposed to customers.
    """

    __tablename__ = "payment_attempts"

    __table_args__ = (
        Index("ix_payment_attempts_payment_id", "payment_id"),
        Index("ix_payment_attempts_status", "payment_id", "attempt_status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Attempt Sequence ──────────────────────────────────────────────────────

    attempt_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Sequential counter starting at 1 per payment",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    attempt_status: Mapped[PaymentAttemptStatus] = mapped_column(
        SAEnum(PaymentAttemptStatus, name="payment_attempt_status", native_enum=False),
        nullable=False,
        default=PaymentAttemptStatus.INITIATED,
    )

    # ── Device & Network ──────────────────────────────────────────────────────

    device_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Platform, OS, app version, device model, network type",
    )

    ip_address: Mapped[str | None] = mapped_column(
        INET,
        nullable=True,
        comment="Customer's IP address at checkout time (IPv4 or IPv6)",
    )

    # ── Gateway Response ──────────────────────────────────────────────────────

    gateway_response: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw gateway response for this attempt. INTERNAL — never expose to customers.",
    )

    failure_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Human-readable failure reason for internal analytics",
    )

    failure_code: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Machine-readable error code from gateway (e.g. 'INSUFFICIENT_FUNDS')",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    initiated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processing_duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Gateway round-trip time in milliseconds for SLA monitoring",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    payment: Mapped[Payment] = relationship(
        "Payment",
        back_populates="attempts",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentAttempt id={self.id} payment_id={self.payment_id} "
            f"attempt={self.attempt_number} status={self.attempt_status}>"
        )
