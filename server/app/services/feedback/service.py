"""
FeedbackService — standalone customer feedback submissions.
"""

from __future__ import annotations

from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.schemas.base import CursorPage
from app.schemas.feedback.create import FeedbackCreate
from app.schemas.feedback.filters import FeedbackFilters
from app.schemas.feedback.response import FeedbackResponse
from app.services.base import BaseService
from app.services.feedback.exceptions import FeedbackNotFoundError


class FeedbackService(BaseService):
    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        super().__init__(session_factory)

    async def submit_feedback(self, user_id: UUID, data: FeedbackCreate) -> FeedbackResponse:
        async with self._uow() as uow:
            feedback = await uow.feedback.feedback.create_from_dict({
                "customer_id": user_id,
                "rating": data.rating,
                "category": data.category,
                "comments": data.comments,
                "app_version": data.app_version,
                "is_reviewed": False,
            })
            await uow.commit()
            return FeedbackResponse.model_validate(feedback)

    async def list_feedback(
        self,
        filters: FeedbackFilters,
        cursor: str | None,
        limit: int,
    ) -> CursorPage[FeedbackResponse]:
        from app.models.feedback.feedback import Feedback

        conditions = []
        if filters.category is not None:
            conditions.append(Feedback.category == filters.category)
        if filters.rating is not None:
            conditions.append(Feedback.rating == filters.rating)
        if filters.is_reviewed is not None:
            conditions.append(Feedback.is_reviewed == filters.is_reviewed)
        if filters.from_date is not None:
            conditions.append(Feedback.created_at >= filters.from_date)
        if filters.to_date is not None:
            conditions.append(Feedback.created_at <= filters.to_date)

        async with self._uow() as uow:
            page = await uow.feedback.feedback.cursor_paginate(
                *conditions,
                cursor=cursor,
                limit=limit,
            )
            return CursorPage(
                items=[FeedbackResponse.model_validate(f) for f in page.items],
                next_cursor=page.next_cursor,
                has_more=page.next_cursor is not None,
            )

    async def get_feedback(self, feedback_id: UUID) -> FeedbackResponse:
        async with self._uow() as uow:
            feedback = await uow.feedback.feedback.get_by_id(feedback_id)
            if feedback is None:
                raise FeedbackNotFoundError(str(feedback_id))
            return FeedbackResponse.model_validate(feedback)

    async def mark_reviewed(self, feedback_id: UUID, admin_id: UUID) -> FeedbackResponse:
        async with self._uow() as uow:
            updated = await uow.feedback.feedback.mark_reviewed(feedback_id, admin_id)
            if updated is None:
                raise FeedbackNotFoundError(str(feedback_id))
            await uow.commit()
            return FeedbackResponse.model_validate(updated)
