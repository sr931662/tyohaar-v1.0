"""
Bookings Routes — booking lifecycle, assignments, cancellations, reschedules, and invoices.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.bookings import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.bookings import (
    BookingAssignmentInternal,
    BookingCancellationResponse,
    BookingDetailResponse,
    BookingInvoiceResponse,
    BookingItemResponse,
    BookingRescheduleResponse,
    BookingResponse,
    BookingStatusHistoryResponse,
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])

# ── Core booking CRUD ─────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.create_booking,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Booking",
    description="Create a new service booking for the authenticated customer.",
    operation_id="bookings_create_booking",
)

router.add_api_route(
    "",
    ctrl.list_bookings,
    methods=["GET"],
    response_model=CursorPaginatedResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Bookings",
    description="Return a cursor-paginated list of bookings for the authenticated customer.",
    operation_id="bookings_list_bookings",
)

router.add_api_route(
    "/vendor",
    ctrl.list_vendor_bookings,
    methods=["GET"],
    response_model=CursorPaginatedResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="List Vendor Bookings",
    description="Return a cursor-paginated list of bookings assigned to the authenticated vendor.",
    operation_id="bookings_list_vendor_bookings",
)

router.add_api_route(
    "/{booking_id}",
    ctrl.get_booking,
    methods=["GET"],
    response_model=SuccessResponse[BookingDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Booking",
    description="Return full details for a single booking. Access is role-gated (customer, vendor, admin).",
    operation_id="bookings_get_booking",
)

# ── Status transitions ────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/confirm",
    ctrl.confirm_booking,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Confirm Booking (Admin)",
    description="Confirm a pending booking. Admin access required.",
    operation_id="bookings_confirm_booking",
)

router.add_api_route(
    "/{booking_id}/start",
    ctrl.start_booking,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Start Service",
    description="Mark the booking service as started. Vendor role required.",
    operation_id="bookings_start_booking",
)

router.add_api_route(
    "/{booking_id}/complete",
    ctrl.complete_booking,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Complete Service",
    description="Mark the booking service as completed. Vendor role required.",
    operation_id="bookings_complete_booking",
)

# ── Vendor assignments ────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/items/{item_id}/assignments/{vendor_id}",
    ctrl.assign_vendor,
    methods=["POST"],
    response_model=SuccessResponse[BookingAssignmentInternal],
    status_code=status.HTTP_201_CREATED,
    summary="Assign Vendor to Booking Item (Admin)",
    description="Assign a vendor to a specific item within a booking. Admin access required.",
    operation_id="bookings_assign_vendor",
)

router.add_api_route(
    "/{booking_id}/assignments/{assignment_id}",
    ctrl.unassign_vendor,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Unassign Vendor (Admin)",
    description="Remove a vendor assignment from a booking. Admin access required.",
    operation_id="bookings_unassign_vendor",
)

router.add_api_route(
    "/{booking_id}/items/{item_id}/prep-time",
    ctrl.update_booking_item_prep_time,
    methods=["PATCH"],
    response_model=SuccessResponse[BookingItemResponse],
    status_code=status.HTTP_200_OK,
    summary="Set Booking Item Prep Time (Vendor)",
    description="Vendor sets/updates the setup/prep time required before this item's "
                "scheduled start. Requires the calling vendor to be assigned to the item.",
    operation_id="bookings_update_booking_item_prep_time",
)

# ── Cancellations ─────────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/cancellation",
    ctrl.request_cancellation,
    methods=["POST"],
    response_model=SuccessResponse[BookingCancellationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request Cancellation",
    description="Submit a cancellation request for a booking.",
    operation_id="bookings_request_cancellation",
)

router.add_api_route(
    "/{booking_id}/cancellation/process",
    ctrl.process_cancellation,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Process Cancellation (Admin)",
    description="Approve or reject a pending cancellation request. Admin access required. Pass `approved` as a query parameter.",
    operation_id="bookings_process_cancellation",
)

# ── Reschedules ───────────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/reschedule",
    ctrl.request_reschedule,
    methods=["POST"],
    response_model=SuccessResponse[BookingRescheduleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Request Reschedule",
    description="Submit a reschedule request for an existing booking.",
    operation_id="bookings_request_reschedule",
)

router.add_api_route(
    "/{booking_id}/reschedules/{reschedule_id}/process",
    ctrl.process_reschedule,
    methods=["POST"],
    response_model=SuccessResponse[BookingResponse],
    status_code=status.HTTP_200_OK,
    summary="Process Reschedule (Admin)",
    description="Approve or reject a pending reschedule request. Admin access required. Pass `approved` as a query parameter.",
    operation_id="bookings_process_reschedule",
)

# ── History ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/history",
    ctrl.get_booking_history,
    methods=["GET"],
    response_model=SuccessResponse[list[dict]],
    status_code=status.HTTP_200_OK,
    summary="Get Booking History",
    description="Return the full event log for a booking. Access is role-gated.",
    operation_id="bookings_get_booking_history",
)

router.add_api_route(
    "/{booking_id}/status-history",
    ctrl.get_booking_status_history,
    methods=["GET"],
    response_model=SuccessResponse[list[BookingStatusHistoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="Get Status History",
    description="Return the chronological status-transition log for a booking.",
    operation_id="bookings_get_booking_status_history",
)

# ── Invoice ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/{booking_id}/invoice",
    ctrl.get_booking_invoice,
    methods=["GET"],
    response_model=SuccessResponse[BookingInvoiceResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Booking Invoice",
    description="Return the invoice for a completed booking. Customer ownership required.",
    operation_id="bookings_get_booking_invoice",
)

router.add_api_route(
    "/{booking_id}/invoice",
    ctrl.generate_booking_invoice,
    methods=["POST"],
    response_model=SuccessResponse[BookingInvoiceResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Booking Invoice (Admin)",
    description="Generate and persist an invoice for a booking. Admin access required.",
    operation_id="bookings_generate_booking_invoice",
)
