"""
UserReward — a reward credit or loyalty point grant assigned to a customer.

Covers cashback campaigns, festival rewards, referral bonuses, membership
perks, welcome credits, and admin promotional grants.
"""

from __future__ import annotations

import enum
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
from app.models.enums import Currency, RewardType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.wallets.wallet import Wallet
    from app.models.wallets.transaction import WalletTransaction


class UserRewardStatus(str, enum.Enum):
    """
    Lifecycle state of a reward assigned to a user.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"        # Created but not yet confirmed (e.g. pending booking completion)
    ACTIVE = "active"          # Available to claim or has been credited to wallet
    USED = "used"              # Monetary value has been applied to a wallet or checkout
    EXPIRED = "expired"        # Past expires_at without being used
    CANCELLED = "cancelled"    # Revoked by admin (fraud, error, policy)


class UserReward(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single reward grant given to a customer.

    Rewards can be:
    - Monetary (`monetary_value` > 0): credited to the wallet as available_balance
      or promotional_balance when status transitions to ACTIVE.
    - Points-based (`points` > 0): added to wallet.reward_points.
    - Combined: both monetary and points in one grant.

    Reward lifecycle:
    1. Created with status=PENDING (e.g., booking cashback pending confirmation).
    2. Service layer validates eligibility and transitions to ACTIVE.
    3. When ACTIVE, the service credits the wallet (creating a WalletTransaction)
       and sets `wallet_transaction_id` to link them.
    4. When the customer spends the reward, status becomes USED.
    5. If expires_at passes without use, a background job sets EXPIRED.

    `source_type` + `source_id` form a polymorphic pointer to the entity that
    triggered this reward (similar to WalletTransaction.reference_type/id):
    - "booking"    → bookings.id (cashback on a completed booking)
    - "referral"   → users.id of the referred user (referral bonus)
    - "membership" → user_memberships.id (membership activation bonus)
    - "campaign"   → admin-defined campaign ID (promotional credit)
    - "admin"      → NULL (manual admin grant)
    - "review"     → package_reviews.id (review reward)

    `eligibility_rules` stores structured conditions checked before activation:
    {
      "min_booking_value": 5000,
      "valid_occasion_ids": ["uuid1", "uuid2"],
      "first_booking_only": true
    }
    """

    __tablename__ = "user_rewards"

    __table_args__ = (
        Index("ix_user_rewards_user_id", "user_id"),
        Index("ix_user_rewards_status", "user_id", "reward_status"),
        Index("ix_user_rewards_type", "reward_type"),
        Index("ix_user_rewards_expires_at", "expires_at"),
        Index("ix_user_rewards_source", "source_type", "source_id"),
        CheckConstraint("monetary_value >= 0", name="ck_user_rewards_monetary_non_negative"),
        CheckConstraint("points >= 0", name="ck_user_rewards_points_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Customer this reward belongs to.",
    )

    wallet_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wallets.id", ondelete="RESTRICT"),
        nullable=True,
        comment="Set when the reward is credited to the customer's wallet.",
    )

    wallet_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("wallet_transactions.id", ondelete="SET NULL"),
        nullable=True,
        comment="The WalletTransaction that credited this reward's value to the wallet.",
    )

    # ── Reward Identity ───────────────────────────────────────────────────────

    reward_type: Mapped[RewardType] = mapped_column(
        SAEnum(RewardType, name="reward_type", native_enum=False),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Customer-visible reward title e.g. 'Birthday Cashback ₹500'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Customer-visible reward description and terms.",
    )

    # ── Value ─────────────────────────────────────────────────────────────────

    monetary_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="INR value to be credited to the wallet. Zero for points-only rewards.",
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
        comment="Loyalty points to add to wallet.reward_points. Zero for monetary-only rewards.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    reward_status: Mapped[UserRewardStatus] = mapped_column(
        SAEnum(UserRewardStatus, name="user_reward_status", native_enum=False),
        nullable=False,
        default=UserRewardStatus.PENDING,
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Reward expires if not used by this timestamp. NULL = no expiry.",
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the reward was applied at checkout or redeemed.",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancellation_reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Admin reason for revoking this reward.",
    )

    # ── Source (polymorphic) ──────────────────────────────────────────────────

    source_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Entity type that triggered this reward: booking, referral, membership, campaign, review, admin.",
    )

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the source entity. Not a FK to allow cross-domain flexibility.",
    )

    # ── Eligibility & Rules ───────────────────────────────────────────────────

    eligibility_rules: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Conditions checked before the reward is activated. "
            "Example: {min_booking_value: 5000, first_booking_only: true}."
        ),
    )

    is_auto_credited: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True if the system automatically credits the wallet on activation. "
            "False if the customer must manually claim the reward."
        ),
    )

    extra_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Internal context: campaign ID, A/B test variant, admin notes, etc.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship("User", lazy="noload")

    wallet: Mapped[Wallet | None] = relationship(
        "Wallet",
        back_populates="rewards",
        lazy="noload",
    )

    wallet_transaction: Mapped[WalletTransaction | None] = relationship(
        "WalletTransaction",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<UserReward id={self.id} user_id={self.user_id} "
            f"type={self.reward_type} value={self.monetary_value} status={self.reward_status}>"
        )
