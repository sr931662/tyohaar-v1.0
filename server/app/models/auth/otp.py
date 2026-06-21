"""
OTPRecord — production-grade OTP storage for all authentication flows.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import OTPDeliveryChannel, OTPPurpose, OTPStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OTPRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Persistent record of every OTP issued across all authentication flows.

    Security model:
    - OTPs are NEVER stored in plain text. Only a HMAC-SHA256 hash is persisted.
    - At most one PENDING OTP exists per (identifier, purpose) pair at any time;
      issuing a new OTP atomically supersedes the previous one.
    - attempt_count enforces brute-force protection; the record is marked
      EXHAUSTED when max_attempts is reached.
    - resend_count enforces rate limiting on retries within a time window.
    - IP address, user agent, and device fingerprint support abuse detection,
      velocity checks, and forensic investigation.
    - failure_log provides a tamper-evident audit trail of every bad attempt.

    Cleanup:
    - A background job should periodically hard-delete rows where status is
      VERIFIED, EXPIRED, EXHAUSTED, or SUPERSEDED and created_at < retention window.
    """

    __tablename__ = "otp_records"

    __table_args__ = (
        # Primary query path: fetch the active OTP for a given identifier+purpose
        Index("ix_otp_identifier_purpose_status", "identifier", "purpose", "status"),
        # Efficient cleanup: find all expired/stale OTPs by TTL
        Index("ix_otp_expires_at", "expires_at"),
        # Ownership lookup
        Index("ix_otp_user_id", "user_id"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_non_negative"),
        CheckConstraint("resend_count >= 0", name="resend_count_non_negative"),
        CheckConstraint("max_attempts > 0", name="max_attempts_positive"),
        CheckConstraint("max_resends >= 0", name="max_resends_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "NULL for pre-registration OTPs where the user row does not yet exist. "
            "Populated after account creation is confirmed."
        ),
    )

    # ── Delivery Target ───────────────────────────────────────────────────────

    identifier: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        comment="Phone number (E.164 format) or email address the OTP was sent to",
    )

    channel: Mapped[OTPDeliveryChannel] = mapped_column(
        SAEnum(OTPDeliveryChannel, name="otp_delivery_channel", native_enum=False),
        nullable=False,
        comment="Delivery channel: SMS, EMAIL, WHATSAPP, or VOICE",
    )

    # ── Intent ────────────────────────────────────────────────────────────────

    purpose: Mapped[OTPPurpose] = mapped_column(
        SAEnum(OTPPurpose, name="otp_purpose", native_enum=False),
        nullable=False,
        comment="Declares why this OTP was issued; prevents cross-purpose reuse",
    )

    # ── Lifecycle State ───────────────────────────────────────────────────────

    status: Mapped[OTPStatus] = mapped_column(
        SAEnum(OTPStatus, name="otp_status", native_enum=False),
        nullable=False,
        default=OTPStatus.PENDING,
        index=True,
    )

    # ── Security: Stored Credential ───────────────────────────────────────────

    otp_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment=(
            "HMAC-SHA256(secret_key, otp + identifier + purpose + issued_at). "
            "Never store the plain OTP. Verify by re-computing the hash."
        ),
    )

    # ── Brute-Force Protection ────────────────────────────────────────────────

    attempt_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Number of incorrect verification attempts so far",
    )

    max_attempts: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        comment="Maximum incorrect attempts allowed before the OTP is exhausted",
    )

    # ── Resend Rate Limiting ──────────────────────────────────────────────────

    resend_count: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Number of times this OTP has been resent",
    )

    max_resends: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=3,
        comment="Maximum resends allowed within the current rate-limit window",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Hard expiry timestamp. OTP is invalid after this point regardless of status.",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Set when the OTP is successfully verified by the user",
    )

    # ── Request Context ───────────────────────────────────────────────────────

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment="IPv4 or IPv6 address of the client that requested this OTP",
    )

    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Raw User-Agent header from the OTP request",
    )

    device_fingerprint: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        comment=(
            "Client-generated device fingerprint (canvas hash, screen dims, fonts, etc.). "
            "Used for cross-session device recognition and velocity abuse detection."
        ),
    )

    # ── Failure Tracking ──────────────────────────────────────────────────────

    failure_reason: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable reason for the last failure (wrong_otp / expired / exhausted)",
    )

    failure_log: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Append-only array of failed attempt records. "
            "Each entry: {timestamp, reason, ip_address, user_agent}. "
            "Retained for forensics and abuse pattern analysis."
        ),
    )

    # ── Gateway Delivery Status ───────────────────────────────────────────────

    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the SMS/email gateway confirmed delivery",
    )

    delivery_reference: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Message SID or reference ID returned by the delivery gateway",
    )

    # ── Computed Properties ───────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_attempts_exhausted(self) -> bool:
        return self.attempt_count >= self.max_attempts

    @property
    def is_usable(self) -> bool:
        """True only if this OTP can still be presented for verification."""
        return (
            self.status == OTPStatus.PENDING
            and not self.is_expired
            and not self.is_attempts_exhausted
        )

    def __repr__(self) -> str:
        return (
            f"<OTPRecord id={self.id} identifier={self.identifier!r} "
            f"purpose={self.purpose} status={self.status}>"
        )
