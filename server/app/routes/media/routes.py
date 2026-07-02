"""
Media Routes — images, videos, and memory albums.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.media import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.media.response import (
    ImageResponse,
    MemoryResponse,
    VideoResponse,
)
from app.services.media.service import ImageUploadResponse, VideoUploadResponse

router = APIRouter(prefix="/media", tags=["Media"])

# ── Images — pending moderation (static, must precede /images/{image_id}) ────

router.add_api_route(
    "/images/pending-moderation",
    ctrl.list_pending_moderation,
    methods=["GET"],
    response_model=CursorPaginatedResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="List Pending Moderation (Admin)",
    description="Return a cursor-paginated list of images awaiting content moderation. Admin access required.",
    operation_id="media_list_pending_moderation",
)

# ── Images — entity listing (static, must precede /images/{image_id}) ────────

router.add_api_route(
    "/images/entity/{entity_id}",
    ctrl.list_images_for_entity,
    methods=["GET"],
    response_model=CursorPaginatedResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="List Images for Entity",
    description="Return cursor-paginated images attached to a given entity. Pass `entity_type` as a query parameter.",
    operation_id="media_list_images_for_entity",
)

# ── Images — direct upload (multipart) ────────────────────────────────────────

router.add_api_route(
    "/upload",
    ctrl.upload_image,
    methods=["POST"],
    response_model=SuccessResponse[ImageResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Upload Image",
    description=(
        "Upload an image file directly (multipart/form-data). Stores it via "
        "Cloudinary and returns the resulting public URL. Requires authentication."
    ),
    operation_id="media_upload_image",
)

# ── Images — upload flow ──────────────────────────────────────────────────────

router.add_api_route(
    "/images/register",
    ctrl.register_image_upload,
    methods=["POST"],
    response_model=SuccessResponse[ImageUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Image Upload",
    description="Register an image upload intent and receive a pre-signed upload URL.",
    operation_id="media_register_image_upload",
)

router.add_api_route(
    "/images/{image_id}/confirm",
    ctrl.confirm_image_upload,
    methods=["POST"],
    response_model=SuccessResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Confirm Image Upload",
    description="Confirm that the image has been successfully uploaded to storage.",
    operation_id="media_confirm_image_upload",
)

router.add_api_route(
    "/images/{image_id}/moderate",
    ctrl.moderate_image,
    methods=["POST"],
    response_model=SuccessResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Moderate Image (Admin)",
    description="Approve or reject an image after content review. Admin access required. Pass `approved` as a query parameter.",
    operation_id="media_moderate_image",
)

router.add_api_route(
    "/images/{image_id}",
    ctrl.get_image,
    methods=["GET"],
    response_model=SuccessResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Image",
    description="Return metadata for a single image by ID.",
    operation_id="media_get_image",
)

router.add_api_route(
    "/images/{image_id}",
    ctrl.update_image_metadata,
    methods=["PATCH"],
    response_model=SuccessResponse[ImageResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Image Metadata",
    description="Update alt text, caption, or other metadata on an image.",
    operation_id="media_update_image_metadata",
)

router.add_api_route(
    "/images/{image_id}",
    ctrl.delete_image,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Image",
    description="Soft-delete an image. User ownership or admin role required.",
    operation_id="media_delete_image",
)

# ── Videos — entity listing (static, must precede /videos/{video_id}) ────────

router.add_api_route(
    "/videos/entity/{entity_id}",
    ctrl.list_videos_for_entity,
    methods=["GET"],
    response_model=CursorPaginatedResponse[VideoResponse],
    status_code=status.HTTP_200_OK,
    summary="List Videos for Entity",
    description="Return cursor-paginated videos attached to a given entity. Pass `entity_type` as a query parameter.",
    operation_id="media_list_videos_for_entity",
)

# ── Videos — upload flow ──────────────────────────────────────────────────────

router.add_api_route(
    "/videos/register",
    ctrl.register_video_upload,
    methods=["POST"],
    response_model=SuccessResponse[VideoUploadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register Video Upload",
    description="Register a video upload intent and receive a pre-signed upload URL.",
    operation_id="media_register_video_upload",
)

router.add_api_route(
    "/videos/{video_id}/confirm",
    ctrl.confirm_video_upload,
    methods=["POST"],
    response_model=SuccessResponse[VideoResponse],
    status_code=status.HTTP_200_OK,
    summary="Confirm Video Upload",
    description="Confirm that the video has been successfully uploaded to storage.",
    operation_id="media_confirm_video_upload",
)

router.add_api_route(
    "/videos/{video_id}",
    ctrl.get_video,
    methods=["GET"],
    response_model=SuccessResponse[VideoResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Video",
    description="Return metadata for a single video by ID.",
    operation_id="media_get_video",
)

router.add_api_route(
    "/videos/{video_id}",
    ctrl.delete_video,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Video",
    description="Soft-delete a video. User ownership or admin role required.",
    operation_id="media_delete_video",
)

# ── Memories ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/memories",
    ctrl.list_memories,
    methods=["GET"],
    response_model=CursorPaginatedResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Memories",
    description="Return a cursor-paginated list of memory albums for the authenticated user.",
    operation_id="media_list_memories",
)

router.add_api_route(
    "/memories",
    ctrl.create_memory,
    methods=["POST"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Memory",
    description="Create a new memory album for the authenticated user.",
    operation_id="media_create_memory",
)

router.add_api_route(
    "/memories/{memory_id}",
    ctrl.get_memory,
    methods=["GET"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Memory",
    description="Return a single memory album by ID. Access is role-gated.",
    operation_id="media_get_memory",
)

router.add_api_route(
    "/memories/{memory_id}",
    ctrl.update_memory,
    methods=["PUT"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Memory",
    description="Update metadata on a memory album. User ownership required.",
    operation_id="media_update_memory",
)

router.add_api_route(
    "/memories/{memory_id}",
    ctrl.delete_memory,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Memory",
    description="Delete a memory album and dissociate its images. User ownership required.",
    operation_id="media_delete_memory",
)

router.add_api_route(
    "/memories/{memory_id}/images/{image_id}",
    ctrl.add_image_to_memory,
    methods=["POST"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Add Image to Memory",
    description="Associate an existing image with a memory album.",
    operation_id="media_add_image_to_memory",
)

router.add_api_route(
    "/memories/{memory_id}/images/{image_id}",
    ctrl.remove_image_from_memory,
    methods=["DELETE"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Remove Image from Memory",
    description="Dissociate an image from a memory album.",
    operation_id="media_remove_image_from_memory",
)

router.add_api_route(
    "/memories/{memory_id}/visibility",
    ctrl.set_memory_visibility,
    methods=["PATCH"],
    response_model=SuccessResponse[MemoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Set Memory Visibility",
    description="Toggle a memory album between public and private. Pass `is_public` as a query parameter.",
    operation_id="media_set_memory_visibility",
)
