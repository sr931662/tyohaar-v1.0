"""
PackageItemVendor — internal mapping from a package item to vendor(s).

INTERNAL ONLY. This table is NEVER exposed in customer-facing API responses.
It exists solely for Tyohaar's internal vendor assignment engine.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_item import PackageItem
    from app.models.vendors.vendor import Vendor


class PackageItemVendor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Maps a package item to one or more possible vendors for assignment.

    When a customer books a package, the assignment engine uses this table
    to find available vendors for each item and assigns the best one based
    on priority_rank, vendor availability, and rating.

    Multiple vendors can be mapped to the same item:
    - priority_rank=1: preferred vendor (first choice)
    - priority_rank=2: first backup
    - priority_rank=3: second backup, etc.

    `is_active=False` temporarily removes a vendor from consideration
    without deleting the mapping (e.g., vendor on leave).

    ENFORCEMENT: Never include vendor_id or any field from this table
    in customer-facing API serializers, response schemas, or OpenAPI docs.
    """

    __tablename__ = "package_item_vendors"

    __table_args__ = (
        UniqueConstraint(
            "package_item_id",
            "vendor_id",
            name="uq_package_item_vendors_item_vendor",
        ),
        Index("ix_package_item_vendors_item_id", "package_item_id"),
        Index("ix_package_item_vendors_vendor_id", "vendor_id"),
        Index("ix_package_item_vendors_active", "package_item_id", "is_active", "priority_rank"),
    )

    # ── Mapping ───────────────────────────────────────────────────────────────

    package_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        comment="INTERNAL. Never expose to customers.",
    )

    # ── Assignment Priority ───────────────────────────────────────────────────

    is_preferred: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Primary vendor for this item. Assignment engine picks this first.",
    )

    priority_rank: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="1 = preferred, 2 = first backup, 3 = second backup, etc.",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Inactive mappings are skipped during assignment. Use to temporarily exclude a vendor.",
    )

    # ── Notes ─────────────────────────────────────────────────────────────────

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about this vendor-item mapping (skills, constraints, history)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    package_item: Mapped[PackageItem] = relationship(
        "PackageItem",
        back_populates="vendor_assignments",
        lazy="noload",
    )

    vendor: Mapped[Vendor] = relationship("Vendor", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<PackageItemVendor item={self.package_item_id} "
            f"vendor={self.vendor_id} rank={self.priority_rank}>"
        )
