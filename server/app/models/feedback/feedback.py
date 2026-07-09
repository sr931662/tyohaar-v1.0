"""
Feedback — a standalone customer feedback submission.

Distinct from SupportTicket: this is a one-shot rating + comment, not a
threaded case that needs an agent assigned or a status worked through.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy import Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import FeedbackCategory
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class Feedback(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A single customer feedback submission (rating + optional comment)."""

    __tablename__ = "feedback"

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating_range"),
        Index("ix_feedback_customer_id", "customer_id"),
        Index("ix_feedback_category", "category"),
        Index("ix_feedback_created_at", "created_at"),
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Customer who submitted this feedback.",
    )

    rating: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        comment="1-5 star rating.",
    )

    category: Mapped[FeedbackCategory] = mapped_column(
        SAEnum(FeedbackCategory, name="feedback_category", native_enum=False),
        nullable=False,
    )

    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    app_version: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="Client app version at time of submission, for triage context.",
    )

    is_reviewed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Admin triage flag — true once an admin has looked at this submission.",
    )

    reviewed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    customer: Mapped[User] = relationship(
        "User",
        foreign_keys=[customer_id],
        lazy="noload",
    )

    reviewed_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[reviewed_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Feedback id={self.id} customer_id={self.customer_id} rating={self.rating}>"
