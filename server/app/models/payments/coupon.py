"""
Coupon — a discount code redeemable by customers at booking checkout.

Supports percentage discounts, fixed-amount deductions, cashback grants,
and free-service awards. Configurable eligibility rules control who can use
a coupon, how many times, and on which products.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    CouponAdminStatus,
    CouponApplicability,
    CouponEffectiveStatus,
    CouponType,
    Currency,
)
from app.models.mixins import NotesMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class Coupon(UUIDPrimaryKeyMixin, TimestampMixin, NotesMixin, Base):
    """
    A redeemable discount coupon code for checkout.

    Coupons are created by Tyohaar admins or generated programmatically
    (e.g., referral bonuses, promotional campaigns). Customers enter the
    coupon `code` at checkout; the service layer validates eligibility and
    applies the discount.

    Discount types:
    - PERCENTAGE: `discount_value` % off the order subtotal, capped at
      `max_discount_amount` (NULL means no cap).
    - FIXED_AMOUNT: flat `discount_value` INR deducted from the subtotal.
    - FREE_SERVICE: waives the entire service fee (discount_value ignored).
    - CASHBACK: `discount_value` % or amount credited to wallet after booking
      completion (not at checkout — delay tracked by the service layer).

    Eligibility rules (all conditions must be met simultaneously):
    - `min_order_value`: order subtotal must be ≥ this amount.
    - `first_booking_only`: customer must have zero prior completed bookings.
    - `eligible_membership_tiers`: only customers on listed membership tiers.
    - `applicable_vendor_ids`: only for bookings with these specific vendors.
    - `applicable_package_ids`: only for these specific packages.
    - `applicable_occasion_categories`: only for these occasion types.
    - `total_usage_limit`: global cap across all customers (NULL = unlimited).
    - `per_user_limit`: how many times a single customer can use it (NULL = once by default).
    - `valid_from` / `valid_until`: time window; valid_until NULL means never expires.

    `times_used` is a denormalized counter incremented by the service layer
    on every successful coupon application. It is the source of truth for
    checking against `total_usage_limit` and must be checked under a SELECT
    FOR UPDATE lock to prevent over-redemption under concurrent load.

    `code` is stored in uppercase and must be unique across the platform.
    The service layer normalizes to uppercase before lookup.
    """

    __tablename__ = "coupons"

    __table_args__ = (
        UniqueConstraint("code", name="uq_coupons_code"),
        Index("ix_coupons_is_active", "is_active"),
        Index("ix_coupons_valid_window", "valid_from", "valid_until"),
        Index("ix_coupons_coupon_type", "coupon_type"),
        Index("ix_coupons_applicability", "applicability"),
        CheckConstraint("discount_value > 0", name="ck_coupons_discount_value_positive"),
        CheckConstraint(
            "max_discount_amount IS NULL OR max_discount_amount > 0",
            name="ck_coupons_max_discount_positive",
        ),
        CheckConstraint(
            "min_order_value IS NULL OR min_order_value >= 0",
            name="ck_coupons_min_order_non_negative",
        ),
        CheckConstraint(
            "total_usage_limit IS NULL OR total_usage_limit > 0",
            name="ck_coupons_usage_limit_positive",
        ),
        CheckConstraint(
            "per_user_limit IS NULL OR per_user_limit > 0",
            name="ck_coupons_per_user_limit_positive",
        ),
        CheckConstraint("times_used >= 0", name="ck_coupons_times_used_non_negative"),
    )

    # ── Code & Description ────────────────────────────────────────────────────

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        comment=(
            "Uppercase alphanumeric code entered by customers at checkout. "
            "NULL for automatic (no-code) discounts — see is_automatic. "
            "Service layer normalizes input to uppercase before lookup."
        ),
    )

    is_automatic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment=(
            "True = the engine evaluates and applies this discount without a "
            "code (first booking, weekend offer, festival offer, etc). "
            "Must be the inverse of `code IS NOT NULL` — enforced by the "
            "service layer, not a DB constraint (SQLite/JSONB portability)."
        ),
    )

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Internal/admin display name, e.g. 'Diwali 2026 15% Off'.",
    )

    public_offer_title: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Customer-facing marketing title, e.g. 'Diwali Dhamaka — 15% OFF!'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal description — eligibility summary and admin notes on intent.",
    )

    terms_and_conditions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Customer-facing terms & conditions shown alongside the offer.",
    )

    # ── Discount Configuration ────────────────────────────────────────────────

    coupon_type: Mapped[CouponType] = mapped_column(
        SAEnum(CouponType, name="coupon_type", native_enum=False),
        nullable=False,
    )

    applicability: Mapped[CouponApplicability] = mapped_column(
        SAEnum(CouponApplicability, name="coupon_applicability", native_enum=False),
        nullable=False,
        default=CouponApplicability.ALL,
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment=(
            "For PERCENTAGE: percentage to deduct (e.g., 15.00 = 15%). "
            "For FIXED_AMOUNT / CASHBACK: monetary amount in `currency`. "
            "For FIXED_PRICE: the target final price the package becomes."
        ),
    )

    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment=(
            "Maximum monetary discount allowed for PERCENTAGE coupons. "
            "NULL means uncapped. Irrelevant for FIXED_AMOUNT coupons."
        ),
    )

    currency: Mapped[Currency] = mapped_column(
        SAEnum(Currency, name="currency", native_enum=False),
        nullable=False,
        default=Currency.INR,
    )

    # ── Priority & Stacking ───────────────────────────────────────────────────
    # priority mirrors AutomationRule.priority's exact convention (lower number
    # = evaluated/preferred first) for consistency across the codebase.

    priority: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=100,
        server_default="100",
        comment="Lower number = preferred first when multiple non-stackable discounts are eligible",
    )

    is_stackable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment=(
            "True = this discount can combine with other eligible discounts. "
            "False = mutually exclusive; the engine picks one exclusive "
            "discount by priority (tie-broken by highest amount) and layers "
            "all eligible stackable discounts on top of it."
        ),
    )

    condition_rules: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Condition tree for automatic discounts needing more than a flat "
            "date range (Weekend Offer, Happy Hours, Birthday Month). Same "
            "shape as AutomationRule.conditions: "
            "{'op': 'AND'|'OR', 'clauses': [{'field','operator','value'}]}, "
            "evaluated by the shared app.services.common.rule_conditions."
            "evaluate_conditions() against a per-booking payload dict."
        ),
    )

    # ── Status (admin-controlled subset — see effective_status property) ─────

    admin_status: Mapped[CouponAdminStatus] = mapped_column(
        SAEnum(CouponAdminStatus, name="coupon_admin_status", native_enum=False),
        nullable=False,
        default=CouponAdminStatus.DRAFT,
        server_default=CouponAdminStatus.DRAFT.value,
        comment="Admin-set state. scheduled/active/expired are derived — see effective_status.",
    )

    # ── Presentation ──────────────────────────────────────────────────────────

    banner_image_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="Promotional banner image shown on the offer's customer-facing card.",
    )

    theme_color_hex: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        comment="Brand/accent color for this offer's card, e.g. '#C8A96E'.",
    )

    # ── Eligibility ───────────────────────────────────────────────────────────

    min_order_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Minimum order subtotal required to use this coupon.",
    )

    first_booking_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="If True, only customers with zero prior completed bookings can redeem.",
    )

    eligible_membership_tiers: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "MembershipTier values allowed to use this coupon. "
            "NULL means all tiers. Example: ['gold', 'platinum']."
        ),
    )

    applicable_vendor_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="UUID strings of vendors this coupon applies to. NULL means all vendors.",
    )

    applicable_package_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="UUID strings of packages this coupon applies to. NULL means all packages.",
    )

    applicable_occasion_categories: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "OccasionCategory values this coupon applies to. "
            "NULL means all categories. Example: ['life_event', 'major_festival']."
        ),
    )

    applicable_occasion_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "UUID strings of specific Occasions this coupon applies to — distinct "
            "from applicable_occasion_categories (category-level). NULL means no "
            "specific-occasion restriction."
        ),
    )

    repeat_customers_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="If True, only customers with at least one prior completed booking can redeem.",
    )

    referral_users_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="If True, only customers who signed up via a referral can redeem.",
    )

    eligible_customer_group_ids: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Reserved for future use — no customer-group entity exists yet in "
            "this codebase, so this field is stored but unenforced."
        ),
    )

    min_package_value: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment=(
            "Minimum price of the specific package being booked (Package.base_price), "
            "distinct from min_order_value which is the whole booking subtotal."
        ),
    )

    # ── Usage Limits ──────────────────────────────────────────────────────────

    total_usage_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum total redemptions across all customers. NULL means unlimited.",
    )

    per_user_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment=(
            "Maximum times a single customer can use this coupon. "
            "NULL means once (most common); set to higher for multi-use coupons."
        ),
    )

    max_uses_per_day: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum redemptions allowed platform-wide per calendar day (UTC). NULL means unlimited.",
    )

    max_uses_per_vendor: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Reserved for future use — not yet enforced by the discount engine.",
    )

    max_uses_per_package: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Reserved for future use — not yet enforced by the discount engine.",
    )

    times_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Denormalized total redemption count. Incremented under FOR UPDATE lock. "
            "Must not exceed total_usage_limit when total_usage_limit IS NOT NULL."
        ),
    )

    # ── Validity Window ───────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="False immediately disables the coupon without waiting for valid_until.",
    )

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Coupon is not redeemable before this timestamp.",
    )

    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Coupon expires after this timestamp. NULL means it never expires.",
    )

    deactivated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When is_active was last set to False.",
    )

    # ── Origin ────────────────────────────────────────────────────────────────

    is_system_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for coupons auto-generated by the platform "
            "(e.g., referral codes, birthday coupons, loyalty rewards)."
        ),
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who created this coupon. NULL for system-generated coupons.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    created_by: Mapped[User | None] = relationship(
        "User",
        lazy="noload",
    )

    @property
    def is_exhausted(self) -> bool:
        return (
            self.total_usage_limit is not None
            and self.times_used >= self.total_usage_limit
        )

    @property
    def remaining_uses(self) -> int | None:
        if self.total_usage_limit is None:
            return None
        return max(0, self.total_usage_limit - self.times_used)

    @property
    def effective_status(self) -> CouponEffectiveStatus:
        """
        Fully-derived status combining admin_status with the validity window,
        computed live so expired/scheduled/active transitions need no cron job.
        """
        if self.admin_status == CouponAdminStatus.ARCHIVED:
            return CouponEffectiveStatus.ARCHIVED
        if self.admin_status == CouponAdminStatus.DRAFT:
            return CouponEffectiveStatus.DRAFT
        if self.admin_status == CouponAdminStatus.PAUSED:
            return CouponEffectiveStatus.PAUSED
        # admin_status == PUBLISHED — derive from the validity window
        now = datetime.now(tz=timezone.utc)
        if self.valid_from > now:
            return CouponEffectiveStatus.SCHEDULED
        if self.valid_until is not None and self.valid_until < now:
            return CouponEffectiveStatus.EXPIRED
        return CouponEffectiveStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<Coupon id={self.id} code={self.code!r} "
            f"type={self.coupon_type} value={self.discount_value} used={self.times_used}>"
        )
