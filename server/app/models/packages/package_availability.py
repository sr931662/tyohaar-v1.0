"""
PackageAvailability — city and date-based availability rules for packages.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageAvailability(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A rule defining when and where a package is available or blocked.

    A package can have multiple availability records for different
    city/date combinations:

    - city='Mumbai', is_blackout=False → explicitly available in Mumbai
    - city=NULL, start_date='2024-12-20', end_date='2024-12-26', is_blackout=True
      → blocked during Christmas week in all cities
    - city='Delhi', start_date=NULL, end_date=NULL, is_blackout=True
      → permanently unavailable in Delhi

    The service layer evaluates all active records at booking-time to
    determine final availability for a given city/date combination.

    `min_capacity` and `max_capacity` can override the package-level defaults
    for specific windows (e.g., larger team capacity available in peak season).
    """

    __tablename__ = "package_availabilities"

    __table_args__ = (
        Index("ix_package_avail_package_id", "package_id"),
        Index("ix_package_avail_city", "package_id", "city", "is_active"),
        Index("ix_package_avail_dates", "package_id", "start_date", "end_date"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_package_avail_date_order",
        ),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── City ──────────────────────────────────────────────────────────────────

    city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="City this rule applies to. NULL = applies to all cities.",
    )

    # ── Date Range ────────────────────────────────────────────────────────────

    start_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="First date this rule is effective. NULL = no start boundary.",
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Last date this rule is effective (inclusive). NULL = no end boundary.",
    )

    # ── Capacity Override ─────────────────────────────────────────────────────

    min_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Minimum guest count override for this city/window",
    )

    max_capacity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum guest count override for this city/window",
    )

    # ── Rule Type ─────────────────────────────────────────────────────────────

    is_blackout: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True = this window is blocked (package unavailable). "
            "False = this window is explicitly open (useful for city-by-city activation)."
        ),
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal reason for this availability rule (e.g. 'No vendors in city')",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="availability",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageAvailability id={self.id} package_id={self.package_id} "
            f"city={self.city!r} blackout={self.is_blackout}>"
        )
