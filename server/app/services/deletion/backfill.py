"""
One-off backfill: recover Cloudinary object ids for media uploaded before
`storage_public_id` existed.

Runs outside the migration on purpose. It calls the Cloudinary Admin API once
per asset to *verify* every id it derives, which is slow enough that doing it
inside a schema migration would hold a deploy open for as long as the media
library is large. It is resumable and safe to run repeatedly.

The verification step is the point. Parsing a public_id out of a delivery URL
is guesswork — versioned paths, transformation segments and folders all shift
the shape — and an unverified guess fails in the worst possible way: the purge
calls `destroy()` on an id that does not exist, Cloudinary answers "not found",
and the pipeline records a successful deletion of an asset that is still
public. Verifying before persisting turns that silent failure into a visible
one, recorded in `unresolved_media_assets` while the row is still there to
point at it.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.media.image import Image
from app.models.media.unresolved_asset import UnresolvedMediaAsset
from app.models.media.video import Video
from app.services.media import cloudinary_client

logger = logging.getLogger(__name__)


@dataclass
class BackfillResult:
    scanned: int = 0
    resolved: int = 0
    unresolved: int = 0

    def as_dict(self) -> dict:
        return {
            "scanned": self.scanned,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
        }


async def _mark_unresolved(
    session: AsyncSession,
    *,
    kind: str,
    media_id: uuid.UUID,
    owner_id: uuid.UUID | None,
    url: str,
    reason: str,
) -> None:
    await session.execute(
        pg_insert(UnresolvedMediaAsset)
        .values(
            id=uuid.uuid4(),
            media_kind=kind,
            media_id=media_id,
            owner_id=owner_id,
            url=url[:2000],
            reason=reason,
            last_checked_at=datetime.now(tz=timezone.utc),
        )
        .on_conflict_do_update(
            constraint="uq_unresolved_media_assets_kind_id",
            set_={
                "reason": reason,
                "last_checked_at": datetime.now(tz=timezone.utc),
            },
        )
    )


async def backfill_media_public_ids(
    *,
    batch_size: int = 200,
    max_batches: int | None = None,
    session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
) -> BackfillResult:
    """Resolve and persist `storage_public_id` for images and videos.

    Only rows where it is still NULL are considered, so progress is inherently
    resumable — interrupt it and run it again.
    """
    result = BackfillResult()

    for model, kind, resource_type in (
        (Image, "image", "image"),
        (Video, "video", "video"),
    ):
        batches = 0
        while max_batches is None or batches < max_batches:
            batches += 1

            async with session_factory() as session:
                rows = (
                    (
                        await session.execute(
                            select(
                                model.id,
                                model.url,
                                model.owner_id,
                                model.storage_path,
                            )
                            .where(model.storage_public_id.is_(None))
                            .limit(batch_size)
                        )
                    )
                    .tuples()
                    .all()
                )

                if not rows:
                    break

                for media_id, url, owner_id, storage_path in rows:
                    result.scanned += 1

                    # `storage_path` is documented as a generic object path,
                    # but the Cloudinary upload path has always written the
                    # public_id into it. Try that first — it is an exact value
                    # rather than a parse — and fall back to the URL only when
                    # it is absent or does not verify.
                    candidates = [
                        c
                        for c in (
                            storage_path,
                            cloudinary_client.parse_public_id(url or ""),
                        )
                        if c
                    ]

                    resolved_id = None
                    for candidate in candidates:
                        if await cloudinary_client.asset_exists(
                            candidate, resource_type=resource_type
                        ):
                            resolved_id = candidate
                            break

                    if resolved_id is None:
                        await _mark_unresolved(
                            session,
                            kind=kind,
                            media_id=media_id,
                            owner_id=owner_id,
                            url=url or "",
                            reason=(
                                "no_candidate" if not candidates else "admin_api_miss"
                            ),
                        )
                        result.unresolved += 1
                        continue

                    await session.execute(
                        update(model)
                        .where(model.id == media_id)
                        .values(
                            storage_public_id=resolved_id,
                            storage_provider="cloudinary",
                        )
                    )
                    result.resolved += 1

                await session.commit()

    logger.info("cloudinary backfill complete", extra=result.as_dict())
    return result


async def outstanding_unresolved_count(
    *, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
) -> int:
    """How many assets still cannot be deleted.

    The launch gate: while this is above zero, media deletion is not fully
    reliable and the product must not claim that uploaded photos and videos
    are removed on request.
    """
    async with session_factory() as session:
        rows = await session.execute(
            select(UnresolvedMediaAsset.id).where(
                UnresolvedMediaAsset.resolved_at.is_(None)
            )
        )
        return len(list(rows.scalars().all()))
