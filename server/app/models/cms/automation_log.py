"""Automation log — records each execution of an automation rule."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AutomationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Immutable execution record for one automation rule run."""

    __tablename__ = "cms_automation_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('RUNNING','COMPLETED','FAILED','RETRYING','SKIPPED')",
            name="ck_automation_logs_status",
        ),
        Index("ix_automation_logs_rule_id", "rule_id"),
        Index("ix_automation_logs_entity_id", "entity_id"),
        Index("ix_automation_logs_status", "status"),
        Index("ix_automation_logs_created_at", "created_at"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cms_automation_rules.id", ondelete="CASCADE"),
        nullable=False,
    )

    # The entity that triggered the rule (e.g. a booking_id)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)
    trigger_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    status: Mapped[str] = mapped_column(String(32), nullable=False, default="RUNNING", server_default="RUNNING")

    # Per-action results
    actions_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    actions_completed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    actions_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    action_results: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True, comment="Per-action execution results"
    )

    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_at: Mapped[Any | None] = mapped_column(nullable=True)

    # Relationship
    rule: Mapped["AutomationRule"] = relationship(
        "AutomationRule",
        back_populates="logs",
        lazy="noload",
    )
