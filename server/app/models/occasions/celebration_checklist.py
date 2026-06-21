"""
CelebrationChecklist — to-do tasks for planning a celebration.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
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
    from app.models.occasions.celebration import Celebration


class ChecklistItemStatus(str, enum.Enum):
    """
    Completion status of a single checklist task.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CelebrationChecklist(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single task on the celebration planning checklist.

    Checklist items guide the customer through the planning process.
    Some items are auto-generated (is_system_generated=True) by the service
    layer when a celebration is created (e.g., 'Select a package', 'Invite guests').
    Others are added manually by the customer.

    `due_date` is optional — customers can set deadlines for their tasks.
    `completed_at` is set by the service layer when `status` transitions to COMPLETED.
    """

    __tablename__ = "celebration_checklists"

    __table_args__ = (
        Index("ix_celebration_checklists_celebration_id", "celebration_id"),
        Index("ix_celebration_checklists_status", "celebration_id", "status"),
        Index("ix_celebration_checklists_order", "celebration_id", "display_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Task ──────────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(String(300), nullable=False)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ChecklistItemStatus] = mapped_column(
        SAEnum(ChecklistItemStatus, name="checklist_item_status", native_enum=False),
        nullable=False,
        default=ChecklistItemStatus.PENDING,
    )

    # ── Scheduling ────────────────────────────────────────────────────────────

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_system_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True if created automatically during celebration setup",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    celebration: Mapped[Celebration] = relationship(
        "Celebration",
        back_populates="checklist",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<CelebrationChecklist id={self.id} title={self.title!r} "
            f"status={self.status}>"
        )
