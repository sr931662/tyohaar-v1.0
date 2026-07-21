"""
Media Controller — images, videos, and memory albums.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.config import settings
from app.core.current_user import CurrentUserDep
from app.core.dependencies import MediaServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.models.enums import MediaUsage, UserRole
from app.models.media.image import ImageOwnerType
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
from app.schemas.media.update import ImageMetadataUpdate, MemoryUpdate, VideoMetadataUpdate
from app.services.media.service import ImageUploadResponse, VideoUploadResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── Images ────────────────────────────────────────────────────────────────────

_OWNER_TYPE_BY_ROLE = {
    UserRole.VENDOR: ImageOwnerType.VENDOR,
    UserRole.ADMIN: ImageOwnerType.ADMIN,
    UserRole.SUPER_ADMIN: ImageOwnerType.ADMIN,
}


_ALLOWED_DOCUMENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


async def upload_image(
    current_user: CurrentUserDep,
    service: MediaServiceDep,
    file: UploadFile = File(..., description="Image or document file to upload."),
    usage: MediaUsage = Form(..., description="Feature context, e.g. package_image."),
    entity_type: str | None = Form(default=None),
    entity_id: uuid.UUID | None = Form(default=None),
) -> SuccessResponse[ImageResponse]:
    content_type = file.content_type or ""
    is_image = content_type.startswith("image/")
    is_document = content_type in _ALLOWED_DOCUMENT_TYPES
    if not (is_image or is_document):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only image or document (PDF/Word) files are accepted.",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.",
        )

    owner_type = _OWNER_TYPE_BY_ROLE.get(current_user.role, ImageOwnerType.USER)

    result = await service.upload_image(
        owner_id=current_user.id,
        owner_type=owner_type,
        usage=usage,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        content_type=content_type or "application/octet-stream",
        entity_type=entity_type,
        entity_id=entity_id,
        resource_type="image" if is_image else "raw",
    )
    return SuccessResponse(data=result, message="File uploaded.")


async def register_image_upload(
    body: ImageUploadRegisterCreate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageUploadResponse]:
    owner_type = _OWNER_TYPE_BY_ROLE.get(current_user.role, ImageOwnerType.USER)
    result = await service.register_image_upload(
        owner_id=current_user.id, owner_type=owner_type, data=body
    )
    return SuccessResponse(data=result, message="Image upload registered.")


async def confirm_image_upload(
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.confirm_image_upload(
        image_id=image_id, owner_id=current_user.id
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
    service: MediaServiceDep,
) -> SuccessResponse[list[ImageResponse]]:
    images = await service.list_images_for_entity(entity_type=entity_type, entity_id=entity_id)
    return SuccessResponse(data=images, message="Images retrieved.")


async def delete_image(
    image_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[None]:
    await service.delete_image(image_id=image_id, owner_id=current_user.id)
    return SuccessResponse(data=None, message="Image deleted.")


async def update_image_metadata(
    image_id: uuid.UUID,
    body: ImageMetadataUpdate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    result = await service.update_image_metadata(
        image_id=image_id, owner_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Image metadata updated.")


async def moderate_image(
    image_id: uuid.UUID,
    approved: bool,
    current_user: AdminDep,
    service: MediaServiceDep,
) -> SuccessResponse[ImageResponse]:
    from app.models.media.image import ModerationStatus

    result = await service.moderate_image(
        image_id=image_id,
        admin_id=current_user.id,
        status=ModerationStatus.APPROVED if approved else ModerationStatus.REJECTED,
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
    owner_type = _OWNER_TYPE_BY_ROLE.get(current_user.role, ImageOwnerType.USER)
    result = await service.register_video_upload(
        owner_id=current_user.id, owner_type=owner_type, data=body
    )
    return SuccessResponse(data=result, message="Video upload registered.")


async def confirm_video_upload(
    video_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[VideoResponse]:
    result = await service.confirm_video_upload(
        video_id=video_id, owner_id=current_user.id
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
    service: MediaServiceDep,
) -> SuccessResponse[list[VideoResponse]]:
    videos = await service.list_videos_for_entity(entity_type=entity_type, entity_id=entity_id)
    return SuccessResponse(data=videos, message="Videos retrieved.")


async def delete_video(
    video_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[None]:
    await service.delete_video(video_id=video_id, owner_id=current_user.id)
    return SuccessResponse(data=None, message="Video deleted.")


async def update_video_metadata(
    video_id: uuid.UUID,
    body: VideoMetadataUpdate,
    current_user: CurrentUserDep,
    service: MediaServiceDep,
) -> SuccessResponse[VideoResponse]:
    result = await service.update_video_metadata(
        video_id=video_id, owner_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Video metadata updated.")


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
