"""
PackageDiscount — promotional discounts and coupon codes for packages.
"""

from __future__ import annotations

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import CouponApplicability, CouponType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageDiscount(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A discount or promotional offer attached to a package.

    `code` is optional — discounts without a code are applied automatically.
    `usage_limit` caps total redemptions across all users (NULL = unlimited).
    `usage_limit_per_user` caps per-user redemptions (NULL = unlimited per user).
    `max_discount_amount` caps the INR discount for PERCENTAGE type coupons.
    `package_id` is nullable for platform-wide global discounts.
    """

    __tablename__ = "package_discounts"

    __table_args__ = (
        UniqueConstraint("code", name="uq_package_discounts_code"),
        Index("ix_package_discounts_package_id", "package_id"),
        Index("ix_package_discounts_active", "is_active", "valid_from", "valid_until"),
        CheckConstraint("discount_value > 0", name="ck_package_discount_value_positive"),
        CheckConstraint("usage_count >= 0", name="ck_package_discount_usage_non_negative"),
    )

    # ── Scope ─────────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=True,
        comment="NULL = platform-wide discount applicable to all eligible packages",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        unique=True,
        comment="Coupon code entered by the customer. NULL = auto-applied.",
    )

    # ── Discount Configuration ────────────────────────────────────────────────

    discount_type: Mapped[CouponType] = mapped_column(
        SAEnum(CouponType, name="coupon_type", native_enum=False),
        nullable=False,
    )

    discount_value: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Rupee amount for FIXED_AMOUNT type; percentage for PERCENTAGE type",
    )

    max_discount_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Maximum INR discount for PERCENTAGE type (e.g. max ₹500 off on 20% coupon)",
    )

    min_booking_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Minimum booking value required to apply this discount",
    )

    # ── Applicability ─────────────────────────────────────────────────────────

    applicability: Mapped[CouponApplicability] = mapped_column(
        SAEnum(CouponApplicability, name="coupon_applicability", native_enum=False),
        nullable=False,
    )

    # ── Usage Limits ──────────────────────────────────────────────────────────

    usage_limit: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum total redemptions across all users. NULL = unlimited.",
    )

    usage_limit_per_user: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum redemptions per individual user. NULL = unlimited per user.",
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Current total redemption count. Updated atomically on each use.",
    )

    # ── Validity ──────────────────────────────────────────────────────────────

    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    valid_until: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package | None] = relationship(
        "Package",
        back_populates="discounts",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageDiscount id={self.id} code={self.code!r} "
            f"type={self.discount_type} value={self.discount_value}>"
        )
