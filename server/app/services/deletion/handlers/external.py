"""
Tier: external systems.

Runs before any database row is touched. The ordering is deliberate: if the
run dies halfway, an orphaned database row pointing at an already-deleted
object is recoverable noise, whereas a deleted row pointing at a live object
is a file nobody can ever find again.

The rule this module exists to enforce:

    Never report an asset as deleted when the external object still exists,
    and never delete the database row that is the only pointer to it.

An asset whose provider id cannot be resolved is recorded in
`unresolved_media_assets` and the handler reports failure. The runner then
marks the whole request INCOMPLETE, which is the truthful outcome — the user
has not been fully purged, and no claim to the contrary may be made.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.media.image import Image
from app.models.media.unresolved_asset import UnresolvedMediaAsset
from app.models.media.video import Video
from app.models.support.attachment import SupportAttachment
from app.models.support.ticket import SupportTicket
from app.models.users.device import UserDevice
from app.models.users.profile import UserProfile
from app.services.deletion.registry import (
    TIER_EXTERNAL,
    PurgeReport,
    register_purge,
)
from app.services.media import cloudinary_client


async def _record_unresolved(
    session: AsyncSession,
    *,
    kind: str,
    media_id: uuid.UUID,
    owner_id: uuid.UUID | None,
    url: str,
    reason: str,
) -> None:
    """Durably record an asset we could not delete.

    Upsert rather than insert: the purge is re-runnable, and a second attempt
    on the same still-unresolvable asset must update the timestamp rather than
    raise a unique-violation and abort the whole transaction.
    """
    stmt = (
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
    await session.execute(stmt)


@register_purge("cloudinary_objects", order=TIER_EXTERNAL)
async def purge_cloudinary_objects(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Delete every Cloudinary object belonging to this user."""
    report = PurgeReport(handler="cloudinary_objects")

    # ── Images ────────────────────────────────────────────────────────────────
    images = (
        (
            await session.execute(
                select(Image.id, Image.storage_public_id, Image.url).where(
                    Image.owner_id == user_id
                )
            )
        )
        .tuples()
        .all()
    )
    for image_id, public_id, url in images:
        if not public_id:
            await _record_unresolved(
                session,
                kind="image",
                media_id=image_id,
                owner_id=user_id,
                url=url,
                reason="no_storage_public_id",
            )
            report.fail(f"image {image_id}: no storage_public_id")
            continue
        if await cloudinary_client.destroy_asset(public_id, resource_type="image"):
            report.count("images_destroyed", 1)
        else:
            await _record_unresolved(
                session,
                kind="image",
                media_id=image_id,
                owner_id=user_id,
                url=url,
                reason="destroy_failed",
            )
            report.fail(f"image {image_id}: destroy failed")

    # ── Videos ────────────────────────────────────────────────────────────────
    videos = (
        (
            await session.execute(
                select(Video.id, Video.storage_public_id, Video.url).where(
                    Video.owner_id == user_id
                )
            )
        )
        .tuples()
        .all()
    )
    for video_id, public_id, url in videos:
        if not public_id:
            await _record_unresolved(
                session,
                kind="video",
                media_id=video_id,
                owner_id=user_id,
                url=url,
                reason="no_storage_public_id",
            )
            report.fail(f"video {video_id}: no storage_public_id")
            continue
        if await cloudinary_client.destroy_asset(public_id, resource_type="video"):
            report.count("videos_destroyed", 1)
        else:
            await _record_unresolved(
                session,
                kind="video",
                media_id=video_id,
                owner_id=user_id,
                url=url,
                reason="destroy_failed",
            )
            report.fail(f"video {video_id}: destroy failed")

    # ── Profile photo & cover ─────────────────────────────────────────────────
    profile_row = (
        await session.execute(
            select(
                UserProfile.id,
                UserProfile.profile_photo_public_id,
                UserProfile.profile_photo_url,
                UserProfile.cover_image_public_id,
                UserProfile.cover_image_url,
            ).where(UserProfile.user_id == user_id)
        )
    ).first()

    if profile_row is not None:
        profile_id, photo_id, photo_url, cover_id, cover_url = profile_row
        for kind, pid, purl in (
            ("profile_photo", photo_id, photo_url),
            ("cover_image", cover_id, cover_url),
        ):
            if not purl:
                continue  # nothing was ever uploaded
            if not pid:
                await _record_unresolved(
                    session,
                    kind=kind,
                    media_id=profile_id,
                    owner_id=user_id,
                    url=purl,
                    reason="no_storage_public_id",
                )
                report.fail(f"{kind}: no storage id")
                continue
            if await cloudinary_client.destroy_asset(pid, resource_type="image"):
                report.count(f"{kind}_destroyed", 1)
            else:
                await _record_unresolved(
                    session,
                    kind=kind,
                    media_id=profile_id,
                    owner_id=user_id,
                    url=purl,
                    reason="destroy_failed",
                )
                report.fail(f"{kind}: destroy failed")

    # ── Support attachments ───────────────────────────────────────────────────
    # These already persist the Cloudinary public_id in `storage_key` (see
    # services/support/service.py), so they are deletable today.
    attachments = (
        (
            await session.execute(
                select(
                    SupportAttachment.id,
                    SupportAttachment.storage_key,
                    SupportAttachment.storage_url,
                )
                .join(SupportTicket, SupportAttachment.ticket_id == SupportTicket.id)
                .where(SupportTicket.customer_id == user_id)
            )
        )
        .tuples()
        .all()
    )
    for attachment_id, storage_key, storage_url in attachments:
        if not storage_key:
            await _record_unresolved(
                session,
                kind="support_attachment",
                media_id=attachment_id,
                owner_id=user_id,
                url=storage_url or "",
                reason="no_storage_key",
            )
            report.fail(f"attachment {attachment_id}: no storage_key")
            continue
        if await cloudinary_client.destroy_asset(storage_key, resource_type="image"):
            report.count("support_attachments_destroyed", 1)
        else:
            await _record_unresolved(
                session,
                kind="support_attachment",
                media_id=attachment_id,
                owner_id=user_id,
                url=storage_url or "",
                reason="destroy_failed",
            )
            report.fail(f"attachment {attachment_id}: destroy failed")

    return report


@register_purge("push_tokens", order=TIER_EXTERNAL + 10)
async def purge_push_tokens(
    session: AsyncSession, user_id: uuid.UUID
) -> PurgeReport:
    """Unregister the user's push tokens with the notification provider.

    Deleting the `user_devices` rows stops *us* sending. This stops the
    provider holding a route to the handset. Both are required.

    No FCM dispatcher is wired in the server yet — `services/notifications`
    documents PUSH as unimplemented — so there is nothing to call. The tokens
    are still cleared from our side by the `session_access` handler. This is
    recorded as deferred rather than silently skipped, so the gap is visible
    in the retained purge report instead of being invisible.
    """
    report = PurgeReport(handler="push_tokens")

    token_count = len(
        (
            await session.execute(
                select(UserDevice.id).where(
                    UserDevice.user_id == user_id,
                    UserDevice.push_notification_token.isnot(None),
                )
            )
        )
        .scalars()
        .all()
    )

    if token_count:
        report.count("tokens_found", token_count)
        report.defer(
            "provider_unregister_not_wired: no push dispatcher exists in the "
            "server; local device rows are deleted by session_access"
        )

    return report
