"""
Occasion repository — Occasion, Celebration, and all associated child models.
Also handles Invitation models (invitation.py, invitation_template.py, invitation_guest.py).
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.invitations.invitation import Invitation
from app.models.invitations.invitation_guest import InvitationGuest
from app.models.invitations.invitation_template import InvitationTemplate
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_budget import CelebrationBudget
from app.models.occasions.celebration_checklist import CelebrationChecklist
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.celebration_note import CelebrationNote
from app.models.occasions.celebration_timeline import CelebrationTimeline
from app.models.occasions.occasion import Occasion
from app.models.occasions.occasion_category import OccasionCategory
from app.models.occasions.occasion_mood import OccasionMood
from app.models.occasions.occasion_tag import OccasionTag
from app.models.occasions.occasion_theme import OccasionTheme
from app.repositories.base import BaseRepository


class OccasionRepository(BaseRepository[Occasion]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Occasion)

    async def find_by_slug(self, slug: str) -> Occasion | None:
        return await self.find_one(Occasion.slug == slug)

    async def find_featured(self) -> list[Occasion]:
        return await self.find_many(
            Occasion.is_featured == True,  # noqa: E712
            Occasion.is_active == True,  # noqa: E712
            order_by=Occasion.display_order.asc(),
        )

    async def find_active(self, *, skip: int = 0, limit: int = 100) -> list[Occasion]:
        return await self.find_many(
            Occasion.is_active == True,  # noqa: E712
            skip=skip,
            limit=limit,
        )

    async def find_by_category(self, category_id: uuid.UUID) -> list[Occasion]:
        return await self.find_many(Occasion.category_id == category_id)

    async def find_seasonal(self) -> list[Occasion]:
        return await self.find_many(
            Occasion.is_seasonal == True,  # noqa: E712
            Occasion.is_active == True,  # noqa: E712
        )


class OccasionCategoryRepository(BaseRepository[OccasionCategory]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OccasionCategory)

    async def find_active(self) -> list[OccasionCategory]:
        return await self.find_many(OccasionCategory.is_active == True)  # noqa: E712

    async def find_by_slug(self, slug: str) -> OccasionCategory | None:
        return await self.find_one(OccasionCategory.slug == slug)


class OccasionThemeRepository(BaseRepository[OccasionTheme]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OccasionTheme)

    async def find_by_occasion(self, occasion_id: uuid.UUID) -> list[OccasionTheme]:
        return await self.find_many(OccasionTheme.occasion_id == occasion_id)

    async def find_active_for_occasion(self, occasion_id: uuid.UUID) -> list[OccasionTheme]:
        return await self.find_many(
            OccasionTheme.occasion_id == occasion_id,
            OccasionTheme.is_active == True,  # noqa: E712
        )


class OccasionMoodRepository(BaseRepository[OccasionMood]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OccasionMood)

    async def find_by_occasion(self, occasion_id: uuid.UUID) -> list[OccasionMood]:
        return await self.find_many(OccasionMood.occasion_id == occasion_id)


class OccasionTagRepository(BaseRepository[OccasionTag]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OccasionTag)

    async def find_by_occasion(self, occasion_id: uuid.UUID) -> list[OccasionTag]:
        return await self.find_many(OccasionTag.occasion_id == occasion_id)


class CelebrationRepository(BaseRepository[Celebration]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Celebration)

    async def find_by_customer(
        self,
        customer_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Celebration]:
        return await self.find_many(
            Celebration.customer_id == customer_id,
            order_by=Celebration.celebration_date.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_upcoming_for_customer(
        self,
        customer_id: uuid.UUID,
        after: date,
    ) -> list[Celebration]:
        return await self.find_many(
            Celebration.customer_id == customer_id,
            Celebration.celebration_date > after,
            order_by=Celebration.celebration_date.asc(),
        )

    async def find_by_status(self, status: str, *, skip: int = 0, limit: int = 100) -> list[Celebration]:
        return await self.find_many(
            Celebration.status == status,
            skip=skip,
            limit=limit,
        )

    async def get_with_budget(self, celebration_id: uuid.UUID) -> Celebration | None:
        return await self.get_by_id(
            celebration_id,
            options=[selectinload(Celebration.budget)],
        )

    async def get_full(self, celebration_id: uuid.UUID) -> Celebration | None:
        return await self.get_by_id(
            celebration_id,
            options=[
                selectinload(Celebration.guests),
                selectinload(Celebration.timeline),
                selectinload(Celebration.checklist),
                selectinload(Celebration.budget),
            ],
        )


class CelebrationGuestRepository(BaseRepository[CelebrationGuest]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CelebrationGuest)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[CelebrationGuest]:
        return await self.find_many(CelebrationGuest.celebration_id == celebration_id)

    async def count_for_celebration(self, celebration_id: uuid.UUID) -> int:
        return await self.count(CelebrationGuest.celebration_id == celebration_id)

    async def find_by_rsvp_token(self, token: str) -> CelebrationGuest | None:
        return await self.find_one(CelebrationGuest.rsvp_token == token)


class CelebrationTimelineRepository(BaseRepository[CelebrationTimeline]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CelebrationTimeline)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[CelebrationTimeline]:
        return await self.find_many(
            CelebrationTimeline.celebration_id == celebration_id,
            order_by=CelebrationTimeline.event_time.asc(),
        )


class CelebrationNoteRepository(BaseRepository[CelebrationNote]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CelebrationNote)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[CelebrationNote]:
        return await self.find_many(
            CelebrationNote.celebration_id == celebration_id,
            order_by=CelebrationNote.created_at.desc(),
        )


class CelebrationBudgetRepository(BaseRepository[CelebrationBudget]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CelebrationBudget)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> CelebrationBudget | None:
        return await self.find_one(CelebrationBudget.celebration_id == celebration_id)


class CelebrationChecklistRepository(BaseRepository[CelebrationChecklist]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CelebrationChecklist)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[CelebrationChecklist]:
        return await self.find_many(
            CelebrationChecklist.celebration_id == celebration_id,
            order_by=CelebrationChecklist.display_order.asc(),
        )

    async def count_completed(self, celebration_id: uuid.UUID) -> int:
        return await self.count(
            CelebrationChecklist.celebration_id == celebration_id,
            CelebrationChecklist.is_completed == True,  # noqa: E712
        )


class InvitationRepository(BaseRepository[Invitation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Invitation)

    async def find_by_celebration(self, celebration_id: uuid.UUID) -> list[Invitation]:
        return await self.find_many(Invitation.celebration_id == celebration_id)

    async def find_by_slug(self, slug: str) -> Invitation | None:
        return await self.find_one(Invitation.slug == slug)

    async def find_active_for_celebration(self, celebration_id: uuid.UUID) -> list[Invitation]:
        return await self.find_many(
            Invitation.celebration_id == celebration_id,
            Invitation.is_active == True,  # noqa: E712
        )


class InvitationTemplateRepository(BaseRepository[InvitationTemplate]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvitationTemplate)

    async def find_active(self) -> list[InvitationTemplate]:
        return await self.find_many(InvitationTemplate.is_active == True)  # noqa: E712

    async def find_by_slug(self, slug: str) -> InvitationTemplate | None:
        return await self.find_one(InvitationTemplate.slug == slug)


class InvitationGuestRepository(BaseRepository[InvitationGuest]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InvitationGuest)

    async def find_by_invitation(self, invitation_id: uuid.UUID) -> list[InvitationGuest]:
        return await self.find_many(InvitationGuest.invitation_id == invitation_id)

    async def count_rsvp(self, invitation_id: uuid.UUID, rsvp_status: str) -> int:
        return await self.count(
            InvitationGuest.invitation_id == invitation_id,
            InvitationGuest.rsvp_status == rsvp_status,
        )


class OccasionRepositoryAggregate:
    """Groups all occasion-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.occasions = OccasionRepository(session)
        self.categories = OccasionCategoryRepository(session)
        self.themes = OccasionThemeRepository(session)
        self.moods = OccasionMoodRepository(session)
        self.tags = OccasionTagRepository(session)
        self.celebrations = CelebrationRepository(session)
        self.guests = CelebrationGuestRepository(session)
        self.timeline = CelebrationTimelineRepository(session)
        self.notes = CelebrationNoteRepository(session)
        self.budgets = CelebrationBudgetRepository(session)
        self.checklist = CelebrationChecklistRepository(session)
        self.invitations = InvitationRepository(session)
        self.invitation_templates = InvitationTemplateRepository(session)
        self.invitation_guests = InvitationGuestRepository(session)
