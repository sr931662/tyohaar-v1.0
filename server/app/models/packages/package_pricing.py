"""
PackagePricing — pricing configurations for a package.

Supports base price, weekend premium, festival season pricing,
and dynamic demand-based pricing.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackagePriceType(str, enum.Enum):
    """
    Scenario for which a pricing record applies.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    BASE = "base"                        # Standard year-round pricing
    WEEKEND = "weekend"                  # Friday–Sunday premium
    FESTIVAL_SEASON = "festival_season"  # Diwali, Holi, Christmas window
    PEAK_SEASON = "peak_season"          # High-demand months (e.g. Oct–Dec)
    OFF_SEASON = "off_season"            # Low-demand months with discount
    LAST_MINUTE = "last_minute"          # Within 24–48 hrs of event date


class PackagePricing(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A pricing tier for a package under specific conditions.

    Each package has one BASE pricing record. Additional records define
    overrides for weekends, festivals, and seasonal demand.

    The active pricing record for a booking is resolved at booking-time
    by the service layer based on the celebration date and city.

    Financial semantics:
    - `base_price`:      Package cost (what Tyohaar pays the vendor network)
    - `selling_price`:   Price charged to the customer
    - `commission_pct`:  Percentage of selling_price that Tyohaar retains
    - `platform_fee`:    Flat per-booking processing fee
    - `tax_pct`:         GST rate applied to selling_price (standard 18%)
    """

    __tablename__ = "package_pricings"

    __table_args__ = (
        Index("ix_package_pricings_package_id", "package_id"),
        Index("ix_package_pricings_active", "package_id", "price_type", "is_active"),
        CheckConstraint("base_price >= 0", name="ck_package_pricing_base_non_negative"),
        CheckConstraint("selling_price >= 0", name="ck_package_pricing_selling_non_negative"),
        CheckConstraint(
            "commission_pct BETWEEN 0 AND 100",
            name="ck_package_pricing_commission_pct",
        ),
        CheckConstraint(
            "tax_pct BETWEEN 0 AND 100",
            name="ck_package_pricing_tax_pct",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Pricing Type ──────────────────────────────────────────────────────────

    price_type: Mapped[PackagePriceType] = mapped_column(
        SAEnum(PackagePriceType, name="package_price_type", native_enum=False),
        nullable=False,
        default=PackagePriceType.BASE,
    )

    label: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Human-readable label e.g. 'Diwali Special Price', 'Weekend Rate'",
    )

    # ── Amounts ───────────────────────────────────────────────────────────────

    base_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Package cost (what Tyohaar pays the vendor network)",
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Price charged to the customer",
    )

    platform_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Flat per-booking platform processing fee",
    )

    commission_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Tyohaar commission as a percentage of selling_price",
    )

    tax_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("18.00"),
        comment="GST rate percentage applied to selling_price (standard 18%)",
    )

    # ── Dynamic Pricing ───────────────────────────────────────────────────────

    is_dynamic: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="When True, selling_price can be overridden by the dynamic pricing engine",
    )

    min_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Dynamic pricing floor (selling_price will not go below this)",
    )

    max_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Dynamic pricing ceiling (selling_price will not exceed this)",
    )

    # ── Validity ──────────────────────────────────────────────────────────────

    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)

    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Capacity Override ─────────────────────────────────────────────────────

    min_guest_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="This tier applies only if guest_count >= min_guest_count",
    )

    max_guest_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="This tier applies only if guest_count <= max_guest_count",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="pricing",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackagePricing id={self.id} package_id={self.package_id} "
            f"type={self.price_type} selling={self.selling_price}>"
        )
