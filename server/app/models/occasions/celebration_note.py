"""
CelebrationNote — private customer notes attached to a celebration.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.occasions.celebration import Celebration
    from app.models.users.user import User


class CelebrationNote(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A private text note written by the customer about their celebration.

    Notes are entirely customer-private — never visible to vendors or
    Tyohaar staff in customer-facing contexts. `is_pinned` elevates
    important notes to the top of the notes list.

    Soft-deleted notes are excluded from API responses but retained
    for audit purposes (e.g., dispute resolution).
    """

    __tablename__ = "celebration_notes"

    __table_args__ = (
        Index("ix_celebration_notes_celebration_id", "celebration_id"),
        Index("ix_celebration_notes_author_id", "author_id"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The user who created this note",
    )

    # ── Content ───────────────────────────────────────────────────────────────

    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    body: Mapped[str] = mapped_column(Text, nullable=False)

    is_pinned: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Pinned notes appear at the top of the notes list",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        back_populates="notes",
        lazy="noload",
    )

    author: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<CelebrationNote id={self.id} celebration_id={self.celebration_id} "
            f"pinned={self.is_pinned}>"
        )
