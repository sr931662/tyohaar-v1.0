"""
PackageItemLike — a customer's "like" (favorite) on a package item.

One row per (user_id, package_item_id). Presence of a row means liked;
absence means not liked — no boolean flag needed.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_item import PackageItem
    from app.models.users.user import User


class PackageItemLike(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A customer's like/favorite on a package item."""

    __tablename__ = "package_item_likes"

    __table_args__ = (
        UniqueConstraint(
            "user_id", "package_item_id", name="uq_package_item_likes_user_item"
        ),
        Index("ix_package_item_likes_package_item_id", "package_item_id"),
        Index("ix_package_item_likes_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    package_item_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_items.id", ondelete="CASCADE"),
        nullable=False,
    )

    package_item: Mapped[PackageItem] = relationship(
        "PackageItem",
        back_populates="likes",
        lazy="noload",
    )

    customer: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<PackageItemLike user_id={self.user_id} package_item_id={self.package_item_id}>"
