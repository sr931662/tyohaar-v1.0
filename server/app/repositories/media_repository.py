"""
Media repository — Image, Video, Memory.

Three sub-repositories handle the three media models, each sharing the
same AsyncSession so they participate in one UnitOfWork transaction.

Image and Video use polymorphic entity_type/entity_id attachment (no real FK)
and owner_type/owner_id for upload ownership. Memory links to a Celebration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import MediaStatus, MediaUsage
from app.models.media.image import Image, ImageOwnerType, ModerationStatus
from app.models.media.memory import Memory, MemoryVisibility
from app.models.media.video import Video, VideoTranscodingStatus
from app.repositories.base import BaseRepository


class ImageRepository(BaseRepository[Image]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Image)

    # ── Ownership ─────────────────────────────────────────────────────────────

    async def find_by_owner(
        self,
        owner_type: ImageOwnerType,
        owner_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Image]:
        return await self.find_many(
            Image.owner_type == owner_type,
            Image.owner_id == owner_id,
            order_by=Image.sort_order.asc(),
            skip=skip,
            limit=limit,
        )

    # ── Polymorphic Attachment ─────────────────────────────────────────────────

    async def find_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Image]:
        return await self.find_many(
            Image.entity_type == entity_type,
            Image.entity_id == entity_id,
            order_by=Image.sort_order.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_active_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> list[Image]:
        return await self.find_many(
            Image.entity_type == entity_type,
            Image.entity_id == entity_id,
            Image.media_status == MediaStatus.ACTIVE,
            Image.moderation_status == ModerationStatus.APPROVED,
            order_by=Image.sort_order.asc(),
        )

    async def find_featured_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Image | None:
        return await self.find_one(
            Image.entity_type == entity_type,
            Image.entity_id == entity_id,
            Image.is_featured == True,  # noqa: E712
            Image.media_status == MediaStatus.ACTIVE,
        )

    # ── Usage ─────────────────────────────────────────────────────────────────

    async def find_by_usage(
        self,
        usage: MediaUsage,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Image]:
        return await self.find_many(
            Image.usage == usage,
            order_by=Image.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Moderation ────────────────────────────────────────────────────────────

    async def find_pending_moderation(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Image]:
        return await self.find_many(
            Image.moderation_status == ModerationStatus.PENDING,
            Image.media_status == MediaStatus.ACTIVE,
            order_by=Image.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_requiring_review(self) -> list[Image]:
        return await self.find_many(
            Image.moderation_status == ModerationStatus.REQUIRES_REVIEW,
            order_by=Image.created_at.asc(),
        )

    async def find_rejected(self, *, skip: int = 0, limit: int = 100) -> list[Image]:
        return await self.find_many(
            Image.moderation_status == ModerationStatus.REJECTED,
            order_by=Image.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    # ── Processing ────────────────────────────────────────────────────────────

    async def find_unprocessed(self) -> list[Image]:
        """Images that have been uploaded but not yet transitioned to ACTIVE."""
        return await self.find_many(
            Image.media_status == MediaStatus.UPLOADING,
            order_by=Image.created_at.asc(),
        )

    # ── Deduplication ─────────────────────────────────────────────────────────

    async def find_by_content_hash(self, content_hash: str) -> Image | None:
        return await self.find_one(
            Image.content_hash == content_hash,
            Image.media_status == MediaStatus.ACTIVE,
        )

    # ── Domain Shortcuts ──────────────────────────────────────────────────────

    async def find_for_vendor(
        self,
        vendor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Image]:
        return await self.find_many(
            Image.entity_type == "vendor",
            Image.entity_id == vendor_id,
            Image.media_status == MediaStatus.ACTIVE,
            order_by=Image.sort_order.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_for_package(self, package_id: uuid.UUID) -> list[Image]:
        return await self.find_many(
            Image.entity_type == "package",
            Image.entity_id == package_id,
            Image.media_status == MediaStatus.ACTIVE,
            order_by=Image.sort_order.asc(),
        )

    async def find_for_memory(self, memory_id: uuid.UUID) -> list[Image]:
        return await self.find_many(
            Image.entity_type == "memory",
            Image.entity_id == memory_id,
            Image.media_status == MediaStatus.ACTIVE,
            order_by=Image.sort_order.asc(),
        )

    async def find_for_booking(self, booking_id: uuid.UUID) -> list[Image]:
        return await self.find_many(
            Image.entity_type == "booking",
            Image.entity_id == booking_id,
            order_by=Image.sort_order.asc(),
        )

    # ── Moderation Actions ────────────────────────────────────────────────────

    async def approve(
        self,
        image_id: uuid.UUID,
        reviewed_by_id: uuid.UUID,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Image)
            .where(Image.id == image_id)
            .values(
                moderation_status=ModerationStatus.APPROVED,
                moderation_reviewed_at=now,
                moderation_reviewed_by_id=reviewed_by_id,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)

    async def reject(
        self,
        image_id: uuid.UUID,
        reviewed_by_id: uuid.UUID,
        reason: str,
    ) -> None:
        now = datetime.now(tz=timezone.utc)
        stmt = (
            update(Image)
            .where(Image.id == image_id)
            .values(
                moderation_status=ModerationStatus.REJECTED,
                moderation_notes=reason,
                moderation_reviewed_at=now,
                moderation_reviewed_by_id=reviewed_by_id,
            )
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


class VideoRepository(BaseRepository[Video]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Video)

    # ── Ownership ─────────────────────────────────────────────────────────────

    async def find_by_owner(
        self,
        owner_type: ImageOwnerType,
        owner_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Video]:
        return await self.find_many(
            Video.owner_type == owner_type,
            Video.owner_id == owner_id,
            order_by=Video.sort_order.asc(),
            skip=skip,
            limit=limit,
        )

    # ── Polymorphic Attachment ─────────────────────────────────────────────────

    async def find_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> list[Video]:
        return await self.find_many(
            Video.entity_type == entity_type,
            Video.entity_id == entity_id,
            order_by=Video.sort_order.asc(),
        )

    async def find_active_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> list[Video]:
        return await self.find_many(
            Video.entity_type == entity_type,
            Video.entity_id == entity_id,
            Video.media_status == MediaStatus.ACTIVE,
            Video.moderation_status == ModerationStatus.APPROVED,
            order_by=Video.sort_order.asc(),
        )

    async def find_featured_for_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
    ) -> Video | None:
        return await self.find_one(
            Video.entity_type == entity_type,
            Video.entity_id == entity_id,
            Video.is_featured == True,  # noqa: E712
            Video.media_status == MediaStatus.ACTIVE,
        )

    # ── Transcoding Pipeline ──────────────────────────────────────────────────

    async def find_unprocessed(self) -> list[Video]:
        """Videos queued for transcoding that have not started yet."""
        return await self.find_many(
            Video.transcoding_status == VideoTranscodingStatus.NOT_STARTED,
            Video.media_status == MediaStatus.ACTIVE,
            order_by=Video.created_at.asc(),
        )

    async def find_by_transcoding_status(
        self,
        status: VideoTranscodingStatus,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Video]:
        return await self.find_many(
            Video.transcoding_status == status,
            order_by=Video.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_transcoding_failed(self) -> list[Video]:
        return await self.find_many(
            Video.transcoding_status == VideoTranscodingStatus.FAILED,
            order_by=Video.created_at.asc(),
        )

    # ── Moderation ────────────────────────────────────────────────────────────

    async def find_pending_moderation(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Video]:
        return await self.find_many(
            Video.moderation_status == ModerationStatus.PENDING,
            Video.transcoding_status == VideoTranscodingStatus.COMPLETED,
            order_by=Video.created_at.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_requiring_review(self) -> list[Video]:
        return await self.find_many(
            Video.moderation_status == ModerationStatus.REQUIRES_REVIEW,
            order_by=Video.created_at.asc(),
        )

    # ── Domain Shortcuts ──────────────────────────────────────────────────────

    async def find_for_vendor(
        self,
        vendor_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Video]:
        return await self.find_many(
            Video.entity_type == "vendor",
            Video.entity_id == vendor_id,
            Video.media_status == MediaStatus.ACTIVE,
            order_by=Video.sort_order.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_for_memory(self, memory_id: uuid.UUID) -> list[Video]:
        return await self.find_many(
            Video.entity_type == "memory",
            Video.entity_id == memory_id,
            Video.media_status == MediaStatus.ACTIVE,
            order_by=Video.sort_order.asc(),
        )


class MemoryRepository(BaseRepository[Memory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Memory)

    async def find_by_celebration(
        self,
        celebration_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Memory]:
        return await self.find_many(
            Memory.celebration_id == celebration_id,
            order_by=Memory.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Memory]:
        return await self.find_many(
            Memory.customer_id == customer_id,
            Memory.is_archived == False,  # noqa: E712
            order_by=Memory.event_date.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_public(self, *, skip: int = 0, limit: int = 50) -> list[Memory]:
        return await self.find_many(
            Memory.visibility == MemoryVisibility.PUBLIC,
            Memory.is_archived == False,  # noqa: E712
            order_by=[Memory.is_featured.desc(), Memory.event_date.desc()],
            skip=skip,
            limit=limit,
        )

    async def find_public_for_celebration(
        self,
        celebration_id: uuid.UUID,
    ) -> list[Memory]:
        return await self.find_many(
            Memory.celebration_id == celebration_id,
            Memory.visibility == MemoryVisibility.PUBLIC,
            Memory.is_archived == False,  # noqa: E712
            order_by=Memory.created_at.desc(),
        )

    async def find_featured(self, *, limit: int = 20) -> list[Memory]:
        return await self.find_many(
            Memory.is_featured == True,  # noqa: E712
            Memory.visibility == MemoryVisibility.PUBLIC,
            Memory.is_archived == False,  # noqa: E712
            order_by=Memory.event_date.desc(),
            limit=limit,
        )

    async def find_by_shared_token(self, token: str) -> Memory | None:
        return await self.find_one(
            Memory.shared_token == token,
            Memory.is_archived == False,  # noqa: E712
        )

    async def find_archived_for_customer(
        self,
        customer_id: uuid.UUID,
    ) -> list[Memory]:
        return await self.find_many(
            Memory.customer_id == customer_id,
            Memory.is_archived == True,  # noqa: E712
            order_by=Memory.updated_at.desc(),
        )

    async def find_shared_link(self, *, skip: int = 0, limit: int = 50) -> list[Memory]:
        return await self.find_many(
            Memory.visibility == MemoryVisibility.SHARED_LINK,
            Memory.is_archived == False,  # noqa: E712
            order_by=Memory.shared_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def find_with_media(self, memory_id: uuid.UUID) -> Memory | None:
        return await self.get_by_id(
            memory_id,
            options=[
                selectinload(Memory.celebration),
            ],
        )


# ── Aggregate ─────────────────────────────────────────────────────────────────


class MediaRepositoryAggregate:
    """Groups all media-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.images = ImageRepository(session)
        self.videos = VideoRepository(session)
        self.memories = MemoryRepository(session)
