"""
OccasionService — all occasions-domain business operations.

Layout:
  1. Occasions (reference data)      list / get / list_categories / list_moods / list_tags / list_themes
  2. Admin operations                create / update / delete occasion + reference items
  3. Celebrations                    create / get / list / update / delete
  4. Celebration guests              add / update / remove / list
  5. Celebration checklist           add / update / delete / list / get_progress
  6. Celebration timeline            add / update / delete / list
  7. Celebration notes               add / update / delete / list
"""

from __future__ import annotations

from uuid import UUID

from app.db.session import AsyncSessionLocal
from app.schemas.base import CursorPage as SchemaCursorPage
from app.schemas.occasions import (
    CelebrationChecklistCreate,
    CelebrationChecklistResponse,
    CelebrationChecklistUpdate,
    CelebrationCreate,
    CelebrationGuestCreate,
    CelebrationGuestResponse,
    CelebrationGuestUpdate,
    CelebrationGuestHistoryResponse,
    CelebrationResponse,
    CelebrationUpdate,
    GuestRSVPPublicResponse,
    GuestRSVPSubmit,
    OccasionCreate,
    OccasionFilters,
    OccasionMoodResponse,
    OccasionResponse,
    OccasionTagResponse,
    OccasionThemeResponse,
)
from app.services.base import BaseService
from app.services.occasions.constants import MAX_NOTES_PER_CELEBRATION, MAX_PAGE_SIZE
from app.services.occasions.exceptions import (
    CelebrationNotFoundError,
    CelebrationOwnershipError,
    OccasionNotFoundError,
)
from app.services.occasions.helpers import (
    calculate_celebration_progress,
    sort_timeline_events,
)
from app.services.occasions.validators import (
    validate_celebration_ownership,
    validate_checklist_limit,
    validate_guest_limit,
    validate_occasion_exists,
    validate_timeline_limit,
)

# ---------------------------------------------------------------------------
# Inline schemas for occasion categories, moods, tags, themes, timeline and
# notes — these models exist in the DB layer but were not included in the
# frozen schema layer v1.0. Defined here to avoid modifying frozen files.
# ---------------------------------------------------------------------------
from datetime import datetime as _datetime
from typing import Any as _Any

from app.models.occasions.celebration_timeline import TimelineEventType as _TimelineEventType
from app.schemas.base import BaseSchema as _BaseSchema


class OccasionCategoryCreate(_BaseSchema):
    name: str
    description: str | None = None
    icon_url: str | None = None
    display_order: int = 0


class OccasionCategoryResponse(_BaseSchema):
    id: UUID
    name: str
    description: str | None = None
    icon_url: str | None = None
    display_order: int
    is_active: bool
    created_at: _datetime


class OccasionMoodCreate(_BaseSchema):
    name: str
    description: str | None = None
    icon_url: str | None = None


class OccasionTagCreate(_BaseSchema):
    name: str
    slug: str | None = None


class OccasionThemeCreate(_BaseSchema):
    name: str
    slug: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    thumbnail_url: str | None = None
    primary_color: str | None = None  # hex code, e.g. '#C8A96E'
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    sort_order: int = 0
    is_featured: bool = False


class OccasionThemeUpdate(_BaseSchema):
    name: str | None = None
    description: str | None = None
    cover_image_url: str | None = None
    thumbnail_url: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    accent_color: str | None = None
    background_color: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None
    is_featured: bool | None = None


class OccasionUpdate(_BaseSchema):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    category_id: UUID | None = None
    icon_url: str | None = None
    banner_url: str | None = None
    thumbnail_url: str | None = None
    display_order: int | None = None
    is_featured: bool | None = None


class CelebrationTimelineCreate(_BaseSchema):
    event_type: _TimelineEventType = _TimelineEventType.CUSTOM
    title: str
    description: str | None = None
    occurred_at: _datetime
    display_order: int = 0
    icon_url: str | None = None
    context_data: dict[str, _Any] | None = None


class CelebrationTimelineUpdate(_BaseSchema):
    title: str | None = None
    description: str | None = None
    occurred_at: _datetime | None = None
    display_order: int | None = None
    icon_url: str | None = None


class CelebrationTimelineResponse(_BaseSchema):
    id: UUID
    celebration_id: UUID
    event_type: str
    title: str
    description: str | None = None
    occurred_at: _datetime
    display_order: int
    icon_url: str | None = None
    is_system_generated: bool
    created_at: _datetime


