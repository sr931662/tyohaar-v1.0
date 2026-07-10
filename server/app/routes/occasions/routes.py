"""
Occasions Routes — occasions reference data, celebrations, guests, checklist, timeline, notes.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.occasions import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.occasions import (
    CelebrationChecklistResponse,
    CelebrationGuestResponse,
    CelebrationResponse,
    GuestRSVPPublicResponse,
    OccasionMoodResponse,
    OccasionResponse,
    OccasionTagResponse,
    OccasionThemeResponse,
)
from app.services.occasions.service import (
    CelebrationNoteResponse,
    CelebrationTimelineResponse,
    OccasionCategoryResponse,
)

router = APIRouter(tags=["Occasions"])

# ── Occasion reference data (public) ──────────────────────────────────────────

router.add_api_route(
    "/occasions/categories",
    ctrl.list_occasion_categories,
    methods=["GET"],
    response_model=SuccessResponse[list[OccasionCategoryResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Occasion Categories",
    description="Return all active occasion category records. Public endpoint.",
    operation_id="occasions_list_categories",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/moods",
    ctrl.list_occasion_moods,
    methods=["GET"],
    response_model=SuccessResponse[list[OccasionMoodResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Occasion Moods",
    description="Return all available occasion mood options. Public endpoint.",
    operation_id="occasions_list_moods",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/tags",
    ctrl.list_occasion_tags,
    methods=["GET"],
    response_model=SuccessResponse[list[OccasionTagResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Occasion Tags",
    description="Return all occasion tag records. Public endpoint.",
    operation_id="occasions_list_tags",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/themes",
    ctrl.list_occasion_themes,
    methods=["GET"],
    response_model=SuccessResponse[list[OccasionThemeResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Occasion Themes",
    description="Return all occasion theme records. Public endpoint.",
    operation_id="occasions_list_themes",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions",
    ctrl.list_occasions,
    methods=["GET"],
    response_model=CursorPaginatedResponse[OccasionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Occasions",
    description="Return a cursor-paginated list of occasions with optional filters.",
    operation_id="occasions_list_occasions",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/{occasion_id}",
    ctrl.get_occasion,
    methods=["GET"],
    response_model=SuccessResponse[OccasionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Occasion",
    description="Return a single occasion by ID. Public endpoint.",
    operation_id="occasions_get_occasion",
    tags=["Occasions"],
)

# ── Admin — occasion management ───────────────────────────────────────────────

router.add_api_route(
    "/occasions",
    ctrl.create_occasion,
    methods=["POST"],
    response_model=SuccessResponse[OccasionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Occasion (Admin)",
    description="Create a new occasion record. Admin access required.",
    operation_id="occasions_create_occasion",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/{occasion_id}",
    ctrl.update_occasion,
    methods=["PUT"],
    response_model=SuccessResponse[OccasionResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Occasion (Admin)",
    description="Update an existing occasion record. Admin access required.",
    operation_id="occasions_update_occasion",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/{occasion_id}",
    ctrl.delete_occasion,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Occasion (Admin)",
    description="Soft-delete an occasion record. Admin access required.",
    operation_id="occasions_delete_occasion",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/categories",
    ctrl.create_category,
    methods=["POST"],
    response_model=SuccessResponse[OccasionCategoryResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Occasion Category (Admin)",
    description="Create a new occasion category. Admin access required.",
    operation_id="occasions_create_category",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/moods",
    ctrl.create_mood,
    methods=["POST"],
    response_model=SuccessResponse[OccasionMoodResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Occasion Mood (Admin)",
    description="Create a new mood option. Admin access required.",
    operation_id="occasions_create_mood",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/tags",
    ctrl.create_tag,
    methods=["POST"],
    response_model=SuccessResponse[OccasionTagResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Occasion Tag (Admin)",
    description="Create a new tag. Admin access required.",
    operation_id="occasions_create_tag",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/themes",
    ctrl.create_theme,
    methods=["POST"],
    response_model=SuccessResponse[OccasionThemeResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Occasion Theme (Admin)",
    description="Create a new theme. Admin access required.",
    operation_id="occasions_create_theme",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/themes/{theme_id}",
    ctrl.update_theme,
    methods=["PUT"],
    response_model=SuccessResponse[OccasionThemeResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Occasion Theme (Admin)",
    description="Update an existing theme. Admin access required.",
    operation_id="occasions_update_theme",
    tags=["Occasions"],
)

router.add_api_route(
    "/occasions/themes/{theme_id}",
    ctrl.delete_theme,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Occasion Theme (Admin)",
    description="Delete a theme. Admin access required.",
    operation_id="occasions_delete_theme",
    tags=["Occasions"],
)

# ── Celebrations ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/celebrations",
    ctrl.list_celebrations,
    methods=["GET"],
    response_model=CursorPaginatedResponse[CelebrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List My Celebrations",
    description="Return all celebrations owned by the authenticated user.",
    operation_id="occasions_list_celebrations",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations",
    ctrl.create_celebration,
    methods=["POST"],
    response_model=SuccessResponse[CelebrationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Celebration",
    description="Create a new celebration event for the authenticated user.",
    operation_id="occasions_create_celebration",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}",
    ctrl.get_celebration,
    methods=["GET"],
    response_model=SuccessResponse[CelebrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Celebration",
    description="Return a single celebration by ID. Ownership required.",
    operation_id="occasions_get_celebration",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}",
    ctrl.update_celebration,
    methods=["PUT"],
    response_model=SuccessResponse[CelebrationResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Celebration",
    description="Update fields on an existing celebration. Ownership required.",
    operation_id="occasions_update_celebration",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}",
    ctrl.delete_celebration,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Celebration",
    description="Delete a celebration and all its sub-resources. Ownership required.",
    operation_id="occasions_delete_celebration",
    tags=["Celebrations"],
)

# ── Guests ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/celebrations/{celebration_id}/guests",
    ctrl.list_guests,
    methods=["GET"],
    response_model=SuccessResponse[list[CelebrationGuestResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Guests",
    description="Return all guests on the celebration's guest list.",
    operation_id="occasions_list_guests",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/guests",
    ctrl.add_guest,
    methods=["POST"],
    response_model=SuccessResponse[CelebrationGuestResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Guest",
    description="Add a new guest to the celebration's guest list.",
    operation_id="occasions_add_guest",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/guests/{guest_id}",
    ctrl.update_guest,
    methods=["PUT"],
    response_model=SuccessResponse[CelebrationGuestResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Guest",
    description="Update details for a guest on the celebration's guest list.",
    operation_id="occasions_update_guest",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/guests/{guest_id}",
    ctrl.remove_guest,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Remove Guest",
    description="Remove a guest from the celebration's guest list.",
    operation_id="occasions_remove_guest",
    tags=["Celebrations"],
)

# ── Public RSVP (no auth — reached via the guest's shared WhatsApp/email link) ─

router.add_api_route(
    "/public/rsvp/{token}/page",
    ctrl.get_guest_rsvp_page,
    methods=["GET"],
    status_code=status.HTTP_200_OK,
    summary="Guest RSVP Web Page (Public)",
    description=(
        "Self-contained mobile web page for guests without the app — the "
        "WhatsApp/email invite link points here. No authentication required."
    ),
    operation_id="occasions_get_guest_rsvp_page",
    tags=["Celebrations"],
    include_in_schema=False,
)

router.add_api_route(
    "/public/rsvp/{token}",
    ctrl.get_guest_rsvp,
    methods=["GET"],
    response_model=SuccessResponse[GuestRSVPPublicResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Guest RSVP (Public)",
    description="Return the event details and current RSVP status for a guest's personal invite link. No authentication required.",
    operation_id="occasions_get_guest_rsvp",
    tags=["Celebrations"],
)

router.add_api_route(
    "/public/rsvp/{token}",
    ctrl.submit_guest_rsvp,
    methods=["POST"],
    response_model=SuccessResponse[GuestRSVPPublicResponse],
    status_code=status.HTTP_200_OK,
    summary="Submit Guest RSVP (Public)",
    description="Submit or update a guest's RSVP via their personal invite link. Allowed until the day before the event. No authentication required.",
    operation_id="occasions_submit_guest_rsvp",
    tags=["Celebrations"],
)

# ── Checklist ─────────────────────────────────────────────────────────────────

router.add_api_route(
    "/celebrations/{celebration_id}/checklist/progress",
    ctrl.get_checklist_progress,
    methods=["GET"],
    response_model=SuccessResponse[dict],
    status_code=status.HTTP_200_OK,
    summary="Get Checklist Progress",
    description="Return completion statistics for the celebration checklist.",
    operation_id="occasions_get_checklist_progress",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/checklist",
    ctrl.list_checklist,
    methods=["GET"],
    response_model=SuccessResponse[list[CelebrationChecklistResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Checklist",
    description="Return all checklist items for the celebration.",
    operation_id="occasions_list_checklist",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/checklist",
    ctrl.add_checklist_item,
    methods=["POST"],
    response_model=SuccessResponse[CelebrationChecklistResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Checklist Item",
    description="Add a new to-do item to the celebration checklist.",
    operation_id="occasions_add_checklist_item",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/checklist/{item_id}",
    ctrl.update_checklist_item,
    methods=["PUT"],
    response_model=SuccessResponse[CelebrationChecklistResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Checklist Item",
    description="Update or toggle a checklist item on the celebration.",
    operation_id="occasions_update_checklist_item",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/checklist/{item_id}",
    ctrl.delete_checklist_item,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Checklist Item",
    description="Remove a checklist item from the celebration.",
    operation_id="occasions_delete_checklist_item",
    tags=["Celebrations"],
)

# ── Timeline ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/celebrations/{celebration_id}/timeline",
    ctrl.list_timeline,
    methods=["GET"],
    response_model=SuccessResponse[list[CelebrationTimelineResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Timeline Events",
    description="Return the ordered timeline of events for the celebration.",
    operation_id="occasions_list_timeline",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/timeline",
    ctrl.add_timeline_event,
    methods=["POST"],
    response_model=SuccessResponse[CelebrationTimelineResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Timeline Event",
    description="Add a scheduled event to the celebration timeline.",
    operation_id="occasions_add_timeline_event",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/timeline/{event_id}",
    ctrl.update_timeline_event,
    methods=["PUT"],
    response_model=SuccessResponse[CelebrationTimelineResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Timeline Event",
    description="Update a scheduled event on the celebration timeline.",
    operation_id="occasions_update_timeline_event",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/timeline/{event_id}",
    ctrl.delete_timeline_event,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Timeline Event",
    description="Remove an event from the celebration timeline.",
    operation_id="occasions_delete_timeline_event",
    tags=["Celebrations"],
)

# ── Notes ─────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/celebrations/{celebration_id}/notes",
    ctrl.list_notes,
    methods=["GET"],
    response_model=SuccessResponse[list[CelebrationNoteResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Notes",
    description="Return all notes attached to the celebration.",
    operation_id="occasions_list_notes",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/notes",
    ctrl.add_note,
    methods=["POST"],
    response_model=SuccessResponse[CelebrationNoteResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add Note",
    description="Attach a new note to the celebration.",
    operation_id="occasions_add_note",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/notes/{note_id}",
    ctrl.update_note,
    methods=["PUT"],
    response_model=SuccessResponse[CelebrationNoteResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Note",
    description="Edit the content of an existing celebration note.",
    operation_id="occasions_update_note",
    tags=["Celebrations"],
)

router.add_api_route(
    "/celebrations/{celebration_id}/notes/{note_id}",
    ctrl.delete_note,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Note",
    description="Remove a note from the celebration.",
    operation_id="occasions_delete_note",
    tags=["Celebrations"],
)
