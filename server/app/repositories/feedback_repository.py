"""
Feedback repository.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.feedback.feedback import Feedback
from app.repositories.base import BaseRepository


class FeedbackRepository(BaseRepository[Feedback]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Feedback)

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Feedback]:
        return await self.find_many(
            Feedback.customer_id == customer_id,
            order_by=Feedback.created_at.desc(),
            skip=skip,
            limit=limit,
        )

    async def mark_reviewed(self, feedback_id: uuid.UUID, admin_id: uuid.UUID) -> Feedback | None:
        feedback = await self.get_by_id(feedback_id)
        if feedback is None:
            return None
        return await self.update(feedback, {
            "is_reviewed": True,
            "reviewed_by_id": admin_id,
            "reviewed_at": datetime.now(tz=timezone.utc),
        })


class FeedbackRepositoryAggregate:
    """Groups feedback-domain sub-repositories (currently just the one)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.feedback = FeedbackRepository(session)