class CelebrationNoteCreate(_BaseSchema):
    title: str | None = None
    body: str
    is_pinned: bool = False


class CelebrationNoteUpdate(_BaseSchema):
    title: str | None = None
    body: str | None = None
    is_pinned: bool | None = None


class CelebrationNoteResponse(_BaseSchema):
    id: UUID
    celebration_id: UUID
    author_id: UUID
    title: str | None = None
    body: str
    is_pinned: bool
    created_at: _datetime


class OccasionService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ── 1. Occasions (reference data) ─────────────────────────────────────────

    async def list_occasions(
        self,
        filters: OccasionFilters | None,
        cursor: str | None,
        limit: int,
    ) -> SchemaCursorPage[OccasionResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            from app.models.occasions.occasion import Occasion

            filter_args = []
            if filters is not None:
                if hasattr(filters, "is_active") and filters.is_active is not None:
                    filter_args.append(Occasion.is_active == filters.is_active)
                if hasattr(filters, "is_featured") and filters.is_featured is not None:
                    filter_args.append(Occasion.is_featured == filters.is_featured)
                if hasattr(filters, "category_id") and filters.category_id is not None:
                    filter_args.append(Occasion.category_id == filters.category_id)

            page = await uow.occasions.occasions.cursor_paginate(
                *filter_args,
                cursor=cursor,
                limit=limit,
            )
            return SchemaCursorPage(
                items=[OccasionResponse.model_validate(o) for o in page.items],
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    async def get_occasion(self, occasion_id: UUID) -> OccasionResponse:
        async with self._uow() as uow:
            occasion = await validate_occasion_exists(occasion_id, uow)
            return OccasionResponse.model_validate(occasion)

    async def list_occasion_categories(self) -> list[object]:
        async with self._uow() as uow:
            categories = await uow.occasions.categories.find_active()
            return [OccasionCategoryResponse.model_validate(c) for c in categories]  # type: ignore[call-arg]

    async def list_occasion_moods(self) -> list[OccasionMoodResponse]:
        async with self._uow() as uow:
            moods = await uow.occasions.moods.find_many()
            return [OccasionMoodResponse.model_validate(m) for m in moods]

    async def list_occasion_tags(self) -> list[OccasionTagResponse]:
        async with self._uow() as uow:
            tags = await uow.occasions.tags.find_many()
            return [OccasionTagResponse.model_validate(t) for t in tags]

    async def list_occasion_themes(self) -> list[OccasionThemeResponse]:
        async with self._uow() as uow:
            themes = await uow.occasions.themes.find_many()
            return [OccasionThemeResponse.model_validate(t) for t in themes]

    # ── 2. Admin Operations (reference data management) ────────────────────────

    async def create_occasion(self, data: OccasionCreate) -> OccasionResponse:
        async with self._uow() as uow:
            payload = data.model_dump(exclude_unset=True)
            if not payload.get("slug"):
                from app.services.common.helpers import slugify
                payload["slug"] = slugify(payload["name"])
            occasion = await uow.occasions.occasions.create_from_dict(payload)
            return OccasionResponse.model_validate(occasion)

    async def update_occasion(
        self,
        occasion_id: UUID,
        data: object,
    ) -> OccasionResponse:
        async with self._uow() as uow:
            occasion = await validate_occasion_exists(occasion_id, uow)
            occasion = await uow.occasions.occasions.update(
                occasion, data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return OccasionResponse.model_validate(occasion)

    async def delete_occasion(self, occasion_id: UUID) -> None:
        async with self._uow() as uow:
            occasion = await validate_occasion_exists(occasion_id, uow)
            await uow.occasions.occasions.delete(occasion)

    async def create_category(self, data: object) -> object:
        async with self._uow() as uow:
            category = await uow.occasions.categories.create_from_dict(
                data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return OccasionCategoryResponse.model_validate(category)  # type: ignore[call-arg]

    async def create_mood(self, data: object) -> OccasionMoodResponse:
        async with self._uow() as uow:
            mood = await uow.occasions.moods.create_from_dict(
                data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return OccasionMoodResponse.model_validate(mood)

    async def create_tag(self, data: object) -> OccasionTagResponse:
        async with self._uow() as uow:
            tag = await uow.occasions.tags.create_from_dict(
                data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return OccasionTagResponse.model_validate(tag)

    @staticmethod
    def _theme_payload(data: object) -> dict:
        """
        Translate the flat primary/secondary/accent/background color fields
        (the admin-friendly shape) into the model's real `colors` JSONB column.
        """
        raw = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
        color_keys = {
            "primary_color": "primary",
            "secondary_color": "secondary",
            "accent_color": "accent",
            "background_color": "background",
        }
        colors = {}
        for field, colors_key in color_keys.items():
            if field in raw:
                value = raw.pop(field)
                if value is not None:
                    colors[colors_key] = value
        if colors:
            raw["colors"] = colors
        if not raw.get("slug") and raw.get("name"):
            from app.services.common.helpers import slugify
            raw["slug"] = slugify(raw["name"])
        return raw

    async def create_theme(self, data: object) -> OccasionThemeResponse:
        async with self._uow() as uow:
            theme = await uow.occasions.themes.create_from_dict(self._theme_payload(data))
            return OccasionThemeResponse.model_validate(theme)

    async def update_theme(self, theme_id: UUID, data: object) -> OccasionThemeResponse:
        async with self._uow() as uow:
            theme = await uow.occasions.themes.get_by_id(theme_id)
            if theme is None:
                from app.services.occasions.exceptions import OccasionNotFoundError
                raise OccasionNotFoundError(str(theme_id))
            payload = self._theme_payload(data)
            if "colors" in payload:
                # Merge into the existing palette rather than overwriting it wholesale
                merged = dict(theme.colors or {})
                merged.update(payload["colors"])
                payload["colors"] = merged
            theme = await uow.occasions.themes.update(theme, payload)
            return OccasionThemeResponse.model_validate(theme)

    async def delete_theme(self, theme_id: UUID) -> None:
        async with self._uow() as uow:
            theme = await uow.occasions.themes.get_by_id(theme_id)
            if theme is None:
                from app.services.occasions.exceptions import OccasionNotFoundError
                raise OccasionNotFoundError(str(theme_id))
            await uow.occasions.themes.delete(theme)

    # ── 3. Celebrations ────────────────────────────────────────────────────────

    async def create_celebration(
        self,
        user_id: UUID,
        data: CelebrationCreate,
    ) -> CelebrationResponse:
        async with self._uow() as uow:
            await validate_occasion_exists(data.occasion_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["customer_id"] = user_id
            celebration = await uow.occasions.celebrations.create_from_dict(payload)
            return CelebrationResponse.model_validate(celebration)

    async def _attach_display_data(self, uow, celebrations: list) -> list[CelebrationResponse]:
        """
        Batch-fetch occasion name/hero image and theme colors/cover image
        for a list of celebrations. CelebrationResponse doesn't nest these
        relationships, so the client can't resolve them from bare
        occasion_id/theme_id alone (e.g. the invitation card needs the
        chosen theme's colors, not the app's default saffron gradient).
        """
        occasion_ids = list({c.occasion_id for c in celebrations if c.occasion_id})
        theme_ids = list({c.theme_id for c in celebrations if c.theme_id})
        mood_ids = list({c.mood_id for c in celebrations if c.mood_id})
        occasions = await uow.occasions.occasions.get_by_ids(occasion_ids)
        themes = await uow.occasions.themes.get_by_ids(theme_ids) if theme_ids else []
        moods = await uow.occasions.moods.get_by_ids(mood_ids) if mood_ids else []
        occasions_by_id = {o.id: o for o in occasions}
        themes_by_id = {t.id: t for t in themes}
        moods_by_id = {m.id: m for m in moods}

        results = []
        for c in celebrations:
            response = CelebrationResponse.model_validate(c)
            occ = occasions_by_id.get(c.occasion_id)
            theme = themes_by_id.get(c.theme_id) if c.theme_id else None
            mood = moods_by_id.get(c.mood_id) if c.mood_id else None
            response.occasion_name = occ.name if occ else None
            response.occasion_hero_image_url = occ.banner_url if occ else None
            response.theme_colors = theme.colors if theme else None
            response.theme_cover_image_url = theme.cover_image_url if theme else None
            response.mood_name = mood.name if mood else None
            response.mood_slug = mood.slug if mood else None
            response.mood_emoji = mood.emoji if mood else None
            results.append(response)
        return results

    async def get_celebration(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> CelebrationResponse:
        async with self._uow() as uow:
            celebration = await validate_celebration_ownership(
                celebration_id, user_id, uow
            )
            enriched = await self._attach_display_data(uow, [celebration])
            return enriched[0]

    async def list_celebrations(
        self,
        user_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> SchemaCursorPage[CelebrationResponse]:
        limit = min(limit, MAX_PAGE_SIZE)
        async with self._uow() as uow:
            from app.models.occasions.celebration import Celebration

            page = await uow.occasions.celebrations.cursor_paginate(
                Celebration.customer_id == user_id,
                cursor=cursor,
                limit=limit,
            )
            items = await self._attach_display_data(uow, page.items)
            return SchemaCursorPage(
                items=items,
                next_cursor=page.next_cursor,
                has_more=page.has_next,
            )

    async def update_celebration(
        self,
        celebration_id: UUID,
        user_id: UUID,
        data: CelebrationUpdate,
    ) -> CelebrationResponse:
        async with self._uow() as uow:
            celebration = await validate_celebration_ownership(
                celebration_id, user_id, uow
            )
            celebration = await uow.occasions.celebrations.update(
                celebration, data.model_dump(exclude_unset=True)
            )
            return CelebrationResponse.model_validate(celebration)

    async def delete_celebration(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            celebration = await validate_celebration_ownership(
                celebration_id, user_id, uow
            )
            await uow.occasions.celebrations.soft_delete(celebration)

    # ── 4. Celebration Guests ──────────────────────────────────────────────────

    @staticmethod
    async def _write_guest_history(
        uow,
        *,
        guest_id: UUID,
        celebration_id: UUID,
        event_type,
        previous_status=None,
        new_status=None,
    ) -> None:
        from app.models.occasions.celebration_guest_history import CelebrationGuestHistory

        await uow.occasions.guest_history.create(
            CelebrationGuestHistory(
                celebration_guest_id=guest_id,
                celebration_id=celebration_id,
                event_type=event_type,
                previous_status=previous_status,
                new_status=new_status,
            )
        )

    async def add_guest(
        self,
        celebration_id: UUID,
        user_id: UUID,
        data: CelebrationGuestCreate,
    ) -> CelebrationGuestResponse:
        import secrets
        from app.models.enums import GuestHistoryEventType

        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            await validate_guest_limit(celebration_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["celebration_id"] = celebration_id
            payload["rsvp_token"] = secrets.token_urlsafe(24)
            guest = await uow.occasions.guests.create_from_dict(payload)
            await self._write_guest_history(
                uow, guest_id=guest.id, celebration_id=celebration_id,
                event_type=GuestHistoryEventType.INVITED,
            )
            await uow.commit()
            return CelebrationGuestResponse.model_validate(guest)

    async def update_guest(
        self,
        celebration_id: UUID,
        guest_id: UUID,
        user_id: UUID,
        data: CelebrationGuestUpdate,
    ) -> CelebrationGuestResponse:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            guest = await uow.occasions.guests.get_by_id(guest_id)
            if guest is None or guest.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"guest {guest_id}")
            previous_status = guest.rsvp_status
            update_data = data.model_dump(exclude_unset=True)
            guest = await uow.occasions.guests.update(guest, update_data)
            if "rsvp_status" in update_data and guest.rsvp_status != previous_status:
                from app.models.enums import GuestHistoryEventType
                await self._write_guest_history(
                    uow, guest_id=guest.id, celebration_id=celebration_id,
                    event_type=GuestHistoryEventType.RSVP_CHANGED,
                    previous_status=previous_status, new_status=guest.rsvp_status,
                )
            await uow.commit()
            return CelebrationGuestResponse.model_validate(guest)

    async def remove_guest(
        self,
        celebration_id: UUID,
        guest_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            guest = await uow.occasions.guests.get_by_id(guest_id)
            if guest is None or guest.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"guest {guest_id}")
            await uow.occasions.guests.delete(guest)

    async def list_guests(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> list[CelebrationGuestResponse]:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            guests = await uow.occasions.guests.find_by_celebration(celebration_id)
            return [CelebrationGuestResponse.model_validate(g) for g in guests]

    async def list_guest_history(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> list[CelebrationGuestHistoryResponse]:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            history = await uow.occasions.guest_history.find_by_celebration(celebration_id)
            return [CelebrationGuestHistoryResponse.model_validate(h) for h in history]

    # ── Public RSVP (no auth — reached via the guest's shared link) ────────────

    async def get_guest_rsvp(self, token: str) -> GuestRSVPPublicResponse:
        from datetime import date, datetime, timezone

        from app.services.occasions.exceptions import GuestNotFoundError

        async with self._uow() as uow:
            guest = await uow.occasions.guests.find_by_rsvp_token(token)
            if guest is None:
                raise GuestNotFoundError(token)

            celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
            if celebration is None:
                raise GuestNotFoundError(token)

            if guest.invitation_opened_at is None:
                guest = await uow.occasions.guests.update(
                    guest, {"invitation_opened_at": datetime.now(tz=timezone.utc)}
                )
                from app.models.enums import GuestHistoryEventType
                await self._write_guest_history(
                    uow, guest_id=guest.id, celebration_id=guest.celebration_id,
                    event_type=GuestHistoryEventType.INVITATION_OPENED,
                )
                await uow.commit()

            can_still_respond = date.today() < celebration.celebration_date

            return GuestRSVPPublicResponse(
                guest_name=guest.name,
                rsvp_status=guest.rsvp_status,
                can_still_respond=can_still_respond,
                celebration_title=celebration.title,
                celebration_date=celebration.celebration_date,
                venue_name=celebration.venue_name,
                venue_address=celebration.venue_address,
            )

    async def submit_guest_rsvp(self, token: str, data: GuestRSVPSubmit) -> GuestRSVPPublicResponse:
        from datetime import date, datetime, timezone

        from app.services.exceptions import BusinessRuleError
        from app.services.occasions.exceptions import GuestNotFoundError

        async with self._uow() as uow:
            guest = await uow.occasions.guests.find_by_rsvp_token(token)
            if guest is None:
                raise GuestNotFoundError(token)

            celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
            if celebration is None:
                raise GuestNotFoundError(token)

            # Guests may respond (or change their response) up to the day
            # before the event — matches the "coming/maybe/pending/ignored,
            # changeable up to a day before" requirement.
            if date.today() >= celebration.celebration_date:
                raise BusinessRuleError("The RSVP window for this event has closed.")

            now = datetime.now(tz=timezone.utc)
            previous_status = guest.rsvp_status
            update_payload = {
                "rsvp_status": data.rsvp_status,
                "rsvp_responded_at": now,
            }
            if data.notes:
                update_payload["notes"] = data.notes
            if guest.invitation_opened_at is None:
                update_payload["invitation_opened_at"] = now

            guest = await uow.occasions.guests.update(guest, update_payload)

            from app.models.enums import GuestHistoryEventType
            await self._write_guest_history(
                uow, guest_id=guest.id, celebration_id=guest.celebration_id,
                event_type=GuestHistoryEventType.RSVP_CHANGED,
                previous_status=previous_status, new_status=guest.rsvp_status,
            )
            await uow.commit()

            return GuestRSVPPublicResponse(
                guest_name=guest.name,
                rsvp_status=guest.rsvp_status,
                can_still_respond=date.today() < celebration.celebration_date,
                celebration_title=celebration.title,
                celebration_date=celebration.celebration_date,
                venue_name=celebration.venue_name,
                venue_address=celebration.venue_address,
            )

    # ── 5. Celebration Checklist ───────────────────────────────────────────────

    async def add_checklist_item(
        self,
        celebration_id: UUID,
        user_id: UUID,
        data: CelebrationChecklistCreate,
    ) -> CelebrationChecklistResponse:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            await validate_checklist_limit(celebration_id, uow)
            payload = data.model_dump(exclude_unset=True)
            payload["celebration_id"] = celebration_id
            item = await uow.occasions.checklist.create_from_dict(payload)
            return CelebrationChecklistResponse.model_validate(item)

    async def update_checklist_item(
        self,
        celebration_id: UUID,
        item_id: UUID,
        user_id: UUID,
        data: CelebrationChecklistUpdate,
    ) -> CelebrationChecklistResponse:
        from datetime import datetime, timezone

        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            item = await uow.occasions.checklist.get_by_id(item_id)
            if item is None or item.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"checklist item {item_id}")

            update_data = data.model_dump(exclude_unset=True)

            # Handle is_completed toggle: stamp completed_at
            if "is_completed" in update_data:
                if update_data["is_completed"] and not item.completed_at:
                    from app.models.occasions.celebration_checklist import ChecklistItemStatus

                    update_data["completed_at"] = datetime.now(tz=timezone.utc)
                    update_data["status"] = ChecklistItemStatus.COMPLETED
                elif not update_data["is_completed"]:
                    update_data["completed_at"] = None

            item = await uow.occasions.checklist.update(item, update_data)
            return CelebrationChecklistResponse.model_validate(item)

    async def delete_checklist_item(
        self,
        celebration_id: UUID,
        item_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            item = await uow.occasions.checklist.get_by_id(item_id)
            if item is None or item.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"checklist item {item_id}")
            await uow.occasions.checklist.delete(item)

    async def list_checklist(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> list[CelebrationChecklistResponse]:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            items = await uow.occasions.checklist.find_by_celebration(celebration_id)
            return [CelebrationChecklistResponse.model_validate(i) for i in items]

    async def get_checklist_progress(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> dict:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            from app.models.occasions.celebration_checklist import CelebrationChecklist

            total = await uow.occasions.checklist.count(
                CelebrationChecklist.celebration_id == celebration_id
            )
            completed = await uow.occasions.checklist.count_completed(celebration_id)
            pct = calculate_celebration_progress(total, completed)
            return {"total": total, "completed": completed, "pct": pct}

    # ── 6. Celebration Timeline ────────────────────────────────────────────────

    async def add_timeline_event(
        self,
        celebration_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            await validate_timeline_limit(celebration_id, uow)
            payload = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            payload["celebration_id"] = celebration_id
            event = await uow.occasions.timeline.create_from_dict(payload)
            return CelebrationTimelineResponse.model_validate(event)  # type: ignore[call-arg]

    async def update_timeline_event(
        self,
        celebration_id: UUID,
        event_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            event = await uow.occasions.timeline.get_by_id(event_id)
            if event is None or event.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"timeline event {event_id}")
            event = await uow.occasions.timeline.update(
                event, data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return CelebrationTimelineResponse.model_validate(event)  # type: ignore[call-arg]

    async def delete_timeline_event(
        self,
        celebration_id: UUID,
        event_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            event = await uow.occasions.timeline.get_by_id(event_id)
            if event is None or event.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"timeline event {event_id}")
            await uow.occasions.timeline.delete(event)

    async def list_timeline(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> list[object]:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            events = await uow.occasions.timeline.find_by_celebration(celebration_id)
            sorted_events = sort_timeline_events(list(events))
            return [CelebrationTimelineResponse.model_validate(e) for e in sorted_events]  # type: ignore[call-arg]

    # ── 7. Celebration Notes ───────────────────────────────────────────────────

    async def add_note(
        self,
        celebration_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            # Enforce note limit
            from app.models.occasions.celebration_note import CelebrationNote

            count = await uow.occasions.notes.count(
                CelebrationNote.celebration_id == celebration_id
            )
            if count >= MAX_NOTES_PER_CELEBRATION:
                from app.services.exceptions import BusinessRuleError

                raise BusinessRuleError(
                    f"Note limit reached. A celebration may have at most "
                    f"{MAX_NOTES_PER_CELEBRATION} notes."
                )
            payload = data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            payload["celebration_id"] = celebration_id
            payload["author_id"] = user_id
            note = await uow.occasions.notes.create_from_dict(payload)
            return CelebrationNoteResponse.model_validate(note)  # type: ignore[call-arg]

    async def update_note(
        self,
        celebration_id: UUID,
        note_id: UUID,
        user_id: UUID,
        data: object,
    ) -> object:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            note = await uow.occasions.notes.get_by_id(note_id)
            if note is None or note.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"note {note_id}")
            note = await uow.occasions.notes.update(
                note, data.model_dump(exclude_unset=True)  # type: ignore[union-attr]
            )
            return CelebrationNoteResponse.model_validate(note)  # type: ignore[call-arg]

    async def delete_note(
        self,
        celebration_id: UUID,
        note_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            note = await uow.occasions.notes.get_by_id(note_id)
            if note is None or note.celebration_id != celebration_id:
                raise CelebrationNotFoundError(f"note {note_id}")
            await uow.occasions.notes.delete(note)

    async def list_notes(
        self,
        celebration_id: UUID,
        user_id: UUID,
    ) -> list[object]:
        async with self._uow() as uow:
            await validate_celebration_ownership(celebration_id, user_id, uow)
            notes = await uow.occasions.notes.find_by_celebration(celebration_id)
            return [CelebrationNoteResponse.model_validate(n) for n in notes]  # type: ignore[call-arg]
