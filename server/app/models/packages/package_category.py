"""
PackageCategory — grouping taxonomy for packages.

Examples: Budget, Premium, Luxury, Kids Special, Corporate, Pre-Wedding.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A grouping label for packages visible to customers in browse views.

    Flat list (no parent/child hierarchy). Admin-managed.
    Customers filter packages by category on the browse screen.
    """

    __tablename__ = "package_categories"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_package_categories_slug"),
        Index("ix_package_categories_sort", "is_active", "sort_order"),
    )

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment="URL-safe identifier e.g. 'budget', 'premium', 'luxury', 'kids-special'",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    packages: Mapped[list[Package]] = relationship(
        "Package",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PackageCategory id={self.id} name={self.name!r} slug={self.slug!r}>"
