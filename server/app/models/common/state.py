"""
State — master data for Indian states and union territories.

This table is the geographic anchor for the platform.  Every City record
references a State, and vendor/customer location data throughout the system
uses state codes for fast filtering.

Seeded from the official list of 28 Indian states and 8 union territories.
The `code` field follows the ISO 3166-2:IN standard (two-letter codes,
e.g. MH for Maharashtra, DL for Delhi).

Design decisions:
- State records are never soft-deleted; `is_active = False` deactivates
  them from selection UIs without losing referential integrity.
- `country_code` defaults to "IN" but the schema allows future expansion
  to support international markets (e.g. NP for Nepal, BD for Bangladesh).
- `latitude` / `longitude` represent the geographic centre of the state,
  used for map views and proximity calculations.
- `timezone` is the dominant IANA timezone for the state.  Most Indian
  states share Asia/Kolkata; north-eastern states occasionally differ.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.common.city import City


class State(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A top-level administrative geographic division (state or union territory).

    Used for:
    - Restricting city lookups by state in address forms
    - Regional filtering of vendor searches
    - Service-area configuration for operations teams
    - Tax jurisdiction mapping (future GST state-code integration)

    `code` is the ISO 3166-2 subdivision code without the country prefix:
        India → "MH" (not "IN-MH").
    """

    __tablename__ = "states"

    __table_args__ = (
        UniqueConstraint("code", "country_code", name="uq_states_code_country"),
        UniqueConstraint("name", "country_code", name="uq_states_name_country"),
        Index("ix_states_country_code", "country_code"),
        Index("ix_states_is_active", "is_active"),
        Index("ix_states_display_order", "display_order"),
        CheckConstraint("display_order >= 0", name="ck_states_display_order_non_negative"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Official state / union territory name (e.g. 'Maharashtra', 'Delhi')",
    )

    code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="ISO 3166-2 subdivision code without country prefix (e.g. 'MH', 'DL')",
    )

    country_code: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="IN",
        comment="ISO 3166-1 alpha-2 country code (default 'IN' for India)",
    )

    # ── Geographic ────────────────────────────────────────────────────────────

    capital: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="State capital city name (e.g. 'Mumbai', 'Bengaluru')",
    )

    timezone: Mapped[str] = mapped_column(
        String(60),
        nullable=False,
        default="Asia/Kolkata",
        comment="IANA timezone identifier for the dominant timezone of this state",
    )

    latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Approximate geographic centre latitude (WGS-84, −90 to +90)",
    )

    longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="Approximate geographic centre longitude (WGS-84, −180 to +180)",
    )

    # ── Display & Ordering ────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Sort rank in state picker UIs (lower = displayed earlier)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "False hides this state from selection UIs. "
            "Does NOT cascade to cities — each city has its own is_active flag."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    cities: Mapped[list[City]] = relationship(
        "City",
        back_populates="state",
        lazy="noload",
        cascade="save-update, merge",
    )

    def __repr__(self) -> str:
        return f"<State id={self.id} code={self.code!r} name={self.name!r}>"
