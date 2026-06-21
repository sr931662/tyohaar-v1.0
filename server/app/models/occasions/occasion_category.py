"""
OccasionCategory — hierarchical taxonomy for grouping occasion types.

Admins define these; customers browse by category.
Supports 2-level hierarchy: parent categories (Life Events) with
sub-categories (Birthday, Anniversary, Baby Shower).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import OccasionCategory as OccasionCategoryType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.occasion import Occasion


class OccasionCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A browsable category bucket (e.g. 'Life Events', 'Festivals', 'Corporate').

    `category_type` maps to the OccasionCategory enum for programmatic access.
    `parent_id` enables a 2-level hierarchy: top-level categories have no parent.

    Admin-managed. Customers see this to browse and filter occasions.
    """

    __tablename__ = "occasion_categories"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_occasion_categories_slug"),
        Index("ix_occasion_categories_parent_id", "parent_id"),
        Index("ix_occasion_categories_sort", "is_active", "sort_order"),
    )

    # ── Self-Referential Hierarchy ────────────────────────────────────────────

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("occasion_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL = top-level category. Set to parent.id for sub-categories.",
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(150), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        unique=True,
        comment="URL-safe identifier e.g. 'life-events', 'festivals'",
    )

    category_type: Mapped[OccasionCategoryType | None] = mapped_column(
        SAEnum(OccasionCategoryType, name="occasion_category_type_enum", native_enum=False),
        nullable=True,
        comment="Maps to the canonical OccasionCategory enum for programmatic access",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    icon_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="CDN URL for the category icon (SVG or PNG, shown in browse UI)",
    )

    banner_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="CDN URL for the category banner / header image",
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Display order within the same parent level (ascending)",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    parent: Mapped[OccasionCategory | None] = relationship(
        "OccasionCategory",
        remote_side="OccasionCategory.id",
        back_populates="children",
        lazy="noload",
    )

    children: Mapped[list[OccasionCategory]] = relationship(
        "OccasionCategory",
        back_populates="parent",
        lazy="noload",
        cascade="all, delete-orphan",
    )

    occasions: Mapped[list[Occasion]] = relationship(
        "Occasion",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<OccasionCategory id={self.id} name={self.name!r} slug={self.slug!r}>"
