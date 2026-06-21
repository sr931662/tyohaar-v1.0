"""
ReferralReward — a reward issued to a participant in a referral event.

Both the referrer and the referred user may receive rewards at different
conversion milestones. This model tracks each individual reward grant,
its payout status, and linkage to the wallet system.
"""

from __future__ import annotations

import enum
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
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import Currency, RewardType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.referrals.referral import Referral
    from app.models.users.user import User
    from app.models.wallets.wallet import Wallet
    from app.models.wallets.transaction import WalletTransaction


class ReferralRewardTrigger(str, enum.Enum):
    """
    The milestone event that caused this reward to be issued.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    SIGNUP = "signup"               # Reward issued when referred user completes registration
    FIRST_BOOKING = "first_booking" # Reward issued when referred user completes first booking
    MILESTONE = "milestone"         # Future: custom milestone (e.g., 5th booking, 1 year)


class ReferralRewardStatus(str, enum.Enum):
    """
    Lifecycle state of a single referral reward grant.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"         # Created; eligibility not yet confirmed
    APPROVED = "approved"       # Eligibility confirmed; ready for payout
    PROCESSING = "processing"   # Wallet credit or bank transfer in progress
    PAID = "paid"               # Funds credited to recipient wallet or bank account
    FAILED = "failed"           # Payout attempt failed; will retry
    EXPIRED = "expired"         # Reward was not claimed/activated before expiry
    CANCELLED = "cancelled"     # Revoked by admin due to fraud, policy, or error


class ReferralReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single reward grant tied to a referral conversion event.

    One Referral can generate multiple ReferralReward rows:
    - One for the referrer (REFERRAL_BONUS reward on FIRST_BOOKING conversion).
    - One for the referred user (WELCOME_BONUS on SIGNUP or FIRST_BOOKING).
    - Future milestone rewards.

    Reward types used here:
    - `RewardType.REFERRAL_BONUS`: for the referrer.
    - `RewardType.WELCOME_BONUS`: for the referred user on their first activity.

    Reward value can be:
    - Monetary (`monetary_value` > 0): credited to `wallet_id` as
      available_balance via a WalletTransaction.
    - Points-only (`points` > 0): credited to wallet.reward_points.
    - Combined: both monetary and points in one reward grant.

    Payout flow:
    1. Created with status=PENDING when conversion milestone is detected.
    2. Fraud checks run → status=APPROVED (or CANCELLED if fraud found).
    3. Wallet credit initiated → status=PROCESSING.
    4. WalletTransaction confirmed → status=PAID, wallet_transaction_id set.
    5. If payout fails → status=FAILED; retry logic applies.
    6. If expires_at passes without claiming → status=EXPIRED.

    `calculation_rule_version` records which reward policy was active at
    the time of calculation (important when policies change over time, e.g.
    changing the referral bonus amount mid-campaign).
    """

    __tablename__ = "referral_rewards"

    __table_args__ = (
        Index("ix_referral_rewards_referral_id", "referral_id"),
        Index("ix_referral_rewards_recipient_id", "recipient_id"),
        Index("ix_referral_rewards_status", "reward_status"),
        Index("ix_referral_rewards_trigger", "referral_id", "reward_trigger"),
        Index("ix_referral_rewards_expires_at", "expires_at"),
        CheckConstraint(
            "monetary_value >= 0",
            name="ck_referral_rewards_monetary_non_negative",
        ),
        CheckConstraint(
            "points >= 0",
            name="ck_referral_rewards_points_non_negative",
        ),
        CheckConstraint(
            "monetary_value > 0 OR points > 0",
            name="ck_referral_rewards_has_value",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    referral_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("referrals.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The referral event that triggered this reward.",
    )

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The user receiving this reward (referrer or referred user).",
    )

    # ── Reward Classification ─────────────────────────────────────────────────

    reward_type: Mapped[RewardType] = mapped_column(
        SAEnum(RewardType, name="reward_type", native_enum=False),
        nullable=False,
        comment="REFERRAL_BONUS for the referrer; WELCOME_BONUS for the referred user.",
    )

    reward_trigger: Mapped[ReferralRewardTrigger] = mapped_column(
        SAEnum(ReferralRewardTrigger, name="referral_reward_trigger", native_enum=False),
        nullable=False,
        comment="Conversion milestone that triggered this reward.",
    )

    # ── Reward Value ──────────────────────────────────────────────────────────

    monetary_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Monetary amount to credit to the recipient's wallet in `currency`.",
    )

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    points: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Loyalty points to add to wallet.reward_points. "
            "Zero for purely monetary rewards."
        ),
    )

    # ── Status ────────────────────────────────────────────────────────────────

    reward_status: Mapped[ReferralRewardStatus] = mapped_column(
        SAEnum(ReferralRewardStatus, name="referral_reward_status", native_enum=False),
        nullable=False,
        default=ReferralRewardStatus.PENDING,
    )

    # ── Wallet Linkage ────────────────────────────────────────────────────────

    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=True,
        comment="The recipient's wallet. Set when status transitions to PROCESSING.",
    )

    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
        comment="The WalletTransaction that credited this reward. Set when status=PAID.",
    )

    # ── Approval ─────────────────────────────────────────────────────────────

    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When fraud checks passed and the reward was approved for payout.",
    )

    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Admin who manually approved the reward. "
            "NULL for automatically approved rewards."
        ),
    )

    # ── Payout Timestamps ─────────────────────────────────────────────────────

    calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the reward amount was computed by the rewards calculation service.",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the wallet credit was confirmed (status→PAID).",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Reward expires if not paid out by this timestamp. "
            "NULL means no expiry (most common for direct wallet credits)."
        ),
    )

    # ── Cancellation ──────────────────────────────────────────────────────────

    is_cancelled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True when the reward was revoked by an admin.",
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Admin-provided reason for cancellation (fraud, policy exception, error).",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Policy ────────────────────────────────────────────────────────────────

    calculation_rule_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment=(
            "The referral reward policy version used at calculation time "
            "(e.g., 'v2024-01'). Important when policies change mid-campaign."
        ),
    )

    failure_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Error detail if reward_status=FAILED.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    referral: Mapped[Referral] = relationship(
        "Referral",
        back_populates="rewards",
        lazy="noload",
    )

    recipient: Mapped[User] = relationship(
        "User",
        foreign_keys=[recipient_id],
        lazy="noload",
    )

    wallet: Mapped[Wallet | None] = relationship(
        "Wallet",
        lazy="noload",
    )

    wallet_transaction: Mapped[WalletTransaction | None] = relationship(
        "WalletTransaction",
        lazy="noload",
    )

    approved_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[approved_by_id],
        lazy="noload",
    )

    cancelled_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[cancelled_by_id],
        lazy="noload",
    )

    @property
    def is_paid(self) -> bool:
        return self.reward_status == ReferralRewardStatus.PAID

    def __repr__(self) -> str:
        return (
            f"<ReferralReward id={self.id} referral_id={self.referral_id} "
            f"type={self.reward_type} value={self.monetary_value} status={self.reward_status}>"
        )
