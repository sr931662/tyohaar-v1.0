"""
Feedback Routes — customer submission and admin triage.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.feedback import controller as ctrl
from app.core.responses import CursorPaginatedResponse, SuccessResponse
from app.schemas.feedback.response import FeedbackResponse

router = APIRouter(prefix="/feedback", tags=["Feedback"])

# ── Admin (static — must precede /{feedback_id}) ─────────────────────────────

router.add_api_route(
    "/admin/all",
    ctrl.list_feedback,
    methods=["GET"],
    response_model=CursorPaginatedResponse[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="List Feedback (Admin)",
    description="Return a cursor-paginated, filterable list of all customer feedback. Admin access required.",
    operation_id="feedback_list_all",
)

router.add_api_route(
    "/admin/{feedback_id}",
    ctrl.get_feedback,
    methods=["GET"],
    response_model=SuccessResponse[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Feedback (Admin)",
    description="Return a single feedback submission by ID. Admin access required.",
    operation_id="feedback_get",
)

router.add_api_route(
    "/admin/{feedback_id}/review",
    ctrl.mark_reviewed,
    methods=["POST"],
    response_model=SuccessResponse[FeedbackResponse],
    status_code=status.HTTP_200_OK,
    summary="Mark Feedback Reviewed (Admin)",
    description="Mark a feedback submission as reviewed. Admin access required.",
    operation_id="feedback_mark_reviewed",
)

# ── Customer ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "",
    ctrl.submit_feedback,
    methods=["POST"],
    response_model=SuccessResponse[FeedbackResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Submit Feedback",
    description="Submit app feedback as the authenticated user.",
    operation_id="feedback_submit",
)
