"""
PackageServiceImage — photos illustrating a single PackageService.

Mirrors PackageItemImage exactly (see package_item_image.py).
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package_service import PackageServiceLine


class PackageServiceImage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single photo of a PackageService, shown in a swipeable slider like the package gallery."""

    __tablename__ = "package_service_images"

    __table_args__ = (
        Index("ix_package_service_images_service_id", "service_id"),
    )

    service_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("package_services.id", ondelete="CASCADE"),
        nullable=False,
    )

    image_url: Mapped[str] = mapped_column(String(500), nullable=False)

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    service: Mapped[PackageServiceLine] = relationship(
        "PackageServiceLine",
        back_populates="images",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PackageServiceImage id={self.id} service_id={self.service_id}>"
