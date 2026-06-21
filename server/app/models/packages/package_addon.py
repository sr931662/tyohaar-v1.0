"""
PackageAddon — optional upgrades purchasable alongside a package.

Examples: Drone Photography (+₹3,000), Extra Cake Tier (+₹800),
          LED Backdrop (+₹2,500), Fireworks Display (+₹5,000).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageAddon(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An optional upgrade purchasable on top of a base package during booking.

    Addon prices are always additive — they add to the package base price.
    `max_quantity` limits how many units a customer can add per booking
    (e.g., max 1 drone, but up to 3 extra cake tiers).
    """

    __tablename__ = "package_addons"

    __table_args__ = (
        Index("ix_package_addons_package_id", "package_id"),
        Index("ix_package_addons_active", "package_id", "is_active", "display_order"),
        CheckConstraint("price >= 0", name="ck_package_addon_price_non_negative"),
        CheckConstraint("max_quantity >= 1", name="ck_package_addon_max_qty_positive"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Details ───────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        comment="Additional price (INR) per unit of this addon",
    )

    max_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Maximum units a customer can add in a single booking",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="addons",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageAddon id={self.id} name={self.name!r} price={self.price}>"
        )
