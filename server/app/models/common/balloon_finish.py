"""
BalloonFinish — one entry in the managed balloon finish list (Standard matte,
Pastel, Chrome / metallic …). Admin-managed like the colour palette; a booking
stores the finish *name* as a snapshot.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BalloonFinish(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "balloon_finishes"

    name: Mapped[str] = mapped_column(String(60), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<BalloonFinish {self.name!r} active={self.is_active}>"


Index("uq_balloon_finishes_name_lower", func.lower(BalloonFinish.name), unique=True)
