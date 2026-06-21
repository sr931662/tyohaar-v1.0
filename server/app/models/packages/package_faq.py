"""
PackageFAQ — frequently asked questions for a package.

FAQs are shown on the package detail page to reduce pre-booking support queries.
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
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class PackageFAQ(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single FAQ entry on the package detail page.

    Admin-managed. `display_order` controls the sequence of FAQs shown
    to the customer. Inactive FAQs are hidden without deletion.
    """

    __tablename__ = "package_faqs"

    __table_args__ = (
        Index("ix_package_faqs_package_id", "package_id"),
        Index("ix_package_faqs_order", "package_id", "is_active", "display_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Content ───────────────────────────────────────────────────────────────

    question: Mapped[str] = mapped_column(String(500), nullable=False)

    answer: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="faqs",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageFAQ id={self.id} package_id={self.package_id} "
            f"question={self.question[:40]!r}>"
        )
