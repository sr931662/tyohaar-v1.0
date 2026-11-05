"""
Events Routes — invitation management.

  * /events…                 the organiser, always scoped to their own events
  * /bookings/vendor/…       a vendor's view of the summary an organiser approved
  * /i/{token}               the guest's invitation page (root path, no API prefix)
  * /i/_api/…                what that page's script calls, token in a header

Public and protected routes are on separate routers so a guest route can never
inherit an organiser dependency by accident, or the reverse.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.controllers.events import controller as ctrl
from app.core.rate_limit import (
    INVITE_CLAIM_RATE_LIMIT,
    INVITE_PAGE_RATE_LIMIT,
    PUBLIC_INVITE_RATE_LIMIT,
    rate_limit,
)
from app.core.responses import PaginatedResponse, SuccessResponse
from app.schemas.events import (
    ActivityItem,
    EventAnalytics,
    EventDetail,
    EventList,
    FoodSummary,
    FunctionResponse,
    GuestGroupResponse,
    ImportResult,
    PreviewLink,
    PublicClaimResult,
    PublicInvitationPage,
    ReminderCandidates,
    RSVPRow,
    VendorGuestSummary,
)

router = APIRouter(tags=["Events"])
guest_page_router = APIRouter(tags=["Guest invitation"])

_page_limit = [Depends(rate_limit(INVITE_PAGE_RATE_LIMIT))]
_api_limit = [Depends(rate_limit(PUBLIC_INVITE_RATE_LIMIT))]
_claim_limit = [Depends(rate_limit(INVITE_CLAIM_RATE_LIMIT))]


def _route(r: APIRouter, path: str, endpoint, methods: list[str], model=None, code=status.HTTP_200_OK, summary="", **kw):
    r.add_api_route(
        path, endpoint, methods=methods, response_model=model, status_code=code, summary=summary,
        operation_id=f"events_{endpoint.__name__}", **kw,
    )


_E = "/events/{celebration_id}"

_route(router, "/events", ctrl.list_events, ["GET"], SuccessResponse[EventList],
       summary="The customer's events: upcoming, ongoing, completed")
_route(router, "/events", ctrl.create_event, ["POST"], SuccessResponse[EventDetail], status.HTTP_201_CREATED,
       summary="Create an independently organised event (no booking needed)")
_route(router, _E, ctrl.get_event, ["GET"], SuccessResponse[EventDetail], summary="Event with functions, settings, entitlements")
_route(router, _E, ctrl.update_event, ["PATCH"], SuccessResponse[EventDetail],
       summary="Edit event details; a booked event's date and venue are locked")

_route(router, f"{_E}/invitation", ctrl.update_invitation_settings, ["PUT"], SuccessResponse[EventDetail],
       summary="Design, RSVP questions, display overrides, reminder rules")
_route(router, f"{_E}/invitation/publish", ctrl.publish_invitation, ["POST"], SuccessResponse[EventDetail],
       summary="Make the invitation visible to guests")
_route(router, f"{_E}/invitation/unpublish", ctrl.unpublish_invitation, ["POST"], SuccessResponse[EventDetail],
       summary="Hide the invitation from guests")
_route(router, f"{_E}/invitation/general-link", ctrl.update_general_link, ["PUT"], SuccessResponse[EventDetail],
       summary="Turn the shareable general link on or off, or replace it")
_route(router, f"{_E}/invitation/preview-link", ctrl.invitation_preview_link, ["POST"], SuccessResponse[PreviewLink],
       summary="Short-lived link to see the guest page before publishing")

_route(router, f"{_E}/functions", ctrl.create_function, ["POST"], SuccessResponse[FunctionResponse], status.HTTP_201_CREATED,
       summary="Add a function")
_route(router, f"{_E}/functions/reorder", ctrl.reorder_functions, ["PUT"], SuccessResponse[list[FunctionResponse]],
       summary="Set the order of functions")
_route(router, f"{_E}/functions/guests", ctrl.set_guest_functions, ["PUT"], SuccessResponse[int],
       summary="Choose which functions these guests are invited to")
_route(router, f"{_E}/functions/{{function_id}}", ctrl.update_function, ["PATCH"], SuccessResponse[FunctionResponse],
       summary="Edit or cancel a function")
_route(router, f"{_E}/functions/{{function_id}}", ctrl.delete_function, ["DELETE"], None, status.HTTP_204_NO_CONTENT,
       summary="Remove a function nobody has answered for")

_route(router, f"{_E}/groups", ctrl.create_group, ["POST"], SuccessResponse[list[GuestGroupResponse]], status.HTTP_201_CREATED,
       summary="Create a household")
_route(router, f"{_E}/groups/{{group_id}}", ctrl.update_group, ["PATCH"], SuccessResponse[list[GuestGroupResponse]],
       summary="Edit a household")
_route(router, f"{_E}/groups/{{group_id}}", ctrl.delete_group, ["DELETE"], None, status.HTTP_204_NO_CONTENT,
       summary="Dissolve a household; its guests stay")
_route(router, f"{_E}/guests/import", ctrl.import_guests, ["POST"], SuccessResponse[ImportResult],
       summary="Import guests from CSV or Excel; per-row results")

_route(router, f"{_E}/analytics", ctrl.event_analytics, ["GET"], SuccessResponse[EventAnalytics],
       summary="Invitation funnel and function-wise numbers")
_route(router, f"{_E}/rsvps", ctrl.list_rsvps, ["GET"], PaginatedResponse[RSVPRow], summary="Per-function responses")
_route(router, f"{_E}/food", ctrl.food_summary, ["GET"], SuccessResponse[FoodSummary], summary="Food preferences by function")
_route(router, f"{_E}/food/report.csv", ctrl.food_report, ["GET"], None, summary="Download the food report")
_route(router, f"{_E}/activity", ctrl.event_activity, ["GET"], PaginatedResponse[ActivityItem], summary="Invitation activity")
_route(router, f"{_E}/reminders", ctrl.reminder_candidates, ["GET"], SuccessResponse[ReminderCandidates],
       summary="Guests who haven't answered, and why each is due")
_route(router, f"{_E}/reminders/record", ctrl.record_reminders, ["POST"], SuccessResponse[int],
       summary="Log reminders the host sent from their own device")
_route(router, f"{_E}/operations-summary", ctrl.approve_operations_summary, ["POST"], SuccessResponse[FoodSummary],
       summary="Approve a guest-count and food summary for this booking's vendors")
_route(router, "/bookings/vendor/{booking_id}/guest-summary", ctrl.vendor_guest_summary, ["GET"],
       SuccessResponse[VendorGuestSummary | None], summary="The approved aggregate summary; no guest details")

# ── Guest ─────────────────────────────────────────────────────────────────────
# Static segments first: tokens must never capture /i/_api or /i/preview.

_route(guest_page_router, "/i/_api/view", ctrl.guest_view, ["GET"], SuccessResponse[PublicInvitationPage],
       summary="The invitation (X-Invite-Token)", dependencies=_api_limit)
_route(guest_page_router, "/i/_api/preview", ctrl.guest_preview, ["GET"], SuccessResponse[PublicInvitationPage],
       summary="Organiser's preview (X-Invite-Token)", dependencies=_api_limit)
_route(guest_page_router, "/i/_api/activity", ctrl.guest_activity, ["POST"], None, status.HTTP_204_NO_CONTENT,
       summary="The guest started answering (X-Invite-Token)", dependencies=_api_limit)
_route(guest_page_router, "/i/_api/rsvp", ctrl.guest_rsvp, ["POST"], SuccessResponse[PublicInvitationPage],
       summary="Submit or change a response (X-Invite-Token)", dependencies=_api_limit)
_route(guest_page_router, "/i/_api/claim", ctrl.guest_claim, ["POST"], SuccessResponse[PublicClaimResult],
       summary="Identify yourself on a general link (X-Invite-Token)", dependencies=_claim_limit)
_route(guest_page_router, "/i/_font/{name}", ctrl.guest_font, ["GET"], None,
       summary="Self-hosted invitation font", include_in_schema=False)
_route(guest_page_router, "/i/preview/{token}", ctrl.guest_preview_page, ["GET"], None,
       summary="Organiser's preview page", response_class=HTMLResponse, include_in_schema=False)
_route(guest_page_router, "/i/{token}/calendar.ics", ctrl.guest_calendar, ["GET"], None,
       summary="Add to calendar", response_class=PlainTextResponse, include_in_schema=False, dependencies=_api_limit)
guest_page_router.add_api_route(
    "/i/{token}", ctrl.guest_invitation_page, methods=["GET", "HEAD"], response_class=HTMLResponse,
    include_in_schema=False, operation_id="events_guest_invitation_page", dependencies=_page_limit,
)
