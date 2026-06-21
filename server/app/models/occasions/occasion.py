"""
Occasion — master occasion definition (Birthday, Anniversary, Diwali, etc.).

All occasions are database-driven. Never hardcode occasion types in code.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion_category import OccasionCategory
    from app.models.occasions.occasion_theme import OccasionTheme
    from app.models.occasions.occasion_mood import OccasionMood
    from app.models.occasions.occasion_tag import OccasionTag
    from app.models.occasions.celebration import Celebration
    from app.models.packages.package import Package


# ── M:N Association Tables ────────────────────────────────────────────────────
# Defined here (on the Occasion side) since Occasion is the primary entity.

occasion_theme_links = Table(
    "occasion_theme_links",
    Base.metadata,
    Column(
        "occasion_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "theme_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasion_themes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

occasion_mood_links = Table(
    "occasion_mood_links",
    Base.metadata,
    Column(
        "occasion_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "mood_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasion_moods.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

occasion_tag_links = Table(
    "occasion_tag_links",
    Base.metadata,
    Column(
        "occasion_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        PGUUID(as_uuid=True),
        ForeignKey("occasion_tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ── Model ─────────────────────────────────────────────────────────────────────

class Occasion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A specific occasion type that Tyohaar supports.

    Examples: Birthday, 1st Birthday, Anniversary, Baby Shower,
              Diwali Puja, Navratri, Housewarming, Retirement Party.

    Occasions are fully database-driven — never hardcode them in application
    logic or API responses. Admin team manages the catalog.

    Customers browse occasions, select one, and create a Celebration for it.
    Packages are linked to occasions via the `package_occasions` M:N table.
    """

    __tablename__ = "occasions"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_occasions_slug"),
        Index("ix_occasions_category_id", "category_id"),
        Index("ix_occasions_active_featured", "is_active", "is_featured"),
        Index("ix_occasions_popularity", "popularity_score"),
        Index("ix_occasions_display_order", "category_id", "display_order"),
    )

    # ── Taxonomy ──────────────────────────────────────────────────────────────

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasion_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="Browsable category this occasion belongs to",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        unique=True,
        comment="URL-safe identifier e.g. 'birthday', 'first-birthday', 'diwali-puja'",
    )

    short_name: Mapped[str | None] = mapped_column(
        String(80),
        nullable=True,
        comment="Abbreviated name for compact UI labels and notifications",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Media ─────────────────────────────────────────────────────────────────

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Small icon for cards and list views",
    )

    banner_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Full-width hero banner for the occasion detail page",
    )

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Square thumbnail for grid-style browse screens",
    )

    # ── Discovery ─────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Sort order within the same category (ascending)",
    )

    popularity_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Denormalized score updated by background job for trending sort",
    )

    # ── Flags ─────────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Promoted in home screen featured carousels",
    )

    is_seasonal: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Festival/seasonal occasions have time-bound package availability",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    category: Mapped[OccasionCategory | None] = relationship(
        "OccasionCategory",
        back_populates="occasions",
        lazy="noload",
    )

    themes: Mapped[list[OccasionTheme]] = relationship(
        "OccasionTheme",
        secondary="occasion_theme_links",
        back_populates="occasions",
        lazy="noload",
    )

    moods: Mapped[list[OccasionMood]] = relationship(
        "OccasionMood",
        secondary="occasion_mood_links",
        back_populates="occasions",
        lazy="noload",
    )

    tags: Mapped[list[OccasionTag]] = relationship(
        "OccasionTag",
        secondary="occasion_tag_links",
        back_populates="occasions",
        lazy="noload",
    )

    celebrations: Mapped[list[Celebration]] = relationship(
        "Celebration",
        back_populates="occasion",
        lazy="noload",
    )

    packages: Mapped[list[Package]] = relationship(
        "Package",
        secondary="package_occasions",
        back_populates="occasions",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Occasion id={self.id} name={self.name!r} slug={self.slug!r}>"
