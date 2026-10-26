"""
CelebrationGateAccess — a delegated, scoped credential for entry staff.

Tyohaar has no gate-staff role and residential gates are usually manned by
people who will never have a Tyohaar account. Rather than inventing a role and
an assignment system, the host issues a gate access for *one* celebration: a
link with a random token that opens the gate console. It can verify passes and
record entry/exit for that celebration only — nothing else in the platform —
and it expires on its own or can be revoked by the host at any time.

Only the HMAC of the token is stored; the link is shown to the host once.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CelebrationGateAccess(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "celebration_gate_accesses"

    __table_args__ = (
        Index("ix_celebration_gate_accesses_celebration", "celebration_id"),
    )

    celebration_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("celebrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(
        String(120), nullable=False,
        comment="Who/where this access is for, e.g. 'Main gate — Ramesh'. Shown in entry logs.",
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def is_usable(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at

    def __repr__(self) -> str:
        return f"<CelebrationGateAccess {self.label!r} celebration={self.celebration_id}>"
