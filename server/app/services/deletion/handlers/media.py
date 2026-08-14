"""
Tier: media rows.

Runs after the external handler has actually deleted the objects. A row is
removed only when we are confident its object is gone; anything recorded as
unresolved keeps its row, because that row is the only remaining pointer to a
file that is still publicly reachable.

This is the concrete implementation of the rule that a purge must never trade
a recoverable problem for an unrecoverable one.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media.image import Image
from app.models.media.unresolved_asset import UnresolvedMediaAsset
from app.models.media.video import Video
from app.models.users.profile import UserProfile
from app.services.deletion.registry import (
    TIER_AGGREGATE,
    PurgeReport,
    register_purge,
)


async def _unresolved_ids(
    session: AsyncSession, user_id: uuid.UUID, kind: str
) -> set[uuid.UUID]:
    result = await session.execute(
        select(UnresolvedMediaAsset.media_id).where(
            UnresolvedMediaAsset.owner_id == user_id,
            UnresolvedMediaAsset.media_kind == kind,
            UnresolvedMediaAsset.resolved_at.is_(None),
        )
    )
    return set(result.scalars().all())


@register_purge("media_rows", order=TIER_AGGREGATE + 20)
async def purge_media_rows(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    report = PurgeReport(handler="media_rows")

    for model, kind, label in (
        (Image, "image", "images"),
        (Video, "video", "videos"),
    ):
        blocked = await _unresolved_ids(session, user_id, kind)

        stmt = delete(model).where(model.owner_id == user_id)
        if blocked:
            stmt = stmt.where(model.id.notin_(blocked))

        result = await session.execute(stmt)
        report.count(label, result.rowcount or 0)

        if blocked:
            report.count(f"{label}_retained_unresolved", len(blocked))
            report.fail(
                f"{len(blocked)} {label} row(s) kept: their storage objects "
                "could not be deleted and the row is the only pointer to them"
            )

    # Profile image URLs live on the profile row, which the identity handler
    # deletes outright. Clear them here anyway so that if the identity handler
    # is ever re-scoped, the URLs do not quietly survive.
    photo_blocked = await _unresolved_ids(session, user_id, "profile_photo")
    cover_blocked = await _unresolved_ids(session, user_id, "cover_image")
    if not photo_blocked and not cover_blocked:
        result = await session.execute(
            update(UserProfile)
            .where(UserProfile.user_id == user_id)
            .values(
                profile_photo_url=None,
                profile_photo_public_id=None,
                cover_image_url=None,
                cover_image_public_id=None,
            )
        )
        report.count("profile_images_cleared", result.rowcount or 0)
    else:
        report.fail("profile image object(s) could not be deleted")

    return report
