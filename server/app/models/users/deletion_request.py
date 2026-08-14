"""
DeletionRequest — the durable record of a user asking to be deleted.

This table is the source of truth for the whole lifecycle. Nothing about a
deletion is inferred from the user row: the request carries its own clocks,
its own status, and its own evidence of completion.

It is also the compliance artefact. It outlives the user it refers to, so it
is built to hold *no* raw personal data:

  * `user_id` is nulled once the purge completes.
  * `identifier_hash` is a keyed HMAC of the phone/email the request was
    raised against. It answers "did this person ask to be deleted?" if they
    ever ask again, and cannot be reversed into contact details. Because it
    is keyed with a server secret it is not a rainbow-table lookup either.
  * `purge_report` holds handler names and counts. Never sample values,
    never deleted content.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import DeletionRequestChannel, DeletionRequestStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class DeletionRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's request to have their account and personal data deleted."""

    __tablename__ = "deletion_requests"

    __table_args__ = (
        # The daily job asks "what is due for purge?" — this is that query.
        Index(
            "ix_deletion_requests_due",
            "status",
            "recovery_ends_at",
        ),
        Index("ix_deletion_requests_user_id", "user_id"),
        Index("ix_deletion_requests_identifier_hash", "identifier_hash"),
    )

    # ── Subject ───────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        # SET NULL rather than CASCADE: if a user row is ever removed by other
        # means, the compliance evidence must survive it.
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "The account being deleted. Nulled once the purge completes so no "
            "live link to the person remains."
        ),
    )

    identifier_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment=(
            "Keyed HMAC-SHA256 of the phone (or email) the request was raised "
            "against. Irreversible. Never store the raw identifier here."
        ),
    )

    channel: Mapped[DeletionRequestChannel] = mapped_column(
        SAEnum(
            DeletionRequestChannel,
            name="deletion_request_channel",
            native_enum=False,
        ),
        nullable=False,
        comment="How the request reached us.",
    )

    # ── Status ────────────────────────────────────────────────────────────────

    status: Mapped[DeletionRequestStatus] = mapped_column(
        SAEnum(
            DeletionRequestStatus,
            name="deletion_request_status",
            native_enum=False,
        ),
        nullable=False,
        default=DeletionRequestStatus.PENDING_VERIFICATION,
        comment="Current lifecycle state.",
    )

    # ── Clocks ────────────────────────────────────────────────────────────────

    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="When the user asked to be deleted.",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "When identity was proven. For an authenticated in-app request "
            "this equals requested_at — the bearer token is the proof."
        ),
    )

    recovery_ends_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "End of the window during which the user may restore the account. "
            "The purge job ignores anything before this instant."
        ),
    )

    purge_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Outer SLA by which the purge should have completed. Used for "
            "alerting on overdue requests, not for scheduling."
        ),
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the purge finished — successfully or incompletely.",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the user restored the account inside the recovery window.",
    )

    # ── Holds ─────────────────────────────────────────────────────────────────

    legal_hold_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Set when an open dispute, chargeback or notice requires the data "
            "to be preserved. The purge job skips any request under hold."
        ),
    )

    legal_hold_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Why the hold was placed. Internal only.",
    )

    # ── Evidence ──────────────────────────────────────────────────────────────

    attempt_count: Mapped[int] = mapped_column(
        default=0,
        nullable=False,
        comment="How many times the purge runner has executed for this request.",
    )

    purge_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Per-handler outcome: name, status, rows/objects affected, errors. "
            "Counts and identifiers only — never deleted content."
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<DeletionRequest id={self.id} status={self.status.value} "
            f"user_id={self.user_id}>"
        )
