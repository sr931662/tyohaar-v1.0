"""
EventService — the invitation-management layer over celebrations.

One engine for both customer journeys. A customer who booked through Tyohaar
and one organising independently use exactly these methods on exactly the same
tables; ``Celebration.event_source`` only changes onboarding, entitlements and
which fields are locked. Guests, links, passes and the gate stay in
InvitationService and are reused from here, never reimplemented.

Layout:
  1. Shared helpers       settings, segments, cards, date rollups
  2. Organiser: events    list / detail / create / update / settings / publish
  3. Organiser: functions create / update / reorder / assign guests
  4. Organiser: households, import
  5. Organiser: insight   analytics / RSVPs / food / activity / reminders
  6. Guest (public)       view / track / RSVP / general link / preview
  7. Bookings             associate a confirmed booking; vendor summary

Authorisation: every organiser method resolves the event with
``InvitationService._owned_celebration`` (404 for someone else's). Every public
method sees only what its token names. Ids a guest sends are checked against
that set, so a valid link can't be pointed at another guest or event.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
import uuid
from datetime import date, datetime, time, timedelta, timezone
from urllib.parse import quote

import segno
from sqlalchemy import and_, case, delete, func, select

from app.core.config import settings
from app.models.bookings.booking import Booking
from app.models.enums import (
    BookingStatus,
    CelebrationStatus,
    EventSource,
    GuestEntryStatus,
    GuestGroupResponseMode,
    GuestHistoryEventType,
    GuestPassStatus,
    InvitationPublishStatus,
    NotificationType,
    RSVPStatus,
)
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.celebration_guest_history import CelebrationGuestHistory
from app.models.occasions.event_planning import (
    CelebrationFunction,
    CelebrationGuestGroup,
    GuestFunctionResponse,
)
from app.models.occasions.occasion import Occasion
from app.models.packages.package import Package
from app.schemas.events import (
    DIETARY_TYPES,
    EVENT_TYPES,
    ActivityItem,
    BookingInfo,
    EventAnalytics,
    EventCard,
    EventCounts,
    EventCreate,
    EventDetail,
    EventList,
    EventUpdate,
    FoodFunctionSummary,
    FoodSummary,
    FunctionCreate,
    FunctionResponse,
    FunctionStats,
    FunctionUpdate,
    GeneralLinkUpdate,
    GuestFunctionsUpdate,
    GuestGroupCreate,
    GuestGroupMember,
    GuestGroupResponse,
    GuestGroupUpdate,
    ImportResult,
    ImportRowResult,
    InvitationDesign,
    InvitationSettings,
    InvitationSettingsUpdate,
    OperationsApproval,
    PreviewLink,
    PublicClaim,
    PublicClaimResult,
    PublicEvent,
    PublicFunction,
    PublicInvitationPage,
    PublicMember,
    PublicMemberResponse,
    PublicPass,
    PublicRSVPConfig,
    PublicRSVPRequest,
    ReminderCandidate,
    ReminderCandidates,
    ReminderRecord,
    RSVPRow,
    VendorGuestSummary,
)
from app.schemas.invitations import GuestInvitationCreate
from app.services.base import BaseService
from app.services.exceptions import BusinessRuleError, ConflictError, ValidationError
from app.services.invitations import credentials as cred
from app.services.invitations import entitlements as ent
from app.services.invitations import rules
from app.services.invitations.service import Actor, InvitationService, _host_label, _now
from app.services.occasions.exceptions import CelebrationNotFoundError, GuestNotFoundError

logger = logging.getLogger(__name__)

MAX_IMPORT_ROWS = 1000
MAX_IMPORT_BYTES = 2 * 1024 * 1024
PREVIEW_TTL = timedelta(minutes=30)
DEAD_BOOKING_STATUSES = (BookingStatus.CANCELLED, BookingStatus.REFUNDED)
_OPS_KEY = "operations"

# Header spellings accepted when importing a guest list.
_IMPORT_COLUMNS = {
    "name": ("name", "guest name", "guest", "full name"),
    "phone": ("phone", "mobile", "mobile number", "phone number", "contact", "whatsapp"),
    "email": ("email", "email address", "e-mail"),
    "group": ("group", "household", "family", "group name"),
    "category": ("category", "tag", "side", "guest category"),
    "plus_ones": ("plus ones", "plus_ones", "extra guests", "plus one", "+1"),
    "functions": ("functions", "function", "events"),
    "notes": ("notes", "note", "remarks"),
}


def settings_of(celebration: Celebration) -> InvitationSettings:
    stored = dict(celebration.invitation_settings or {})
    stored.pop(_OPS_KEY, None)  # server-written, never part of the editable shape
    try:
        return InvitationSettings.model_validate(stored)
    except ValueError:
        # Stored by an older version: defaults are safer than a broken page.
        logger.warning("Ignoring malformed invitation settings on %s", celebration.id)
        return InvitationSettings()


def event_type_label(celebration: Celebration, occasion_name: str | None = None) -> str:
    if celebration.event_type == "custom" and celebration.custom_event_type:
        return celebration.custom_event_type
    if celebration.event_type in EVENT_TYPES:
        return EVENT_TYPES[celebration.event_type]
    return occasion_name or "Celebration"


def segment_of(celebration: Celebration, today: date, *, effective_status: str | None = None) -> tuple[str, int | None]:
    """(upcoming|ongoing|completed, days until it starts when upcoming)."""
    status = effective_status or celebration.status.value
    start = celebration.event_start_date or celebration.celebration_date
    end = celebration.event_end_date or celebration.celebration_date
    start, end = min(start, celebration.celebration_date), max(end, celebration.celebration_date)
    if status in (CelebrationStatus.CANCELLED.value, CelebrationStatus.COMPLETED.value) or end < today:
        return "completed", None
    if status == CelebrationStatus.IN_PROGRESS.value or start <= today:
        return "ongoing", None
    return "upcoming", (start - today).days


def maps_url(*, lat=None, lng=None, venue_name: str | None = None, address: str | None = None) -> str | None:
    if lat is not None and lng is not None:
        return f"https://www.google.com/maps/search/?api=1&query={lat},{lng}"
    query = ", ".join(p for p in (venue_name, address) if p)
    return f"https://www.google.com/maps/search/?api=1&query={quote(query)}" if query else None


def _csv_cell(value) -> str:
    """Spreadsheet apps execute cells starting with these; guests choose this text."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


