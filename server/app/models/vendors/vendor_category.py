"""
VendorCategory — normalized, hierarchical service category taxonomy.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
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
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor_service import VendorService


class VendorCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Hierarchical taxonomy of services available on the platform.

    Two-level hierarchy is sufficient for Tyohaar:
    - Root categories: Decoration, Photography, Catering, etc. (parent_id = NULL)
    - Sub-categories: Birthday Decoration, Wedding Photography, etc.

    `slug` enables URL-safe identifiers and client-side caching.
    `sort_order` controls display ordering on the Explore screen.
    This table is populated via seed data and edited by admins, not by vendors.
    """

    __tablename__ = "vendor_categories"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_vendor_categories_slug"),
        Index("ix_vendor_categories_parent_id", "parent_id"),
        Index("ix_vendor_categories_sort_order", "is_active", "sort_order"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(100), nullable=False)

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        comment="URL-safe lowercase identifier (e.g., 'wedding-photography')",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    icon_url: Mapped[str | None] = mapped_column(
        String(2048),
        nullable=True,
        comment="CDN URL of the category icon shown in the Explore screen",
    )

    # ── Hierarchy ─────────────────────────────────────────────────────────────

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendor_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for root categories. Points to parent for sub-categories.",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Ascending sort order for display on the Explore screen",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    parent: Mapped[VendorCategory | None] = relationship(
        "VendorCategory",
        remote_side="VendorCategory.id",
        foreign_keys=[parent_id],
        lazy="noload",
    )

    children: Mapped[list[VendorCategory]] = relationship(
        "VendorCategory",
        foreign_keys=[parent_id],
        back_populates="parent",
        lazy="noload",
    )

    services: Mapped[list[VendorService]] = relationship(
        "VendorService",
        back_populates="category",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<VendorCategory slug={self.slug!r} parent_id={self.parent_id}>"
