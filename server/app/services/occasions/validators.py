"""
Occasions service — reusable async validator functions.

Each validator receives an active UnitOfWork (inside an `async with` block)
and either returns the requested ORM model or raises a domain exception.
"""

from __future__ import annotations

from uuid import UUID

from app.models.occasions.celebration import Celebration as CelebrationModel
from app.models.occasions.occasion import Occasion as OccasionModel
from app.repositories.unit_of_work import UnitOfWork
from app.services.occasions.constants import (
    MAX_CHECKLIST_ITEMS,
    MAX_GUESTS_PER_CELEBRATION,
    MAX_TIMELINE_EVENTS,
)
from app.services.occasions.exceptions import (
    CelebrationNotFoundError,
    CelebrationOwnershipError,
    ChecklistLimitExceededError,
    GuestLimitExceededError,
    OccasionNotFoundError,
    TimelineLimitExceededError,
)


async def validate_occasion_exists(
    occasion_id: UUID,
    uow: UnitOfWork,
) -> OccasionModel:
    """Return the Occasion if it exists, else raise OccasionNotFoundError."""
    occasion = await uow.occasions.occasions.get_by_id(occasion_id)
    if occasion is None:
        raise OccasionNotFoundError(str(occasion_id))
    return occasion


async def validate_celebration_ownership(
    celebration_id: UUID,
    user_id: UUID,
    uow: UnitOfWork,
) -> CelebrationModel:
    """Return the Celebration if it exists AND is owned by *user_id*.

    Raises:
        CelebrationNotFoundError  — celebration does not exist.
        CelebrationOwnershipError — celebration belongs to a different user.
    """
    celebration = await uow.occasions.celebrations.get_by_id(celebration_id)
    if celebration is None:
        raise CelebrationNotFoundError(str(celebration_id))
    if celebration.customer_id != user_id:
        raise CelebrationOwnershipError()
    return celebration


async def validate_guest_limit(
    celebration_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise GuestLimitExceededError if *celebration_id* already has MAX_GUESTS_PER_CELEBRATION guests."""
    count = await uow.occasions.guests.count_for_celebration(celebration_id)
    if count >= MAX_GUESTS_PER_CELEBRATION:
        raise GuestLimitExceededError()


async def validate_checklist_limit(
    celebration_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise ChecklistLimitExceededError if checklist is at capacity."""
    from app.models.occasions.celebration_checklist import CelebrationChecklist

    count = await uow.occasions.checklist.count(
        CelebrationChecklist.celebration_id == celebration_id
    )
    if count >= MAX_CHECKLIST_ITEMS:
        raise ChecklistLimitExceededError()


async def validate_timeline_limit(
    celebration_id: UUID,
    uow: UnitOfWork,
) -> None:
    """Raise TimelineLimitExceededError if timeline is at capacity."""
    from app.models.occasions.celebration_timeline import CelebrationTimeline

    count = await uow.occasions.timeline.count(
        CelebrationTimeline.celebration_id == celebration_id
    )
    if count >= MAX_TIMELINE_EVENTS:
        raise TimelineLimitExceededError()
