"""
Media Controller — images, videos, and memory albums.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Query

from app.core.current_user import CurrentUserDep
from app.core.dependencies import MediaServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.media.create import (
    ImageUploadRegisterCreate,
    MemoryCreate,
    VideoUploadRegisterCreate,
)
from app.schemas.media.response import (
    ImageResponse,
    MemoryResponse,
    VideoResponse,
)
from app.schemas.media.update import ImageMetadataUpdate, MemoryUpdate
from app.services.media.service import ImageUploadResponse, VideoUploadResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Images ────────────────────────────────────────────────────────────────────

async def register_image_upload(
    body: ImageUploadRegisterCreate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageUploadResponse]:
    result = await service.register_image_upload(uploader_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Image upload registered.")


async def confirm_image_upload(
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.confirm_image_upload(
        image_id=image_id, uploader_id=current_user.id
    )
    return SuccessResponse(data=result, message="Image upload confirmed.")


async def get_image(
    image_id: uuid.UUID,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.get_image(image_id=image_id)
    return SuccessResponse(data=result, message="Image retrieved.")


async def list_images_for_entity(
    entity_id: uuid.UUID,
    entity_type: str,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: MediaServiceDep,
) -> CursorPaginatedResponse[ImageResponse]:
    page = await service.list_images_for_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def delete_image(
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[None]:
    await service.delete_image(
        image_id=image_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=None, message="Image deleted.")


async def update_image_metadata(
    image_id: uuid.UUID,
    body: ImageMetadataUpdate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.update_image_metadata(
        image_id=image_id, uploader_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Image metadata updated.")


async def moderate_image(
    image_id: uuid.UUID,
    approved: bool,
    current_user: AdminDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.moderate_image(
        image_id=image_id, admin_id=current_user.id, approved=approved
    )
    return SuccessResponse(data=result, message="Image moderated.")


async def list_pending_moderation(
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: MediaServiceDep,
) -> CursorPaginatedResponse[ImageResponse]:
    page = await service.list_pending_moderation(
        cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


# ── Videos ────────────────────────────────────────────────────────────────────

async def register_video_upload(
    body: VideoUploadRegisterCreate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[VideoUploadResponse]:
    result = await service.register_video_upload(uploader_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Video upload registered.")


async def confirm_video_upload(
    video_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[VideoResponse]:
    result = await service.confirm_video_upload(
        video_id=video_id, uploader_id=current_user.id
    )
    return SuccessResponse(data=result, message="Video upload confirmed.")


async def get_video(
    video_id: uuid.UUID,
    service: MediaServiceDep,
) -> SuccessResponse[VideoResponse]:
    result = await service.get_video(video_id=video_id)
    return SuccessResponse(data=result, message="Video retrieved.")


async def list_videos_for_entity(
    entity_id: uuid.UUID,
    entity_type: str,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: MediaServiceDep,
) -> CursorPaginatedResponse[VideoResponse]:
    page = await service.list_videos_for_entity(
        entity_id=entity_id,
        entity_type=entity_type,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def delete_video(
    video_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[None]:
    await service.delete_video(
        video_id=video_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=None, message="Video deleted.")


# ── Memories ──────────────────────────────────────────────────────────────────

async def create_memory(
    body: MemoryCreate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[MemoryResponse]:
    result = await service.create_memory(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Memory created.")


async def get_memory(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[MemoryResponse]:
    result = await service.get_memory(
        memory_id=memory_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=result, message="Memory retrieved.")


async def list_memories(
    current_user: CurrentUserDep,
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: MediaServiceDep,
) -> CursorPaginatedResponse[MemoryResponse]:
    page = await service.list_memories(
        user_id=current_user.id, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def update_memory(
    memory_id: uuid.UUID,
    body: MemoryUpdate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[MemoryResponse]:
    result = await service.update_memory(
        memory_id=memory_id, user_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Memory updated.")


async def delete_memory(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[None]:
    await service.delete_memory(memory_id=memory_id, user_id=current_user.id)
    return SuccessResponse(data=None, message="Memory deleted.")


async def add_image_to_memory(
    memory_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[MemoryResponse]:
    result = await service.add_image_to_memory(
        memory_id=memory_id, image_id=image_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Image added to memory.")


async def remove_image_from_memory(
    memory_id: uuid.UUID,
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[MemoryResponse]:
    result = await service.remove_image_from_memory(
        memory_id=memory_id, image_id=image_id, user_id=current_user.id
    )
    return SuccessResponse(data=result, message="Image removed from memory.")


async def set_memory_visibility(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
    is_public: bool = Query(...),
) -> SuccessResponse[MemoryResponse]:
    result = await service.set_memory_visibility(
        memory_id=memory_id, user_id=current_user.id, is_public=is_public
    )
    return SuccessResponse(data=result, message="Memory visibility updated.")
