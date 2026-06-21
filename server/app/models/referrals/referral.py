"""
Referral — tracks every customer referral event on the Tyohaar platform.

A Referral is created when a customer shares their unique referral code or link.
It records the full lifecycle from code generation through referred-user signup
and first-booking conversion, including fraud-prevention signals.
"""

from __future__ import annotations

import enum
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
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ReferralStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.bookings.booking import Booking
    from app.models.referrals.referral_reward import ReferralReward


class ReferralChannel(str, enum.Enum):
    """
    Channel through which the referral was shared.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    SOCIAL_MEDIA = "social_media"
    DIRECT_LINK = "direct_link"     # Copied and pasted from the app
    IN_APP = "in_app"               # Shared via Tyohaar's in-app contacts


class Referral(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single referral event from a Tyohaar customer.

    Lifecycle:
    1. Referrer generates/shares their referral code → Referral(status=PENDING) created.
    2. Referred user clicks the link and signs up → status=SIGNED_UP,
       referred_user_id set, signed_up_at recorded.
    3. Referred user completes their first booking → status=CONVERTED,
       first_booking_id set, converted_at recorded.
    4. Service layer validates eligibility and issues rewards → status=REWARDED,
       rewarded_at recorded; ReferralReward records created.
    5. If link expires before conversion → status=EXPIRED.
    6. Self-referral or fraud detected → status=INVALID, is_fraud_flagged=True.

    `referral_code` is the shared token (typically 8–12 alphanumeric characters)
    embedded in URLs like `https://tyohaar.app/join?ref=CODE`. It is globally
    unique and stable for the referrer's lifetime on the platform.

    One referrer may have multiple Referral rows (one per friend who clicked the
    link and registered), but typically shares a single stable `referral_code`.
    A unique constraint on (referrer_id, referred_user_id) prevents duplicate
    records for the same pair.

    Fraud prevention fields:
    - `ip_address`: captured at click time to detect IP-based self-referrals.
    - `device_fingerprint`: browser/device fingerprint hash from the referral click.
    - `is_fraud_flagged`: manually or automatically set when fraud signals trigger.
    - `fraud_detection_reason`: structured reason for the flag.

    `attribution` JSONB stores marketing attribution data at click time:
        {
          "utm_source": "whatsapp",
          "utm_campaign": "diwali_2024",
          "utm_medium": "referral",
          "landing_page": "/join"
        }
    """

    __tablename__ = "referrals"

    __table_args__ = (
        UniqueConstraint(
            "referrer_id", "referred_user_id",
            name="uq_referrals_referrer_referred_pair",
        ),
        Index("ix_referrals_referral_code", "referral_code"),
        Index("ix_referrals_referrer_id", "referrer_id"),
        Index("ix_referrals_referred_user_id", "referred_user_id"),
        Index("ix_referrals_referral_status", "referral_status"),
        Index("ix_referrals_expires_at", "expires_at"),
        Index("ix_referrals_fraud_flagged", "is_fraud_flagged"),
        CheckConstraint(
            "referrer_id != referred_user_id",
            name="ck_referrals_no_self_referral",
        ),
    )

    # ── Parties ───────────────────────────────────────────────────────────────

    referrer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The customer who shared the referral code.",
    )

    referred_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "The user who signed up via this referral. "
            "Set when status transitions to SIGNED_UP."
        ),
    )

    # ── Code ──────────────────────────────────────────────────────────────────

    referral_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment=(
            "The alphanumeric code embedded in the referral URL. "
            "Stable per referrer and reused across multiple Referral rows."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────

    referral_status: Mapped[ReferralStatus] = mapped_column(
        SAEnum(ReferralStatus, name="referral_status", native_enum=False),
        nullable=False,
        default=ReferralStatus.PENDING,
    )

    # ── Channel ───────────────────────────────────────────────────────────────

    channel: Mapped[ReferralChannel | None] = mapped_column(
        SAEnum(ReferralChannel, name="referral_channel", native_enum=False),
        nullable=True,
        comment="How the referral link was shared.",
    )

    # ── Lifecycle Timestamps ──────────────────────────────────────────────────

    signed_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the referred user completed registration.",
    )

    converted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the referred user completed their first booking.",
    )

    rewarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When rewards were issued for this referral.",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "When the referral link expires for this specific click/share. "
            "NULL means the code never expires."
        ),
    )

    # ── Conversion Context ────────────────────────────────────────────────────

    first_booking_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="SET NULL"),
        nullable=True,
        comment="The first booking made by the referred user (the conversion event).",
    )

    # ── Fraud Prevention ──────────────────────────────────────────────────────

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
        comment=(
            "IP address captured at referral link click time. "
            "Stored as text to support both IPv4 and IPv6 (max 45 chars). "
            "Used for same-IP self-referral detection."
        ),
    )

    device_fingerprint: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Browser/device fingerprint hash captured at referral click.",
    )

    is_fraud_flagged: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when fraud signals triggered: same IP as referrer, "
            "same device, self-referral attempt, or velocity anomaly."
        ),
    )

    fraud_detection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Structured reason for the fraud flag. Internal only.",
    )

    fraud_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When a fraud analyst reviewed and resolved the flag.",
    )

    fraud_reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who reviewed and cleared or confirmed the fraud flag.",
    )

    # ── Attribution ───────────────────────────────────────────────────────────

    attribution: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Marketing attribution at click time: "
            "{utm_source, utm_campaign, utm_medium, utm_content, landing_page}."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    referrer: Mapped[User] = relationship(
        "User",
        foreign_keys=[referrer_id],
        lazy="noload",
    )

    referred_user: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[referred_user_id],
        lazy="noload",
    )

    first_booking: Mapped[Booking | None] = relationship(
        "Booking",
        lazy="noload",
    )

    fraud_reviewer: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[fraud_reviewed_by_id],
        lazy="noload",
    )

    rewards: Mapped[list[ReferralReward]] = relationship(
        "ReferralReward",
        back_populates="referral",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    @property
    def is_converted(self) -> bool:
        return self.referral_status == ReferralStatus.CONVERTED

    @property
    def is_valid(self) -> bool:
        return self.referral_status != ReferralStatus.INVALID and not self.is_fraud_flagged

    def __repr__(self) -> str:
        return (
            f"<Referral id={self.id} referrer_id={self.referrer_id} "
            f"code={self.referral_code!r} status={self.referral_status}>"
        )
