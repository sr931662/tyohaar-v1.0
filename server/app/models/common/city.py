"""
City — master data for cities and towns where Tyohaar operates.

Every vendor service area, customer address, and celebration venue is
associated with a City record.  Cities are the primary geographic entity
for operational decisions: which vendors are available, what platform fees
apply, and whether delivery is supported.

`is_serviceable` is the critical flag: only cities where Tyohaar has onboarded
vendors and operations teams are set to True.  The mobile app shows a
"Coming soon" screen for non-serviceable cities.

`slug` is the canonical URL identifier for SEO-friendly city pages
(e.g. /cities/mumbai, /cities/bengaluru).

Tier classification:
- Tier 1 (Metros): Mumbai, Delhi, Bengaluru, Chennai, Hyderabad, Kolkata.
  Full feature set, lowest platform fees.
- Tier 2: Pune, Ahmedabad, Jaipur, Surat, etc.
  Full feature set, standard fees.
- Other (Tier 3+): Smaller cities with limited vendor pool.
  May have restricted feature set and higher coordination fees.
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
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.common.state import State


class City(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A city or town in the Tyohaar geographic master data.

    Key platform usages:
    - Address forms: city dropdown filtered by selected state.
    - Vendor availability: vendors specify operating_cities by City slug.
    - Pricing engine: tier classification affects platform fee percentages.
    - Home screen: serviceable cities shown in location picker.
    - Analytics: bookings and revenue segmented by city.

    `display_name` may differ from `name` for common aliases:
        name = "Bengaluru", display_name = "Bangalore"
    Both are stored so search handles either spelling.

    `alternate_names` is a PostgreSQL ARRAY of string aliases used for
    fuzzy search and autocomplete (e.g. ["Bombay", "मुंबई"]).
    """

    __tablename__ = "cities"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_cities_slug"),
        UniqueConstraint("state_id", "name", name="uq_cities_state_name"),
        Index("ix_cities_state_id", "state_id"),
        Index("ix_cities_is_active", "is_active"),
        Index("ix_cities_is_serviceable", "is_serviceable"),
        Index("ix_cities_is_metro", "is_metro"),
        Index("ix_cities_display_order", "display_order"),
        Index("ix_cities_active_serviceable", "is_active", "is_serviceable"),
        CheckConstraint("display_order >= 0", name="ck_cities_display_order_non_negative"),
    )

    # ── Parent State ──────────────────────────────────────────────────────────

    state_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("states.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The state or union territory this city belongs to",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Official city name (e.g. 'Bengaluru', 'Mumbai')",
    )

    display_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment=(
            "Preferred display name shown in UIs; may differ from official name "
            "(e.g. 'Bangalore' instead of 'Bengaluru' for recognition)."
        ),
    )

    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        comment="URL-safe unique identifier for SEO pages (e.g. 'mumbai', 'new-delhi')",
    )

    alternate_names: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(150)),
        nullable=True,
        comment="Other spellings/languages (e.g. ['Bombay', 'मुंबई']) used for search",
    )

    # ── Geographic ────────────────────────────────────────────────────────────

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="City centre latitude (WGS-84)",
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="City centre longitude (WGS-84)",
    )

    # ── Tier Classification ───────────────────────────────────────────────────

    is_metro: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for the six major Indian metros: Mumbai, Delhi, Bengaluru, "
            "Chennai, Hyderabad, Kolkata."
        ),
    )

    is_tier_1: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for Tier 1 cities (metros + large regional capitals)",
    )

    is_tier_2: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for Tier 2 cities (mid-size cities with active vendor pools)",
    )

    # ── Operational ───────────────────────────────────────────────────────────

    is_serviceable: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True when Tyohaar actively operates in this city: "
            "vendors are onboarded and bookings can be placed."
        ),
    )

    launch_planned_at: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment=(
            "Expected launch quarter shown in 'Coming soon' city pages "
            "(e.g. 'Q3 2025'). Free-form string, not a typed date."
        ),
    )

    # ── Display & Ordering ────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Sort rank within state in city picker UIs (lower = displayed first)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False hides the city from all UIs without removing its data",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    state: Mapped[State] = relationship(
        "State",
        back_populates="cities",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<City id={self.id} slug={self.slug!r} "
            f"state_id={self.state_id} serviceable={self.is_serviceable}>"
        )
