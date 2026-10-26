"""
GuestEntryLog — append-only record of every gate verification attempt.

One row per verify / check-in / check-out request, successful or not, so the
host and operations staff can see who came in, who was turned away and why,
and which operator did it. Failed attempts against unknown codes are kept too
(with no guest attached) — they are the signal for a probing or confused gate.

`client_scan_id` makes check-in/check-out retry-safe: a gate phone on a flaky
connection re-sends the same id, and the partial unique index guarantees the
same scan can never be recorded twice.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import EntryOperatorType, GuestEntryAction, GuestVerificationResult
from app.models.mixins import UUIDPrimaryKeyMixin


class GuestEntryLog(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "guest_entry_logs"

    __table_args__ = (
        Index("ix_guest_entry_logs_celebration_time", "celebration_id", "occurred_at"),
        Index("ix_guest_entry_logs_guest", "celebration_guest_id"),
        Index("ix_guest_entry_logs_result", "result", "occurred_at"),
        Index(
            "uq_guest_entry_logs_scan",
            "celebration_guest_id",
            "action",
            "client_scan_id",
            unique=True,
            postgresql_where=text("client_scan_id IS NOT NULL AND celebration_guest_id IS NOT NULL"),
        ),
    )

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    celebration_guest_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebration_guests.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL when the presented code matched no guest in scope.",
    )
    action: Mapped[GuestEntryAction] = mapped_column(
        SAEnum(GuestEntryAction, name="guest_entry_action", native_enum=False, length=20),
        nullable=False,
    )
    result: Mapped[GuestVerificationResult] = mapped_column(
        SAEnum(GuestVerificationResult, name="guest_verification_result", native_enum=False, length=30),
        nullable=False,
    )
    method: Mapped[str] = mapped_column(
        String(10), nullable=False, default="manual",
        comment="How the pass was presented: qr | manual | search.",
    )
    party_size: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    operator_type: Mapped[EntryOperatorType] = mapped_column(
        SAEnum(EntryOperatorType, name="entry_operator_type", native_enum=False, length=20),
        nullable=False,
    )
    operator_user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    gate_access_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebration_gate_accesses.id", ondelete="SET NULL"),
        nullable=True,
    )
    operator_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    client_scan_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<GuestEntryLog {self.action} result={self.result} guest={self.celebration_guest_id}>"