class EventService(BaseService):
    def __init__(self, session_factory=None) -> None:
        if session_factory is None:
            from app.db.session import AsyncSessionLocal

            session_factory = AsyncSessionLocal
        super().__init__(session_factory)
        self.invites = InvitationService(session_factory)

    # ══ 1. Shared helpers ═════════════════════════════════════════════════════

    async def _owned(self, uow, celebration_id, user_id, *, lock: bool = False) -> Celebration:
        return await InvitationService._owned_celebration(uow, celebration_id, user_id, lock=lock)

    @staticmethod
    async def _functions(uow, celebration_id, *, include_cancelled: bool = True) -> list[CelebrationFunction]:
        F = CelebrationFunction
        filters = [F.celebration_id == celebration_id]
        if not include_cancelled:
            filters.append(F.is_cancelled.is_(False))
        return await uow.occasions.functions.find_many(
            *filters, order_by=[F.display_order.asc(), F.function_date.asc(), F.created_at.asc()], limit=200,
        )

    @staticmethod
    async def _sync_event_dates(uow, celebration: Celebration) -> None:
        """Keep the date span, and so pass validity and the Events tabs, in step with functions."""
        F = CelebrationFunction
        low, high = (await uow.session.execute(
            select(func.min(F.function_date), func.max(F.function_date))
            .where(F.celebration_id == celebration.id, F.is_cancelled.is_(False))
        )).one()
        changes: dict = {"event_start_date": low, "event_end_date": high}
        # On an independent event the functions are the schedule. A booked
        # event's main date belongs to the booking and is left alone.
        if celebration.event_source is EventSource.STANDALONE and low is not None:
            changes["celebration_date"] = low
        await uow.occasions.celebrations.update(celebration, changes)

    @staticmethod
    async def assign_functions(uow, guest: CelebrationGuest, function_ids: list[uuid.UUID] | None = None) -> None:
        """
        Invite a guest to functions. None means every active one, which is the
        rule for anyone added without a choice being made, whichever screen
        added them. Existing rows (and any answers on them) are kept.
        """
        if function_ids is None:
            F = CelebrationFunction
            function_ids = list((await uow.session.execute(
                select(F.id).where(F.celebration_id == guest.celebration_id, F.is_cancelled.is_(False))
            )).scalars().all())
        if not function_ids:
            return
        R = GuestFunctionResponse
        existing = set((await uow.session.execute(
            select(R.function_id).where(R.celebration_guest_id == guest.id, R.function_id.is_not(None))
        )).scalars().all())
        for function_id in function_ids:
            if function_id not in existing:
                await uow.occasions.function_responses.create_from_dict({
                    "celebration_id": guest.celebration_id,
                    "function_id": function_id,
                    "celebration_guest_id": guest.id,
                    "status": RSVPStatus.PENDING,
                })

    @staticmethod
    async def _rollup(uow, guest: CelebrationGuest, *, now: datetime | None = None) -> None:
        """Refresh the guest-level answer that the gate and guest list read."""
        R = GuestFunctionResponse
        rows = (await uow.session.execute(
            select(R.status, R.attendee_count).where(R.celebration_guest_id == guest.id)
        )).all()
        if not rows:
            return
        status = rules.rollup_rsvp([r[0] for r in rows])
        party = max((r[1] or 1 for r in rows if r[0] is RSVPStatus.ATTENDING), default=None)
        changes: dict = {"rsvp_status": status, "rsvp_party_size": party}
        if now is not None and status not in (RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE):
            changes["rsvp_responded_at"] = now
        await uow.occasions.guests.update(guest, changes)

    @staticmethod
    async def _counts_by_event(uow, celebration_ids: list[uuid.UUID]) -> dict[uuid.UUID, EventCounts]:
        if not celebration_ids:
            return {}
        G = CelebrationGuest
        active = G.pass_status == GuestPassStatus.ACTIVE
        rows = (await uow.session.execute(
            select(
                G.celebration_id,
                func.count().filter(active),
                func.count().filter(and_(active, G.rsvp_status == RSVPStatus.ATTENDING)),
                func.count().filter(and_(active, G.rsvp_status == RSVPStatus.MAYBE)),
                func.count().filter(and_(active, G.rsvp_status == RSVPStatus.DECLINED)),
                func.count().filter(and_(active, G.rsvp_status.in_([RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE]))),
            ).where(G.celebration_id.in_(celebration_ids)).group_by(G.celebration_id)
        )).all()
        return {
            r[0]: EventCounts(invited=r[1], confirmed=r[2], maybe=r[3], declined=r[4], pending=r[5])
            for r in rows
        }

    async def _cards(self, uow, celebrations: list[Celebration]) -> list[EventCard]:
        """Batched, so a customer with many events costs a few queries, not N."""
        if not celebrations:
            return []
        ids = [c.id for c in celebrations]
        counts = await self._counts_by_event(uow, ids)
        F = CelebrationFunction
        function_counts = dict((await uow.session.execute(
            select(F.celebration_id, func.count())
            .where(F.celebration_id.in_(ids), F.is_cancelled.is_(False))
            .group_by(F.celebration_id)
        )).all())

        occasion_ids = list({c.occasion_id for c in celebrations if c.occasion_id})
        occasions = {o.id: o for o in await uow.occasions.occasions.get_by_ids(occasion_ids)} if occasion_ids else {}

        bookings: dict[uuid.UUID, list[Booking]] = {}
        for b in (await uow.session.execute(
            select(Booking).where(Booking.celebration_id.in_(ids)).order_by(Booking.created_at.asc())
        )).scalars().all():
            bookings.setdefault(b.celebration_id, []).append(b)
        package_ids = list({b.package_id for rows in bookings.values() for b in rows})
        package_covers = dict((await uow.session.execute(
            select(Package.id, Package.cover_image_url).where(Package.id.in_(package_ids))
        )).all()) if package_ids else {}

        today = rules.event_today(settings.EVENT_TIMEZONE)
        cards = []
        for c in celebrations:
            rows = bookings.get(c.id, [])
            live = [b for b in rows if b.booking_status not in DEAD_BOOKING_STATUSES]
            booking = live[0] if live else (rows[-1] if rows else None)
            # The booking flow creates the celebration, so if every booking on
            # such an event fell through the event isn't happening. An event
            # the customer created themselves goes on regardless.
            status = c.status.value
            if c.event_source is EventSource.TYOHAAR_BOOKING and rows and not live and c.event_type is None:
                status = CelebrationStatus.CANCELLED.value
            segment, days = segment_of(c, today, effective_status=status)
            occasion = occasions.get(c.occasion_id) if c.occasion_id else None
            cover = c.cover_image_url or (package_covers.get(booking.package_id) if booking else None) \
                or (occasion.banner_url if occasion else None)
            cards.append(EventCard(
                id=c.id,
                title=c.title,
                event_type=c.event_type,
                event_type_label=event_type_label(c, occasion.name if occasion else None),
                cover_image_url=cover,
                celebration_date=c.celebration_date,
                end_date=c.event_end_date,
                start_time=c.start_time or (booking.scheduled_start_time if booking else None),
                venue_name=c.venue_name,
                venue_address=c.venue_address,
                status=status,
                segment=segment,
                days_remaining=days,
                event_source=c.event_source.value,
                booking_id=booking.id if booking else None,
                booking_status=booking.booking_status.value if booking else None,
                function_count=function_counts.get(c.id, 0),
                invitation_status=c.invitation_status.value,
                invitations_configured=c.invitation_settings is not None,
                counts=counts.get(c.id, EventCounts()),
            ))
        return cards

    # ══ 2. Organiser: events ══════════════════════════════════════════════════

    async def list_events(self, user_id: uuid.UUID) -> EventList:
        async with self._uow() as uow:
            celebrations = await uow.occasions.celebrations.find_many(
                Celebration.customer_id == user_id,
                order_by=Celebration.celebration_date.asc(),
                limit=200,
            )
            cards = await self._cards(uow, celebrations)
        upcoming = [c for c in cards if c.segment == "upcoming"]
        ongoing = [c for c in cards if c.segment == "ongoing"]
        completed = sorted((c for c in cards if c.segment == "completed"), key=lambda c: c.celebration_date, reverse=True)
        return EventList(upcoming=upcoming, ongoing=ongoing, completed=completed)

    async def _detail(self, uow, celebration: Celebration, base_url: str | None) -> EventDetail:
        card = (await self._cards(uow, [celebration]))[0]
        functions = await self._functions(uow, celebration.id)
        booking_info = None
        if card.booking_id and celebration.event_source is EventSource.TYOHAAR_BOOKING:
            row = (await uow.session.execute(
                select(Booking, Package.name, Package.cover_image_url)
                .outerjoin(Package, Package.id == Booking.package_id)
                .where(Booking.id == card.booking_id)
            )).first()
            if row:
                b, package_name, package_cover = row
                booking_info = BookingInfo(
                    booking_id=b.id,
                    booking_number=b.booking_number,
                    status=b.booking_status.value,
                    package_name=package_name,
                    package_cover_url=package_cover,
                    scheduled_date=b.scheduled_date,
                )
        token = cred.decrypt(celebration.general_link_enc)
        current = settings_of(celebration)
        booked = celebration.event_source is EventSource.TYOHAAR_BOOKING
        return EventDetail(
            **card.model_dump(),
            description=celebration.description,
            host_name=celebration.host_name,
            custom_event_type=celebration.custom_event_type,
            contact_name=celebration.contact_name,
            contact_phone=celebration.contact_phone,
            end_time=celebration.end_time,
            settings=current,
            functions=[FunctionResponse.model_validate(f) for f in functions],
            groups=await self._group_views(uow, celebration.id, base_url),
            entitlements=await ent.for_event(uow, celebration),
            booking=booking_info,
            general_link_url=InvitationService.invite_url(base_url, token) if current.general_link.enabled else None,
            invitation_published_at=celebration.invitation_published_at,
            operations_summary=(celebration.invitation_settings or {}).get(_OPS_KEY),
            locked_fields=["celebration_date", "venue_name", "venue_address"] if booked and card.booking_id else [],
        )

    async def get_event(self, celebration_id, user_id, *, base_url) -> EventDetail:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            return await self._detail(uow, celebration, base_url)

    async def create_event(self, user, data: EventCreate, *, base_url) -> tuple[EventDetail, bool]:
        """Returns (event, created). The idempotency key makes a double-tap harmless."""
        today = rules.event_today(settings.EVENT_TIMEZONE)
        if data.celebration_date < today:
            raise ValidationError("The event date has passed.", field="celebration_date")
        for f in data.functions:
            if f.function_date < today:
                raise ValidationError(f"{f.name}'s date has passed.", field="functions")
        async with self._uow() as uow:
            metadata_key = data.client_request_id
            if metadata_key:
                existing = await uow.occasions.celebrations.find_one(
                    Celebration.customer_id == user.id,
                    Celebration.extra_metadata["client_request_id"].astext == metadata_key,
                )
                if existing is not None:
                    return await self._detail(uow, existing, base_url), False

            # Reuse the occasion's artwork when the category matches one, but
            # an event never needs an occasion Tyohaar happens to sell.
            occasion = await uow.occasions.occasions.find_one(
                Occasion.slug == data.event_type.replace("_", "-")
            )
            celebration = await uow.occasions.celebrations.create_from_dict({
                "customer_id": user.id,
                "occasion_id": occasion.id if occasion else None,
                "title": data.title,
                "event_type": data.event_type,
                "custom_event_type": data.custom_event_type if data.event_type == "custom" else None,
                "host_name": data.host_name,
                "description": data.description,
                "celebration_date": data.celebration_date,
                "start_time": data.start_time,
                "end_time": data.end_time,
                "venue_name": data.venue_name,
                "venue_address": data.venue_address,
                "cover_image_url": data.cover_image_url,
                "contact_name": data.contact_name,
                "contact_phone": data.contact_phone,
                "status": CelebrationStatus.PLANNING,
                "event_source": EventSource.STANDALONE,
                "invitation_status": InvitationPublishStatus.DRAFT,
                "guest_count": 0,
                "extra_metadata": {"client_request_id": metadata_key} if metadata_key else None,
            })
            for index, f in enumerate(data.functions):
                await self._insert_function(uow, celebration, f, index)
            if data.functions:
                await self._sync_event_dates(uow, celebration)
            return await self._detail(uow, celebration, base_url), True

    @staticmethod
    async def _insert_function(uow, celebration, data: FunctionCreate, order: int) -> CelebrationFunction:
        return await uow.occasions.functions.create_from_dict({
            "celebration_id": celebration.id,
            "display_order": order,
            **data.model_dump(exclude={"invite_all_guests"}),
        })

    async def update_event(self, celebration_id, user_id, data: EventUpdate, *, base_url) -> EventDetail:
        changes = data.model_dump(exclude_unset=True)
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            if celebration.event_source is EventSource.TYOHAAR_BOOKING:
                # A booked event's date and venue are commitments to vendors. The
                # invitation can say something different through display
                # overrides, but nothing here may quietly change the booking.
                locked = {"celebration_date", "venue_name", "venue_address"} & set(changes)
                if locked and any(getattr(celebration, k) != changes[k] for k in locked):
                    raise ConflictError(
                        "This event's date and venue come from your booking. "
                        "Change them on the booking, or adjust what guests see in the invitation settings."
                    )
                for key in locked:
                    changes.pop(key)
            if changes.get("celebration_date") and changes["celebration_date"] < rules.event_today(settings.EVENT_TIMEZONE):
                raise ValidationError("The event date has passed.", field="celebration_date")
            if "title" in changes and not changes["title"]:
                raise ValidationError("Give the event a name.", field="title")
            if changes:
                celebration = await uow.occasions.celebrations.update(celebration, changes)
            return await self._detail(uow, celebration, base_url)

    async def update_settings(self, celebration_id, user_id, data: InvitationSettingsUpdate, *, base_url) -> EventDetail:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            entitlements = await ent.for_event(uow, celebration)
            current = settings_of(celebration)
            incoming = data.model_dump(exclude_unset=True, exclude_none=True)
            if "design" in incoming and not entitlements.custom_templates and incoming["design"].get("template") != "classic":
                raise BusinessRuleError("Custom templates aren't included for this event.")
            if not entitlements.food_preferences and incoming.get("rsvp", {}).get("ask_food"):
                raise BusinessRuleError("Food preferences aren't included for this event.")
            if not entitlements.advanced_rsvp and incoming.get("rsvp", {}).get("questions"):
                raise BusinessRuleError("Custom RSVP questions aren't included for this event.")
            merged = current.model_copy(update={k: getattr(data, k) for k in incoming})
            await self._write_settings(uow, celebration, merged)
            return await self._detail(uow, celebration, base_url)

    @staticmethod
    async def _write_settings(uow, celebration: Celebration, value: InvitationSettings) -> None:
        stored = value.model_dump(mode="json")
        ops = (celebration.invitation_settings or {}).get(_OPS_KEY)
        if ops:
            stored[_OPS_KEY] = ops
        await uow.occasions.celebrations.update(celebration, {"invitation_settings": stored})

    async def publish(self, celebration_id, user_id, *, base_url, published: bool = True) -> EventDetail:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            changes: dict = {
                "invitation_status": InvitationPublishStatus.PUBLISHED if published else InvitationPublishStatus.DRAFT,
            }
            if published:
                changes["invitation_published_at"] = celebration.invitation_published_at or _now()
            if celebration.invitation_settings is None:
                changes["invitation_settings"] = InvitationSettings().model_dump(mode="json")
            celebration = await uow.occasions.celebrations.update(celebration, changes)
            return await self._detail(uow, celebration, base_url)

    async def update_general_link(self, celebration_id, user_id, data: GeneralLinkUpdate, *, base_url) -> EventDetail:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            current = settings_of(celebration)
            general = current.general_link.model_copy(update={
                "enabled": data.enabled,
                **({"plus_ones_allowed": data.plus_ones_allowed} if data.plus_ones_allowed is not None else {}),
            })
            changes: dict = {}
            if data.enabled and (data.rotate or not celebration.general_link_hash):
                token = cred.new_link_token()
                changes = {
                    "general_link_hash": cred.hash_secret(cred.GENERAL_LINK_KIND, token),
                    "general_link_enc": cred.encrypt(token),
                }
            if changes:
                celebration = await uow.occasions.celebrations.update(celebration, changes)
            await self._write_settings(uow, celebration, current.model_copy(update={"general_link": general}))
            return await self._detail(uow, celebration, base_url)

    async def preview_link(self, celebration_id, user_id, *, base_url) -> PreviewLink:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            expires = _now() + PREVIEW_TTL
            # Encrypted, not just signed: the id stays private and the link dies by itself.
            token = cred.encrypt(f"{celebration.id}:{int(expires.timestamp())}")
            origin = (settings.INVITE_BASE_URL or base_url or "").rstrip("/")
            return PreviewLink(url=f"{origin}/i/preview/{token}", expires_at=expires)

    # ══ 3. Organiser: functions ═══════════════════════════════════════════════

    async def create_function(self, celebration_id, user_id, data: FunctionCreate) -> FunctionResponse:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            if data.function_date < rules.event_today(settings.EVENT_TIMEZONE):
                raise ValidationError("That date has passed.", field="function_date")
            count = await uow.occasions.functions.count(CelebrationFunction.celebration_id == celebration.id)
            if count >= 30:
                raise BusinessRuleError("An event can have at most 30 functions.")
            function = await self._insert_function(uow, celebration, data, count)
            guests = await uow.occasions.guests.find_many(
                CelebrationGuest.celebration_id == celebration.id,
                CelebrationGuest.pass_status == GuestPassStatus.ACTIVE,
                limit=5000,
            )
            await self._split_event_response(uow, celebration, function, guests)
            if data.invite_all_guests:
                for guest in guests:
                    await self.assign_functions(uow, guest, [function.id])
                    await self._rollup(uow, guest)
            await self._sync_event_dates(uow, celebration)
            return FunctionResponse.model_validate(function)

    @staticmethod
    async def _split_event_response(uow, celebration, function, guests) -> None:
        """
        The first function added to an event that already has answers: those
        answers were for the event as a whole, so they carry over to it rather
        than being orphaned, and nobody gets asked again.
        """
        R = GuestFunctionResponse
        rows = await uow.occasions.function_responses.find_many(
            R.celebration_id == celebration.id, R.function_id.is_(None), limit=5000,
        )
        for row in rows:
            await uow.occasions.function_responses.update(row, {"function_id": function.id})

    async def _owned_function(self, uow, celebration_id, function_id) -> CelebrationFunction:
        function = await uow.occasions.functions.get_by_id(function_id)
        if function is None or function.celebration_id != celebration_id:
            raise ValidationError("That function isn't part of this event.", field="function_id")
        return function

    async def update_function(self, celebration_id, function_id, user_id, data: FunctionUpdate) -> FunctionResponse:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            function = await self._owned_function(uow, celebration.id, function_id)
            changes = data.model_dump(exclude_unset=True)
            if "name" in changes and not changes["name"]:
                raise ValidationError("Give the function a name.", field="name")
            if "function_date" in changes and changes["function_date"] is None:
                changes.pop("function_date")
            if "is_cancelled" in changes and changes["is_cancelled"] is None:
                changes.pop("is_cancelled")
            function = await uow.occasions.functions.update(function, changes)
            await self._sync_event_dates(uow, celebration)
            return FunctionResponse.model_validate(function)

    async def delete_function(self, celebration_id, function_id, user_id) -> None:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            function = await self._owned_function(uow, celebration.id, function_id)
            R = GuestFunctionResponse
            answered = await uow.occasions.function_responses.count(
                R.function_id == function.id, R.responded_at.is_not(None),
            )
            if answered:
                raise ConflictError(
                    f"{answered} guest(s) have already answered for {function.name}. "
                    "Cancel the function instead, so their answers are kept."
                )
            await uow.occasions.functions.delete(function)
            await uow.session.flush()
            await self._sync_event_dates(uow, celebration)

    async def reorder_functions(self, celebration_id, user_id, ids: list[uuid.UUID]) -> list[FunctionResponse]:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            functions = {f.id: f for f in await self._functions(uow, celebration.id)}
            if set(ids) != set(functions):
                raise ValidationError("Send every function exactly once.", field="function_ids")
            for order, function_id in enumerate(ids):
                await uow.occasions.functions.update(functions[function_id], {"display_order": order})
            return [FunctionResponse.model_validate(functions[i]) for i in ids]

    async def set_guest_functions(self, celebration_id, user, data: GuestFunctionsUpdate) -> int:
        """Replace which functions these guests are invited to. Answers on kept functions survive."""
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user.id, lock=True)
            valid = {f.id for f in await self._functions(uow, celebration.id)}
            wanted = set(data.function_ids)
            if not wanted <= valid:
                raise ValidationError("That function isn't part of this event.", field="function_ids")
            guests = await uow.occasions.guests.find_many(
                CelebrationGuest.celebration_id == celebration.id,
                CelebrationGuest.id.in_(data.guest_ids),
                limit=len(data.guest_ids),
            )
            if len(guests) != len(set(data.guest_ids)):
                raise GuestNotFoundError("guest")
            actor = Actor("host", user.id, _host_label(user))
            R = GuestFunctionResponse
            for guest in guests:
                before = set((await uow.session.execute(
                    select(R.function_id).where(R.celebration_guest_id == guest.id, R.function_id.is_not(None))
                )).scalars().all())
                if before == wanted:
                    continue
                await uow.session.execute(
                    delete(R).where(R.celebration_guest_id == guest.id, R.function_id.in_(before - wanted))
                )
                await self.assign_functions(uow, guest, sorted(wanted - before, key=str))
                await uow.session.flush()
                await self._rollup(uow, guest)
                await InvitationService._history(
                    uow, guest, GuestHistoryEventType.FUNCTIONS_CHANGED, actor,
                    details={"function_ids": sorted(str(f) for f in wanted)},
                )
            return len(guests)

    # ══ 4. Organiser: households, import ══════════════════════════════════════

    async def _group_views(self, uow, celebration_id, base_url) -> list[GuestGroupResponse]:
        groups = await uow.occasions.guest_groups.find_many(
            CelebrationGuestGroup.celebration_id == celebration_id,
            order_by=CelebrationGuestGroup.name.asc(),
            limit=1000,
        )
        if not groups:
            return []
        G = CelebrationGuest
        members = await uow.occasions.guests.find_many(
            G.celebration_id == celebration_id, G.group_id.is_not(None), limit=5000,
        )
        by_group: dict[uuid.UUID, list[CelebrationGuest]] = {}
        for m in members:
            by_group.setdefault(m.group_id, []).append(m)
        views = []
        for group in groups:
            rows = by_group.get(group.id, [])
            primary = next((m for m in rows if m.id == group.primary_guest_id), None)
            active = primary is not None and primary.pass_status is GuestPassStatus.ACTIVE
            views.append(GuestGroupResponse(
                id=group.id,
                celebration_id=group.celebration_id,
                name=group.name,
                category=group.category,
                invitation_capacity=group.invitation_capacity,
                response_mode=group.response_mode,
                primary_guest_id=group.primary_guest_id,
                members=[GuestGroupMember(id=m.id, name=m.name, plus_ones_allowed=m.plus_ones_allowed) for m in rows],
                invite_url=InvitationService.invite_url(base_url, cred.decrypt(primary.link_token_enc)) if active else None,
            ))
        return views

    async def _apply_members(self, uow, celebration, group, guest_ids: list[uuid.UUID], primary_id) -> None:
        G = CelebrationGuest
        guests = await uow.occasions.guests.find_many(
            G.celebration_id == celebration.id, G.id.in_(guest_ids), limit=len(guest_ids) or 1,
        ) if guest_ids else []
        if len(guests) != len(set(guest_ids)):
            raise GuestNotFoundError("guest")
        current = await uow.occasions.guests.find_many(G.group_id == group.id, limit=500)
        wanted = set(guest_ids)
        for guest in current:
            if guest.id not in wanted:
                await uow.occasions.guests.update(guest, {"group_id": None})
        for guest in guests:
            await uow.occasions.guests.update(guest, {"group_id": group.id})
        if primary_id is not None and primary_id not in wanted:
            raise ValidationError("The main contact must be a member of the household.", field="primary_guest_id")
        primary = primary_id or (group.primary_guest_id if group.primary_guest_id in wanted else None) \
            or (guest_ids[0] if guest_ids else None)
        await uow.occasions.guest_groups.update(group, {"primary_guest_id": primary})

    async def create_group(self, celebration_id, user_id, data: GuestGroupCreate, *, base_url) -> list[GuestGroupResponse]:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            group = await uow.occasions.guest_groups.create_from_dict({
                "celebration_id": celebration.id,
                "name": data.name,
                "category": data.category,
                "invitation_capacity": data.invitation_capacity,
                "response_mode": data.response_mode,
            })
            await self._apply_members(uow, celebration, group, data.guest_ids, data.primary_guest_id)
            await uow.session.flush()
            return await self._group_views(uow, celebration.id, base_url)

    async def _owned_group(self, uow, celebration_id, group_id) -> CelebrationGuestGroup:
        group = await uow.occasions.guest_groups.get_by_id(group_id)
        if group is None or group.celebration_id != celebration_id:
            raise GuestNotFoundError(str(group_id))
        return group

    async def update_group(self, celebration_id, group_id, user_id, data: GuestGroupUpdate, *, base_url) -> list[GuestGroupResponse]:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            group = await self._owned_group(uow, celebration.id, group_id)
            changes = data.model_dump(exclude_unset=True, exclude={"guest_ids", "primary_guest_id"})
            if changes.get("name") is None:
                changes.pop("name", None)
            if changes.get("response_mode") is None:
                changes.pop("response_mode", None)
            if changes:
                group = await uow.occasions.guest_groups.update(group, changes)
            if data.guest_ids is not None or data.primary_guest_id is not None:
                if data.guest_ids is not None:
                    ids = data.guest_ids
                else:
                    G = CelebrationGuest
                    ids = [m.id for m in await uow.occasions.guests.find_many(G.group_id == group.id, limit=500)]
                await self._apply_members(uow, celebration, group, ids, data.primary_guest_id)
            await uow.session.flush()
            return await self._group_views(uow, celebration.id, base_url)

    async def delete_group(self, celebration_id, group_id, user_id) -> None:
        """Dissolves the household. Its guests, links and answers stay."""
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            group = await self._owned_group(uow, celebration.id, group_id)
            for guest in await uow.occasions.guests.find_many(CelebrationGuest.group_id == group.id, limit=500):
                await uow.occasions.guests.update(guest, {"group_id": None})
            await uow.occasions.guest_groups.update(group, {"primary_guest_id": None})
            await uow.session.flush()
            await uow.occasions.guest_groups.delete(group)

    @staticmethod
    def parse_guest_file(filename: str, content: bytes) -> list[dict]:
        """CSV or XLSX → rows keyed by canonical column. Raises ValidationError on junk."""
        if len(content) > MAX_IMPORT_BYTES:
            raise ValidationError("That file is larger than 2 MB.", field="file")
        lower = (filename or "").lower()
        if lower.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook

            try:
                sheet = load_workbook(io.BytesIO(content), read_only=True, data_only=True).active
                table = [
                    ["" if cell is None else str(cell).strip() for cell in row]
                    for row in sheet.iter_rows(values_only=True)
                ]
            except Exception as exc:
                raise ValidationError("We couldn't read that Excel file.", field="file") from exc
        elif lower.endswith((".csv", ".txt")):
            text = None
            for encoding in ("utf-8-sig", "cp1252"):
                try:
                    text = content.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            if text is None:
                raise ValidationError("We couldn't read that file.", field="file")
            table = [[c.strip() for c in row] for row in csv.reader(io.StringIO(text))]
        else:
            raise ValidationError("Upload a .csv or .xlsx file.", field="file")

        table = [row for row in table if any(row)]
        if not table:
            raise ValidationError("That file is empty.", field="file")
        headers = {}
        for index, header in enumerate(table[0]):
            key = header.strip().lower()
            for column, spellings in _IMPORT_COLUMNS.items():
                if key in spellings and column not in headers:
                    headers[column] = index
        if "name" not in headers:
            raise ValidationError('The first row needs a "Name" column.', field="file")
        if len(table) - 1 > MAX_IMPORT_ROWS:
            raise ValidationError(f"Import at most {MAX_IMPORT_ROWS} guests at a time.", field="file")
        rows = []
        for row in table[1:]:
            rows.append({c: (row[i].strip() if i < len(row) else "") for c, i in headers.items()})
        return rows

    async def import_guests(self, celebration_id, user, filename: str, content: bytes, *, base_url) -> ImportResult:
        rows = self.parse_guest_file(filename, content)
        batch = hashlib.sha256(content).hexdigest()[:24]
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user.id, lock=True)
            policy = await InvitationService.load_policy(uow)
            await self.invites._assert_can_invite(uow, celebration, policy)
            actor = Actor("host", user.id, _host_label(user))
            functions = {f.name.strip().lower(): f.id for f in await self._functions(uow, celebration.id)}
            groups = {
                g.name.strip().lower(): g
                for g in await uow.occasions.guest_groups.find_many(
                    CelebrationGuestGroup.celebration_id == celebration.id, limit=1000,
                )
            }
            results: list[ImportRowResult] = []
            created = groups_created = 0
            for index, raw in enumerate(rows):
                number = index + 2  # as the customer sees it in their spreadsheet
                name = raw.get("name") or ""
                try:
                    function_ids = None
                    if raw.get("functions"):
                        wanted = [p.strip().lower() for p in raw["functions"].replace(";", ",").split(",") if p.strip()]
                        unknown = [w for w in wanted if w not in functions]
                        if unknown:
                            raise ValidationError(f"No function called '{unknown[0]}'.")
                        function_ids = [functions[w] for w in wanted]
                    plus = (raw.get("plus_ones") or "0").split(".")[0]
                    if not plus.isdigit():
                        raise ValidationError("Plus ones must be a number.")
                    data = GuestInvitationCreate(
                        name=name,
                        phone=raw.get("phone") or None,
                        email=raw.get("email") or None,
                        group_tag=raw.get("category") or None,
                        notes=raw.get("notes") or None,
                        plus_ones_allowed=int(plus),
                    )
                except ValueError as exc:
                    message = exc.errors()[0]["msg"] if hasattr(exc, "errors") else str(exc)
                    results.append(ImportRowResult(row=number, status="error", name=name or None, message=message))
                    continue
                except ValidationError as exc:
                    results.append(ImportRowResult(row=number, status="error", name=name or None, message=exc.message))
                    continue
                try:
                    async with uow.session.begin_nested():
                        guest, was_created = await self.invites._create_one(
                            uow, celebration, data, policy, actor,
                            client_request_id=f"imp{batch}:{index}",
                            function_ids=function_ids,
                            source="import",
                        )
                except ConflictError as exc:
                    results.append(ImportRowResult(row=number, status="duplicate", name=name, message=exc.message))
                    continue
                except ValidationError as exc:
                    results.append(ImportRowResult(row=number, status="error", name=name, message=exc.message))
                    continue
                group_name = (raw.get("group") or "").strip()
                if group_name and was_created:
                    group = groups.get(group_name.lower())
                    if group is None:
                        group = await uow.occasions.guest_groups.create_from_dict({
                            "celebration_id": celebration.id,
                            "name": group_name,
                            "category": raw.get("category") or None,
                            "primary_guest_id": guest.id,
                        })
                        groups[group_name.lower()] = group
                        groups_created += 1
                    await uow.occasions.guests.update(guest, {"group_id": group.id})
                created += int(was_created)
                results.append(ImportRowResult(row=number, status="created" if was_created else "existing", name=name))
            return ImportResult(
                created=created,
                skipped=sum(1 for r in results if r.status in ("duplicate", "error")),
                groups_created=groups_created,
                rows=results,
            )

    # ══ 5. Organiser: insight ═════════════════════════════════════════════════

    async def analytics(self, celebration_id, user_id) -> EventAnalytics:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            summary = await InvitationService._summary(uow, celebration.id)
            G = CelebrationGuest
            active = G.pass_status == GuestPassStatus.ACTIVE
            shared, accessed, visited, started = (await uow.session.execute(
                select(
                    func.count().filter(and_(active, G.last_shared_at.is_not(None))),
                    func.count().filter(and_(active, G.link_accessed_at.is_not(None))),
                    func.count().filter(and_(active, G.invitation_opened_at.is_not(None))),
                    func.count().filter(and_(active, G.rsvp_started_at.is_not(None))),
                ).where(G.celebration_id == celebration.id)
            )).one()
            functions = await self._function_stats(uow, celebration.id)
            pending = summary.rsvp_pending
            responded = summary.active - pending
            denominator = summary.active or 1
            return EventAnalytics(
                summary=summary,
                invitations_generated=summary.active,
                shared=shared,
                link_accessed=accessed,
                qualified_visits=visited,
                rsvp_started=started,
                responded=responded,
                pending=pending,
                confirmed=summary.rsvp_attending,
                declined=summary.rsvp_declined,
                maybe=summary.rsvp_maybe,
                response_rate=round(responded / denominator, 4),
                confirmation_rate=round(summary.rsvp_attending / denominator, 4),
                general_link_visits=celebration.general_link_visits,
                functions=functions,
            )

    async def _function_stats(self, uow, celebration_id) -> list[FunctionStats]:
        functions = await self._functions(uow, celebration_id)
        if not functions:
            return []
        R, G = GuestFunctionResponse, CelebrationGuest
        rows = (await uow.session.execute(
            select(
                R.function_id,
                func.count(),
                func.count().filter(R.status == RSVPStatus.ATTENDING),
                func.count().filter(R.status == RSVPStatus.MAYBE),
                func.count().filter(R.status == RSVPStatus.DECLINED),
                func.coalesce(func.sum(case(
                    (R.status == RSVPStatus.ATTENDING, func.coalesce(R.attendee_count, 1)), else_=0,
                )), 0),
            )
            .join(G, G.id == R.celebration_guest_id)
            .where(R.celebration_id == celebration_id, G.pass_status == GuestPassStatus.ACTIVE)
            .group_by(R.function_id)
        )).all()
        by_function = {r[0]: r for r in rows}
        stats = []
        for f in functions:
            row = by_function.get(f.id)
            invited, confirmed, maybe, declined, people = (row[1], row[2], row[3], row[4], int(row[5])) if row else (0, 0, 0, 0, 0)
            stats.append(FunctionStats(
                function_id=f.id, name=f.name, function_date=f.function_date, is_cancelled=f.is_cancelled,
                invited=invited, confirmed=confirmed, maybe=maybe, declined=declined,
                pending=invited - confirmed - maybe - declined, confirmed_people=people,
            ))
        return stats

    async def list_rsvps(self, celebration_id, user_id, *, function_id=None, status=None, page=1, page_size=50) -> tuple[list[RSVPRow], int]:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            R, G, F, H = GuestFunctionResponse, CelebrationGuest, CelebrationFunction, CelebrationGuestGroup
            filters = [R.celebration_id == celebration.id, G.pass_status == GuestPassStatus.ACTIVE]
            if function_id is not None:
                filters.append(R.function_id == function_id)
            if status:
                try:
                    filters.append(R.status == RSVPStatus(status))
                except ValueError as exc:
                    raise ValidationError(f"Unknown status '{status}'.", field="status") from exc
            total = (await uow.session.execute(
                select(func.count()).select_from(R).join(G, G.id == R.celebration_guest_id).where(*filters)
            )).scalar_one()
            rows = (await uow.session.execute(
                select(R, G.name, H.name, F.name)
                .join(G, G.id == R.celebration_guest_id)
                .outerjoin(H, H.id == G.group_id)
                .outerjoin(F, F.id == R.function_id)
                .where(*filters)
                .order_by(R.responded_at.desc().nullslast(), G.name.asc(), R.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )).all()
            return (
                [
                    RSVPRow(
                        guest_id=r.celebration_guest_id, guest_name=name, group_name=group, function_id=r.function_id,
                        function_name=fname, status=r.status, attendee_count=r.attendee_count,
                        dietary_type=r.dietary_type, meal_selection=r.meal_selection, allergies=r.allergies,
                        special_requirements=r.special_requirements, answers=r.answers, responded_at=r.responded_at,
                    )
                    for r, name, group, fname in rows
                ],
                total,
            )

    @staticmethod
    async def _food(uow, celebration_id) -> list[FoodFunctionSummary]:
        """Aggregates only: counts of people, never names. Safe to hand to catering."""
        R, F, G = GuestFunctionResponse, CelebrationFunction, CelebrationGuest
        rows = (await uow.session.execute(
            select(R.function_id, F.name, F.display_order, R.dietary_type, R.meal_selection, R.allergies, R.attendee_count)
            .join(G, G.id == R.celebration_guest_id)
            .outerjoin(F, F.id == R.function_id)
            .where(
                R.celebration_id == celebration_id,
                R.status == RSVPStatus.ATTENDING,
                G.pass_status == GuestPassStatus.ACTIVE,
            )
        )).all()
        out: dict = {}
        order: dict = {}
        for function_id, name, display_order, dietary, meal, allergies, count in rows:
            people = 1 if count is None else count
            summary = out.setdefault(function_id, FoodFunctionSummary(function_id=function_id, name=name or "Event"))
            order[function_id] = display_order or 0
            summary.people += people
            if dietary:
                summary.dietary[dietary] = summary.dietary.get(dietary, 0) + people
            else:
                summary.not_specified += people
            if meal:
                summary.meals[meal] = summary.meals.get(meal, 0) + people
            if allergies:
                summary.with_allergies += 1
        return [out[k] for k in sorted(out, key=lambda k: order[k])]

    async def food_summary(self, celebration_id, user_id) -> FoodSummary:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            current = settings_of(celebration)
            return FoodSummary(enabled=current.rsvp.ask_food, functions=await self._food(uow, celebration.id))

    async def food_report_csv(self, celebration_id, user_id) -> tuple[str, str]:
        """(filename, CSV): the summary first, then each guest's answers, for the organiser's own use."""
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            summaries = await self._food(uow, celebration.id)
            R, G, F = GuestFunctionResponse, CelebrationGuest, CelebrationFunction
            rows = (await uow.session.execute(
                select(F.name, G.name, R.attendee_count, R.dietary_type, R.meal_selection, R.allergies, R.special_requirements)
                .join(G, G.id == R.celebration_guest_id)
                .outerjoin(F, F.id == R.function_id)
                .where(
                    R.celebration_id == celebration.id,
                    R.status == RSVPStatus.ATTENDING,
                    G.pass_status == GuestPassStatus.ACTIVE,
                )
                .order_by(F.display_order.asc().nullsfirst(), G.name.asc())
            )).all()
            title = celebration.title
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["Summary"])
        writer.writerow(["Function", "People", *[d.replace("_", " ").title() for d in DIETARY_TYPES], "Not specified", "Guests with allergies"])
        for s in summaries:
            writer.writerow([_csv_cell(s.name), s.people, *[s.dietary.get(d, 0) for d in DIETARY_TYPES], s.not_specified, s.with_allergies])
        writer.writerow([])
        writer.writerow(["Guests"])
        writer.writerow(["Function", "Guest", "People", "Dietary", "Meal", "Allergies", "Requirements"])
        for function_name, guest, people, dietary, meal, allergies, requirements in rows:
            writer.writerow([_csv_cell(c) for c in (function_name or "Event", guest, people, dietary, meal, allergies, requirements)])
        safe = "".join(ch if ch.isalnum() else "-" for ch in title).strip("-").lower() or "event"
        # BOM so Excel reads names in Hindi correctly.
        return f"{safe}-food-report.csv", "\ufeff" + buffer.getvalue()

    async def activity(self, celebration_id, user_id, *, page=1, page_size=50) -> tuple[list[ActivityItem], int]:
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            H, G = CelebrationGuestHistory, CelebrationGuest
            total = await uow.occasions.guest_history.count(H.celebration_id == celebration.id)
            rows = (await uow.session.execute(
                select(H, G.name)
                .join(G, G.id == H.celebration_guest_id)
                .where(H.celebration_id == celebration.id)
                .order_by(H.occurred_at.desc(), H.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )).all()
            items = []
            for h, name in rows:
                details = h.details or {}
                items.append(ActivityItem(
                    id=h.id, guest_id=h.celebration_guest_id, guest_name=name,
                    event_type=h.event_type.value, previous_status=h.previous_status, new_status=h.new_status,
                    actor_type=h.actor_type, function_name=details.get("function_name"),
                    channel=details.get("channel"), is_update=bool(details.get("is_update")),
                    occurred_at=h.occurred_at,
                ))
            return items, total

    async def reminder_candidates(self, celebration_id, user_id, *, base_url) -> ReminderCandidates:
        """Everyone who hasn't answered, with why each is due. Answered or declined guests can't appear."""
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id)
            entitlements = await ent.for_event(uow, celebration)
            current = settings_of(celebration)
            now = _now()
            today = rules.event_today(settings.EVENT_TIMEZONE, now)
            G = CelebrationGuest
            guests = await uow.occasions.guests.find_many(
                G.celebration_id == celebration.id,
                G.pass_status == GuestPassStatus.ACTIVE,
                G.rsvp_status.in_([RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE]),
                order_by=G.name.asc(),
                limit=2000,
            )
            r = current.reminders
            candidates = []
            for g in guests:
                reasons = []
                if r.after_visit_no_rsvp_days and g.invitation_opened_at \
                        and now - g.invitation_opened_at >= timedelta(days=r.after_visit_no_rsvp_days):
                    reasons.append("visited_no_rsvp")
                sent_at = g.last_shared_at or g.invitation_sent_at
                if r.not_responded_days and sent_at and now - sent_at >= timedelta(days=r.not_responded_days):
                    reasons.append("not_responded")
                deadline = current.rsvp.deadline
                if r.final_before_deadline_days and deadline \
                        and 0 <= (deadline - today).days <= r.final_before_deadline_days:
                    reasons.append("deadline_soon")
                candidates.append(ReminderCandidate(
                    guest_id=g.id, guest_name=g.name, phone=g.phone,
                    invite_url=InvitationService.invite_url(base_url, cred.decrypt(g.link_token_enc)),
                    reasons=reasons, reminder_count=g.reminder_count, last_reminded_at=g.last_reminded_at,
                ))
            return ReminderCandidates(
                automated_available=entitlements.automated_reminders,
                rules=current.reminders,
                candidates=candidates,
            )

    async def record_reminders(self, celebration_id, user, data: ReminderRecord) -> int:
        """Log reminders the host sent from their own device. We never claim delivery."""
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user.id)
            G = CelebrationGuest
            guests = await uow.occasions.guests.find_many(
                G.celebration_id == celebration.id, G.id.in_(data.guest_ids), limit=len(data.guest_ids),
            )
            actor = Actor("host", user.id, _host_label(user))
            now = _now()
            for guest in guests:
                await uow.occasions.guests.update(guest, {
                    "last_reminded_at": now, "reminder_count": (guest.reminder_count or 0) + 1,
                })
                await InvitationService._history(
                    uow, guest, GuestHistoryEventType.REMINDER_SENT, actor, details={"channel": data.channel},
                )
            return len(guests)

    # ══ 6. Guest (public) ═════════════════════════════════════════════════════

    @staticmethod
    def _closed_reason(celebration: Celebration, config, today: date) -> str | None:
        if celebration.status is CelebrationStatus.CANCELLED:
            return "This event has been cancelled."
        if celebration.status is CelebrationStatus.COMPLETED:
            return "This event has taken place."
        if config.deadline and today > config.deadline:
            return "The host has closed responses for this event."
        return None

    @staticmethod
    def _function_open(function: CelebrationFunction, today: date) -> bool:
        return not function.is_cancelled and today < function.function_date

    def _public_event(self, celebration, current: InvitationSettings, *, label: str) -> PublicEvent:
        d = current.display
        venue_name = d.venue_name or celebration.venue_name
        venue_address = d.venue_address or celebration.venue_address
        return PublicEvent(
            title=d.title or celebration.title,
            event_type_label=label,
            host_name=celebration.host_name,
            heading=current.design.heading,
            message=current.design.message or celebration.description,
            instructions=d.instructions,
            cover_image_url=None,  # filled by _cover
            celebration_date=celebration.celebration_date,
            end_date=celebration.event_end_date,
            start_time=d.start_time or celebration.start_time,
            end_time=celebration.end_time,
            venue_name=venue_name,
            venue_address=venue_address,
            map_url=maps_url(
                lat=None if d.venue_address else celebration.latitude,
                lng=None if d.venue_address else celebration.longitude,
                venue_name=venue_name, address=venue_address,
            ),
            contact_name=celebration.contact_name,
            contact_phone=celebration.contact_phone,
            design=current.design,
            status=celebration.status.value,
            website_url=settings.TYOHAAR_WEBSITE_URL,
            android_app_url=settings.TYOHAAR_ANDROID_APP_URL or None,
            ios_app_url=settings.TYOHAAR_IOS_APP_URL or None,
        )

    @staticmethod
    async def _cover(uow, celebration) -> str | None:
        if celebration.cover_image_url:
            return celebration.cover_image_url
        row = (await uow.session.execute(
            select(Package.cover_image_url)
            .join(Booking, Booking.package_id == Package.id)
            .where(Booking.celebration_id == celebration.id)
            .order_by(Booking.created_at.asc())
            .limit(1)
        )).scalar_one_or_none()
        if row:
            return row
        if celebration.occasion_id:
            occasion = await uow.occasions.occasions.get_by_id(celebration.occasion_id)
            if occasion:
                return occasion.banner_url
        return None

    async def _label(self, uow, celebration) -> str:
        name = None
        if celebration.occasion_id and not celebration.event_type:
            occasion = await uow.occasions.occasions.get_by_id(celebration.occasion_id)
            name = occasion.name if occasion else None
        return event_type_label(celebration, name)

    @staticmethod
    def _rsvp_config(current: InvitationSettings, entitlements) -> PublicRSVPConfig:
        r = current.rsvp
        food = r.ask_food and entitlements.food_preferences
        return PublicRSVPConfig(
            allow_maybe=r.allow_maybe,
            allow_edit=r.allow_edit,
            ask_attendee_count=r.ask_attendee_count,
            ask_food=food,
            ask_allergies=food and r.ask_allergies,
            ask_special_requirements=r.ask_special_requirements,
            meal_options=r.meal_options if food else [],
            questions=r.questions if entitlements.advanced_rsvp else [],
            deadline=r.deadline,
        )

    async def _household(self, uow, guest: CelebrationGuest) -> tuple[list[CelebrationGuest], CelebrationGuestGroup | None]:
        """Who this link answers for: the household for its main contact, otherwise just this guest."""
        if guest.group_id is None:
            return [guest], None
        group = await uow.occasions.guest_groups.get_by_id(guest.group_id)
        if group is None or group.primary_guest_id != guest.id:
            return [guest], None
        G = CelebrationGuest
        members = await uow.occasions.guests.find_many(
            G.group_id == group.id, G.pass_status == GuestPassStatus.ACTIVE, order_by=G.created_at.asc(), limit=100,
        )
        ordered = sorted(members, key=lambda m: (m.id != guest.id, m.name))
        return ordered or [guest], group

    @staticmethod
    def _capacity(members: list[CelebrationGuest], group: CelebrationGuestGroup | None) -> int:
        total = sum(1 + m.plus_ones_allowed for m in members)
        return group.invitation_capacity if group is not None and group.invitation_capacity else total

    async def _personal_page(self, uow, guest: CelebrationGuest, celebration: Celebration) -> PublicInvitationPage:
        policy = await InvitationService.load_policy(uow)
        current = settings_of(celebration)
        entitlements = await ent.for_event(uow, celebration)
        config = self._rsvp_config(current, entitlements)
        now = _now()
        today = rules.event_today(settings.EVENT_TIMEZONE, now)
        functions = await self._functions(uow, celebration.id)
        members, group = await self._household(uow, guest)

        R = GuestFunctionResponse
        rows = await uow.occasions.function_responses.find_many(
            R.celebration_guest_id.in_([m.id for m in members]), limit=2000,
        )
        by_member: dict[uuid.UUID, list[GuestFunctionResponse]] = {}
        for row in rows:
            by_member.setdefault(row.celebration_guest_id, []).append(row)

        all_active = [f.id for f in functions if not f.is_cancelled]
        invited_ids: set[uuid.UUID] = set()
        public_members = []
        for m in members:
            member_rows = by_member.get(m.id, [])
            # Added by a screen that doesn't choose functions: invited to all.
            function_ids = [r.function_id for r in member_rows if r.function_id] or all_active
            invited_ids.update(function_ids)
            public_members.append(PublicMember(
                id=m.id, name=m.name, plus_ones_allowed=m.plus_ones_allowed, is_self=m.id == guest.id,
                function_ids=function_ids,
                responses=[
                    PublicMemberResponse(
                        function_id=r.function_id, status=r.status, attendee_count=r.attendee_count,
                        dietary_type=r.dietary_type, meal_selection=r.meal_selection, allergies=r.allergies,
                        special_requirements=r.special_requirements, answers=r.answers,
                    )
                    for r in member_rows
                ],
            ))

        visible = [f for f in functions if f.id in invited_ids]
        public_functions = [self._public_function(f, today) for f in visible]

        closed = self._closed_reason(celebration, config, today)
        if guest.pass_status is GuestPassStatus.REVOKED:
            closed = "The host has cancelled this invitation."
        if closed is None:
            is_open = any(f.is_open for f in public_functions) if public_functions else today < celebration.celebration_date
            if not is_open:
                closed = "Responses for this event have closed."
        has_responded = any(
            r.responded_at is not None for member_rows in by_member.values() for r in member_rows
        ) or guest.rsvp_status not in (RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE)

        passes = []
        state = self.invites._pass_state(guest, celebration, policy, now)
        if entitlements.qr_check_in and state in ("valid", "not_yet_valid", "checked_out"):
            for m in members:
                code = cred.decrypt(m.entry_code_enc)
                if code:
                    qr = segno.make(cred.qr_payload(code), error="m")
                    passes.append(PublicPass(
                        name=m.name,
                        entry_code=cred.format_entry_code(code),
                        qr_svg=qr.svg_inline(omitsize=True, border=2, dark="#2A2018", light="#FFFFFF"),
                    ))

        event = self._public_event(celebration, current, label=await self._label(uow, celebration))
        event.cover_image_url = await self._cover(uow, celebration)
        mode = "single"
        if group is not None and len(members) > 1:
            mode = "individual" if group.response_mode is GuestGroupResponseMode.INDIVIDUAL else "group"
        return PublicInvitationPage(
            kind="personal",
            event=event,
            functions=public_functions,
            members=public_members,
            response_mode=mode,
            capacity=self._capacity(members, group),
            rsvp=config,
            can_respond=closed is None and (config.allow_edit or not has_responded),
            closed_reason=closed,
            has_responded=has_responded,
            guest_note=guest.guest_note,
            pass_state=state,
            passes=passes,
        )

    def _public_function(self, f: CelebrationFunction, today: date) -> PublicFunction:
        return PublicFunction(
            id=f.id, name=f.name, function_date=f.function_date, start_time=f.start_time, end_time=f.end_time,
            venue_name=f.venue_name, venue_address=f.venue_address,
            map_url=f.map_url or maps_url(venue_name=f.venue_name, address=f.venue_address),
            description=f.description, dress_code=f.dress_code,
            is_open=self._function_open(f, today), is_cancelled=f.is_cancelled,
        )

    async def _general_event(self, uow, token: str | None) -> Celebration:
        if not token or len(token) > 128:
            raise GuestNotFoundError("invitation")
        celebration = await uow.occasions.celebrations.find_one(
            Celebration.general_link_hash == cred.hash_secret(cred.GENERAL_LINK_KIND, token)
        )
        if celebration is None or not settings_of(celebration).general_link.enabled:
            raise GuestNotFoundError("invitation")
        return celebration

    async def _general_page(self, uow, celebration: Celebration, kind: str = "general") -> PublicInvitationPage:
        current = settings_of(celebration)
        entitlements = await ent.for_event(uow, celebration)
        config = self._rsvp_config(current, entitlements)
        today = rules.event_today(settings.EVENT_TIMEZONE)
        functions = await self._functions(uow, celebration.id)
        event = self._public_event(celebration, current, label=await self._label(uow, celebration))
        event.cover_image_url = await self._cover(uow, celebration)
        return PublicInvitationPage(
            kind=kind,
            event=event,
            functions=[self._public_function(f, today) for f in functions if not f.is_cancelled],
            rsvp=config,
            can_respond=kind == "general" and self._closed_reason(celebration, config, today) is None,
            closed_reason=self._closed_reason(celebration, config, today),
            general_plus_ones=current.general_link.plus_ones_allowed,
        )

    @staticmethod
    def _require_published(celebration: Celebration) -> None:
        if celebration.invitation_status is InvitationPublishStatus.DRAFT:
            raise BusinessRuleError("This invitation hasn't been published yet.")

    async def resolve_token(self, token: str | None, *, is_real_browser: bool) -> dict:
        """
        Everything the server-rendered shell and link preview need, for either
        kind of link. Records "link accessed" only for a real browser: a crawler
        fetching the preview must never look like a guest.
        """
        async with self._uow() as uow:
            lookup = cred.link_lookup(token)
            guest = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
            if guest is not None:
                celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
                if celebration is None:
                    raise GuestNotFoundError("invitation")
                revoked = guest.pass_status is GuestPassStatus.REVOKED
                if is_real_browser and not revoked and guest.link_accessed_at is None:
                    guest = await uow.occasions.guests.update(guest, {"link_accessed_at": _now()})
                    await InvitationService._history(
                        uow, guest, GuestHistoryEventType.LINK_ACCESSED, Actor("guest", label=guest.name),
                    )
                kind = "revoked" if revoked else "personal"
            else:
                celebration = await self._general_event(uow, token)
                kind = "general"
            current = settings_of(celebration)
            return {
                "kind": kind,
                "draft": celebration.invitation_status is InvitationPublishStatus.DRAFT,
                "title": current.display.title or celebration.title,
                "host_name": celebration.host_name,
                "date": celebration.celebration_date,
                "end_date": celebration.event_end_date,
                "start_time": current.display.start_time or celebration.start_time,
                "venue_name": current.display.venue_name or celebration.venue_name,
                "venue_address": current.display.venue_address or celebration.venue_address,
                "description": current.design.message or celebration.description,
                "heading": current.design.heading,
                "cover": await self._cover(uow, celebration),
                "design": current.design,
                "status": celebration.status.value,
                "label": await self._label(uow, celebration),
            }

    async def public_view(self, token: str | None, *, is_real_browser: bool) -> PublicInvitationPage:
        """Called by the page's script once on screen, the closest thing to a real visit we can observe."""
        async with self._uow() as uow:
            lookup = cred.link_lookup(token)
            guest = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
            if guest is None:
                celebration = await self._general_event(uow, token)
                self._require_published(celebration)
                if is_real_browser:
                    await uow.occasions.celebrations.update(
                        celebration, {"general_link_visits": (celebration.general_link_visits or 0) + 1}
                    )
                return await self._general_page(uow, celebration)
            celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
            if celebration is None:
                raise GuestNotFoundError("invitation")
            self._require_published(celebration)
            if is_real_browser and guest.pass_status is GuestPassStatus.ACTIVE:
                now = _now()
                first = guest.invitation_opened_at is None
                guest = await uow.occasions.guests.update(guest, {
                    "invitation_opened_at": guest.invitation_opened_at or now,
                    "link_accessed_at": guest.link_accessed_at or now,
                    "visit_count": (guest.visit_count or 0) + 1,
                    "last_visited_at": now,
                })
                if first:
                    await InvitationService._history(
                        uow, guest, GuestHistoryEventType.INVITATION_OPENED, Actor("guest", label=guest.name),
                    )
            return await self._personal_page(uow, guest, celebration)

    async def preview_page(self, token: str) -> PublicInvitationPage:
        celebration_id = self._preview_target(token)
        async with self._uow() as uow:
            celebration = await uow.occasions.celebrations.get_by_id(celebration_id)
            if celebration is None:
                raise GuestNotFoundError("invitation")
            page = await self._general_page(uow, celebration, kind="preview")
            page.members = [PublicMember(
                id=uuid.UUID(int=0), name="Your guest", plus_ones_allowed=1, is_self=True,
                function_ids=[f.id for f in page.functions],
            )]
            page.capacity = 2
            return page

    @staticmethod
    def _preview_target(token: str) -> uuid.UUID:
        raw = cred.decrypt(token)
        try:
            celebration_id, expires = (raw or "").split(":")
            if int(expires) < _now().timestamp():
                raise ValueError
            return uuid.UUID(celebration_id)
        except ValueError as exc:
            raise GuestNotFoundError("invitation") from exc

    async def preview_meta(self, token: str) -> dict:
        celebration_id = self._preview_target(token)
        async with self._uow() as uow:
            celebration = await uow.occasions.celebrations.get_by_id(celebration_id)
            if celebration is None:
                raise GuestNotFoundError("invitation")
            current = settings_of(celebration)
            return {
                "kind": "preview",
                "draft": False,
                "title": current.display.title or celebration.title,
                "host_name": celebration.host_name,
                "date": celebration.celebration_date,
                "end_date": celebration.event_end_date,
                "start_time": current.display.start_time or celebration.start_time,
                "venue_name": current.display.venue_name or celebration.venue_name,
                "venue_address": current.display.venue_address or celebration.venue_address,
                "description": current.design.message or celebration.description,
                "heading": current.design.heading,
                "cover": await self._cover(uow, celebration),
                "design": current.design,
                "status": celebration.status.value,
                "label": await self._label(uow, celebration),
            }

    async def track_rsvp_started(self, token: str | None) -> None:
        """First interaction with the form. Idempotent; anything unknown is silently ignored."""
        async with self._uow() as uow:
            lookup = cred.link_lookup(token)
            guest = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
            if guest is None or guest.rsvp_started_at is not None or guest.pass_status is not GuestPassStatus.ACTIVE:
                return
            guest = await uow.occasions.guests.update(guest, {"rsvp_started_at": _now()})
            await InvitationService._history(
                uow, guest, GuestHistoryEventType.RSVP_STARTED, Actor("guest", label=guest.name),
            )

    async def submit_rsvp(self, token: str | None, data: PublicRSVPRequest) -> PublicInvitationPage:
        notify = None
        async with self._uow() as uow:
            lookup = cred.link_lookup(token)
            holder = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
            if holder is None:
                raise GuestNotFoundError("invitation")
            celebration = await uow.occasions.celebrations.get_by_id(holder.celebration_id)
            if celebration is None:
                raise GuestNotFoundError("invitation")
            self._require_published(celebration)
            if holder.pass_status is GuestPassStatus.REVOKED:
                raise BusinessRuleError("The host has cancelled this invitation.")

            current = settings_of(celebration)
            entitlements = await ent.for_event(uow, celebration)
            config = self._rsvp_config(current, entitlements)
            now = _now()
            today = rules.event_today(settings.EVENT_TIMEZONE, now)
            closed = self._closed_reason(celebration, config, today)
            if closed:
                raise BusinessRuleError(closed)

            members, group = await self._household(uow, holder)
            # Stable lock order, so two family members submitting together can't deadlock.
            for member in sorted(members, key=lambda m: str(m.id)):
                await uow.occasions.guests.get_by_id_with_lock(member.id)
            by_id = {m.id: m for m in members}
            mode = "single"
            if group is not None and len(members) > 1:
                mode = "individual" if group.response_mode is GuestGroupResponseMode.INDIVIDUAL else "group"

            functions = {f.id: f for f in await self._functions(uow, celebration.id)}
            active_ids = [f.id for f in functions.values() if not f.is_cancelled]
            R = GuestFunctionResponse
            rows = {
                (r.celebration_guest_id, r.function_id): r
                for r in await uow.occasions.function_responses.find_many(
                    R.celebration_guest_id.in_(list(by_id)), limit=2000,
                )
            }
            # A guest added without a function choice is invited to all of them.
            for member in members:
                if functions and not any(k[0] == member.id and k[1] for k in rows):
                    for function_id in active_ids:
                        rows[(member.id, function_id)] = await uow.occasions.function_responses.create_from_dict({
                            "celebration_id": celebration.id, "function_id": function_id,
                            "celebration_guest_id": member.id, "status": RSVPStatus.PENDING,
                        })

            per_function_people: dict[uuid.UUID | None, int] = {}
            capacity = self._capacity(members, group)
            changed: list[tuple] = []
            for item in data.responses:
                targets = members if mode == "group" else [by_id.get(item.guest_id or holder.id)]
                if targets[0] is None:
                    # Same answer as a bad token: a valid link can't probe other guests.
                    raise GuestNotFoundError("invitation")
                if not functions and item.function_id is not None:
                    raise ValidationError("This event has no separate functions.", field="function_id")
                if functions:
                    function = functions.get(item.function_id) if item.function_id else None
                    if function is None or (targets[0].id, function.id) not in rows:
                        raise ValidationError("You haven't been invited to that function.", field="function_id")
                    if not self._function_open(function, today):
                        raise BusinessRuleError(f"Responses for {function.name} have closed.")
                elif today >= celebration.celebration_date:
                    raise BusinessRuleError("Responses for this event have closed.")
                if item.status is RSVPStatus.MAYBE and not config.allow_maybe:
                    raise ValidationError("Please answer yes or no.", field="status")

                # How many people. On a group answer the household's total goes
                # on the main contact and members count zero, so nobody is
                # counted twice.
                count = None
                if item.status is RSVPStatus.ATTENDING:
                    count = (item.attendee_count or 1) if config.ask_attendee_count else 1
                    if mode != "group" and count > 1 + targets[0].plus_ones_allowed:
                        raise ValidationError(
                            f"{targets[0].name}'s invitation admits {1 + targets[0].plus_ones_allowed} in total.",
                            field="attendee_count",
                        )
                    per_function_people[item.function_id] = per_function_people.get(item.function_id, 0) + count
                    if per_function_people[item.function_id] > capacity:
                        raise ValidationError(f"This invitation admits {capacity} in total.", field="attendee_count")

                food = self._food_fields(item, config)
                answers = self._valid_answers(item, config)
                for target in targets:
                    key = (target.id, item.function_id)
                    row = rows.get(key)
                    if row is None:
                        row = await uow.occasions.function_responses.create_from_dict({
                            "celebration_id": celebration.id, "function_id": item.function_id,
                            "celebration_guest_id": target.id, "status": RSVPStatus.PENDING,
                        })
                        rows[key] = row
                    member_count = count
                    if mode == "group" and count is not None and target.id != holder.id:
                        member_count = 0
                    new_values = {"status": item.status, "attendee_count": member_count, **food, "answers": answers}
                    if all(getattr(row, k) == v for k, v in new_values.items()) and row.responded_at is not None:
                        continue  # a resubmitted form changes nothing and logs nothing
                    previous = row.status
                    if row.responded_at is not None and not config.allow_edit:
                        raise ConflictError("You've already responded, and the host isn't accepting changes.")
                    await uow.occasions.function_responses.update(row, {**new_values, "responded_at": now})
                    changed.append((target, item, previous))

            for member in members:
                await uow.session.flush()
                await self._rollup(uow, member, now=now if any(c[0].id == member.id for c in changed) else None)
                if any(c[0].id == member.id for c in changed):
                    await uow.occasions.guests.update(member, {
                        "invitation_opened_at": member.invitation_opened_at or now,
                    })

            for target, item, previous in changed:
                function = functions.get(item.function_id) if item.function_id else None
                await InvitationService._history(
                    uow, target, GuestHistoryEventType.RSVP_CHANGED, Actor("guest", label=holder.name),
                    previous_status=previous, new_status=item.status,
                    details={
                        "function_id": str(function.id) if function else None,
                        "function_name": function.name if function else None,
                        "attendee_count": item.attendee_count,
                        "is_update": previous not in (RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE),
                    },
                )
            if data.note is not None:
                await uow.occasions.guests.update(holder, {"guest_note": data.note.strip() or None})
            if changed:
                notify = (celebration.customer_id, celebration.id, holder.name, celebration.title, holder.rsvp_status)
            await uow.session.flush()
            page = await self._personal_page(uow, holder, celebration)
        if notify:
            user_id, celebration_id, name, title, status = notify
            verb = {
                RSVPStatus.ATTENDING: "is coming to",
                RSVPStatus.MAYBE: "might come to",
                RSVPStatus.DECLINED: "can't make it to",
            }.get(status, "responded to")
            await InvitationService._notify(
                user_id, NotificationType.RSVP_UPDATE, "New RSVP", f"{name} {verb} {title}.", celebration_id,
            )
        return page

    @staticmethod
    def _food_fields(item, config: PublicRSVPConfig) -> dict:
        """Only what this event asks for, and only from someone who may be there."""
        fields = {"dietary_type": None, "meal_selection": None, "allergies": None, "special_requirements": None}
        if item.status is RSVPStatus.DECLINED:
            return fields
        if config.ask_food:
            if item.dietary_type is not None and item.dietary_type not in DIETARY_TYPES:
                raise ValidationError("Choose one of the food preferences.", field="dietary_type")
            fields["dietary_type"] = item.dietary_type
            if item.meal_selection is not None:
                if config.meal_options and item.meal_selection not in config.meal_options:
                    raise ValidationError("Choose one of the meal options.", field="meal_selection")
                fields["meal_selection"] = item.meal_selection
            if config.ask_allergies:
                fields["allergies"] = item.allergies
        if config.ask_special_requirements:
            fields["special_requirements"] = item.special_requirements
        return fields

    @staticmethod
    def _valid_answers(item, config: PublicRSVPConfig) -> dict | None:
        supplied = item.answers or {}
        answers: dict[str, str] = {}
        for question in config.questions:
            value = (supplied.get(question.id) or "").strip()
            if not value:
                if question.required and item.status is RSVPStatus.ATTENDING:
                    raise ValidationError(f"Please answer: {question.label}", field="answers")
                continue
            if question.kind == "choice" and value not in question.options:
                raise ValidationError(f"Choose an option for: {question.label}", field="answers")
            if question.kind == "yes_no" and value not in ("yes", "no"):
                raise ValidationError(f"Answer yes or no: {question.label}", field="answers")
            answers[question.id] = value
        return answers or None

    async def claim_general_link(self, token: str | None, data: PublicClaim, *, base_url) -> PublicClaimResult:
        """
        A visitor to the general link says who they are and gets their own
        invitation. Someone giving a number already on the list is not handed
        that guest's link: that would give away their invitation and pass to
        anyone who knows their phone number.
        """
        if data.website:
            raise ValidationError("Please check your details and try again.")
        async with self._uow() as uow:
            found = await self._general_event(uow, token)
            celebration = await InvitationService._owned_celebration(uow, found.id, found.customer_id, lock=True)
            self._require_published(celebration)
            current = settings_of(celebration)
            config = self._rsvp_config(current, await ent.for_event(uow, celebration))
            closed = self._closed_reason(celebration, config, rules.event_today(settings.EVENT_TIMEZONE))
            if closed:
                raise BusinessRuleError(closed)
            policy = await InvitationService.load_policy(uow)
            await self.invites._assert_can_invite(uow, celebration, policy)
            try:
                create = GuestInvitationCreate(
                    name=data.name,
                    phone=data.phone or None,
                    email=data.email or None,
                    plus_ones_allowed=current.general_link.plus_ones_allowed,
                )
            except ValueError as exc:
                raise ValidationError("Please check your details and try again.") from exc
            try:
                guest, _ = await self.invites._create_one(
                    uow, celebration, create, policy, Actor("guest", label=data.name),
                    client_request_id=None, source="general_link",
                )
            except ConflictError as exc:
                raise ConflictError(
                    "This number is already on the guest list. Please use your personal invitation "
                    "link, or ask the host to send it again.",
                ) from exc
            link_token = cred.decrypt(guest.link_token_enc)
            return PublicClaimResult(url=InvitationService.invite_url(base_url, link_token) or "", token=link_token or "")

    async def calendar(self, token: str) -> tuple[str, str]:
        """(filename, .ics) for what this link is invited to."""
        async with self._uow() as uow:
            lookup = cred.link_lookup(token)
            guest = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
            if guest is not None:
                celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
                if celebration is None:
                    raise GuestNotFoundError("invitation")
                page = await self._personal_page(uow, guest, celebration)
            else:
                celebration = await self._general_event(uow, token)
                page = await self._general_page(uow, celebration)
            self._require_published(celebration)

        def escape(text: str | None) -> str:
            return (text or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        def entry(uid: str, name: str, day: date, start: time | None, end: time | None, venue: str | None) -> list[str]:
            if start:
                ending = end or (datetime.combine(day, start) + timedelta(hours=3)).time()
                end_day = day + timedelta(days=1) if ending <= start else day
                stamp = [
                    f"DTSTART;TZID={settings.EVENT_TIMEZONE}:{day:%Y%m%d}T{start:%H%M%S}",
                    f"DTEND;TZID={settings.EVENT_TIMEZONE}:{end_day:%Y%m%d}T{ending:%H%M%S}",
                ]
            else:
                stamp = [f"DTSTART;VALUE=DATE:{day:%Y%m%d}", f"DTEND;VALUE=DATE:{day + timedelta(days=1):%Y%m%d}"]
            return [
                "BEGIN:VEVENT", f"UID:{uid}@tyohaar", f"DTSTAMP:{_now():%Y%m%dT%H%M%SZ}", *stamp,
                f"SUMMARY:{escape(name)}", *([f"LOCATION:{escape(venue)}"] if venue else []), "END:VEVENT",
            ]

        event = page.event
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tyohaar//Invitation//EN", "CALSCALE:GREGORIAN"]
        if page.functions:
            for f in page.functions:
                if not f.is_cancelled:
                    venue = ", ".join(p for p in (f.venue_name or event.venue_name, f.venue_address or event.venue_address) if p)
                    lines += entry(str(f.id), f"{f.name} — {event.title}", f.function_date, f.start_time, f.end_time, venue)
        else:
            venue = ", ".join(p for p in (event.venue_name, event.venue_address) if p)
            lines += entry(str(celebration.id), event.title, event.celebration_date, event.start_time, event.end_time, venue)
        lines.append("END:VCALENDAR")
        safe = "".join(ch if ch.isalnum() else "-" for ch in event.title).strip("-").lower() or "invitation"
        return f"{safe}.ics", "\r\n".join(lines) + "\r\n"

    # ══ 7. Bookings ═══════════════════════════════════════════════════════════

    @staticmethod
    async def associate_confirmed_booking(uow, booking: Booking) -> None:
        """
        A confirmed booking makes its event a Tyohaar event. Same row, same id:
        guests, links, answers and history all carry over because nothing moves.
        Idempotent, and safe against a second booking on the same event, which
        keeps the first association.
        """
        celebration = await uow.occasions.celebrations.get_by_id_with_lock(booking.celebration_id)
        if celebration is None:
            return
        if celebration.linked_booking_id == booking.id:
            return
        changes: dict = {"event_source": EventSource.TYOHAAR_BOOKING}
        if celebration.linked_booking_id is None:
            changes["linked_booking_id"] = booking.id
        else:
            current = await uow.bookings.bookings.get_by_id(celebration.linked_booking_id)
            if current is None or current.booking_status in DEAD_BOOKING_STATUSES:
                changes["linked_booking_id"] = booking.id
        await uow.occasions.celebrations.update(celebration, changes)

    async def approve_operations_summary(self, celebration_id, user_id, data: OperationsApproval) -> FoodSummary:
        """
        The organiser publishes a snapshot for the vendors on their booking. It
        is theirs to approve, it is a copy, and it changes no vendor quantity.
        """
        async with self._uow() as uow:
            celebration = await self._owned(uow, celebration_id, user_id, lock=True)
            entitlements = await ent.for_event(uow, celebration)
            if not entitlements.vendor_reports:
                raise BusinessRuleError("Vendor reports are available on confirmed Tyohaar bookings.")
            functions = await self._food(uow, celebration.id)
            stored = dict(celebration.invitation_settings or {})
            stored[_OPS_KEY] = {
                "approved_at": _now().isoformat(),
                "final_guest_count": data.final_guest_count,
                "note": data.note,
                "functions": [f.model_dump(mode="json") for f in functions],
            }
            await uow.occasions.celebrations.update(celebration, {"invitation_settings": stored})
            return FoodSummary(enabled=True, functions=functions)

    async def vendor_guest_summary(self, booking_id, vendor_id) -> VendorGuestSummary | None:
        """The approved snapshot, for a vendor assigned to this booking. None until approved."""
        from app.services.bookings.service import BookingService
        from app.services.bookings.exceptions import BookingNotFoundError

        async with self._uow() as uow:
            booking = await uow.bookings.bookings.get_by_id(booking_id)
            if booking is None or not await BookingService.vendor_owns_booking(uow, booking, vendor_id):
                raise BookingNotFoundError(str(booking_id))
            celebration = await uow.occasions.celebrations.get_by_id(booking.celebration_id)
            ops = (celebration.invitation_settings or {}).get(_OPS_KEY) if celebration else None
            if not ops:
                return None
            return VendorGuestSummary.model_validate(ops)
