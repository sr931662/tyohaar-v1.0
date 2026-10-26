"""
InvitationService — guest invitations, guest passes and gate entry.

Builds on the existing ``celebration_guests`` model (the live guest list the
app already uses) rather than the unused ``invitations`` scaffolding, so there
is one source of truth for "who is invited to this celebration".

Layout:
  1. Shared helpers       policy, scope checks, serialisation, history
  2. Host                 list / summary / create / bulk / detail / edit /
                          revoke / rotate / shared / email
  3. Guest (public)       view / RSVP by link token
  4. Gate                 verify / check-in / check-out / search, for three
                          operator kinds: host, delegated gate access, admin
  5. Gate access          host-issued, celebration-scoped gate credentials
  6. Admin                cross-celebration list / detail / revoke /
                          entry logs / policy

Authorisation is enforced here, not in the UI: every host operation resolves
the celebration with ``customer_id == user_id`` (404 otherwise, so ids cannot
be probed), every gate operation is pinned to one celebration's scope, and the
public endpoints only ever see the single guest their token names.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import segno
from sqlalchemy import and_, case, func, or_, select, update

from app.core.config import settings
from app.core.rate_limit import GATE_FAILURE_LIMIT, enforce_rate_limit, limiter
from app.db.session import AsyncSessionLocal
from app.models.enums import (
    AccountStatus,
    CelebrationStatus,
    EntryOperatorType,
    GuestEntryAction,
    GuestEntryStatus,
    GuestHistoryEventType,
    GuestPassStatus,
    GuestVerificationResult as R,
    NotificationChannel,
    NotificationType,
    RSVPStatus,
    UserRole,
)
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.celebration_guest_history import CelebrationGuestHistory
from app.models.occasions.gate_access import CelebrationGateAccess
from app.models.occasions.guest_entry_log import GuestEntryLog
from app.schemas.invitations import (
    AdminInvitationDetail,
    AdminInvitationRow,
    BulkCreateResult,
    BulkRowResult,
    DeliveryCapabilities,
    EmailSendResult,
    EntryLogItem,
    GateAccessCreate,
    GateAccessResponse,
    GateCheckIn,
    GateGuest,
    GateRequest,
    GateResult,
    GateSession,
    GuestHistoryItem,
    GuestInvitationBulkCreate,
    GuestInvitationCreate,
    GuestInvitationDetail,
    GuestInvitationResponse,
    GuestInvitationUpdate,
    InvitationSummary,
    PublicInvitation,
    PublicRSVPSubmit,
)
from app.services.base import BaseService
from app.services.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    ValidationError,
)
from app.services.invitations import credentials as cred
from app.services.invitations import rules
from app.services.invitations.rules import InvitationPolicy
from app.services.occasions.constants import MAX_GUESTS_PER_CELEBRATION
from app.services.occasions.exceptions import (
    CelebrationNotFoundError,
    GuestLimitExceededError,
    GuestNotFoundError,
)

logger = logging.getLogger(__name__)

INVITE_PAGE_PATH = "/public/invite/page"
GATE_PAGE_PATH = "/public/gate/page"


@dataclass(frozen=True)
class Actor:
    """Who is performing an action — recorded on history and entry logs."""

    kind: str  # host | guest | gate_access | admin | system
    user_id: uuid.UUID | None = None
    label: str | None = None
    gate_access_id: uuid.UUID | None = None

    @property
    def operator_type(self) -> EntryOperatorType:
        return {
            "host": EntryOperatorType.HOST,
            "gate_access": EntryOperatorType.GATE_ACCESS,
            "admin": EntryOperatorType.ADMIN,
        }[self.kind]


@dataclass(frozen=True)
class GateScope:
    """The celebration a gate operator may act on (None = admin, any)."""

    actor: Actor
    celebration_id: uuid.UUID | None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _host_label(user) -> str:
    name = " ".join(p for p in (getattr(user, "first_name", None), getattr(user, "last_name", None)) if p)
    return name or "Host"


class InvitationService(BaseService):
    def __init__(self, session_factory=AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    # ══ 1. Shared helpers ═════════════════════════════════════════════════════

    @staticmethod
    async def load_policy(uow) -> InvitationPolicy:
        setting = await uow.common.settings.get_by_key(rules.POLICY_SETTING_KEY)
        if setting is None or not setting.value:
            return InvitationPolicy()
        try:
            return InvitationPolicy.model_validate(json.loads(setting.value))
        except (ValueError, TypeError):
            logger.warning("Ignoring malformed %s setting; using defaults", rules.POLICY_SETTING_KEY)
            return InvitationPolicy()

    @staticmethod
    def window(celebration: Celebration, policy: InvitationPolicy) -> tuple[datetime, datetime]:
        return rules.entry_window(
            celebration.celebration_date,
            celebration.start_time,
            celebration.end_time,
            tz_name=settings.EVENT_TIMEZONE,
            policy=policy,
        )

    @staticmethod
    async def _owned_celebration(uow, celebration_id: uuid.UUID, user_id: uuid.UUID, *, lock: bool = False) -> Celebration:
        repo = uow.occasions.celebrations
        celebration = await (repo.get_by_id_with_lock(celebration_id) if lock else repo.get_by_id(celebration_id))
        # Not-found rather than forbidden for someone else's celebration, so
        # celebration ids cannot be probed.
        if celebration is None or celebration.customer_id != user_id:
            raise CelebrationNotFoundError(str(celebration_id))
        return celebration

    @staticmethod
    async def _guest_in(uow, celebration_id: uuid.UUID, guest_id: uuid.UUID, *, lock: bool = False) -> CelebrationGuest:
        repo = uow.occasions.guests
        guest = await (repo.get_by_id_with_lock(guest_id) if lock else repo.get_by_id(guest_id))
        if guest is None or guest.celebration_id != celebration_id:
            raise GuestNotFoundError(str(guest_id))
        return guest

    @staticmethod
    def invite_url(base_url: str | None, token: str | None) -> str | None:
        if not base_url or not token:
            return None
        # Token in the fragment: browsers never send it to the server, so it
        # stays out of access logs and Referer headers.
        return f"{base_url.rstrip('/')}{settings.API_V1_PREFIX}{INVITE_PAGE_PATH}#{token}"

    def _host_view(
        self,
        guest: CelebrationGuest,
        celebration: Celebration,
        policy: InvitationPolicy,
        base_url: str | None,
        now: datetime,
    ) -> GuestInvitationResponse:
        code = cred.decrypt(guest.entry_code_enc)
        return GuestInvitationResponse(
            id=guest.id,
            celebration_id=guest.celebration_id,
            name=guest.name,
            phone=guest.phone,
            email=guest.email,
            group_tag=guest.group_tag,
            notes=guest.notes,
            plus_ones_allowed=guest.plus_ones_allowed,
            arrival_window_start=guest.arrival_window_start,
            arrival_window_end=guest.arrival_window_end,
            vehicle_number=guest.vehicle_number,
            pass_status=guest.pass_status,
            pass_state=self._pass_state(guest, celebration, policy, now),
            rsvp_status=guest.rsvp_status,
            rsvp_party_size=guest.rsvp_party_size,
            rsvp_responded_at=guest.rsvp_responded_at,
            guest_note=guest.guest_note,
            entry_status=guest.entry_status,
            checked_in_at=guest.checked_in_at,
            checked_out_at=guest.checked_out_at,
            checked_in_party_size=guest.checked_in_party_size,
            invitation_opened_at=guest.invitation_opened_at,
            last_shared_at=guest.last_shared_at,
            last_shared_channel=guest.last_shared_channel,
            share_count=guest.share_count or 0,
            revoked_at=guest.revoked_at,
            revoked_reason=guest.revoked_reason,
            created_at=guest.created_at,
            # A revoked invitation's link and code are dead — don't hand them
            # back out where they might be re-shared.
            invite_url=None if guest.pass_status is GuestPassStatus.REVOKED
            else self.invite_url(base_url, cred.decrypt(guest.link_token_enc)),
            entry_code=None if guest.pass_status is GuestPassStatus.REVOKED or not code
            else cred.format_entry_code(code),
            qr_payload=None if guest.pass_status is GuestPassStatus.REVOKED or not code
            else cred.qr_payload(code),
        )

    def _pass_state(self, guest, celebration, policy, now) -> str:
        return rules.pass_state(
            pass_status=guest.pass_status,
            entry_status=guest.entry_status,
            celebration_status=celebration.status,
            window=self.window(celebration, policy),
            now=now,
            policy=policy,
        )

    @staticmethod
    async def _history(
        uow,
        guest: CelebrationGuest,
        event_type: GuestHistoryEventType,
        actor: Actor,
        *,
        previous_status: RSVPStatus | None = None,
        new_status: RSVPStatus | None = None,
        details: dict | None = None,
    ) -> None:
        await uow.occasions.guest_history.create(
            CelebrationGuestHistory(
                celebration_guest_id=guest.id,
                celebration_id=guest.celebration_id,
                event_type=event_type,
                previous_status=previous_status,
                new_status=new_status,
                actor_type=actor.kind,
                actor_user_id=actor.user_id,
                actor_label=actor.label,
                details=details,
            )
        )

    @staticmethod
    async def _phone_taken(uow, celebration_id, phone: str | None, *, exclude_id=None) -> bool:
        """An active invitation for the same (normalised) phone already exists."""
        normalized = rules.normalize_phone(phone)
        if not normalized:
            return False
        stmt = select(CelebrationGuest.id, CelebrationGuest.phone).where(
            CelebrationGuest.celebration_id == celebration_id,
            CelebrationGuest.pass_status == GuestPassStatus.ACTIVE,
            CelebrationGuest.phone.is_not(None),
        )
        if exclude_id is not None:
            stmt = stmt.where(CelebrationGuest.id != exclude_id)
        for _id, other in (await uow.session.execute(stmt)).all():
            if rules.normalize_phone(other) == normalized:
                return True
        return False

    @staticmethod
    async def _unique_credentials(uow) -> dict[str, str]:
        """Fresh credentials whose code hash is not already taken."""
        for _ in range(5):
            values = cred.issue_guest_credentials()
            if not await uow.occasions.guests.exists_where(
                CelebrationGuest.entry_code_hash == values["entry_code_hash"]
            ):
                return values
        raise ConflictError("Could not allocate a unique entry code; please retry.")

    @staticmethod
    def _entry_item(log: GuestEntryLog, guest_name: str | None) -> EntryLogItem:
        return EntryLogItem(
            id=log.id,
            celebration_id=log.celebration_id,
            celebration_guest_id=log.celebration_guest_id,
            guest_name=guest_name,
            action=log.action,
            result=log.result,
            method=log.method,
            party_size=log.party_size,
            operator_type=log.operator_type,
            operator_label=log.operator_label,
            occurred_at=log.occurred_at,
        )

    async def _guest_timeline(self, uow, guest: CelebrationGuest) -> tuple[list, list]:
        history = await uow.occasions.guest_history.find_many(
            CelebrationGuestHistory.celebration_guest_id == guest.id,
            order_by=CelebrationGuestHistory.occurred_at.desc(),
            limit=200,
        )
        logs = await uow.occasions.entry_logs.find_many(
            GuestEntryLog.celebration_guest_id == guest.id,
            order_by=GuestEntryLog.occurred_at.desc(),
            limit=200,
        )
        return (
            [GuestHistoryItem.model_validate(h) for h in history],
            [self._entry_item(log, guest.name) for log in logs],
        )

    # ══ 2. Host ═══════════════════════════════════════════════════════════════

    _HOST_FILTERS = {
        "all", "expected", "arrived", "inside", "pending_rsvp", "attending",
        "maybe", "declined", "not_opened", "revoked",
    }
    _SORTS = {"created_at", "name", "checked_in_at", "rsvp_responded_at"}

    def _filter_clause(self, status: str):
        G = CelebrationGuest
        active = G.pass_status == GuestPassStatus.ACTIVE
        return {
            "all": None,
            "expected": and_(active, G.rsvp_status != RSVPStatus.DECLINED, G.entry_status == GuestEntryStatus.NOT_ARRIVED),
            "arrived": G.entry_status.in_([GuestEntryStatus.CHECKED_IN, GuestEntryStatus.CHECKED_OUT]),
            "inside": G.entry_status == GuestEntryStatus.CHECKED_IN,
            "pending_rsvp": and_(active, G.rsvp_status.in_([RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE])),
            "attending": and_(active, G.rsvp_status == RSVPStatus.ATTENDING),
            "maybe": and_(active, G.rsvp_status == RSVPStatus.MAYBE),
            "declined": G.rsvp_status == RSVPStatus.DECLINED,
            "not_opened": and_(active, G.invitation_opened_at.is_(None)),
            "revoked": G.pass_status == GuestPassStatus.REVOKED,
        }[status]

    @staticmethod
    def _search_clause(q: str):
        G = CelebrationGuest
        like = f"%{q}%"
        clauses = [G.name.ilike(like), G.email.ilike(like), G.vehicle_number.ilike(like)]
        digits = "".join(ch for ch in q if ch.isdigit())
        if len(digits) >= 3:
            clauses.append(G.phone.ilike(f"%{digits}%"))
        code = cred.normalize_entry_code(q)
        if code:
            clauses.append(G.entry_code_hash == cred.hash_secret(cred.ENTRY_CODE_KIND, code))
        return or_(*clauses)

    async def list_invitations(
        self,
        celebration_id: uuid.UUID,
        user_id: uuid.UUID,
        *,
        status: str = "all",
        q: str | None = None,
        sort: str = "created_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
        base_url: str | None = None,
    ) -> tuple[list[GuestInvitationResponse], int]:
        if status not in self._HOST_FILTERS:
            raise ValidationError(f"Unknown status filter '{status}'.", field="status")
        if sort not in self._SORTS:
            raise ValidationError(f"Unknown sort '{sort}'.", field="sort")
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user_id)
            policy = await self.load_policy(uow)
            G = CelebrationGuest
            filters = [G.celebration_id == celebration_id]
            clause = self._filter_clause(status)
            if clause is not None:
                filters.append(clause)
            if q and q.strip():
                filters.append(self._search_clause(q.strip()))
            column = getattr(G, sort)
            ordering = column.asc().nullslast() if order == "asc" else column.desc().nullslast()
            result = await uow.occasions.guests.paginate(
                *filters, page=page, page_size=page_size, order_by=[ordering, G.id.asc()]
            )
            now = _now()
            return (
                [self._host_view(g, celebration, policy, base_url, now) for g in result.items],
                result.total,
            )

    async def summary(self, celebration_id: uuid.UUID, user_id: uuid.UUID) -> InvitationSummary:
        async with self._uow() as uow:
            await self._owned_celebration(uow, celebration_id, user_id)
            return await self._summary(uow, celebration_id)

    @staticmethod
    async def _summary(uow, celebration_id: uuid.UUID) -> InvitationSummary:
        G = CelebrationGuest
        active = G.pass_status == GuestPassStatus.ACTIVE
        not_declined = G.rsvp_status != RSVPStatus.DECLINED
        arrived = G.entry_status.in_([GuestEntryStatus.CHECKED_IN, GuestEntryStatus.CHECKED_OUT])

        def count(cond):
            return func.count().filter(cond)

        def total(expr, cond):
            return func.coalesce(func.sum(case((cond, expr), else_=0)), 0)

        row = (await uow.session.execute(
            select(
                func.count(),
                count(active),
                count(G.pass_status == GuestPassStatus.REVOKED),
                count(and_(active, G.rsvp_status == RSVPStatus.ATTENDING)),
                count(and_(active, G.rsvp_status == RSVPStatus.MAYBE)),
                count(G.rsvp_status == RSVPStatus.DECLINED),
                count(and_(active, G.rsvp_status.in_([RSVPStatus.PENDING, RSVPStatus.NO_RESPONSE]))),
                count(G.invitation_opened_at.is_not(None)),
                total(func.coalesce(G.rsvp_party_size, 1), and_(active, not_declined)),
                count(arrived),
                total(func.coalesce(G.checked_in_party_size, 1), arrived),
                count(G.entry_status == GuestEntryStatus.CHECKED_IN),
                count(G.entry_status == GuestEntryStatus.CHECKED_OUT),
                count(and_(active, not_declined, G.entry_status == GuestEntryStatus.NOT_ARRIVED)),
            ).where(G.celebration_id == celebration_id)
        )).one()
        keys = (
            "total", "active", "revoked", "rsvp_attending", "rsvp_maybe", "rsvp_declined",
            "rsvp_pending", "opened", "expected_people", "arrived_guests", "arrived_people",
            "inside_now", "checked_out", "still_expected",
        )
        return InvitationSummary(celebration_id=celebration_id, **{k: int(v or 0) for k, v in zip(keys, row)})

    async def _create_one(
        self,
        uow,
        celebration: Celebration,
        data: GuestInvitationCreate,
        policy: InvitationPolicy,
        actor: Actor,
        *,
        client_request_id: str | None,
    ) -> tuple[CelebrationGuest, bool]:
        """Returns (guest, created). Caller holds the celebration row lock."""
        if client_request_id:
            existing = await uow.occasions.guests.find_one(
                CelebrationGuest.celebration_id == celebration.id,
                CelebrationGuest.client_request_id == client_request_id,
            )
            if existing is not None:
                return existing, False

        if data.plus_ones_allowed > policy.max_plus_ones:
            raise ValidationError(
                f"A pass can admit at most {policy.max_plus_ones} accompanying guests.",
                field="plus_ones_allowed",
            )
        if data.phone and not rules.normalize_phone(data.phone):
            raise ValidationError("Enter a valid phone number.", field="phone")
        if await self._phone_taken(uow, celebration.id, data.phone):
            raise ConflictError(
                "This guest already has an active invitation for this celebration.",
                detail={"field": "phone"},
            )
        if await uow.occasions.guests.count_for_celebration(celebration.id) >= MAX_GUESTS_PER_CELEBRATION:
            raise GuestLimitExceededError()

        guest = await uow.occasions.guests.create_from_dict({
            "celebration_id": celebration.id,
            "name": data.name,
            "phone": rules.normalize_phone(data.phone),
            "email": data.email,
            "group_tag": data.group_tag,
            "notes": data.notes,
            "plus_ones_allowed": data.plus_ones_allowed,
            "arrival_window_start": data.arrival_window_start,
            "arrival_window_end": data.arrival_window_end,
            "vehicle_number": data.vehicle_number,
            "client_request_id": client_request_id,
            **(await self._unique_credentials(uow)),
        })
        await self._history(uow, guest, GuestHistoryEventType.INVITED, actor)
        return guest, True

    async def _assert_can_invite(self, uow, celebration: Celebration, policy: InvitationPolicy) -> None:
        reason = rules.can_invite_to(
            celebration_status=celebration.status,
            celebration_date=celebration.celebration_date,
            today=rules.event_today(settings.EVENT_TIMEZONE),
            policy=policy,
        )
        if reason:
            raise BusinessRuleError(reason)

    async def create_invitation(
        self,
        celebration_id: uuid.UUID,
        user,
        data: GuestInvitationCreate,
        *,
        base_url: str | None,
    ) -> tuple[GuestInvitationResponse, bool]:
        async with self._uow() as uow:
            # The row lock serialises concurrent creates for one celebration:
            # the duplicate-phone check, guest limit and idempotency lookup
            # cannot interleave.
            celebration = await self._owned_celebration(uow, celebration_id, user.id, lock=True)
            policy = await self.load_policy(uow)
            if not data.client_request_id or not await uow.occasions.guests.exists_where(
                CelebrationGuest.celebration_id == celebration_id,
                CelebrationGuest.client_request_id == data.client_request_id,
            ):
                await self._assert_can_invite(uow, celebration, policy)
            guest, created = await self._create_one(
                uow, celebration, data, policy,
                Actor("host", user.id, _host_label(user)),
                client_request_id=data.client_request_id,
            )
            return self._host_view(guest, celebration, policy, base_url, _now()), created

    async def bulk_create(
        self,
        celebration_id: uuid.UUID,
        user,
        data: GuestInvitationBulkCreate,
        *,
        base_url: str | None,
    ) -> BulkCreateResult:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id, lock=True)
            policy = await self.load_policy(uow)
            if len(data.guests) > policy.bulk_create_limit:
                raise ValidationError(
                    f"At most {policy.bulk_create_limit} guests can be invited at once.", field="guests"
                )
            await self._assert_can_invite(uow, celebration, policy)
            actor = Actor("host", user.id, _host_label(user))
            now = _now()
            results: list[BulkRowResult] = []
            seen_phones: set[str] = set()
            created = 0
            for index, row in enumerate(data.guests):
                phone = rules.normalize_phone(row.phone)
                if phone and phone in seen_phones:
                    results.append(BulkRowResult(index=index, status="duplicate", message="Same phone appears earlier in this list."))
                    continue
                try:
                    async with uow.session.begin_nested():
                        guest, was_created = await self._create_one(
                            uow, celebration, row, policy, actor,
                            client_request_id=f"{data.client_request_id}:{index}",
                        )
                except ConflictError as exc:
                    results.append(BulkRowResult(index=index, status="duplicate", message=exc.message))
                    continue
                except (ValidationError, GuestLimitExceededError) as exc:
                    results.append(BulkRowResult(index=index, status="error", message=exc.message))
                    if isinstance(exc, GuestLimitExceededError):
                        break
                    continue
                if phone:
                    seen_phones.add(phone)
                created += int(was_created)
                results.append(BulkRowResult(
                    index=index,
                    status="created" if was_created else "existing",
                    invitation=self._host_view(guest, celebration, policy, base_url, now),
                ))
            return BulkCreateResult(
                created=created,
                skipped=sum(1 for r in results if r.status in ("duplicate", "error")),
                results=results,
            )

    async def get_detail(self, celebration_id, guest_id, user_id, *, base_url) -> GuestInvitationDetail:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user_id)
            guest = await self._guest_in(uow, celebration_id, guest_id)
            policy = await self.load_policy(uow)
            history, entries = await self._guest_timeline(uow, guest)
            return GuestInvitationDetail(
                invitation=self._host_view(guest, celebration, policy, base_url, _now()),
                history=history,
                entries=entries,
            )

    async def update_invitation(self, celebration_id, guest_id, user, data: GuestInvitationUpdate, *, base_url) -> GuestInvitationResponse:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id, lock=True)
            guest = await self._guest_in(uow, celebration_id, guest_id, lock=True)
            if guest.pass_status is GuestPassStatus.REVOKED:
                raise ConflictError("A cancelled invitation can't be edited. Create a new invitation instead.")
            policy = await self.load_policy(uow)
            changes = data.model_dump(exclude_unset=True)
            if "name" in changes and not changes["name"]:
                raise ValidationError("Name is required.", field="name")
            if "plus_ones_allowed" in changes:
                if changes["plus_ones_allowed"] is None:
                    changes.pop("plus_ones_allowed")
                elif changes["plus_ones_allowed"] > policy.max_plus_ones:
                    raise ValidationError(
                        f"A pass can admit at most {policy.max_plus_ones} accompanying guests.",
                        field="plus_ones_allowed",
                    )
            if "phone" in changes:
                if changes["phone"] and not rules.normalize_phone(changes["phone"]):
                    raise ValidationError("Enter a valid phone number.", field="phone")
                changes["phone"] = rules.normalize_phone(changes["phone"])
                if await self._phone_taken(uow, celebration_id, changes["phone"], exclude_id=guest.id):
                    raise ConflictError(
                        "Another active invitation already uses this phone number.", detail={"field": "phone"}
                    )
            start = changes.get("arrival_window_start", guest.arrival_window_start)
            end = changes.get("arrival_window_end", guest.arrival_window_end)
            if (start is None) != (end is None):
                raise ValidationError("Give both the start and end of the arrival window, or neither.")
            changed = sorted(k for k, v in changes.items() if getattr(guest, k) != v)
            if changed:
                guest = await uow.occasions.guests.update(guest, {k: changes[k] for k in changed})
                await self._history(
                    uow, guest, GuestHistoryEventType.DETAILS_UPDATED,
                    Actor("host", user.id, _host_label(user)),
                    details={"fields": changed},
                )
            return self._host_view(guest, celebration, policy, base_url, _now())

    async def revoke(self, celebration_id, guest_id, user, reason: str | None, *, base_url) -> GuestInvitationResponse:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id)
            guest = await self._guest_in(uow, celebration_id, guest_id, lock=True)
            policy = await self.load_policy(uow)
            guest = await self._revoke(uow, guest, reason, Actor("host", user.id, _host_label(user)))
            return self._host_view(guest, celebration, policy, base_url, _now())

    async def _revoke(self, uow, guest: CelebrationGuest, reason: str | None, actor: Actor) -> CelebrationGuest:
        if guest.pass_status is GuestPassStatus.REVOKED:
            return guest  # idempotent: a repeated revoke is not an error
        # The lookup hashes stay so the old link shows "cancelled" and the gate
        # shows "revoked" (rather than a confusing "not found"); the
        # ciphertexts go so the link and code can never be re-shared. The
        # pass_status check in every gate path is what actually denies entry.
        guest = await uow.occasions.guests.update(guest, {
            "pass_status": GuestPassStatus.REVOKED,
            "revoked_at": _now(),
            "revoked_reason": reason,
            "entry_code_enc": None,
            "link_token_enc": None,
        })
        await self._history(uow, guest, GuestHistoryEventType.REVOKED, actor, details={"reason": reason} if reason else None)
        return guest

    async def rotate_credentials(self, celebration_id, guest_id, user, *, base_url) -> GuestInvitationResponse:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id)
            guest = await self._guest_in(uow, celebration_id, guest_id, lock=True)
            if guest.pass_status is GuestPassStatus.REVOKED:
                raise ConflictError("A cancelled invitation can't be reissued. Create a new invitation instead.")
            policy = await self.load_policy(uow)
            guest = await uow.occasions.guests.update(guest, {
                **(await self._unique_credentials(uow)),
                "credentials_rotated_at": _now(),
            })
            await self._history(uow, guest, GuestHistoryEventType.LINK_ROTATED, Actor("host", user.id, _host_label(user)))
            return self._host_view(guest, celebration, policy, base_url, _now())

    async def mark_shared(self, celebration_id, guest_id, user, channel: str, *, base_url) -> GuestInvitationResponse:
        """Record a share the host's device confirmed. Never implies delivery."""
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id)
            guest = await self._guest_in(uow, celebration_id, guest_id, lock=True)
            if guest.pass_status is GuestPassStatus.REVOKED:
                raise ConflictError("This invitation has been cancelled.")
            policy = await self.load_policy(uow)
            now = _now()
            guest = await uow.occasions.guests.update(guest, {
                "last_shared_at": now,
                "last_shared_channel": channel,
                "share_count": (guest.share_count or 0) + 1,
                "invitation_sent_at": guest.invitation_sent_at or now,
            })
            await self._history(uow, guest, GuestHistoryEventType.SHARED, Actor("host", user.id, _host_label(user)), details={"channel": channel})
            return self._host_view(guest, celebration, policy, base_url, now)

    @staticmethod
    def delivery_capabilities() -> DeliveryCapabilities:
        from app.services.notifications.email_client import is_configured

        return DeliveryCapabilities(email=is_configured())

    async def send_email(self, celebration_id, guest_id, user, *, base_url) -> EmailSendResult:
        from app.services.notifications.email_client import is_configured, send_email

        if not is_configured():
            raise BusinessRuleError("Email delivery isn't configured on this server. Share the link instead.")
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user.id)
            guest = await self._guest_in(uow, celebration_id, guest_id)
            if guest.pass_status is GuestPassStatus.REVOKED:
                raise ConflictError("This invitation has been cancelled.")
            if not guest.email:
                raise ValidationError("This guest has no email address.", field="email")
            link = self.invite_url(base_url, cred.decrypt(guest.link_token_enc))
            if not link:
                raise ConflictError("This invitation's link is unavailable; reissue it first.")
            to, title, name = guest.email, celebration.title, guest.name
            date_text = celebration.celebration_date.strftime("%A, %d %B %Y")
            host = _host_label(user)

        from html import escape

        subject = f"You're invited: {title}"
        text = f"Hi {name},\n\n{host} has invited you to {title} on {date_text}.\n\nView your invitation and RSVP: {link}\n"
        html_body = (
            f"<div style=\"font-family:sans-serif;font-size:15px;color:#2A2018\">"
            f"<p>Hi {escape(name)},</p><p>{escape(host)} has invited you to <b>{escape(title)}</b> on {escape(date_text)}.</p>"
            f"<p><a href=\"{escape(link)}\" style=\"background:#C96E1A;color:#fff;padding:10px 18px;border-radius:10px;"
            f"text-decoration:none;display:inline-block\">View invitation &amp; RSVP</a></p>"
            f"<p style=\"color:#6B5D50;font-size:13px\">This link is personal to you — please don't forward it.</p></div>"
        )
        sent, error = True, None
        try:
            await send_email(to=to, subject=subject, html_body=html_body, text_body=text)
        except Exception as exc:  # report honestly, never pretend it went out
            logger.exception("Invitation email failed for guest %s", guest_id)
            sent, error = False, type(exc).__name__

        async with self._uow() as uow:
            guest = await self._guest_in(uow, celebration_id, guest_id, lock=True)
            actor = Actor("host", user.id, host)
            if sent:
                now = _now()
                guest = await uow.occasions.guests.update(guest, {
                    "last_shared_at": now,
                    "last_shared_channel": "email",
                    "share_count": (guest.share_count or 0) + 1,
                    "invitation_sent_at": guest.invitation_sent_at or now,
                })
                await self._history(uow, guest, GuestHistoryEventType.EMAIL_SENT, actor)
            else:
                await self._history(uow, guest, GuestHistoryEventType.EMAIL_FAILED, actor, details={"error": error})
        return EmailSendResult(
            sent=sent,
            message="Email sent." if sent else "The email could not be sent. Share the link instead.",
        )

    # ══ 3. Guest (public) ═════════════════════════════════════════════════════

    async def _guest_by_token(self, uow, token: str | None) -> tuple[CelebrationGuest, Celebration]:
        lookup = cred.link_lookup(token)
        guest = await uow.occasions.guests.find_by_link_hash(lookup) if lookup else None
        celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id) if guest else None
        if guest is None or celebration is None:
            # One message for unknown, revoked-and-scrubbed or deleted, so a
            # token's validity can't be distinguished from its nonexistence.
            raise GuestNotFoundError("invitation")
        return guest, celebration

    def _public_view(self, guest, celebration, policy, theme_colors, host_first_name, now) -> PublicInvitation:
        state = self._pass_state(guest, celebration, policy, now)
        usable = state in ("valid", "not_yet_valid", "checked_out")
        code = cred.decrypt(guest.entry_code_enc) if usable else None
        qr_svg = None
        if code:
            qr = segno.make(cred.qr_payload(code), error="m")
            qr_svg = qr.svg_inline(scale=6, border=2, dark="#2A2018", light="#FFFFFF")
        map_url = None
        if celebration.latitude is not None and celebration.longitude is not None:
            map_url = f"https://www.google.com/maps/search/?api=1&query={celebration.latitude},{celebration.longitude}"
        return PublicInvitation(
            guest_name=guest.name,
            host_first_name=host_first_name,
            celebration_title=celebration.title,
            celebration_date=celebration.celebration_date,
            start_time=celebration.start_time,
            end_time=celebration.end_time,
            venue_name=celebration.venue_name,
            venue_address=celebration.venue_address,
            map_url=map_url,
            theme_colors=theme_colors,
            plus_ones_allowed=guest.plus_ones_allowed,
            arrival_window_start=guest.arrival_window_start,
            arrival_window_end=guest.arrival_window_end,
            rsvp_status=guest.rsvp_status,
            rsvp_party_size=guest.rsvp_party_size,
            can_respond=rules.can_rsvp(
                pass_status=guest.pass_status,
                celebration_status=celebration.status,
                celebration_date=celebration.celebration_date,
                today=rules.event_today(settings.EVENT_TIMEZONE, now),
            ),
            pass_state=state,
            entry_code=cred.format_entry_code(code) if code else None,
            qr_svg=qr_svg,
            celebration_status=celebration.status.value,
        )

    async def _public_context(self, uow, celebration: Celebration) -> tuple[dict | None, str | None]:
        theme_colors = celebration.custom_theme_colors
        if celebration.theme_id:
            theme = await uow.occasions.themes.get_by_id(celebration.theme_id)
            if theme:
                theme_colors = theme.colors
        host = await uow.users.users.get_by_id(celebration.customer_id)
        return theme_colors, (host.first_name if host else None)

    async def public_view(self, token: str | None) -> PublicInvitation:
        async with self._uow() as uow:
            guest, celebration = await self._guest_by_token(uow, token)
            if guest.invitation_opened_at is None:
                guest = await uow.occasions.guests.update(guest, {"invitation_opened_at": _now()})
                await self._history(uow, guest, GuestHistoryEventType.INVITATION_OPENED, Actor("guest", label=guest.name))
            policy = await self.load_policy(uow)
            theme_colors, host_first = await self._public_context(uow, celebration)
            return self._public_view(guest, celebration, policy, theme_colors, host_first, _now())

    async def public_rsvp(self, token: str | None, data: PublicRSVPSubmit) -> PublicInvitation:
        notify: tuple | None = None
        async with self._uow() as uow:
            guest, celebration = await self._guest_by_token(uow, token)
            guest = await uow.occasions.guests.get_by_id_with_lock(guest.id)
            now = _now()
            if not rules.can_rsvp(
                pass_status=guest.pass_status,
                celebration_status=celebration.status,
                celebration_date=celebration.celebration_date,
                today=rules.event_today(settings.EVENT_TIMEZONE, now),
            ):
                raise BusinessRuleError("Responses for this invitation are closed.")
            party_size = None
            if data.rsvp_status is RSVPStatus.ATTENDING:
                party_size = data.party_size or 1
                if party_size > 1 + guest.plus_ones_allowed:
                    raise ValidationError(
                        f"This invitation admits {1 + guest.plus_ones_allowed} "
                        f"{'person' if guest.plus_ones_allowed == 0 else 'people'} in total.",
                        field="party_size",
                    )
            previous = guest.rsvp_status
            changes = {
                "rsvp_status": data.rsvp_status,
                "rsvp_party_size": party_size,
                "rsvp_responded_at": now,
                "invitation_opened_at": guest.invitation_opened_at or now,
            }
            if data.note is not None:
                changes["guest_note"] = data.note or None  # never touches host's `notes`
            guest = await uow.occasions.guests.update(guest, changes)
            if previous != data.rsvp_status or guest.rsvp_party_size != party_size:
                await self._history(
                    uow, guest, GuestHistoryEventType.RSVP_CHANGED, Actor("guest", label=guest.name),
                    previous_status=previous, new_status=data.rsvp_status,
                    details={"party_size": party_size} if party_size else None,
                )
            if previous != data.rsvp_status:
                notify = (celebration.customer_id, celebration.id, guest.name, data.rsvp_status, celebration.title)
            policy = await self.load_policy(uow)
            theme_colors, host_first = await self._public_context(uow, celebration)
            view = self._public_view(guest, celebration, policy, theme_colors, host_first, now)
        if notify:
            await self._notify_rsvp(*notify)
        return view

    @staticmethod
    async def _notify(user_id, notification_type, title, body, celebration_id) -> None:
        """Best effort, after commit: a failed push never undoes the action."""
        from app.schemas.notifications import NotificationCreate
        from app.services.notifications.service import NotificationService

        try:
            await NotificationService().send_notification(
                user_id=user_id,
                data=NotificationCreate(
                    user_id=user_id,
                    notification_type=notification_type,
                    channel=NotificationChannel.PUSH,
                    title=title,
                    body=body,
                    reference_type="celebration",
                    reference_id=celebration_id,
                ),
            )
        except Exception:
            logger.exception("Invitation notification failed for user %s", user_id)

    async def _notify_rsvp(self, host_id, celebration_id, guest_name, status: RSVPStatus, title) -> None:
        verb = {RSVPStatus.ATTENDING: "is coming to", RSVPStatus.MAYBE: "might come to", RSVPStatus.DECLINED: "can't make it to"}[status]
        await self._notify(host_id, NotificationType.RSVP_UPDATE, "New RSVP", f"{guest_name} {verb} {title}.", celebration_id)

    # ══ 4. Gate ═══════════════════════════════════════════════════════════════

    def _gate_guest(self, guest: CelebrationGuest) -> GateGuest:
        return GateGuest(
            id=guest.id,
            name=guest.name,
            phone_masked=rules.mask_phone(guest.phone),
            plus_ones_allowed=guest.plus_ones_allowed,
            rsvp_status=guest.rsvp_status,
            rsvp_party_size=guest.rsvp_party_size,
            entry_status=guest.entry_status,
            checked_in_at=guest.checked_in_at,
            checked_in_party_size=guest.checked_in_party_size,
            arrival_window_start=guest.arrival_window_start,
            arrival_window_end=guest.arrival_window_end,
            vehicle_number=guest.vehicle_number,
        )

    async def host_scope(self, celebration_id: uuid.UUID, user) -> GateScope:
        async with self._uow() as uow:
            await self._owned_celebration(uow, celebration_id, user.id)
        return GateScope(Actor("host", user.id, _host_label(user)), celebration_id)

    async def gate_access_scope(self, token: str | None) -> GateScope:
        """Resolve a delegated gate token; reject expired, revoked or orphaned ones."""
        if not token or len(token) > 128:
            raise AuthenticationError("This gate link is invalid or has expired.")
        async with self._uow() as uow:
            access = await uow.occasions.gate_accesses.find_by_token_hash(cred.hash_secret(cred.GATE_TOKEN_KIND, token))
            now = _now()
            if access is None or not access.is_usable(now):
                raise AuthenticationError("This gate link is invalid or has expired.")
            celebration = await uow.occasions.celebrations.get_by_id(access.celebration_id)
            host = await uow.users.users.get_by_id(celebration.customer_id) if celebration else None
            if celebration is None or host is None or host.account_status not in (
                AccountStatus.ACTIVE, AccountStatus.PENDING_VERIFICATION
            ):
                raise AuthenticationError("This gate link is invalid or has expired.")
            if access.last_used_at is None or now - access.last_used_at > timedelta(minutes=1):
                await uow.occasions.gate_accesses.update(access, {"last_used_at": now})
            return GateScope(Actor("gate_access", label=access.label, gate_access_id=access.id), access.celebration_id)

    async def gate_session(self, scope: GateScope) -> GateSession:
        async with self._uow() as uow:
            celebration = await uow.occasions.celebrations.get_by_id(scope.celebration_id)
            if celebration is None:
                raise CelebrationNotFoundError(str(scope.celebration_id))
            access = (
                await uow.occasions.gate_accesses.get_by_id(scope.actor.gate_access_id)
                if scope.actor.gate_access_id else None
            )
            s = await self._summary(uow, celebration.id)
            return GateSession(
                celebration_id=celebration.id,
                celebration_title=celebration.title,
                celebration_date=celebration.celebration_date,
                start_time=celebration.start_time,
                end_time=celebration.end_time,
                venue_name=celebration.venue_name,
                operator_label=scope.actor.label or "Gate",
                expires_at=access.expires_at if access else None,
                arrived_guests=s.arrived_guests,
                arrived_people=s.arrived_people,
                still_expected=s.still_expected,
            )

    def _failure_key(self, scope: GateScope) -> str:
        who = scope.actor.gate_access_id or scope.actor.user_id
        return f"{GATE_FAILURE_LIMIT.key_prefix}:{who}"

    async def _resolve_pass(self, uow, scope: GateScope, req: GateRequest) -> CelebrationGuest | None:
        """Find the guest a request names, but only inside the operator's scope."""
        guest = None
        if req.guest_id is not None:
            guest = await uow.occasions.guests.get_by_id(req.guest_id)
        else:
            code = cred.normalize_entry_code(req.code)
            if code:
                guest = await uow.occasions.guests.find_by_code_hash(cred.hash_secret(cred.ENTRY_CODE_KIND, code))
        if guest is None:
            return None
        if scope.celebration_id is not None and guest.celebration_id != scope.celebration_id:
            return None  # a real pass for another event is "invalid" here
        return guest

    async def gate_action(self, scope: GateScope, req: GateRequest, action: GuestEntryAction) -> GateResult:
        # Throttle operators who keep presenting bad codes (guessing). Checked
        # before touching the database; only failures count against it.
        failure_key = self._failure_key(scope)
        if not await limiter.is_allowed(failure_key, GATE_FAILURE_LIMIT):
            await enforce_rate_limit(failure_key, GATE_FAILURE_LIMIT)

        party_size = req.party_size if isinstance(req, GateCheckIn) else None
        notify: tuple | None = None
        async with self._uow() as uow:
            guest = await self._resolve_pass(uow, scope, req)
            if guest is None:
                if scope.celebration_id is not None:
                    await self._log(uow, scope, None, scope.celebration_id, action, R.INVALID, req, party_size)
                await limiter.hit(failure_key, GATE_FAILURE_LIMIT)
                return GateResult(result=R.INVALID, message=rules.MESSAGES[R.INVALID], recorded=False)

            celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id)
            if celebration is None:
                await limiter.hit(failure_key, GATE_FAILURE_LIMIT)
                return GateResult(result=R.INVALID, message=rules.MESSAGES[R.INVALID], recorded=False)
            policy = await self.load_policy(uow)
            window = self.window(celebration, policy)

            # Retried scan (lost response, double tap): answer with the
            # original outcome instead of recording a second entry.
            if req.client_scan_id and action is not GuestEntryAction.VERIFY:
                earlier = await uow.occasions.entry_logs.find_one(
                    GuestEntryLog.celebration_guest_id == guest.id,
                    GuestEntryLog.action == action,
                    GuestEntryLog.client_scan_id == req.client_scan_id,
                )
                if earlier is not None:
                    return self._gate_result(guest, celebration, window, earlier.result, recorded=True, replayed=True, occurred_at=earlier.occurred_at)

            now = _now()
            evaluation = rules.evaluate(
                action=action,
                pass_status=guest.pass_status,
                entry_status=guest.entry_status,
                rsvp_status=guest.rsvp_status,
                plus_ones_allowed=guest.plus_ones_allowed,
                celebration_status=celebration.status,
                window=window,
                now=now,
                policy=policy,
                party_size=party_size,
            )

            if action is GuestEntryAction.VERIFY or evaluation.result not in (R.CHECKED_IN, R.CHECKED_OUT):
                if evaluation.result not in (R.VALID,):
                    await self._log(uow, scope, guest, celebration.id, action, evaluation.result, req, party_size)
                    if evaluation.result in (R.REVOKED, R.EXPIRED, R.NOT_YET_VALID, R.EVENT_CANCELLED):
                        await limiter.hit(failure_key, GATE_FAILURE_LIMIT)
                return self._gate_result(guest, celebration, window, evaluation.result, recorded=False, warnings=evaluation.warnings, message=evaluation.reason)

            # The state change itself is a conditional UPDATE: of two
            # concurrent check-ins for the same pass, exactly one matches.
            G = CelebrationGuest
            if action is GuestEntryAction.CHECK_IN:
                allowed = [GuestEntryStatus.NOT_ARRIVED] + ([GuestEntryStatus.CHECKED_OUT] if policy.allow_reentry else [])
                stmt = (
                    update(G)
                    .where(G.id == guest.id, G.pass_status == GuestPassStatus.ACTIVE, G.entry_status.in_(allowed))
                    .values(
                        entry_status=GuestEntryStatus.CHECKED_IN,
                        checked_in_at=now,
                        checked_in_party_size=party_size,
                        checked_out_at=None,
                        entry_count=G.entry_count + 1,
                        updated_at=now,
                    )
                )
            else:
                stmt = (
                    update(G)
                    .where(G.id == guest.id, G.entry_status == GuestEntryStatus.CHECKED_IN)
                    .values(entry_status=GuestEntryStatus.CHECKED_OUT, checked_out_at=now, updated_at=now)
                )
            changed = (await uow.session.execute(stmt.execution_options(synchronize_session=False))).rowcount
            await uow.session.refresh(guest)

            if not changed:
                # Lost the race. If it was our own retry that won, replay it.
                if req.client_scan_id:
                    earlier = await uow.occasions.entry_logs.find_one(
                        GuestEntryLog.celebration_guest_id == guest.id,
                        GuestEntryLog.action == action,
                        GuestEntryLog.client_scan_id == req.client_scan_id,
                    )
                    if earlier is not None:
                        return self._gate_result(guest, celebration, window, earlier.result, recorded=True, replayed=True, occurred_at=earlier.occurred_at)
                lost = R.ALREADY_CHECKED_IN if action is GuestEntryAction.CHECK_IN else R.NOT_CHECKED_IN
                if guest.pass_status is GuestPassStatus.REVOKED and action is GuestEntryAction.CHECK_IN:
                    lost = R.REVOKED
                await self._log(uow, scope, guest, celebration.id, action, lost, req, party_size)
                return self._gate_result(guest, celebration, window, lost, recorded=False)

            await self._log(uow, scope, guest, celebration.id, action, evaluation.result, req, party_size, scan_id=req.client_scan_id)
            event = GuestHistoryEventType.CHECKED_IN if action is GuestEntryAction.CHECK_IN else GuestHistoryEventType.CHECKED_OUT
            await self._history(uow, guest, event, scope.actor, details={"party_size": party_size} if party_size else None)
            if (
                action is GuestEntryAction.CHECK_IN
                and policy.notify_host_on_check_in
                and scope.actor.user_id != celebration.customer_id
            ):
                people = f" (+{party_size - 1})" if party_size and party_size > 1 else ""
                notify = (celebration.customer_id, NotificationType.GUEST_CHECKED_IN, "Guest arrived",
                          f"{guest.name}{people} has arrived at {celebration.title}.", celebration.id)
            result = self._gate_result(guest, celebration, window, evaluation.result, recorded=True, warnings=evaluation.warnings, occurred_at=now)
        if notify:
            await self._notify(*notify)
        return result

    def _gate_result(self, guest, celebration, window, result: R, *, recorded: bool, replayed: bool = False,
                     warnings=(), message: str | None = None, occurred_at=None) -> GateResult:
        return GateResult(
            result=result,
            message=message or rules.MESSAGES[result],
            recorded=recorded,
            replayed=replayed,
            warnings=list(warnings),
            guest=self._gate_guest(guest),
            celebration_title=celebration.title,
            valid_from=window[0],
            valid_until=window[1],
            occurred_at=occurred_at,
        )

    @staticmethod
    async def _log(uow, scope: GateScope, guest, celebration_id, action, result, req: GateRequest, party_size, *, scan_id=None) -> None:
        await uow.occasions.entry_logs.create(GuestEntryLog(
            celebration_id=celebration_id,
            celebration_guest_id=guest.id if guest else None,
            action=action,
            result=result,
            method=req.method,
            party_size=party_size,
            operator_type=scope.actor.operator_type,
            operator_user_id=scope.actor.user_id,
            gate_access_id=scope.actor.gate_access_id,
            operator_label=scope.actor.label,
            # Only successful state changes carry the scan id — that is what
            # makes a retry replayable and a duplicate impossible.
            client_scan_id=scan_id,
        ))

    async def gate_search(self, scope: GateScope, q: str) -> list[GateGuest]:
        q = (q or "").strip()
        if len(q) < 2 or scope.celebration_id is None:
            return []
        async with self._uow() as uow:
            G = CelebrationGuest
            clauses = [G.name.ilike(f"%{q}%")]
            digits = "".join(ch for ch in q if ch.isdigit())
            if len(digits) >= 4:
                clauses.append(G.phone.ilike(f"%{digits}"))  # last digits only
            if len(q) >= 4:
                clauses.append(G.vehicle_number.ilike(f"%{q}%"))
            guests = await uow.occasions.guests.find_many(
                G.celebration_id == scope.celebration_id,
                G.pass_status == GuestPassStatus.ACTIVE,
                or_(*clauses),
                order_by=G.name.asc(),
                limit=10,
            )
            return [self._gate_guest(g) for g in guests]

    # ══ 5. Gate access ════════════════════════════════════════════════════════

    @staticmethod
    def _access_view(access: CelebrationGateAccess, now: datetime, console_url: str | None = None) -> GateAccessResponse:
        return GateAccessResponse(
            id=access.id,
            celebration_id=access.celebration_id,
            label=access.label,
            expires_at=access.expires_at,
            revoked_at=access.revoked_at,
            last_used_at=access.last_used_at,
            created_at=access.created_at,
            is_active=access.is_usable(now),
            console_url=console_url,
        )

    async def list_gate_accesses(self, celebration_id, user_id) -> list[GateAccessResponse]:
        async with self._uow() as uow:
            await self._owned_celebration(uow, celebration_id, user_id)
            accesses = await uow.occasions.gate_accesses.find_many(
                CelebrationGateAccess.celebration_id == celebration_id,
                order_by=CelebrationGateAccess.created_at.desc(),
                limit=50,
            )
            now = _now()
            return [self._access_view(a, now) for a in accesses]

    async def create_gate_access(self, celebration_id, user_id, data: GateAccessCreate, *, base_url) -> GateAccessResponse:
        async with self._uow() as uow:
            celebration = await self._owned_celebration(uow, celebration_id, user_id)
            if celebration.status in (CelebrationStatus.CANCELLED, CelebrationStatus.COMPLETED):
                raise BusinessRuleError("Gate access can't be issued for a cancelled or completed celebration.")
            policy = await self.load_policy(uow)
            now = _now()
            _, window_end = self.window(celebration, policy)
            if window_end <= now:
                raise BusinessRuleError("This celebration's entry window has already closed.")
            hours = min(data.valid_hours or policy.gate_access_max_hours, policy.gate_access_max_hours)
            # Never outlive the event's entry window.
            expires_at = min(now + timedelta(hours=hours), window_end)
            token = cred.new_gate_token()
            access = await uow.occasions.gate_accesses.create(CelebrationGateAccess(
                celebration_id=celebration_id,
                label=data.label,
                token_hash=cred.hash_secret(cred.GATE_TOKEN_KIND, token),
                created_by_id=user_id,
                expires_at=expires_at,
            ))
            url = f"{base_url.rstrip('/')}{settings.API_V1_PREFIX}{GATE_PAGE_PATH}#{token}" if base_url else None
            return self._access_view(access, now, console_url=url)

    async def revoke_gate_access(self, celebration_id, access_id, user_id) -> GateAccessResponse:
        async with self._uow() as uow:
            await self._owned_celebration(uow, celebration_id, user_id)
            access = await uow.occasions.gate_accesses.get_by_id(access_id)
            if access is None or access.celebration_id != celebration_id:
                raise GuestNotFoundError(f"gate access {access_id}")
            if access.revoked_at is None:
                access = await uow.occasions.gate_accesses.update(access, {"revoked_at": _now()})
            return self._access_view(access, _now())

    # ══ 6. Admin ══════════════════════════════════════════════════════════════

    _ADMIN_SORTS = {
        "created_at": CelebrationGuest.created_at,
        "name": CelebrationGuest.name,
        "celebration_date": Celebration.celebration_date,
        "checked_in_at": CelebrationGuest.checked_in_at,
    }

    def _admin_row(self, guest, celebration, policy, now, *, mask: bool) -> AdminInvitationRow:
        return AdminInvitationRow(
            id=guest.id,
            celebration_id=celebration.id,
            celebration_title=celebration.title,
            celebration_date=celebration.celebration_date,
            celebration_status=celebration.status.value,
            host_id=celebration.customer_id,
            name=guest.name,
            phone=rules.mask_phone(guest.phone) if mask else guest.phone,
            email=None if mask else guest.email,
            plus_ones_allowed=guest.plus_ones_allowed,
            pass_status=guest.pass_status,
            pass_state=self._pass_state(guest, celebration, policy, now),
            rsvp_status=guest.rsvp_status,
            entry_status=guest.entry_status,
            checked_in_at=guest.checked_in_at,
            revoked_at=guest.revoked_at,
            created_at=guest.created_at,
        )

    @staticmethod
    def _masks_contact(user) -> bool:
        """Support staff help customers but don't need guests' contact details."""
        return user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN)

    def _admin_filters(self, *, q=None, celebration_id=None, pass_status=None, entry_status=None,
                       rsvp_status=None, date_from=None, date_to=None):
        G, C = CelebrationGuest, Celebration
        filters = [C.deleted_at.is_(None)]
        if celebration_id:
            filters.append(G.celebration_id == celebration_id)
        if pass_status:
            filters.append(G.pass_status == pass_status)
        if entry_status:
            filters.append(G.entry_status == entry_status)
        if rsvp_status:
            filters.append(G.rsvp_status == rsvp_status)
        if date_from:
            filters.append(C.celebration_date >= date_from)
        if date_to:
            filters.append(C.celebration_date <= date_to)
        if q and q.strip():
            filters.append(or_(self._search_clause(q.strip()), C.title.ilike(f"%{q.strip()}%")))
        return filters

    async def admin_list(self, user, *, page=1, page_size=20, sort="created_at", order="desc", **filters):
        if sort not in self._ADMIN_SORTS:
            raise ValidationError(f"Unknown sort '{sort}'.", field="sort")
        page, page_size = max(1, page), max(1, min(page_size, 100))
        async with self._uow() as uow:
            policy = await self.load_policy(uow)
            where = self._admin_filters(**filters)
            base = select(CelebrationGuest, Celebration).join(Celebration, Celebration.id == CelebrationGuest.celebration_id).where(*where)
            total = (await uow.session.execute(
                select(func.count()).select_from(CelebrationGuest).join(Celebration, Celebration.id == CelebrationGuest.celebration_id).where(*where)
            )).scalar_one()
            column = self._ADMIN_SORTS[sort]
            ordering = column.asc().nullslast() if order == "asc" else column.desc().nullslast()
            rows = (await uow.session.execute(
                base.order_by(ordering, CelebrationGuest.id).offset((page - 1) * page_size).limit(page_size)
            )).all()
            now, mask = _now(), self._masks_contact(user)
            return [self._admin_row(g, c, policy, now, mask=mask) for g, c in rows], total, page, page_size

    async def admin_export_rows(self, user, *, limit: int = 5000, **filters) -> list[AdminInvitationRow]:
        async with self._uow() as uow:
            policy = await self.load_policy(uow)
            rows = (await uow.session.execute(
                select(CelebrationGuest, Celebration)
                .join(Celebration, Celebration.id == CelebrationGuest.celebration_id)
                .where(*self._admin_filters(**filters))
                .order_by(Celebration.celebration_date.desc(), CelebrationGuest.name)
                .limit(limit)
            )).all()
            now = _now()
            return [self._admin_row(g, c, policy, now, mask=self._masks_contact(user)) for g, c in rows]

    async def admin_detail(self, user, guest_id: uuid.UUID) -> AdminInvitationDetail:
        async with self._uow() as uow:
            guest = await uow.occasions.guests.get_by_id(guest_id)
            celebration = await uow.occasions.celebrations.get_by_id(guest.celebration_id) if guest else None
            if guest is None or celebration is None:
                raise GuestNotFoundError(str(guest_id))
            policy = await self.load_policy(uow)
            history, entries = await self._guest_timeline(uow, guest)
            return AdminInvitationDetail(
                invitation=self._admin_row(guest, celebration, policy, _now(), mask=self._masks_contact(user)),
                revoked_reason=guest.revoked_reason,
                history=history,
                entries=entries,
            )

    async def admin_revoke(self, user, guest_id: uuid.UUID, reason: str | None) -> AdminInvitationDetail:
        async with self._uow() as uow:
            guest = await uow.occasions.guests.get_by_id_with_lock(guest_id)
            if guest is None or await uow.occasions.celebrations.get_by_id(guest.celebration_id) is None:
                raise GuestNotFoundError(str(guest_id))
            await self._revoke(uow, guest, reason, Actor("admin", user.id, f"Admin · {_host_label(user)}"))
        return await self.admin_detail(user, guest_id)

    async def admin_summary(self, celebration_id: uuid.UUID) -> InvitationSummary:
        async with self._uow() as uow:
            if await uow.occasions.celebrations.get_by_id(celebration_id) is None:
                raise CelebrationNotFoundError(str(celebration_id))
            return await self._summary(uow, celebration_id)

    async def entry_logs(
        self,
        *,
        celebration_id=None,
        result=None,
        action=None,
        failed_only=False,
        page=1,
        page_size=20,
    ) -> tuple[list[EntryLogItem], int, int, int]:
        page, page_size = max(1, page), max(1, min(page_size, 100))
        L, G = GuestEntryLog, CelebrationGuest
        filters = []
        if celebration_id:
            filters.append(L.celebration_id == celebration_id)
        if result:
            filters.append(L.result == result)
        if action:
            filters.append(L.action == action)
        if failed_only:
            filters.append(L.result.not_in([R.CHECKED_IN, R.CHECKED_OUT, R.VALID]))
        async with self._uow() as uow:
            total = (await uow.session.execute(select(func.count()).select_from(L).where(*filters))).scalar_one()
            rows = (await uow.session.execute(
                select(L, G.name).outerjoin(G, G.id == L.celebration_guest_id).where(*filters)
                .order_by(L.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)
            )).all()
            return [self._entry_item(log, name) for log, name in rows], total, page, page_size

    async def get_policy(self) -> InvitationPolicy:
        async with self._uow() as uow:
            return await self.load_policy(uow)

    async def update_policy(self, user, policy: InvitationPolicy) -> InvitationPolicy:
        from app.models.common.app_setting import AppSetting
        from app.models.enums import AppSettingDataType

        value = policy.model_dump_json()
        async with self._uow() as uow:
            setting = await uow.common.settings.get_by_key(rules.POLICY_SETTING_KEY)
            if setting is None:
                await uow.common.settings.create(AppSetting(
                    key=rules.POLICY_SETTING_KEY,
                    group="invitations",
                    label="Guest invitation policy",
                    description="Limits and rules for guest invitations and gate entry.",
                    value=value,
                    default_value=InvitationPolicy().model_dump_json(),
                    data_type=AppSettingDataType.JSON,
                    is_sensitive=False,
                    is_readonly=False,
                    is_environment_specific=False,
                    is_active=True,
                    created_by_id=user.id,
                    updated_by_id=user.id,
                ))
            else:
                await uow.common.settings.update(setting, {"value": value, "updated_by_id": user.id})
        logger.info("Invitation policy updated by %s: %s", user.id, value)
        return policy
