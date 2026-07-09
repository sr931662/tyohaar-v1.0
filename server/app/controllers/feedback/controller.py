"""
Feedback Controller — customer submission and admin triage.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.current_user import CurrentUserDep
from app.core.dependencies import FeedbackServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.feedback.create import FeedbackCreate
from app.schemas.feedback.filters import FeedbackFilters
from app.schemas.feedback.response import FeedbackResponse


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def submit_feedback(
    body: FeedbackCreate,
    current_user: CurrentUserDep,
    service: FeedbackServiceDep,
) -> SuccessResponse[FeedbackResponse]:
    result = await service.submit_feedback(user_id=current_user.id, data=body)
    return SuccessResponse(data=result, message="Thanks for your feedback.")


async def list_feedback(
    filters: Annotated[FeedbackFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: FeedbackServiceDep,
) -> CursorPaginatedResponse[FeedbackResponse]:
    page = await service.list_feedback(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def get_feedback(
    feedback_id: uuid.UUID,
    _admin: AdminDep,
    service: FeedbackServiceDep,
) -> SuccessResponse[FeedbackResponse]:
    result = await service.get_feedback(feedback_id=feedback_id)
    return SuccessResponse(data=result, message="Feedback retrieved.")


async def mark_reviewed(
    feedback_id: uuid.UUID,
    current_user: AdminDep,
    service: FeedbackServiceDep,
) -> SuccessResponse[FeedbackResponse]:
    result = await service.mark_reviewed(feedback_id=feedback_id, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Feedback marked reviewed.")
