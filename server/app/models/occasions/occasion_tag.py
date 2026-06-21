"""
OccasionTag — flexible labels for filtering and discovery.

Tags like "Indoor", "Outdoor", "Family", "Premium", "Kids-Friendly"
help customers discover appropriate occasions and packages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion import Occasion


class OccasionTag(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A searchable label applied to occasions for discovery and filtering.
    Linked to occasions via the `occasion_tag_links` association table.
    """

    __tablename__ = "occasion_tags"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_occasion_tags_slug"),
        Index("ix_occasion_tags_sort", "is_active", "sort_order"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        comment="Machine-readable label e.g. 'indoor', 'outdoor', 'premium'",
    )

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    occasions: Mapped[list[Occasion]] = relationship(
        "Occasion",
        secondary="occasion_tag_links",
        back_populates="tags",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<OccasionTag id={self.id} slug={self.slug!r}>"
