"""
Bookings Controller — booking lifecycle, assignments, cancellations, reschedules, and invoices.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import BookingServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep, CurrentVendorIdDep
from app.models.enums import UserRole
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
