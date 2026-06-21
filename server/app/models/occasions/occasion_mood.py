"""
OccasionMood — emotional tone / atmosphere descriptor for a celebration.

Moods help customers articulate what feeling they want:
Elegant, Grand, Fun, Romantic, Intimate, Traditional, etc.
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion import Occasion


class OccasionMood(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    An emotional descriptor for the desired celebration atmosphere.

    Linked to occasions via the `occasion_mood_links` association table.
    Customers select a mood when planning their celebration alongside a theme.
    """

    __tablename__ = "occasion_moods"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_occasion_moods_slug"),
        Index("ix_occasion_moods_sort", "is_active", "sort_order"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment="URL-safe identifier e.g. 'elegant', 'grand', 'fun', 'romantic'",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Emoji-style icon or illustration for the mood selector UI",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    occasions: Mapped[list[Occasion]] = relationship(
        "Occasion",
        secondary="occasion_mood_links",
        back_populates="moods",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<OccasionMood id={self.id} name={self.name!r} slug={self.slug!r}>"
