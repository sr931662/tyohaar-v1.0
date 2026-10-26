"""
Guest invitations, passes and gate entry against a real Postgres.

Skipped without TEST_DATABASE_URL (same convention and the same
disposable-database guard as test_deletion_lifecycle_integration):

    TEST_DATABASE_URL=postgresql+asyncpg://user@localhost:5432/tyohaar_test \
        python -m pytest tests/test_invitations_integration.py

Covers what only a real database can show: tenant isolation through real
queries, the conditional UPDATE that makes concurrent check-ins safe, the
partial unique index behind retry-safe scans, row locks behind idempotent
creates, and the HTTP surface (auth, roles, status codes, headers).
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.rate_limit import limiter
from app.models import *  # noqa: F401,F403 - registers every table on Base
from app.models.base import Base
from app.models.enums import (
    AccountStatus,
    CelebrationStatus,
    Currency,
    GuestEntryAction,
    GuestEntryStatus,
    GuestPassStatus,
    GuestVerificationResult as R,
    NotificationType,
    RSVPStatus,
    UserRole,
    UserType,
)
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.guest_entry_log import GuestEntryLog
from app.models.occasions.occasion import Occasion
from app.models.users.user import User
from app.schemas.invitations import (
    GateAccessCreate,
    GateCheckIn,
    GateRequest,
    GuestInvitationBulkCreate,
    GuestInvitationCreate,
    GuestInvitationUpdate,
    PublicRSVPSubmit,
)
from app.services.exceptions import (
    AuthenticationError,
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    RateLimitError,
    ValidationError,
)
from app.services.invitations import credentials as cred
from app.services.invitations.rules import InvitationPolicy, event_today
from app.services.invitations.service import InvitationService

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BASE = "https://invite.test"

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set — needs Postgres"),
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def engine():
    from test_deletion_lifecycle_integration import _assert_disposable  # same guard, one copy

    _assert_disposable(TEST_DATABASE_URL)
    from app.db.session import _build_engine_args

    url, connect_args = _build_engine_args(TEST_DATABASE_URL)
    engine = create_async_engine(url, connect_args=connect_args, future=True, pool_size=10)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        saved = {}
        for table in Base.metadata.tables.values():
            saved[table] = (table.comment, {c: c.comment for c in table.columns})
            table.comment = None
            for column in table.columns:
                column.comment = None
        try:
            await conn.run_sync(Base.metadata.create_all)
        finally:
            for table, (tc, cc) in saved.items():
                table.comment = tc
                for column, comment in cc.items():
                    column.comment = comment
    yield engine
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True, loop_scope="module")
async def clean(engine):
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, occasions, app_settings RESTART IDENTITY CASCADE"))
    limiter.reset()
    yield


@pytest_asyncio.fixture(loop_scope="module")
async def sf(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
def notified(monkeypatch):
    sent: list[tuple] = []

    async def capture(user_id, notification_type, title, body, celebration_id):
        sent.append((user_id, notification_type, body))

    monkeypatch.setattr(InvitationService, "_notify", staticmethod(capture))
    return sent


@pytest_asyncio.fixture(loop_scope="module")
async def svc(sf, notified):
    return InvitationService(sf)


async def make_user(sf, role=UserRole.CUSTOMER, first="Priya", status=AccountStatus.ACTIVE) -> User:
    async with sf() as s:
        user = User(
            id=uuid.uuid4(), phone=f"+9198{uuid.uuid4().int % 100000000:08d}", first_name=first,
            last_name="Host", role=role, user_type=UserType.INDIVIDUAL, account_status=status,
        )
        s.add(user)
        await s.commit()
        return user


async def make_celebration(sf, owner, *, days_ahead=0, start=None, end=None,
                           status=CelebrationStatus.CONFIRMED) -> Celebration:
    async with sf() as s:
        occasion = Occasion(id=uuid.uuid4(), name="Diwali", slug=f"diwali-{uuid.uuid4().hex[:6]}",
                            display_order=0, popularity_score=0, is_active=True, is_featured=False,
                            is_seasonal=False, allow_balloon_theme=False)
        s.add(occasion)
        await s.flush()
        celebration = Celebration(
            id=uuid.uuid4(), customer_id=owner.id, occasion_id=occasion.id, title="Diwali at home",
            celebration_date=event_today(settings.EVENT_TIMEZONE) + timedelta(days=days_ahead),
            start_time=start, end_time=end, guest_count=50, status=status, completion_percentage=0,
            currency=Currency.INR, venue_name="Tower B Clubhouse", venue_address="12 Lake Road",
        )
        s.add(celebration)
        await s.commit()
        return celebration


async def invite(svc, celebration, host, name="Ravi", **kw):
    data = GuestInvitationCreate(name=name, **kw)
    result, created = await svc.create_invitation(celebration.id, host, data, base_url=BASE)
    return result


def token_of(inv) -> str:
    return inv.invite_url.split("#", 1)[1]


async def set_day(sf, celebration, days_from_today: int, **extra):
    async with sf() as s:
        await s.execute(update(Celebration).where(Celebration.id == celebration.id).values(
            celebration_date=event_today(settings.EVENT_TIMEZONE) + timedelta(days=days_from_today), **extra))
        await s.commit()


# ── Host: create / list / detail / edit ───────────────────────────────────────

async def test_create_list_summary_and_detail(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=3)
    inv = await invite(svc, cel, host, phone="+91 98765 43210", plus_ones_allowed=2,
                       arrival_window_start=time(19), arrival_window_end=time(21),
                       vehicle_number="mh12ab1234", notes="Seat near family")
    assert inv.phone == "+919876543210" and inv.vehicle_number == "MH12AB1234"
    assert inv.pass_state == "not_yet_valid" and inv.entry_code and inv.qr_payload.startswith("TYH1:")
    assert inv.invite_url.startswith(f"{BASE}{settings.API_V1_PREFIX}/public/invite/page#")

    items, total = await svc.list_invitations(cel.id, host.id, base_url=BASE)
    assert total == 1 and items[0].id == inv.id

    summary = await svc.summary(cel.id, host.id)
    assert (summary.total, summary.active, summary.still_expected, summary.arrived_guests) == (1, 1, 1, 0)

    detail = await svc.get_detail(cel.id, inv.id, host.id, base_url=BASE)
    assert [h.event_type for h in detail.history] == ["invited"]
    assert detail.history[0].actor_type == "host"

    # Nothing secret is stored in the clear.
    async with sf() as s:
        row = (await s.execute(select(CelebrationGuest).where(CelebrationGuest.id == inv.id))).scalar_one()
        assert token_of(inv) not in (row.link_token_enc or "") and row.link_token_hash != token_of(inv)


async def test_search_filters_and_sort(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    a = await invite(svc, cel, host, name="Asha Rao", phone="+919000000001")
    await invite(svc, cel, host, name="Bimal", phone="+919000000002")
    items, _ = await svc.list_invitations(cel.id, host.id, q="asha")
    assert [i.id for i in items] == [a.id]
    items, _ = await svc.list_invitations(cel.id, host.id, q="0001")
    assert [i.id for i in items] == [a.id]
    items, _ = await svc.list_invitations(cel.id, host.id, q=a.entry_code)  # code lookup
    assert [i.id for i in items] == [a.id]
    items, _ = await svc.list_invitations(cel.id, host.id, sort="name", order="asc")
    assert [i.name for i in items] == ["Asha Rao", "Bimal"]
    with pytest.raises(ValidationError):
        await svc.list_invitations(cel.id, host.id, status="bogus")


async def test_duplicate_phone_is_rejected_after_normalisation(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    await invite(svc, cel, host, phone="+91 90000 00001")
    with pytest.raises(ConflictError):
        await invite(svc, cel, host, name="Same person", phone="+919000000001")


async def test_idempotent_create_under_concurrency(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    data = GuestInvitationCreate(name="Retry", client_request_id="req-12345678")
    results = await asyncio.gather(*[
        svc.create_invitation(cel.id, host, data, base_url=BASE) for _ in range(5)
    ])
    ids = {r[0].id for r in results}
    assert len(ids) == 1 and sum(created for _, created in results) == 1
    async with sf() as s:
        assert (await s.execute(select(func.count()).select_from(CelebrationGuest))).scalar_one() == 1


async def test_validation_and_business_rules(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    with pytest.raises(ValidationError):
        await invite(svc, cel, host, plus_ones_allowed=11)  # default policy max 10
    with pytest.raises(ValidationError):
        await invite(svc, cel, host, phone="12")
    with pytest.raises(ValueError):
        GuestInvitationCreate(name="x", arrival_window_start=time(19))
    with pytest.raises(ValueError):
        GuestInvitationCreate(name="", phone="+919000000001")
    past = await make_celebration(sf, host, days_ahead=-1)
    with pytest.raises(BusinessRuleError):
        await invite(svc, past, host)
    cancelled = await make_celebration(sf, host, days_ahead=5, status=CelebrationStatus.CANCELLED)
    with pytest.raises(BusinessRuleError):
        await invite(svc, cancelled, host)


async def test_bulk_create_reports_per_row_and_is_retry_safe(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    await invite(svc, cel, host, name="Existing", phone="+919000000009")
    payload = GuestInvitationBulkCreate(client_request_id="bulk-abcdefgh", guests=[
        GuestInvitationCreate(name="One", phone="+919000000001"),
        GuestInvitationCreate(name="Two", phone="+91 90000 00001"),   # same as row 0
        GuestInvitationCreate(name="Three", phone="+919000000009"),    # already invited
        GuestInvitationCreate(name="Four", plus_ones_allowed=40),      # over policy
        GuestInvitationCreate(name="Five"),
    ])
    result = await svc.bulk_create(cel.id, host, payload, base_url=BASE)
    assert [r.status for r in result.results] == ["created", "duplicate", "duplicate", "error", "created"]
    assert result.created == 2
    again = await svc.bulk_create(cel.id, host, payload, base_url=BASE)
    assert again.created == 0 and [r.status for r in again.results][0] == "existing"
    assert (await svc.summary(cel.id, host.id)).total == 3


async def test_edit_records_changed_fields_and_blocks_revoked(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=2)
    inv = await invite(svc, cel, host, phone="+919000000001")
    other = await invite(svc, cel, host, name="Other", phone="+919000000002")
    updated = await svc.update_invitation(cel.id, inv.id, host, GuestInvitationUpdate(plus_ones_allowed=3, name="Ravi K"), base_url=BASE)
    assert updated.plus_ones_allowed == 3 and updated.name == "Ravi K"
    detail = await svc.get_detail(cel.id, inv.id, host.id, base_url=BASE)
    assert detail.history[0].event_type == "details_updated"
    assert detail.history[0].details == {"fields": ["name", "plus_ones_allowed"]}
    with pytest.raises(ConflictError):
        await svc.update_invitation(cel.id, inv.id, host, GuestInvitationUpdate(phone="+919000000002"), base_url=BASE)
    await svc.revoke(cel.id, other.id, host, "wrong person", base_url=BASE)
    with pytest.raises(ConflictError):
        await svc.update_invitation(cel.id, other.id, host, GuestInvitationUpdate(name="x"), base_url=BASE)


# ── Tenant isolation ──────────────────────────────────────────────────────────

async def test_other_users_cannot_read_or_change_invitations(sf, svc):
    host, intruder = await make_user(sf), await make_user(sf, first="Mallory")
    cel = await make_celebration(sf, host, days_ahead=0)
    inv = await invite(svc, cel, host)
    for call in (
        svc.list_invitations(cel.id, intruder.id),
        svc.summary(cel.id, intruder.id),
        svc.get_detail(cel.id, inv.id, intruder.id, base_url=BASE),
        svc.revoke(cel.id, inv.id, intruder, None, base_url=BASE),
        svc.rotate_credentials(cel.id, inv.id, intruder, base_url=BASE),
        svc.create_invitation(cel.id, intruder, GuestInvitationCreate(name="x"), base_url=BASE),
        svc.host_scope(cel.id, intruder),
        svc.list_gate_accesses(cel.id, intruder.id),
    ):
        with pytest.raises(NotFoundError):
            await call
    # Guessing a guest id under one's own celebration doesn't reach it either.
    mine = await make_celebration(sf, intruder, days_ahead=1)
    with pytest.raises(NotFoundError):
        await svc.get_detail(mine.id, inv.id, intruder.id, base_url=BASE)


# ── Guest (public) ────────────────────────────────────────────────────────────

async def test_public_view_shows_only_permitted_fields(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=0)
    inv = await invite(svc, cel, host, phone="+919000000001", notes="PRIVATE host note", plus_ones_allowed=1)
    view = await svc.public_view(token_of(inv))
    dumped = view.model_dump_json()
    assert view.guest_name == "Ravi" and view.host_first_name == "Priya"
    assert "PRIVATE" not in dumped and "+919000000001" not in dumped and str(inv.id) not in dumped
    assert view.pass_state == "valid" and view.entry_code == inv.entry_code and "<svg" in view.qr_svg
    detail = await svc.get_detail(cel.id, inv.id, host.id, base_url=BASE)
    assert detail.invitation.invitation_opened_at is not None
    for bad in ("nope", "", None, token_of(inv)[:-1] + "x"):
        with pytest.raises(NotFoundError):
            await svc.public_view(bad)


async def test_rsvp_rules_notes_and_notification_dedupe(sf, svc, notified):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=3)
    inv = await invite(svc, cel, host, plus_ones_allowed=1, notes="host only")
    with pytest.raises(ValidationError):
        await svc.public_rsvp(token_of(inv), PublicRSVPSubmit(rsvp_status=RSVPStatus.ATTENDING, party_size=3))
    view = await svc.public_rsvp(token_of(inv), PublicRSVPSubmit(rsvp_status=RSVPStatus.ATTENDING, party_size=2, note="Veg"))
    assert view.rsvp_status is RSVPStatus.ATTENDING and view.rsvp_party_size == 2
    await svc.public_rsvp(token_of(inv), PublicRSVPSubmit(rsvp_status=RSVPStatus.ATTENDING, party_size=2))
    detail = await svc.get_detail(cel.id, inv.id, host.id, base_url=BASE)
    assert detail.invitation.notes == "host only" and detail.invitation.guest_note == "Veg"
    assert len([n for n in notified if n[1] is NotificationType.RSVP_UPDATE]) == 1  # repeat didn't re-notify
    assert (await svc.summary(cel.id, host.id)).expected_people == 2
    with pytest.raises(ValueError):
        PublicRSVPSubmit(rsvp_status=RSVPStatus.PENDING)
    await set_day(sf, cel, 0)  # responses close on the event day
    with pytest.raises(BusinessRuleError):
        await svc.public_rsvp(token_of(inv), PublicRSVPSubmit(rsvp_status=RSVPStatus.DECLINED))


# ── Gate ──────────────────────────────────────────────────────────────────────

async def _host_gate(sf, svc, **cel_kw):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, **cel_kw)
    return host, cel, await svc.host_scope(cel.id, host)


async def test_verify_then_check_in_then_duplicate(sf, svc, notified):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host, plus_ones_allowed=2)
    verify = await svc.gate_action(scope, GateRequest(code=inv.qr_payload, method="qr"), GuestEntryAction.VERIFY)
    assert verify.result is R.VALID and not verify.recorded and verify.guest.plus_ones_allowed == 2
    done = await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, party_size=3, client_scan_id="scan-0001"), GuestEntryAction.CHECK_IN)
    assert done.result is R.CHECKED_IN and done.recorded and done.guest.checked_in_party_size == 3
    again = await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id="scan-0002"), GuestEntryAction.CHECK_IN)
    assert again.result is R.ALREADY_CHECKED_IN and not again.recorded
    s = await svc.summary(cel.id, host.id)
    assert (s.arrived_guests, s.arrived_people, s.inside_now, s.still_expected) == (1, 3, 1, 0)
    assert notified == []  # the host checked them in personally — no self-notification


async def test_concurrent_check_ins_record_exactly_one_entry(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host)
    results = await asyncio.gather(*[
        svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id=f"scan-par-{i:04d}"), GuestEntryAction.CHECK_IN)
        for i in range(8)
    ])
    outcomes = sorted(r.result.value for r in results)
    assert outcomes.count("checked_in") == 1 and outcomes.count("already_checked_in") == 7
    async with sf() as s:
        guest = (await s.execute(select(CelebrationGuest).where(CelebrationGuest.id == inv.id))).scalar_one()
        assert guest.entry_count == 1
        recorded = (await s.execute(select(func.count()).select_from(GuestEntryLog).where(
            GuestEntryLog.result == R.CHECKED_IN))).scalar_one()
        assert recorded == 1


async def test_retried_scan_is_replayed_not_duplicated(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host)
    req = GateCheckIn(code=inv.entry_code, client_scan_id="scan-retry-01")
    results = await asyncio.gather(*[svc.gate_action(scope, req, GuestEntryAction.CHECK_IN) for _ in range(4)])
    assert all(r.recorded for r in results)  # every retry reports the (single) success
    assert sum(not r.replayed for r in results) == 1
    later = await svc.gate_action(scope, req, GuestEntryAction.CHECK_IN)
    assert later.replayed and later.result is R.CHECKED_IN


async def test_check_out_and_reentry_policy(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host)
    await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id="in-000001"), GuestEntryAction.CHECK_IN)
    out = await svc.gate_action(scope, GateRequest(code=inv.entry_code, client_scan_id="out-00001"), GuestEntryAction.CHECK_OUT)
    assert out.result is R.CHECKED_OUT and out.recorded
    no = await svc.gate_action(scope, GateRequest(code=inv.entry_code, client_scan_id="out-00002"), GuestEntryAction.CHECK_OUT)
    assert no.result is R.NOT_CHECKED_IN
    used = await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id="in-000002"), GuestEntryAction.CHECK_IN)
    assert used.result is R.ALREADY_USED
    admin = await make_user(sf, role=UserRole.SUPER_ADMIN)
    await svc.update_policy(admin, InvitationPolicy(allow_reentry=True))
    back = await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id="in-000003"), GuestEntryAction.CHECK_IN)
    assert back.result is R.CHECKED_IN and "reentry" in back.warnings


async def test_time_window_cancellation_and_reschedule(sf, svc):
    host, cel, scope = await _host_gate(sf, svc, days_ahead=2)
    inv = await invite(svc, cel, host)
    req = GateRequest(code=inv.entry_code)
    assert (await svc.gate_action(scope, req, GuestEntryAction.VERIFY)).result is R.NOT_YET_VALID
    await set_day(sf, cel, 0)  # rescheduled to today: the same pass follows the event
    assert (await svc.gate_action(scope, req, GuestEntryAction.VERIFY)).result is R.VALID
    await set_day(sf, cel, -2)
    assert (await svc.gate_action(scope, req, GuestEntryAction.VERIFY)).result is R.EXPIRED
    await set_day(sf, cel, 0, status=CelebrationStatus.CANCELLED)
    assert (await svc.gate_action(scope, req, GuestEntryAction.VERIFY)).result is R.EVENT_CANCELLED
    view = await svc.public_view(token_of(inv))
    assert view.pass_state == "event_cancelled" and view.entry_code is None and not view.can_respond


async def test_party_size_limit_and_invalid_codes(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host, plus_ones_allowed=1)
    over = await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, party_size=3), GuestEntryAction.CHECK_IN)
    assert over.result is R.PARTY_SIZE_EXCEEDED and not over.recorded
    for code in ("ZZZZ-ZZZZ", "not a code", "TYH1:"):
        assert (await svc.gate_action(scope, GateRequest(code=code), GuestEntryAction.VERIFY)).result is R.INVALID
    async with sf() as s:
        failed = (await s.execute(select(func.count()).select_from(GuestEntryLog).where(
            GuestEntryLog.celebration_guest_id.is_(None)))).scalar_one()
        assert failed == 3  # unknown codes are logged against the event for review


async def test_revocation_and_rotation(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host)
    rotated = await svc.rotate_credentials(cel.id, inv.id, host, base_url=BASE)
    assert rotated.entry_code != inv.entry_code and token_of(rotated) != token_of(inv)
    assert (await svc.gate_action(scope, GateRequest(code=inv.entry_code), GuestEntryAction.VERIFY)).result is R.INVALID
    with pytest.raises(NotFoundError):
        await svc.public_view(token_of(inv))
    revoked = await svc.revoke(cel.id, inv.id, host, "plans changed", base_url=BASE)
    assert revoked.pass_status is GuestPassStatus.REVOKED and revoked.invite_url is None and revoked.entry_code is None
    again = await svc.revoke(cel.id, inv.id, host, None, base_url=BASE)  # idempotent
    assert again.revoked_reason == "plans changed"
    assert (await svc.gate_action(scope, GateCheckIn(code=rotated.entry_code), GuestEntryAction.CHECK_IN)).result is R.REVOKED
    view = await svc.public_view(token_of(rotated))  # the old link explains itself, nothing more
    assert view.pass_state == "revoked" and view.entry_code is None and view.qr_svg is None
    with pytest.raises(BusinessRuleError):
        await svc.public_rsvp(token_of(rotated), PublicRSVPSubmit(rsvp_status=RSVPStatus.ATTENDING))
    with pytest.raises(ConflictError):
        await svc.rotate_credentials(cel.id, inv.id, host, base_url=BASE)
    # Re-inviting the same phone is allowed once the old pass is revoked.
    assert (await invite(svc, cel, host, name="Ravi again")).pass_status is GuestPassStatus.ACTIVE


async def test_check_out_still_works_after_revocation(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    inv = await invite(svc, cel, host)
    await svc.gate_action(scope, GateCheckIn(code=inv.entry_code, client_scan_id="in-rev-0001"), GuestEntryAction.CHECK_IN)
    await svc.revoke(cel.id, inv.id, host, None, base_url=BASE)
    out = await svc.gate_action(scope, GateRequest(guest_id=inv.id, method="search", client_scan_id="out-rev-001"), GuestEntryAction.CHECK_OUT)
    assert out.result is R.CHECKED_OUT


# ── Gate access (delegated staff) ─────────────────────────────────────────────

async def test_gate_access_is_scoped_expiring_and_revocable(sf, svc, notified):
    host = await make_user(sf)
    cel = await make_celebration(sf, host, end=time(23, 59))
    other_cel = await make_celebration(sf, host)
    inv = await invite(svc, cel, host, phone="+919876543210")
    foreign = await invite(svc, other_cel, host, name="Elsewhere")

    access = await svc.create_gate_access(cel.id, host.id, GateAccessCreate(label="Main gate — Ramesh", valid_hours=300), base_url=BASE)
    assert access.console_url.startswith(f"{BASE}{settings.API_V1_PREFIX}/public/gate/page#")
    window_end = svc.window(cel, InvitationPolicy())[1]
    assert access.expires_at <= window_end  # never outlives the event
    token = access.console_url.split("#", 1)[1]
    listed = await svc.list_gate_accesses(cel.id, host.id)
    assert listed[0].console_url is None  # shown once only

    scope = await svc.gate_access_scope(token)
    session = await svc.gate_session(scope)
    assert session.operator_label == "Main gate — Ramesh" and session.still_expected == 1

    assert (await svc.gate_action(scope, GateRequest(code=foreign.entry_code), GuestEntryAction.VERIFY)).result is R.INVALID
    found = await svc.gate_search(scope, "3210")
    assert [g.id for g in found] == [inv.id] and found[0].phone_masked == "••••3210"
    assert await svc.gate_search(scope, "Elsewhere") == []

    done = await svc.gate_action(scope, GateCheckIn(guest_id=inv.id, method="search", client_scan_id="ga-000001"), GuestEntryAction.CHECK_IN)
    assert done.recorded
    assert notified and notified[0][1] is NotificationType.GUEST_CHECKED_IN  # staff check-in tells the host
    detail = await svc.get_detail(cel.id, inv.id, host.id, base_url=BASE)
    assert detail.entries[0].operator_label == "Main gate — Ramesh"
    assert detail.history[0].actor_type == "gate_access"

    await svc.revoke_gate_access(cel.id, access.id, host.id)
    with pytest.raises(AuthenticationError):
        await svc.gate_access_scope(token)
    for bad in (None, "", "x" * 200, "guess"):
        with pytest.raises(AuthenticationError):
            await svc.gate_access_scope(bad)


async def test_gate_access_dies_with_expiry_and_host_deactivation(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host)
    access = await svc.create_gate_access(cel.id, host.id, GateAccessCreate(label="Gate"), base_url=BASE)
    token = access.console_url.split("#", 1)[1]
    async with sf() as s:
        await s.execute(update(User).where(User.id == host.id).values(account_status=AccountStatus.SUSPENDED))
        await s.commit()
    with pytest.raises(AuthenticationError):
        await svc.gate_access_scope(token)
    async with sf() as s:
        await s.execute(update(User).where(User.id == host.id).values(account_status=AccountStatus.ACTIVE))
        from app.models.occasions.gate_access import CelebrationGateAccess
        await s.execute(update(CelebrationGateAccess).values(expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)))
        await s.commit()
    with pytest.raises(AuthenticationError):
        await svc.gate_access_scope(token)


async def test_repeated_bad_codes_are_throttled(sf, svc):
    host, cel, scope = await _host_gate(sf, svc)
    for _ in range(30):
        await svc.gate_action(scope, GateRequest(code="ZZZZ-ZZZZ"), GuestEntryAction.VERIFY)
    with pytest.raises(RateLimitError):
        await svc.gate_action(scope, GateRequest(code="ZZZZ-ZZZZ"), GuestEntryAction.VERIFY)


# ── Admin ─────────────────────────────────────────────────────────────────────

async def test_admin_list_masks_for_support_and_admin_revokes(sf, svc):
    host = await make_user(sf)
    cel = await make_celebration(sf, host)
    inv = await invite(svc, cel, host, phone="+919876543210", email="ravi@example.com")
    support, admin = await make_user(sf, role=UserRole.SUPPORT), await make_user(sf, role=UserRole.ADMIN)

    rows, total, _, _ = await svc.admin_list(support, q="ravi")
    assert total == 1 and rows[0].phone == "••••3210" and rows[0].email is None
    rows, _, _, _ = await svc.admin_list(admin, pass_status=GuestPassStatus.ACTIVE, date_from=date.today() - timedelta(days=2))
    assert rows[0].phone == "+919876543210"

    detail = await svc.admin_revoke(admin, inv.id, "reported compromised")
    assert detail.invitation.pass_status is GuestPassStatus.REVOKED
    assert detail.history[0].actor_type == "admin" and detail.history[0].details == {"reason": "reported compromised"}
    scope = await svc.host_scope(cel.id, host)
    await svc.gate_action(scope, GateRequest(code=inv.entry_code), GuestEntryAction.VERIFY)
    logs, total, _, _ = await svc.entry_logs(failed_only=True)
    assert total == 1 and logs[0].result is R.REVOKED and logs[0].guest_name == "Ravi"
    export = await svc.admin_export_rows(admin, celebration_id=cel.id)
    assert len(export) == 1


async def test_policy_round_trip_and_enforcement(sf, svc):
    super_admin = await make_user(sf, role=UserRole.SUPER_ADMIN)
    assert await svc.get_policy() == InvitationPolicy()
    await svc.update_policy(super_admin, InvitationPolicy(max_plus_ones=1))
    assert (await svc.get_policy()).max_plus_ones == 1
    host = await make_user(sf)
    cel = await make_celebration(sf, host, days_ahead=1)
    with pytest.raises(ValidationError):
        await invite(svc, cel, host, plus_ones_allowed=2)


# ── HTTP surface ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(loop_scope="module")
async def http(sf, notified):
    from app.core.current_user import get_current_user
    from app.core.dependencies import get_invitation_service
    from app.main import create_app
    from app.schemas.users.response import UserResponse

    app = create_app()
    state: dict = {"user": None}

    async def current_user():
        from fastapi import HTTPException
        if state["user"] is None:
            raise HTTPException(status_code=401, detail="Not authenticated")
        return state["user"]

    from app.core.dependencies import get_occasion_service
    from app.services.occasions.service import OccasionService

    app.dependency_overrides[get_current_user] = current_user
    app.dependency_overrides[get_invitation_service] = lambda: InvitationService(sf)
    # The legacy RSVP routes live on OccasionService. Every service an
    # exercised route touches must be bound to the scratch database — the
    # default factory points at whatever server/.env configures.
    app.dependency_overrides[get_occasion_service] = lambda: OccasionService(sf)

    def login(user):
        state["user"] = None if user is None else UserResponse.model_validate(user, from_attributes=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.login = login  # type: ignore[attr-defined]
        yield client


P = settings.API_V1_PREFIX


async def _user_for_http(sf, role=UserRole.CUSTOMER):
    user = await make_user(sf, role=role)
    async with sf() as s:  # UserResponse needs the server-defaulted columns
        return (await s.execute(select(User).where(User.id == user.id))).scalar_one()


async def test_http_host_flow_status_codes(sf, http):
    host = await _user_for_http(sf)
    cel = await make_celebration(sf, host)
    http.login(None)
    assert (await http.get(f"{P}/celebrations/{cel.id}/invitations")).status_code == 401
    http.login(host)
    body = {"name": "Ravi", "phone": "+919000000001", "client_request_id": "http-req-0001"}
    first = await http.post(f"{P}/celebrations/{cel.id}/invitations", json=body)
    assert first.status_code == 201
    retry = await http.post(f"{P}/celebrations/{cel.id}/invitations", json=body)
    assert retry.status_code == 200 and retry.json()["data"]["id"] == first.json()["data"]["id"]
    dup = await http.post(f"{P}/celebrations/{cel.id}/invitations", json={**body, "client_request_id": "http-req-0002"})
    assert dup.status_code == 409 and dup.json()["error"]["code"] == "CONFLICT"
    assert (await http.post(f"{P}/celebrations/{cel.id}/invitations", json={"phone": "1"})).status_code == 422
    listing = await http.get(f"{P}/celebrations/{cel.id}/invitations", params={"status": "expected", "page_size": 5})
    assert listing.status_code == 200 and listing.json()["meta"]["total"] == 1
    assert (await http.get(f"{P}/celebrations/{cel.id}/invitations/summary")).json()["data"]["total"] == 1
    gid = first.json()["data"]["id"]
    code = first.json()["data"]["entry_code"]
    checkin = await http.post(f"{P}/celebrations/{cel.id}/gate/check-in", json={"code": code, "client_scan_id": "http-scan-1"})
    assert checkin.status_code == 200 and checkin.json()["data"]["recorded"] is True
    assert (await http.post(f"{P}/celebrations/{cel.id}/gate/check-in", json={})).status_code == 422
    shared = await http.post(f"{P}/celebrations/{cel.id}/invitations/{gid}/shared", json={"channel": "whatsapp"})
    assert shared.json()["data"]["last_shared_channel"] == "whatsapp"
    assert (await http.post(f"{P}/celebrations/{cel.id}/invitations/{gid}/shared", json={"channel": "sms"})).status_code == 422
    caps = (await http.get(f"{P}/invitations/capabilities")).json()["data"]
    assert caps["copy_link"] is True and caps["email"] is (bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD))
    if not caps["email"]:  # no fake success when email is not configured
        assert (await http.post(f"{P}/celebrations/{cel.id}/invitations/{gid}/email")).status_code == 422

    intruder = await _user_for_http(sf)
    http.login(intruder)
    assert (await http.get(f"{P}/celebrations/{cel.id}/invitations/{gid}")).status_code == 404
    assert (await http.post(f"{P}/celebrations/{cel.id}/gate/verify", json={"code": code})).status_code == 404


async def test_http_roles_on_admin_endpoints(sf, http):
    customer, support = await _user_for_http(sf), await _user_for_http(sf, UserRole.SUPPORT)
    admin, super_admin = await _user_for_http(sf, UserRole.ADMIN), await _user_for_http(sf, UserRole.SUPER_ADMIN)
    vendor = await _user_for_http(sf, UserRole.VENDOR)
    for user in (customer, vendor):
        http.login(user)
        assert (await http.get(f"{P}/admin/invitations")).status_code == 403
        assert (await http.get(f"{P}/admin/invitations/entry-logs")).status_code == 403
    http.login(support)
    assert (await http.get(f"{P}/admin/invitations")).status_code == 200
    assert (await http.get(f"{P}/admin/invitations/export.csv")).status_code == 403
    assert (await http.post(f"{P}/admin/invitations/{uuid.uuid4()}/revoke", json={})).status_code == 403
    http.login(admin)
    assert (await http.get(f"{P}/admin/invitations/policy")).status_code == 200
    assert (await http.put(f"{P}/admin/invitations/policy", json={"max_plus_ones": 2})).status_code == 403
    export = await http.get(f"{P}/admin/invitations/export.csv")
    assert export.status_code == 200 and export.headers["content-type"].startswith("text/csv")
    http.login(super_admin)
    put = await http.put(f"{P}/admin/invitations/policy", json={"max_plus_ones": 2})
    assert put.status_code == 200 and put.json()["data"]["max_plus_ones"] == 2
    assert (await http.put(f"{P}/admin/invitations/policy", json={"max_plus_ones": -3})).status_code == 422


async def test_http_public_pages_and_endpoints(sf, http):
    host = await _user_for_http(sf)
    cel = await make_celebration(sf, host, days_ahead=1)
    http.login(host)
    inv = (await http.post(f"{P}/celebrations/{cel.id}/invitations", json={"name": "Guest"})).json()["data"]
    token = inv["invite_url"].split("#", 1)[1]
    http.login(None)

    page = await http.get(f"{P}/public/invite/page")
    assert page.status_code == 200 and "script-src 'nonce-" in page.headers["content-security-policy"]
    assert "camera=()" in page.headers["permissions-policy"]
    gate_page = await http.get(f"{P}/public/gate/page")
    assert "camera=(self)" in gate_page.headers["permissions-policy"]

    view = await http.get(f"{P}/public/invite/view", headers={"X-Invite-Token": token})
    assert view.status_code == 200 and view.json()["data"]["guest_name"] == "Guest"
    assert (await http.get(f"{P}/public/invite/view")).status_code == 404
    rsvp = await http.post(f"{P}/public/invite/rsvp", headers={"X-Invite-Token": token}, json={"rsvp_status": "declined"})
    assert rsvp.status_code == 200 and rsvp.json()["data"]["rsvp_status"] == "declined"

    legacy = await http.get(f"{P}/public/rsvp/{token}/page", follow_redirects=False)
    assert legacy.status_code == 302 and legacy.headers["location"].endswith(f"/public/invite/page#{token}")
    legacy_json = await http.get(f"{P}/public/rsvp/{token}")
    assert legacy_json.status_code == 200 and legacy_json.json()["data"]["rsvp_status"] == "declined"

    assert (await http.get(f"{P}/public/gate/session")).status_code == 401
    assert (await http.get(f"{P}/public/gate/session", headers={"X-Gate-Token": "nope"})).status_code == 401


async def test_http_public_invite_is_rate_limited(sf, http):
    statuses = [
        (await http.get(f"{P}/public/invite/view", headers={"X-Invite-Token": f"guess-{i}"})).status_code
        for i in range(61)
    ]
    assert statuses[:60] == [404] * 60 and statuses[60] == 429
