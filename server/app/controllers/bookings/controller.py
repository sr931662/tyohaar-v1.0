"""
Bookings Controller — booking lifecycle, assignments, cancellations, reschedules, and invoices.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, File, HTTPException, Query, UploadFile, status as http_status

from app.core.config import settings
from app.core.current_user import CurrentUserDep
from app.core.dependencies import BookingServiceDep, MediaServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep, CurrentVendorIdDep
from app.models.enums import MediaUsage, UserRole
from app.models.media.image import ImageOwnerType
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.bookings import (
    BookingAssignmentInternal,
    BookingCancellationCreate,
    BookingCancellationResponse,
    BookingCreate,
    BookingDetailResponse,
    BookingFilters,
    BookingInvoiceResponse,
    BookingItemPrepTimeUpdate,
    BookingItemResponse,
    BookingMediaSummary,
    BookingPSTUpdate,
    BookingRescheduleCreate,
    BookingRescheduleResponse,
    BookingResponse,
    BookingStatusHistoryResponse,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def create_booking(
    body: BookingCreate,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.create_booking(customer_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Booking created.")


async def get_booking(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingDetailResponse]:
    result = await service.get_booking(
        booking_id=booking_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=result, message="Booking retrieved.")


async def list_bookings(
    current_user: CurrentUserDep,
    filters: Annotated[BookingFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: BookingServiceDep,
) -> CursorPaginatedResponse[BookingResponse]:
    # Admins see all bookings; customers see only their own
    is_admin = current_user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN)
    page = await service.list_bookings(
        customer_id=None if is_admin else current_user.id,
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def list_vendor_bookings(
    vendor_id: CurrentVendorIdDep,
    filters: Annotated[BookingFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: BookingServiceDep,
) -> CursorPaginatedResponse[BookingResponse]:
    page = await service.list_vendor_bookings(
        vendor_id=vendor_id,
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def confirm_booking(
    booking_id: uuid.UUID,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.confirm_booking(booking_id=booking_id, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Booking confirmed.")


async def start_booking(
    booking_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.start_booking(booking_id=booking_id, vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Service started.")


async def complete_booking(
    booking_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.complete_booking(booking_id=booking_id, vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Booking completed.")


async def assign_vendor(
    booking_id: uuid.UUID,
    item_id: uuid.UUID,
    vendor_id: uuid.UUID,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingAssignmentInternal]:
    result = await service.assign_vendor(
        booking_id=booking_id,
        item_id=item_id,
        vendor_id=vendor_id,
        admin_id=current_user.id,
    )
    return SuccessResponse(data=result, message="Vendor assigned.")


async def unassign_vendor(
    booking_id: uuid.UUID,
    assignment_id: uuid.UUID,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[None]:
    await service.unassign_vendor(
        booking_id=booking_id,
        assignment_id=assignment_id,
        admin_id=current_user.id,
    )
    return SuccessResponse(data=None, message="Vendor unassigned.")


async def update_booking_item_prep_time(
    booking_id: uuid.UUID,
    item_id: uuid.UUID,
    body: BookingItemPrepTimeUpdate,
    vendor_id: CurrentVendorIdDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingItemResponse]:
    result = await service.update_booking_item_prep_time(
        booking_id=booking_id,
        item_id=item_id,
        vendor_id=vendor_id,
        prep_time_minutes=body.prep_time_minutes,
    )
    return SuccessResponse(data=result, message="Prep time updated.")


async def update_pst(
    booking_id: uuid.UUID,
    body: BookingPSTUpdate,
    vendor_id: CurrentVendorIdDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.update_pst(
        booking_id=booking_id,
        vendor_id=vendor_id,
        pst_at=body.preparation_start_at,
    )
    return SuccessResponse(data=result, message="Preparation Starting Time updated.")


async def request_cancellation(
    booking_id: uuid.UUID,
    body: BookingCancellationCreate,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingCancellationResponse]:
    result = await service.request_cancellation(
        booking_id=booking_id, customer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Cancellation request submitted.")


async def process_cancellation(
    booking_id: uuid.UUID,
    approved: bool,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.process_cancellation(
        booking_id=booking_id, admin_id=current_user.id, approved=approved
    )
    return SuccessResponse(data=result, message="Cancellation processed.")


async def request_reschedule(
    booking_id: uuid.UUID,
    body: BookingRescheduleCreate,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingRescheduleResponse]:
    result = await service.request_reschedule(
        booking_id=booking_id, customer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Reschedule request submitted.")


async def process_reschedule(
    booking_id: uuid.UUID,
    reschedule_id: uuid.UUID,
    approved: bool,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingResponse]:
    result = await service.process_reschedule(
        booking_id=booking_id,
        reschedule_id=reschedule_id,
        admin_id=current_user.id,
        approved=approved,
    )
    return SuccessResponse(data=result, message="Reschedule processed.")


async def get_booking_history(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[list[dict]]:
    history = await service.get_booking_history(
        booking_id=booking_id,
        requester_id=current_user.id,
        requester_role=current_user.role.value,
    )
    return SuccessResponse(data=history, message="Booking history retrieved.")


async def get_booking_status_history(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[list[BookingStatusHistoryResponse]]:
    records = await service.get_booking_status_history(booking_id=booking_id)
    return SuccessResponse(data=records, message="Status history retrieved.")


async def get_booking_invoice(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingInvoiceResponse]:
    result = await service.get_booking_invoice(
        booking_id=booking_id, customer_id=current_user.id
    )
    return SuccessResponse(data=result, message="Invoice retrieved.")


async def generate_booking_invoice(
    booking_id: uuid.UUID,
    current_user: AdminDep,
    service: BookingServiceDep,
) -> SuccessResponse[BookingInvoiceResponse]:
    result = await service.generate_booking_invoice(
        booking_id=booking_id, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Invoice generated.")


# ── Multimedia (vendor-uploaded event media) ───────────────────────────────────

async def list_vendor_booking_media(
    vendor_id: CurrentVendorIdDep,
    service: BookingServiceDep,
) -> SuccessResponse[list[BookingMediaSummary]]:
    result = await service.list_vendor_booking_media(vendor_id=vendor_id)
    return SuccessResponse(data=result, message="Bookings retrieved.")


async def list_admin_booking_media(
    service: BookingServiceDep,
    _admin: AdminDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> SuccessResponse:
    skip = (page - 1) * page_size
    items, total = await service.list_admin_booking_media(skip=skip, limit=page_size)
    total_pages = max((total + page_size - 1) // page_size, 1)
    return SuccessResponse(data={
        "items": items,
        "total": total,
        "page": page,
        "per_page": page_size,
        "pages": total_pages,
    })


async def _upload_booking_media_file(
    *,
    booking_id: uuid.UUID,
    vendor_id: uuid.UUID,
    current_user: CurrentUserDep,
    booking_service,
    media_service,
    file: UploadFile,
    resource_type: str,
):
    await booking_service.assert_vendor_media_upload_allowed(
        booking_id=booking_id, vendor_id=vendor_id
    )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=http_status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB upload limit.",
        )

    if resource_type == "image":
        return await media_service.upload_image(
            owner_id=current_user.id,
            owner_type=ImageOwnerType.VENDOR,
            usage=MediaUsage.BOOKING_EVIDENCE,
            file_bytes=file_bytes,
            filename=file.filename or "upload",
            content_type=file.content_type or "application/octet-stream",
            entity_type="booking",
            entity_id=booking_id,
            resource_type="image",
        )
    return await media_service.upload_video(
        owner_id=current_user.id,
        owner_type=ImageOwnerType.VENDOR,
        usage=MediaUsage.BOOKING_EVIDENCE,
        file_bytes=file_bytes,
        filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        entity_type="booking",
        entity_id=booking_id,
    )


async def upload_booking_image(
    booking_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    current_user: CurrentUserDep,
    booking_service: BookingServiceDep,
    media_service: MediaServiceDep,
    file: UploadFile = File(..., description="Event photo to upload."),
) -> SuccessResponse:
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only image files are accepted here.",
        )
    result = await _upload_booking_media_file(
        booking_id=booking_id,
        vendor_id=vendor_id,
        current_user=current_user,
        booking_service=booking_service,
        media_service=media_service,
        file=file,
        resource_type="image",
    )
    return SuccessResponse(data=result, message="Event photo uploaded.")


async def upload_booking_video(
    booking_id: uuid.UUID,
    vendor_id: CurrentVendorIdDep,
    current_user: CurrentUserDep,
    booking_service: BookingServiceDep,
    media_service: MediaServiceDep,
    file: UploadFile = File(..., description="Event video to upload."),
) -> SuccessResponse:
    content_type = file.content_type or ""
    if not content_type.startswith("video/"):
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only video files are accepted here.",
        )
    result = await _upload_booking_media_file(
        booking_id=booking_id,
        vendor_id=vendor_id,
        current_user=current_user,
        booking_service=booking_service,
        media_service=media_service,
        file=file,
        resource_type="video",
    )
    return SuccessResponse(data=result, message="Event video uploaded.")
