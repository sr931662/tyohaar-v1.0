"""Automation rule — defines trigger → condition → action workflows."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AutomationRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Defines an automation workflow triggered by a business event.

    Example:
        trigger_event  = "booking.completed"
        conditions     = {"booking_value_gte": 5000}
        actions        = [
            {"type": "generate_invoice"},
            {"type": "wallet_settlement"},
            {"type": "send_notification", "template": "review_request"},
        ]
    """

    __tablename__ = "cms_automation_rules"
    __table_args__ = (
        CheckConstraint(
            "trigger_event IN ("
            "'vendor.registered','vendor.approved','vendor.rejected',"
            "'booking.created','booking.confirmed','booking.completed','booking.cancelled',"
            "'payment.completed','payment.failed','payment.refunded',"
            "'membership.expiring','membership.expired','membership.renewed',"
            "'user.registered','user.inactive','referral.completed',"
            "'support.ticket_opened','support.ticket_resolved'"
            ")",
            name="ck_automation_rules_trigger_event",
        ),
        Index("ix_automation_rules_trigger_event", "trigger_event"),
        Index("ix_automation_rules_is_active", "is_active"),
        Index("ix_automation_rules_created_by", "created_by_admin_id"),
    )

    created_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("admins.id", ondelete="SET NULL"),
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_event: Mapped[str] = mapped_column(String(64), nullable=False)

    # JSON condition tree evaluated against the event payload
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Optional condition tree; null = always run",
    )

    # Ordered list of action objects
    actions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        comment="List of {type, params} action descriptors",
    )

    # Control
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100, server_default="100",
        comment="Lower number = higher priority when multiple rules match",
    )
    delay_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0",
        comment="Seconds to wait before executing actions after trigger",
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, nullable=False, default=3, server_default="3",
    )

    # Stats
    total_executions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    successful_executions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_executions: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_triggered_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    logs: Mapped[list["AutomationLog"]] = relationship(
        "AutomationLog",
        back_populates="rule",
        lazy="noload",
    )
