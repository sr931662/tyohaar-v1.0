"""
MediaService — Image, Video, and Memory business operations.

All public methods open their own UoW so each call is a single atomic
transaction.  Callers should NOT share a UoW across service calls.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone
from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.models.enums import MediaStatus
from app.models.media.image import Image, ImageOwnerType, ModerationStatus
from app.models.media.memory import Memory, MemoryVisibility
from app.models.media.video import Video, VideoTranscodingStatus
from app.schemas.base import CursorPage
from app.schemas.media.create import ImageCreate, MemoryCreate, VideoCreate
from app.schemas.media.response import ImageResponse, MemoryResponse, VideoResponse
from app.services.base import BaseService
from app.services.media.constants import (
    IMAGE_CDN_BASE_URL,
    MAX_IMAGES_PER_ENTITY,
    MAX_VIDEOS_PER_ENTITY,
)
from app.services.media.exceptions import (
    ImageCountLimitError,
    ImageNotFoundError,
    ImageOwnershipError,
    MemoryAccessDeniedError,
    MemoryNotFoundError,
    MemoryOwnershipError,
    VideoNotFoundError,
    VideoOwnershipError,
)
from app.services.media.helpers import build_public_url, generate_storage_key
from app.services.media.validators import (
    validate_image_count_for_entity,
    validate_image_exists,
    validate_image_ownership,
    validate_memory_exists,
    validate_memory_ownership,
    validate_video_exists,
    validate_video_ownership,
)

# ---------------------------------------------------------------------------
# Lightweight upload-response stubs (routers will extend these as needed)
# ---------------------------------------------------------------------------

from app.schemas.base import BaseSchema as _BaseSchema


class ImageUploadResponse(_BaseSchema):
    """Returned by register_image_upload before the file is actually transferred."""
    image_id: UUID
    storage_key: str
    presigned_url_hint: str  # stub — real implementation calls the storage SDK


class VideoUploadResponse(_BaseSchema):
    """Returned by register_video_upload before the file is actually transferred."""
    video_id: UUID
    storage_key: str
    presigned_url_hint: str


# ---------------------------------------------------------------------------
# Helpers for cursor pagination (thin wrapper over raw list results)
# ---------------------------------------------------------------------------

def _make_cursor_page(items: list, limit: int) -> CursorPage:
    """Wrap a list in a CursorPage. next_cursor is stubbed here (use repository
    cursor helpers in production when offset-keyset pagination is wired up)."""
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]
    return CursorPage(items=items, has_more=has_more, next_cursor=None)


class MediaService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # =========================================================================
    # Images
    # =========================================================================

    async def upload_image(
        self,
        owner_id: UUID,
        owner_type: ImageOwnerType,
        usage,
        file_bytes: bytes,
        filename: str,
        content_type: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
    ) -> ImageResponse:
        """
        Upload a raw image file straight to Cloudinary and record it as an
        immediately-usable Image row. Unlike register/confirm (which models a
        client-direct-to-storage flow), this proxies the bytes through the
        backend — simpler, and appropriate for the image sizes vendors/admins
        upload here.
        """
        import hashlib

        from app.services.media.cloudinary_client import upload_image_bytes

        content_hash = hashlib.sha256(file_bytes).hexdigest()
        result = await upload_image_bytes(file_bytes, folder=f"tyohaar/{usage.value}")

        async with self._uow() as uow:
            image = Image(
                owner_id=owner_id,
                owner_type=owner_type,
                url=result["secure_url"],
                storage_path=result["public_id"],
                original_filename=filename,
                file_size_bytes=result.get("bytes") or len(file_bytes),
                mime_type=content_type,
                image_format=result.get("format"),
                width=result.get("width") or 1,
                height=result.get("height") or 1,
                usage=usage,
                media_status=MediaStatus.ACTIVE,
                moderation_status=ModerationStatus.APPROVED,
                content_hash=content_hash,
                cdn_provider="cloudinary",
                entity_type=entity_type,
                entity_id=entity_id,
                uploaded_at=datetime.now(tz=timezone.utc),
            )
            image = await uow.media.images.create(image)
            await uow.commit()
        return ImageResponse.model_validate(image)

    async def register_image_upload(
        self,
        owner_id: UUID,
        owner_type: str,
        data: ImageCreate,
    ) -> ImageUploadResponse:
        """
        Create an Image record with media_status=UPLOADING before the file
        is transferred to storage.  Returns the image_id and a storage_key
        the caller uses to build the actual upload request.
        """
        storage_key = generate_storage_key(
            owner_id,
            data.entity_type if hasattr(data, "entity_type") and data.entity_type else owner_type,
            data.file_name or "upload",
        )
        async with self._uow() as uow:
            if hasattr(data, "entity_type") and data.entity_type and hasattr(data, "entity_id") and data.entity_id:
                await validate_image_count_for_entity(data.entity_type, data.entity_id, uow)

            image = Image(
                owner_id=owner_id,
                owner_type=ImageOwnerType(owner_type) if isinstance(owner_type, str) else owner_type,
                url=build_public_url(storage_key, IMAGE_CDN_BASE_URL) or storage_key,
                storage_path=storage_key,
                original_filename=data.file_name,
                file_size_bytes=data.file_size_bytes or 0,
                mime_type=data.mime_type or "application/octet-stream",
                width=data.width or 1,
                height=data.height or 1,
                usage=data.usage,
                media_status=MediaStatus.UPLOADING,
                moderation_status=ModerationStatus.PENDING,
                sort_order=data.display_order,
                is_featured=data.is_primary,
                alt_text=data.alt_text,
                entity_type=getattr(data, "entity_type", None),
                entity_id=getattr(data, "entity_id", None),
            )
            image = await uow.media.images.create(image)
            await uow.commit()

        return ImageUploadResponse(
            image_id=image.id,
            storage_key=storage_key,
            presigned_url_hint=f"STUB:presign:{storage_key}",
        )

    async def confirm_image_upload(
        self,
        image_id: UUID,
        owner_id: UUID,
    ) -> ImageResponse:
        """Mark image as ACTIVE and transition moderation to PENDING review."""
        async with self._uow() as uow:
            image = await validate_image_ownership(image_id, owner_id, uow)
            image = await uow.media.images.update(image, {
                "media_status": MediaStatus.ACTIVE,
                "moderation_status": ModerationStatus.PENDING,
                "uploaded_at": datetime.now(tz=timezone.utc),
            })
            await uow.commit()
        return ImageResponse.model_validate(image)

    async def get_image(self, image_id: UUID) -> ImageResponse:
        async with self._uow() as uow:
            image = await validate_image_exists(image_id, uow)
        return ImageResponse.model_validate(image)

    async def list_images_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
        approved_only: bool = True,
    ) -> list[ImageResponse]:
        async with self._uow() as uow:
            if approved_only:
                images = await uow.media.images.find_active_for_entity(entity_type, entity_id)
            else:
                images = await uow.media.images.find_by_entity(entity_type, entity_id)
        return [ImageResponse.model_validate(img) for img in images]

    async def delete_image(self, image_id: UUID, owner_id: UUID) -> None:
        """Soft-delete an image after verifying ownership."""
        async with self._uow() as uow:
            image = await validate_image_ownership(image_id, owner_id, uow)
            await uow.media.images.soft_delete(image)
            await uow.commit()

    async def update_image_metadata(
        self,
        image_id: UUID,
        owner_id: UUID,
        data: object,  # ImageUpdate schema
    ) -> ImageResponse:
        async with self._uow() as uow:
            image = await validate_image_ownership(image_id, owner_id, uow)
            update_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            image = await uow.media.images.update(image, update_dict)
            await uow.commit()
        return ImageResponse.model_validate(image)

    # ── Admin moderation ──────────────────────────────────────────────────────

    async def moderate_image(
        self,
        image_id: UUID,
        admin_id: UUID,
        status: ModerationStatus,
        rejection_reason: str | None = None,
    ) -> ImageResponse:
        async with self._uow() as uow:
            image = await validate_image_exists(image_id, uow)
            update_payload: dict = {
                "moderation_status": status,
                "moderation_reviewed_by_id": admin_id,
                "moderation_reviewed_at": datetime.now(tz=timezone.utc),
            }
            if rejection_reason:
                update_payload["moderation_notes"] = rejection_reason
            if status == ModerationStatus.REJECTED:
                update_payload["media_status"] = MediaStatus.DELETED
            image = await uow.media.images.update(image, update_payload)
            await uow.commit()
        return ImageResponse.model_validate(image)

    async def list_pending_moderation(
        self,
        entity_type: str | None = None,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            images = await uow.media.images.find_pending_moderation(limit=limit + 1)
        responses = [ImageResponse.model_validate(img) for img in images]
        return _make_cursor_page(responses, limit)

    # =========================================================================
    # Videos
    # =========================================================================

    async def register_video_upload(
        self,
        owner_id: UUID,
        owner_type: str,
        data: VideoCreate,
    ) -> VideoUploadResponse:
        storage_key = generate_storage_key(
            owner_id,
            getattr(data, "entity_type", None) or owner_type,
            data.file_name or "upload",
        )
        async with self._uow() as uow:
            video = Video(
                owner_id=owner_id,
                owner_type=ImageOwnerType(owner_type) if isinstance(owner_type, str) else owner_type,
                url=build_public_url(storage_key, IMAGE_CDN_BASE_URL) or storage_key,
                storage_path=storage_key,
                original_filename=data.file_name,
                file_size_bytes=data.file_size_bytes or 0,
                mime_type=data.mime_type or "application/octet-stream",
                duration_seconds=data.duration_seconds or 0,
                width=data.width,
                height=data.height,
                usage=data.usage,
                media_status=MediaStatus.UPLOADING,
                moderation_status=ModerationStatus.PENDING,
                transcoding_status=VideoTranscodingStatus.NOT_STARTED,
                is_featured=data.is_primary,
                entity_type=getattr(data, "entity_type", None),
                entity_id=getattr(data, "entity_id", None),
            )
            video = await uow.media.videos.create(video)
            await uow.commit()

        return VideoUploadResponse(
            video_id=video.id,
            storage_key=storage_key,
            presigned_url_hint=f"STUB:presign:{storage_key}",
        )

    async def confirm_video_upload(
        self,
        video_id: UUID,
        owner_id: UUID,
    ) -> VideoResponse:
        """Transition video to ACTIVE and queue for transcoding."""
        async with self._uow() as uow:
            video = await validate_video_ownership(video_id, owner_id, uow)
            video = await uow.media.videos.update(video, {
                "media_status": MediaStatus.ACTIVE,
                "transcoding_status": VideoTranscodingStatus.QUEUED,
                "uploaded_at": datetime.now(tz=timezone.utc),
            })
            await uow.commit()
        return VideoResponse.model_validate(video)

    async def update_transcoding_status(
        self,
        video_id: UUID,
        status: VideoTranscodingStatus,
        thumbnail_url: str | None = None,
    ) -> VideoResponse:
        """Called by internal webhook/job when transcoding progresses."""
        async with self._uow() as uow:
            video = await validate_video_exists(video_id, uow)
            payload: dict = {"transcoding_status": status}
            if thumbnail_url:
                payload["thumbnail_url"] = thumbnail_url
            if status == VideoTranscodingStatus.COMPLETED:
                payload["transcoded_at"] = datetime.now(tz=timezone.utc)
            video = await uow.media.videos.update(video, payload)
            await uow.commit()
        return VideoResponse.model_validate(video)

    async def get_video(self, video_id: UUID) -> VideoResponse:
        async with self._uow() as uow:
            video = await validate_video_exists(video_id, uow)
        return VideoResponse.model_validate(video)

    async def list_videos_for_entity(
        self,
        entity_type: str,
        entity_id: UUID,
    ) -> list[VideoResponse]:
        async with self._uow() as uow:
            videos = await uow.media.videos.find_by_entity(entity_type, entity_id)
        return [VideoResponse.model_validate(v) for v in videos]

    async def delete_video(self, video_id: UUID, owner_id: UUID) -> None:
        async with self._uow() as uow:
            video = await validate_video_ownership(video_id, owner_id, uow)
            await uow.media.videos.soft_delete(video)
            await uow.commit()

    # =========================================================================
    # Memories
    # =========================================================================

    async def create_memory(
        self,
        user_id: UUID,
        data: MemoryCreate,
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = Memory(
                customer_id=user_id,
                celebration_id=data.celebration_id or uuid.uuid4(),  # requires valid FK in prod
                title=data.title,
                description=data.description,
                visibility=data.visibility,
                event_date=data.memory_date,
            )
            memory = await uow.media.memories.create(memory)
            await uow.commit()
        return MemoryResponse.model_validate(memory)

    async def get_memory(
        self,
        memory_id: UUID,
        requester_id: UUID | None = None,
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = await validate_memory_exists(memory_id, uow)

        if memory.visibility == MemoryVisibility.PRIVATE:
            if requester_id is None or memory.customer_id != requester_id:
                raise MemoryAccessDeniedError()

        return MemoryResponse.model_validate(memory)

    async def list_memories(
        self,
        user_id: UUID,
        cursor: str | None = None,
        limit: int = 20,
    ) -> CursorPage:
        async with self._uow() as uow:
            memories = await uow.media.memories.find_by_customer(
                user_id, limit=limit + 1
            )
        responses = [MemoryResponse.model_validate(m) for m in memories]
        return _make_cursor_page(responses, limit)

    async def update_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
        data: object,  # MemoryUpdate schema
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = await validate_memory_ownership(memory_id, user_id, uow)
            update_dict = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            memory = await uow.media.memories.update(memory, update_dict)
            await uow.commit()
        return MemoryResponse.model_validate(memory)

    async def delete_memory(self, memory_id: UUID, user_id: UUID) -> None:
        async with self._uow() as uow:
            memory = await validate_memory_ownership(memory_id, user_id, uow)
            await uow.media.memories.soft_delete(memory)
            await uow.commit()

    async def add_image_to_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
        image_id: UUID,
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = await validate_memory_ownership(memory_id, user_id, uow)
            image = await validate_image_exists(image_id, uow)

            # Link image to this memory via polymorphic attachment
            image = await uow.media.images.update(image, {
                "entity_type": "memory",
                "entity_id": memory_id,
            })
            # Increment denormalized count
            memory = await uow.media.memories.update(memory, {
                "image_count": memory.image_count + 1,
            })
            await uow.commit()
        return MemoryResponse.model_validate(memory)

    async def remove_image_from_memory(
        self,
        memory_id: UUID,
        user_id: UUID,
        image_id: UUID,
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = await validate_memory_ownership(memory_id, user_id, uow)
            image = await validate_image_exists(image_id, uow)

            # Detach image from this memory
            image = await uow.media.images.update(image, {
                "entity_type": None,
                "entity_id": None,
            })
            new_count = max(0, memory.image_count - 1)
            memory = await uow.media.memories.update(memory, {"image_count": new_count})
            await uow.commit()
        return MemoryResponse.model_validate(memory)

    async def set_memory_visibility(
        self,
        memory_id: UUID,
        user_id: UUID,
        visibility: MemoryVisibility,
    ) -> MemoryResponse:
        async with self._uow() as uow:
            memory = await validate_memory_ownership(memory_id, user_id, uow)
            payload: dict = {"visibility": visibility}
            if visibility in (MemoryVisibility.SHARED_LINK, MemoryVisibility.PUBLIC):
                if not memory.shared_token:
                    payload["shared_token"] = secrets.token_urlsafe(24)
                    payload["shared_at"] = datetime.now(tz=timezone.utc)
            memory = await uow.media.memories.update(memory, payload)
            await uow.commit()
        return MemoryResponse.model_validate(memory)
