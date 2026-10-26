"""
BalloonColor — one entry in the managed balloon décor colour palette.

Replaces the hard-coded palette: admins add, rename, re-order, disable or
remove colours from the portal, and the app plus booking validation read this
table. A booking stores the chosen *hex codes* (a snapshot), so editing or
deleting a colour here never rewrites an existing order.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class BalloonColor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "balloon_colors"

    name: Mapped[str] = mapped_column(String(60), nullable=False)
    hex_code: Mapped[str] = mapped_column(
        String(7), nullable=False, unique=True,
        comment="Upper-case #RRGGBB. Bookings store the lower-cased hex, not a reference to this row.",
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    def __repr__(self) -> str:
        return f"<BalloonColor {self.name!r} {self.hex_code} active={self.is_active}>"


# Two colours may not share a name, ignoring case ("Gold" vs "gold").
Index("uq_balloon_colors_name_lower", func.lower(BalloonColor.name), unique=True)
