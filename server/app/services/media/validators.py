"""Media domain — async validator helpers that operate inside a UnitOfWork."""

from __future__ import annotations

import uuid

from app.models.media.image import Image
from app.models.media.memory import Memory
from app.models.media.video import Video
from app.repositories.unit_of_work import UnitOfWork
from app.services.media.constants import MAX_IMAGES_PER_ENTITY
from app.services.media.exceptions import (
    ImageCountLimitError,
    ImageNotFoundError,
    ImageOwnershipError,
    MemoryNotFoundError,
    MemoryOwnershipError,
    VideoNotFoundError,
    VideoOwnershipError,
)


async def validate_image_exists(image_id: uuid.UUID, uow: UnitOfWork) -> Image:
    """Fetch an image by ID or raise ImageNotFoundError."""
    image = await uow.media.images.get_by_id(image_id)
    if image is None:
        raise ImageNotFoundError(str(image_id))
    return image


async def validate_image_ownership(
    image_id: uuid.UUID,
    owner_id: uuid.UUID,
    uow: UnitOfWork,
) -> Image:
    """Fetch image and verify owner_id matches or raise ImageOwnershipError."""
    image = await validate_image_exists(image_id, uow)
    if image.owner_id != owner_id:
        raise ImageOwnershipError()
    return image


async def validate_video_exists(video_id: uuid.UUID, uow: UnitOfWork) -> Video:
    """Fetch a video by ID or raise VideoNotFoundError."""
    video = await uow.media.videos.get_by_id(video_id)
    if video is None:
        raise VideoNotFoundError(str(video_id))
    return video


async def validate_video_ownership(
    video_id: uuid.UUID,
    owner_id: uuid.UUID,
    uow: UnitOfWork,
) -> Video:
    """Fetch video and verify owner_id matches or raise VideoOwnershipError."""
    video = await validate_video_exists(video_id, uow)
    if video.owner_id != owner_id:
        raise VideoOwnershipError()
    return video


async def validate_memory_exists(memory_id: uuid.UUID, uow: UnitOfWork) -> Memory:
    """Fetch a memory by ID or raise MemoryNotFoundError."""
    memory = await uow.media.memories.get_by_id(memory_id)
    if memory is None:
        raise MemoryNotFoundError(str(memory_id))
    return memory


async def validate_memory_ownership(
    memory_id: uuid.UUID,
    owner_id: uuid.UUID,
    uow: UnitOfWork,
) -> Memory:
    """Fetch memory and verify customer_id matches or raise MemoryOwnershipError."""
    memory = await validate_memory_exists(memory_id, uow)
    if memory.customer_id != owner_id:
        raise MemoryOwnershipError()
    return memory


async def validate_image_count_for_entity(
    entity_type: str,
    entity_id: uuid.UUID,
    uow: UnitOfWork,
) -> None:
    """Raise ImageCountLimitError when the entity has reached MAX_IMAGES_PER_ENTITY."""
    count = await uow.media.images.count(
        uow.media.images._model.entity_type == entity_type,  # type: ignore[attr-defined]
        uow.media.images._model.entity_id == entity_id,  # type: ignore[attr-defined]
    )
    if count >= MAX_IMAGES_PER_ENTITY:
        raise ImageCountLimitError(MAX_IMAGES_PER_ENTITY)
