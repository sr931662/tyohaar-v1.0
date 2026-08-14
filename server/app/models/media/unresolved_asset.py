"""
UnresolvedMediaAsset — media rows whose provider object id could not be
determined, and which therefore cannot be deleted from storage.

This table exists so that a failure to delete is *loud and durable* rather
than a log line nobody reads. The backfill writes a row here for every image
or video whose `storage_public_id` could not be resolved from its URL, and
the purge pipeline refuses to report a request as fully purged while any of
its assets appear here unresolved.

The rule this table enforces:

    Never report an asset as deleted when the external object still exists,
    and never delete the database row that is the only pointer to it.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class UnresolvedMediaAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A media object we know about but cannot delete."""

    __tablename__ = "unresolved_media_assets"

    __table_args__ = (
        UniqueConstraint(
            "media_kind",
            "media_id",
            name="uq_unresolved_media_assets_kind_id",
        ),
        Index("ix_unresolved_media_assets_owner_id", "owner_id"),
        Index("ix_unresolved_media_assets_resolved_at", "resolved_at"),
    )

    media_kind: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        comment="Which table the row lives in: 'image', 'video', 'profile_photo', 'cover_image'.",
    )

    media_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=False,
        comment=(
            "Primary key of the row in that table. Deliberately not a foreign "
            "key: this record must survive even if the source row is removed "
            "by some other path, otherwise the orphaned object is lost."
        ),
    )

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="The user the asset belonged to, so a purge can find its own failures.",
    )

    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The serving URL. The only handle we have on the object until resolved.",
    )

    reason: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Why resolution failed, e.g. 'url_not_cloudinary', 'admin_api_miss'.",
    )

    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When resolution was last attempted.",
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Set once the object was manually located and deleted, or "
            "confirmed already absent. NULL means still outstanding."
        ),
    )

    resolution_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="How it was resolved. Internal ops note.",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<UnresolvedMediaAsset {self.media_kind}:{self.media_id} "
            f"resolved={self.resolved_at is not None}>"
        )
