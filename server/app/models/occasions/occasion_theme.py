"""
OccasionTheme — visual theme templates available for celebrations.

Themes define the aesthetic: color palette, cover image, name.
A theme can apply to multiple occasions (Royal theme for Birthday and Anniversary).
Customers select a theme when planning their celebration.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion import Occasion
    from app.models.packages.package import Package


class OccasionTheme(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A reusable visual theme with a color palette and cover imagery.

    `colors` JSONB structure:
        {
          "primary":    "#C8A96E",
          "secondary":  "#F5F0E8",
          "accent":     "#8B1A1A",
          "background": "#FFF8F0"
        }

    Linked to occasions via the `occasion_theme_links` association table.
    Celebrations reference this to store the customer's selected theme.
    """

    __tablename__ = "occasion_themes"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_occasion_themes_slug"),
        Index("ix_occasion_themes_sort", "is_active", "sort_order"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment="URL-safe identifier e.g. 'royal-gold', 'minimal-white'",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Visual Design ─────────────────────────────────────────────────────────

    cover_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Hero/preview image showing the theme aesthetic",
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Smaller preview for grid views",
    )

    colors: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Color palette: {primary, secondary, accent, background}",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Featured themes are promoted in the theme picker UI",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    occasions: Mapped[list[Occasion]] = relationship(
        "Occasion",
        secondary="occasion_theme_links",
        back_populates="themes",
        lazy="noload",
    )

    packages: Mapped[list[Package]] = relationship(
        "Package",
        secondary="package_themes",
        back_populates="themes",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<OccasionTheme id={self.id} name={self.name!r} slug={self.slug!r}>"
