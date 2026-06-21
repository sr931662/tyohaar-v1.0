"""
MembershipPlan — the platform's membership tier definitions.

Defines pricing, benefits, and eligibility rules for each tier.
Instances are managed by Tyohaar admin; customers subscribe via UserMembership.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, List

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import MembershipTier
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.memberships.user_membership import UserMembership


class MembershipPlan(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Definition of a Tyohaar membership tier.

    Each tier is identified by its `tier` (MembershipTier enum) and `slug`.
    UNIQUE constraints on both ensure no duplicate tiers or slugs.

    Pricing:
    - `monthly_price` / `yearly_price`: subscription cost per billing cycle.
    - `yearly_price` should be ≤ 12 × monthly_price to reflect the annual discount.
    - FREE tier has both prices = 0.00.

    Benefits:
    - `cashback_percentage`: applied to booking totals (e.g. 5% for Gold).
    - `discount_percentage`: discount on package base price at checkout.
    - `reward_multiplier`: 1.0 = standard points; 2.0 = double points per booking.
    - `wallet_bonus`: one-time INR credit added to wallet on plan activation/renewal.
    - `free_invitations_count`: digital invitation credits per renewal period.
    - `customer_support_priority`: 1=standard queue, 2=priority channel, 3=dedicated CSR.
    - `priority_booking`: whether the customer gets early access to new packages.
    - `has_exclusive_packages`: access to Gold/Platinum-only packages.
    - `cancellation_protection`: reduced/waived cancellation fees.

    Upgrade paths:
    - `can_upgrade_to_tier` / `can_downgrade_to_tier`: nullable MembershipTier values
      indicating the tier this plan can transition to. Service layer validates these
      before creating a new UserMembership.

    `benefits` JSONB holds additional structured benefits that don't warrant
    dedicated columns (e.g., free cake add-on, dedicated venue coordinator, etc.).
    This lets new benefit types be shipped without migrations.
    """

    __tablename__ = "membership_plans"

    __table_args__ = (
        UniqueConstraint("tier", name="uq_membership_plans_tier"),
        UniqueConstraint("slug", name="uq_membership_plans_slug"),
        UniqueConstraint("name", name="uq_membership_plans_name"),
        CheckConstraint("monthly_price >= 0", name="ck_membership_plans_monthly_non_negative"),
        CheckConstraint("yearly_price >= 0", name="ck_membership_plans_yearly_non_negative"),
        CheckConstraint(
            "cashback_percentage >= 0 AND cashback_percentage <= 100",
            name="ck_membership_plans_cashback_pct_range",
        ),
        CheckConstraint(
            "discount_percentage >= 0 AND discount_percentage <= 100",
            name="ck_membership_plans_discount_pct_range",
        ),
        CheckConstraint(
            "reward_multiplier >= 1",
            name="ck_membership_plans_multiplier_min",
        ),
        CheckConstraint("wallet_bonus >= 0", name="ck_membership_plans_wallet_bonus_non_negative"),
        CheckConstraint("free_invitations_count >= 0", name="ck_membership_plans_invites_non_negative"),
        CheckConstraint(
            "customer_support_priority BETWEEN 1 AND 3",
            name="ck_membership_plans_support_priority_range",
        ),
        CheckConstraint("display_order >= 0", name="ck_membership_plans_display_order_non_negative"),
        Index("ix_membership_plans_is_active", "is_active"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    tier: Mapped[MembershipTier] = mapped_column(
        SAEnum(MembershipTier, name="membership_tier", native_enum=False),
        nullable=False,
        unique=True,
        comment="Platform tier this plan represents. One plan per tier.",
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name e.g. 'Gold', 'Platinum', 'Corporate'.",
    )

    slug: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="URL-safe identifier e.g. 'gold', 'platinum'. UNIQUE.",
    )

    tagline: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Short marketing headline e.g. 'Celebrate More, Spend Less'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Full description of the plan's benefits for the pricing page.",
    )

    # ── Pricing ───────────────────────────────────────────────────────────────

    monthly_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="INR subscription fee per month. 0 for the FREE tier.",
    )

    yearly_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="INR subscription fee per year (typically < 12 × monthly_price).",
    )

    validity_days: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Explicit validity duration in days for custom/lifetime plans. "
            "NULL = derive from billing cycle (30 days for monthly, 365 for annual)."
        ),
    )

    # ── Cashback & Discount Benefits ──────────────────────────────────────────

    cashback_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Percentage cashback on booking subtotal credited to wallet after completion.",
    )

    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Instant discount percentage applied to package price at checkout.",
    )

    reward_multiplier: Mapped[Decimal] = mapped_column(
        Numeric(4, 2),
        nullable=False,
        default=Decimal("1.00"),
        comment=(
            "Multiplier applied to standard loyalty points per booking. "
            "1.00 = normal; 2.00 = double points."
        ),
    )

    # ── Wallet & Credits ──────────────────────────────────────────────────────

    wallet_bonus: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="One-time INR wallet credit granted on plan activation or each renewal.",
    )

    # ── Access & Service Benefits ─────────────────────────────────────────────

    free_invitations_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of free digital invitation credits granted per renewal period.",
    )

    priority_booking: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Early access to new packages and limited-availability slots.",
    )

    has_exclusive_packages: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Access to packages restricted to this tier and above.",
    )

    customer_support_priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=1,
        comment="Support queue priority: 1=standard, 2=priority channel, 3=dedicated CSR.",
    )

    cancellation_protection: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Reduced or waived cancellation fees per platform policy.",
    )

    # ── Upgrade / Downgrade Paths ─────────────────────────────────────────────

    can_upgrade_to_tier: Mapped[MembershipTier | None] = mapped_column(
        SAEnum(MembershipTier, name="membership_tier", native_enum=False),
        nullable=True,
        comment="Which tier a subscriber on this plan can upgrade to. NULL = no upgrade path.",
    )

    can_downgrade_to_tier: Mapped[MembershipTier | None] = mapped_column(
        SAEnum(MembershipTier, name="membership_tier", native_enum=False),
        nullable=True,
        comment="Which tier a subscriber on this plan can downgrade to. NULL = no downgrade path.",
    )

    # ── Flexible Benefits ─────────────────────────────────────────────────────

    benefits: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Flexible bag for additional structured benefits not in dedicated columns. "
            "Example: {free_cake_addon: true, dedicated_coordinator: true, "
            "lounge_access: false, partner_discounts: [{brand: 'FabIndia', pct: 10}]}."
        ),
    )

    # ── Display ───────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inactive plans cannot be subscribed to but existing subscriptions remain valid.",
    )

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Sort order for the pricing page (ascending).",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    subscriptions: Mapped[List[UserMembership]] = relationship(
        "UserMembership",
        back_populates="plan",
        foreign_keys="UserMembership.plan_id",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<MembershipPlan id={self.id} tier={self.tier} "
            f"monthly={self.monthly_price} active={self.is_active}>"
        )
