"""
Invitation management end to end, against a real Postgres and the real HTTP app.

Skipped without TEST_DATABASE_URL (same convention and disposable-database guard
as test_invitations_integration). Each journey goes through the API the Flutter
app and the guest page use, so what passes here is what ships.
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.current_user import get_current_user
from app.core.dependencies import get_event_service, get_invitation_service, get_occasion_service
from app.core.rate_limit import limiter
from app.main import create_app
from app.models import *  # noqa: F401,F403 - registers every table on Base
from app.models.base import Base
from app.models.bookings.booking import Booking
from app.models.enums import (
    AccountStatus,
    BookingStatus,
    BookingType,
    CelebrationStatus,
    Currency,
    EventSource,
    GuestHistoryEventType,
    PaymentStatus,
    RSVPStatus,
    UserRole,
    UserType,
)
from app.models.occasions.celebration import Celebration
from app.models.occasions.celebration_guest import CelebrationGuest
from app.models.occasions.celebration_guest_history import CelebrationGuestHistory
from app.models.occasions.occasion import Occasion
from app.models.users.user import User
from app.schemas.users.response import UserResponse
from app.services.invitations.events import EventService
from app.services.invitations.service import InvitationService
from app.services.occasions.service import OccasionService

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
BROWSER = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/126 Mobile Safari/537.36"
WHATSAPP = "WhatsApp/2.24.1 A"
P = "/api/v1"

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set — needs Postgres"),
]


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def engine():
    from test_deletion_lifecycle_integration import _assert_disposable

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


@pytest_asyncio.fixture(loop_scope="module")
async def sessions(engine, monkeypatch):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, occasions, app_settings RESTART IDENTITY CASCADE"))
    limiter.reset()

    async def no_notification(*_args, **_kwargs):
        return None

    monkeypatch.setattr(InvitationService, "_notify", staticmethod(no_notification))
    return factory


async def _user(factory, name="Priya") -> User:
    async with factory() as s:
        user = User(
            id=uuid.uuid4(), phone=f"+9198{uuid.uuid4().int % 100000000:08d}", first_name=name,
            last_name="Host", role=UserRole.CUSTOMER, user_type=UserType.INDIVIDUAL,
            account_status=AccountStatus.ACTIVE,
        )
        s.add(user)
        await s.commit()
        return user


def _occasion(name="Wedding") -> Occasion:
    return Occasion(
        id=uuid.uuid4(), name=name, slug=f"{name.lower()}-{uuid.uuid4().hex[:6]}", display_order=0,
        popularity_score=0, is_active=True, is_featured=False, is_seasonal=False, allow_balloon_theme=False,
    )


def _celebration(user, occasion, title, **over) -> Celebration:
    return Celebration(
        id=uuid.uuid4(), customer_id=user.id, occasion_id=occasion.id, title=title,
        celebration_date=date.today() + timedelta(days=60), guest_count=0, completion_percentage=0,
        currency=Currency.INR, status=CelebrationStatus.CONFIRMED, event_source=EventSource.TYOHAAR_BOOKING,
        **over,
    )


class Host:
    """A signed-in organiser talking to the real app, on the scratch database."""

    def __init__(self, factory, user: User):
        self.user = user
        self.app = create_app()
        response = UserResponse.model_validate(user, from_attributes=True)

        async def current_user():
            return response

        self.app.dependency_overrides[get_current_user] = current_user
        self.app.dependency_overrides[get_invitation_service] = lambda: InvitationService(factory)
        self.app.dependency_overrides[get_event_service] = lambda: EventService(factory)
        self.app.dependency_overrides[get_occasion_service] = lambda: OccasionService(factory)
        self.http = AsyncClient(transport=ASGITransport(app=self.app), base_url="https://site.test")

    async def create_event(self, **over) -> dict:
        body = {
            "title": "Aarav's First Birthday", "event_type": "birthday", "host_name": "The Mehta Family",
            "celebration_date": str(date.today() + timedelta(days=30)), "venue_name": "Our Home",
            "venue_address": "12 MG Road, Indiranagar, Bengaluru", **over,
        }
        r = await self.http.post(f"{P}/events", json=body)
        assert r.status_code == 201, r.text
        return r.json()["data"]

    async def invite(self, event_id, name, phone=None, plus=0, **over) -> dict:
        r = await self.http.post(f"{P}/celebrations/{event_id}/invitations", json={
            "name": name, "phone": phone, "plus_ones_allowed": plus, **over,
        })
        assert r.status_code == 201, r.text
        return r.json()["data"]

    async def publish(self, event_id) -> dict:
        r = await self.http.post(f"{P}/events/{event_id}/invitation/publish")
        assert r.status_code == 200, r.text
        return r.json()["data"]


@pytest_asyncio.fixture(loop_scope="module")
async def host(sessions):
    return Host(sessions, await _user(sessions))


def guest_client(app, agent=BROWSER) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="https://site.test", headers={"user-agent": agent})


def token_of(invitation: dict) -> str:
    return invitation["invite_url"].rsplit("/i/", 1)[1]


async def view(app, token, agent=BROWSER):
    async with guest_client(app, agent) as c:
        return await c.get("/i/_api/view", headers={"X-Invite-Token": token})


async def rsvp(app, token, responses, note=None):
    async with guest_client(app) as c:
        return await c.post("/i/_api/rsvp", headers={"X-Invite-Token": token}, json={"responses": responses, "note": note})


async def guest_row(factory, guest_id) -> CelebrationGuest:
    async with factory() as s:
        return await s.get(CelebrationGuest, uuid.UUID(guest_id))


# ── Journey B: independent organiser ─────────────────────────────────────────

async def test_standalone_journey_needs_no_booking(host, sessions):
    event = await host.create_event()
    assert event["event_source"] == "standalone" and event["booking"] is None
    assert event["invitation_status"] == "draft"
    assert event["entitlements"]["vendor_reports"] is False
    assert event["functions"] == []  # functions are optional
    assert event["event_type_label"] == "Birthday"

    listed = (await host.http.get(f"{P}/events")).json()["data"]
    assert [e["id"] for e in listed["upcoming"]] == [event["id"]]
    assert listed["upcoming"][0]["days_remaining"] == 30

    invitation = await host.invite(event["id"], "Rohan", "+919812345678", plus=2)
    token = token_of(invitation)
    assert invitation["invite_url"].endswith(f"/i/{token}")

    # Draft: the link exists but shows nothing about the event.
    async with guest_client(host.app) as c:
        page = await c.get(f"/i/{token}")
    assert page.status_code == 200 and "Aarav" not in page.text and "Not published yet" in page.text

    await host.publish(event["id"])
    r = await rsvp(host.app, token, [{"status": "attending", "attendee_count": 3}], note="Coming early")
    assert r.status_code == 200, r.text
    row = await guest_row(sessions, invitation["id"])
    assert row.rsvp_status is RSVPStatus.ATTENDING and row.rsvp_party_size == 3 and row.guest_note == "Coming early"

    analytics = (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]
    assert analytics["confirmed"] == 1 and analytics["pending"] == 0 and analytics["response_rate"] == 1.0


async def test_create_event_is_idempotent_and_validates(host):
    first = await host.http.post(f"{P}/events", json={
        "title": "Griha Pravesh", "event_type": "custom", "custom_event_type": "Griha Pravesh",
        "celebration_date": str(date.today() + timedelta(days=9)), "client_request_id": "evt-abcdef12",
    })
    again = await host.http.post(f"{P}/events", json={
        "title": "Griha Pravesh", "event_type": "custom", "custom_event_type": "Griha Pravesh",
        "celebration_date": str(date.today() + timedelta(days=9)), "client_request_id": "evt-abcdef12",
    })
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["data"]["id"] == again.json()["data"]["id"]
    assert first.json()["data"]["event_type_label"] == "Griha Pravesh"

    past = await host.http.post(f"{P}/events", json={
        "title": "Old", "event_type": "birthday", "celebration_date": str(date.today() - timedelta(days=1)),
    })
    assert past.status_code in (400, 422)
    unnamed = await host.http.post(f"{P}/events", json={
        "title": "X", "event_type": "custom", "celebration_date": str(date.today() + timedelta(days=1)),
    })
    assert unnamed.status_code == 422


# ── Functions, per-function answers ──────────────────────────────────────────

async def _wedding(host: Host) -> tuple[dict, dict]:
    base = date.today() + timedelta(days=40)
    event = await host.create_event(
        title="Sharma Wedding", event_type="wedding", celebration_date=str(base),
        functions=[
            {"name": "Haldi", "function_date": str(base), "dress_code": "Yellow"},
            {"name": "Wedding", "function_date": str(base + timedelta(days=2)), "start_time": "19:00:00"},
            {"name": "Reception", "function_date": str(base + timedelta(days=3))},
        ],
    )
    await host.publish(event["id"])
    return event, {f["name"]: f["id"] for f in event["functions"]}


async def test_guest_answers_each_function_separately_and_sees_only_their_own(host, sessions):
    event, fns = await _wedding(host)
    assert event["end_date"] == str(date.today() + timedelta(days=43))  # span follows the functions

    close = await host.invite(event["id"], "Meera", "+919800000001", plus=1)
    colleague = await host.invite(
        event["id"], "Arjun", "+919800000002", function_ids=[fns["Reception"]],
    )
    # Only the Reception is visible to someone invited only to the Reception.
    page = (await view(host.app, token_of(colleague))).json()["data"]
    assert [f["name"] for f in page["functions"]] == ["Reception"]
    assert "Haldi" not in str(page) and "Meera" not in str(page) and "+91" not in str(page)

    # ...and they can't answer for the Wedding by naming it.
    denied = await rsvp(host.app, token_of(colleague), [{"function_id": fns["Wedding"], "status": "attending"}])
    assert denied.status_code == 422

    # Attending one, declining another: both stored, not one blended answer.
    token = token_of(close)
    r = await rsvp(host.app, token, [
        {"function_id": fns["Haldi"], "status": "declined"},
        {"function_id": fns["Wedding"], "status": "attending", "attendee_count": 2},
        {"function_id": fns["Reception"], "status": "maybe"},
    ])
    assert r.status_code == 200, r.text
    row = await guest_row(sessions, close["id"])
    assert row.rsvp_status is RSVPStatus.ATTENDING and row.rsvp_party_size == 2

    stats = {
        f["name"]: f
        for f in (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]["functions"]
    }
    assert (stats["Haldi"]["invited"], stats["Haldi"]["declined"]) == (1, 1)
    assert (stats["Wedding"]["confirmed"], stats["Wedding"]["confirmed_people"]) == (1, 2)
    assert (stats["Reception"]["invited"], stats["Reception"]["maybe"], stats["Reception"]["pending"]) == (2, 1, 1)

    # Over the allowance is refused, by the server.
    over = await rsvp(host.app, token, [{"function_id": fns["Wedding"], "status": "attending", "attendee_count": 3}])
    assert over.status_code == 422

    # A resubmit changes nothing and logs nothing; a real change is an update.
    async def history_count():
        async with sessions() as s:
            return len((await s.execute(select(CelebrationGuestHistory).where(
                CelebrationGuestHistory.celebration_guest_id == uuid.UUID(close["id"]),
                CelebrationGuestHistory.event_type == GuestHistoryEventType.RSVP_CHANGED,
            ))).scalars().all())

    before = await history_count()
    assert before == 3
    same = await rsvp(host.app, token, [{"function_id": fns["Haldi"], "status": "declined"}])
    assert same.status_code == 200 and await history_count() == before
    changed = await rsvp(host.app, token, [{"function_id": fns["Haldi"], "status": "attending"}])
    assert changed.status_code == 200 and await history_count() == before + 1
    activity = (await host.http.get(f"{P}/events/{event['id']}/activity")).json()["data"]
    assert any(a["is_update"] and a["function_name"] == "Haldi" for a in activity)


async def test_pass_works_across_the_whole_span_of_a_multi_day_event(host, sessions):
    from app.services.invitations import rules
    from app.services.invitations.rules import InvitationPolicy

    start, end = rules.entry_window(
        date(2027, 1, 10), None, None, tz_name="Asia/Kolkata", policy=InvitationPolicy(),
        start_date=date(2027, 1, 10), end_date=date(2027, 1, 13),
    )
    assert (end - start).days >= 3


async def test_removing_a_function_with_answers_is_refused(host):
    event, fns = await _wedding(host)
    invitation = await host.invite(event["id"], "Kabir", "+919800000003")
    assert (await rsvp(host.app, token_of(invitation), [{"function_id": fns["Haldi"], "status": "attending"}])).status_code == 200
    refused = await host.http.delete(f"{P}/events/{event['id']}/functions/{fns['Haldi']}")
    assert refused.status_code == 409
    fine = await host.http.delete(f"{P}/events/{event['id']}/functions/{fns['Reception']}")
    assert fine.status_code == 204


async def test_first_function_keeps_answers_already_given(host, sessions):
    event = await host.create_event()
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Tara", "+919800000004")
    assert (await rsvp(host.app, token_of(invitation), [{"status": "attending"}])).status_code == 200
    r = await host.http.post(f"{P}/events/{event['id']}/functions", json={
        "name": "Lunch", "function_date": str(date.today() + timedelta(days=30)),
    })
    assert r.status_code == 201, r.text
    page = (await view(host.app, token_of(invitation))).json()["data"]
    assert page["members"][0]["responses"][0]["status"] == "attending"
    assert page["members"][0]["responses"][0]["function_id"] == r.json()["data"]["id"]


# ── Households ───────────────────────────────────────────────────────────────

async def test_household_group_answer_counts_people_once(host, sessions):
    event, fns = await _wedding(host)
    mother = await host.invite(event["id"], "Mother", "+919800000005", plus=1)
    father = await host.invite(event["id"], "Father", "+919800000006")
    outsider = await host.invite(event["id"], "Outsider", "+919800000007")
    r = await host.http.post(f"{P}/events/{event['id']}/groups", json={
        "name": "Verma Family", "invitation_capacity": 3, "response_mode": "group",
        "guest_ids": [mother["id"], father["id"]], "primary_guest_id": mother["id"],
    })
    assert r.status_code == 201, r.text
    assert r.json()["data"][0]["invite_url"].endswith(token_of(mother))

    token = token_of(mother)
    page = (await view(host.app, token)).json()["data"]
    assert page["response_mode"] == "group" and page["capacity"] == 3
    assert {m["name"] for m in page["members"]} == {"Mother", "Father"}

    # A member's own link opens only themselves, not the household.
    solo = (await view(host.app, token_of(father))).json()["data"]
    assert [m["name"] for m in solo["members"]] == ["Father"]

    too_many = await rsvp(host.app, token, [{"function_id": fns["Wedding"], "status": "attending", "attendee_count": 4}])
    assert too_many.status_code == 422
    ok = await rsvp(host.app, token, [{"function_id": fns["Wedding"], "status": "attending", "attendee_count": 3}])
    assert ok.status_code == 200, ok.text

    wedding = next(
        f for f in (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]["functions"]
        if f["name"] == "Wedding"
    )
    assert wedding["confirmed"] == 2 and wedding["confirmed_people"] == 3  # not 3 + 3

    # The household link can't reach a guest outside the household.
    probe = await rsvp(host.app, token, [{"guest_id": outsider["id"], "function_id": fns["Wedding"], "status": "declined"}])
    assert probe.status_code in (200, 404)  # group mode answers for the household only...
    assert (await guest_row(sessions, outsider["id"])).rsvp_status is RSVPStatus.PENDING  # ...and never touches them


async def test_individual_household_cannot_answer_for_a_stranger(host, sessions):
    event, fns = await _wedding(host)
    a = await host.invite(event["id"], "Asha", "+919800000008")
    b = await host.invite(event["id"], "Bela", "+919800000009")
    stranger = await host.invite(event["id"], "Stranger", "+919800000010")
    await host.http.post(f"{P}/events/{event['id']}/groups", json={
        "name": "Sisters", "response_mode": "individual", "guest_ids": [a["id"], b["id"]], "primary_guest_id": a["id"],
    })
    token = token_of(a)
    ok = await rsvp(host.app, token, [
        {"guest_id": a["id"], "function_id": fns["Wedding"], "status": "attending"},
        {"guest_id": b["id"], "function_id": fns["Wedding"], "status": "declined"},
    ])
    assert ok.status_code == 200, ok.text
    # Bela declined one function and hasn't answered the others: still pending overall.
    assert (await guest_row(sessions, b["id"])).rsvp_status is RSVPStatus.PENDING
    bela = (await view(host.app, token_of(b))).json()["data"]["members"][0]
    answered = {r["function_id"]: r["status"] for r in bela["responses"]}
    assert answered[fns["Wedding"]] == "declined" and answered[fns["Haldi"]] == "pending"
    denied = await rsvp(host.app, token, [{"guest_id": stranger["id"], "function_id": fns["Wedding"], "status": "declined"}])
    assert denied.status_code == 404
    assert (await guest_row(sessions, stranger["id"])).rsvp_status is RSVPStatus.PENDING


# ── Food ─────────────────────────────────────────────────────────────────────

async def test_food_only_when_asked_and_aggregates_real_answers(host):
    event, fns = await _wedding(host)
    a = await host.invite(event["id"], "Veg Guest", "+919800000011", plus=1)
    b = await host.invite(event["id"], "Jain Guest", "+919800000012")
    answer = {"function_id": fns["Wedding"], "status": "attending", "attendee_count": 2, "dietary_type": "vegetarian"}

    # Not asked for yet: the answer is accepted but the food isn't stored.
    assert (await rsvp(host.app, token_of(a), [answer])).status_code == 200
    summary = (await host.http.get(f"{P}/events/{event['id']}/food")).json()["data"]
    assert summary["enabled"] is False
    wedding = next(f for f in summary["functions"] if f["name"] == "Wedding")
    assert wedding["dietary"] == {} and wedding["not_specified"] == 2

    r = await host.http.put(f"{P}/events/{event['id']}/invitation", json={
        "rsvp": {"ask_food": True, "ask_allergies": True, "meal_options": ["Thali", "Buffet"]},
    })
    assert r.status_code == 200, r.text
    assert (await rsvp(host.app, token_of(a), [{**answer, "meal_selection": "Thali"}])).status_code == 200
    assert (await rsvp(host.app, token_of(b), [{
        "function_id": fns["Wedding"], "status": "attending", "dietary_type": "jain",
        "allergies": "Peanuts", "meal_selection": "Buffet",
    }])).status_code == 200
    # Something the host didn't offer is refused.
    bad = await rsvp(host.app, token_of(b), [{"function_id": fns["Wedding"], "status": "attending", "meal_selection": "Steak"}])
    assert bad.status_code == 422

    wedding = next(
        f for f in (await host.http.get(f"{P}/events/{event['id']}/food")).json()["data"]["functions"]
        if f["name"] == "Wedding"
    )
    assert wedding["people"] == 3
    assert wedding["dietary"] == {"vegetarian": 2, "jain": 1}
    assert wedding["meals"] == {"Thali": 2, "Buffet": 1} and wedding["with_allergies"] == 1

    report = await host.http.get(f"{P}/events/{event['id']}/food/report.csv")
    assert report.status_code == 200 and "text/csv" in report.headers["content-type"]
    assert "Jain Guest" in report.text and "Peanuts" in report.text


# ── Tracking honesty ─────────────────────────────────────────────────────────

async def test_crawlers_never_look_like_guests(host, sessions):
    event = await host.create_event(cover_image_url="https://cdn.example.com/cover.jpg")
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Ira", "+919800000013")
    token = token_of(invitation)

    async with guest_client(host.app, WHATSAPP) as c:
        preview = await c.get(f"/i/{token}")
    assert preview.status_code == 200
    # WhatsApp gets a real preview in the HTML itself, without running script.
    assert 'property="og:title" content="You&#x27;re invited: Aarav&#x27;s First Birthday"' in preview.text
    assert 'property="og:image" content="https://cdn.example.com/cover.jpg"' in preview.text
    assert 'property="og:url"' in preview.text
    # This link may be forwarded: the guest's name isn't in it.
    assert "Ira" not in preview.text.split("<script")[0]

    row = await guest_row(sessions, invitation["id"])
    assert row.link_accessed_at is None and row.invitation_opened_at is None and row.visit_count == 0

    # A browser fetching the page is "accessed", still not a visit.
    async with guest_client(host.app) as c:
        await c.get(f"/i/{token}")
    row = await guest_row(sessions, invitation["id"])
    assert row.link_accessed_at is not None and row.invitation_opened_at is None

    # The page's script running is the visit.
    assert (await view(host.app, token)).status_code == 200
    assert (await view(host.app, token)).status_code == 200
    row = await guest_row(sessions, invitation["id"])
    assert row.invitation_opened_at is not None and row.visit_count == 2

    async with guest_client(host.app) as c:
        started = await c.post("/i/_api/activity", headers={"X-Invite-Token": token}, json={"type": "rsvp_started"})
    assert started.status_code == 204
    assert (await guest_row(sessions, invitation["id"])).rsvp_started_at is not None

    funnel = (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]
    assert (funnel["link_accessed"], funnel["qualified_visits"], funnel["rsvp_started"], funnel["responded"]) == (1, 1, 1, 0)


async def test_bad_revoked_and_rotated_links(host):
    event = await host.create_event()
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Nikhil", "+919800000014")
    token = token_of(invitation)
    async with guest_client(host.app) as c:
        assert (await c.get("/i/not-a-real-token")).status_code == 404
        assert (await c.get("/i/_api/view", headers={"X-Invite-Token": "nope"})).status_code == 404
        assert (await c.get("/i/_api/view")).status_code == 404

    rotated = (await host.http.post(f"{P}/celebrations/{event['id']}/invitations/{invitation['id']}/rotate")).json()["data"]
    async with guest_client(host.app) as c:
        assert (await c.get(f"/i/{token}")).status_code == 404
        assert (await c.get(f"/i/{token_of(rotated)}")).status_code == 200

    await host.http.post(f"{P}/celebrations/{event['id']}/invitations/{invitation['id']}/revoke", json={})
    async with guest_client(host.app) as c:
        gone = await c.get(f"/i/{token_of(rotated)}")
    assert gone.status_code == 410 and "Aarav" not in gone.text
    refused = await rsvp(host.app, token_of(rotated), [{"status": "attending"}])
    assert refused.status_code in (400, 409, 422)


async def test_responses_close_and_can_be_locked(host):
    event = await host.create_event()
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Zoya", "+919800000015")
    token = token_of(invitation)
    await host.http.put(f"{P}/events/{event['id']}/invitation", json={"rsvp": {"allow_edit": False}})
    assert (await rsvp(host.app, token, [{"status": "attending"}])).status_code == 200
    assert (await rsvp(host.app, token, [{"status": "attending"}])).status_code == 200  # same answer: harmless
    changed = await rsvp(host.app, token, [{"status": "declined"}])
    assert changed.status_code == 409

    past = str(date.today() - timedelta(days=1))
    await host.http.put(f"{P}/events/{event['id']}/invitation", json={"rsvp": {"deadline": past}})
    closed = await rsvp(host.app, token, [{"status": "maybe"}])
    assert closed.status_code in (400, 409, 422)
    assert "closed" in closed.text


# ── General link ─────────────────────────────────────────────────────────────

async def test_general_link_identifies_nobody_until_they_say_who_they_are(host, sessions):
    event = await host.create_event()
    await host.publish(event["id"])
    on = await host.http.put(f"{P}/events/{event['id']}/invitation/general-link", json={"enabled": True, "plus_ones_allowed": 1})
    url = on.json()["data"]["general_link_url"]
    token = url.rsplit("/i/", 1)[1]

    known = await host.invite(event["id"], "Already Invited", "+919800000016")

    async with guest_client(host.app) as c:
        assert (await c.get(f"/i/{token}")).status_code == 200
    page = (await view(host.app, token)).json()["data"]
    assert page["kind"] == "general" and page["members"] == []
    assert "Already Invited" not in str(page)
    assert (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]["general_link_visits"] == 1

    # Knowing someone's number doesn't get you their invitation.
    async with guest_client(host.app) as c:
        stolen = await c.post("/i/_api/claim", headers={"X-Invite-Token": token}, json={
            "name": "Impostor", "phone": "+919800000016",
        })
    assert stolen.status_code == 409 and token_of(known) not in stolen.text

    async with guest_client(host.app) as c:
        claimed = await c.post("/i/_api/claim", headers={"X-Invite-Token": token}, json={
            "name": "New Friend", "phone": "+919800000017",
        })
    assert claimed.status_code == 200, claimed.text
    personal = claimed.json()["data"]["token"]
    assert personal != token
    mine = (await view(host.app, personal)).json()["data"]
    assert mine["kind"] == "personal" and mine["members"][0]["name"] == "New Friend"
    assert mine["members"][0]["plus_ones_allowed"] == 1
    assert (await rsvp(host.app, personal, [{"status": "attending", "attendee_count": 2}])).status_code == 200

    off = await host.http.put(f"{P}/events/{event['id']}/invitation/general-link", json={"enabled": False})
    assert off.json()["data"]["general_link_url"] is None
    async with guest_client(host.app) as c:
        assert (await c.get(f"/i/{token}")).status_code == 404
    # Someone already admitted keeps their own invitation.
    assert (await view(host.app, personal)).status_code == 200


# ── Isolation ────────────────────────────────────────────────────────────────

async def test_other_customers_get_nothing(host, sessions):
    event, fns = await _wedding(host)
    guest = await host.invite(event["id"], "Private Guest", "+919800000018")
    other = Host(sessions, await _user(sessions, "Mallory"))
    E = f"{P}/events/{event['id']}"
    calls = [
        ("GET", E, None), ("PATCH", E, {"title": "Hacked"}),
        ("PUT", f"{E}/invitation", {"rsvp": {"ask_food": True}}), ("POST", f"{E}/invitation/publish", None),
        ("POST", f"{E}/invitation/preview-link", None),
        ("PUT", f"{E}/invitation/general-link", {"enabled": True}),
        ("POST", f"{E}/functions", {"name": "X", "function_date": str(date.today() + timedelta(days=5))}),
        ("DELETE", f"{E}/functions/{fns['Haldi']}", None),
        ("PUT", f"{E}/functions/guests", {"guest_ids": [guest["id"]], "function_ids": [fns["Haldi"]]}),
        ("POST", f"{E}/groups", {"name": "X"}),
        ("GET", f"{E}/analytics", None), ("GET", f"{E}/rsvps", None), ("GET", f"{E}/food", None),
        ("GET", f"{E}/food/report.csv", None), ("GET", f"{E}/activity", None), ("GET", f"{E}/reminders", None),
        ("POST", f"{E}/reminders/record", {"guest_ids": [guest["id"]], "channel": "whatsapp"}),
        ("POST", f"{E}/operations-summary", {}),
    ]
    for method, path, body in calls:
        r = await other.http.request(method, path, json=body)
        assert r.status_code == 404, (method, path, r.status_code, r.text)
        assert "Private Guest" not in r.text

    # A function from another event is rejected even for one's own guest.
    own = await other.create_event()
    mine = await other.invite(own["id"], "Own Guest", "+919800000019")
    cross = await other.http.put(f"{P}/events/{own['id']}/functions/guests", json={
        "guest_ids": [mine["id"]], "function_ids": [fns["Haldi"]],
    })
    assert cross.status_code == 422


async def test_endpoints_require_sign_in(sessions):
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://site.test") as anon:
        assert (await anon.get(f"{P}/events")).status_code == 401
        assert (await anon.post(f"{P}/events", json={})).status_code in (401, 422)


# ── Journey A and conversion ─────────────────────────────────────────────────

async def _booking(sessions, user: User, celebration_id, status=BookingStatus.CONFIRMED) -> Booking:
    from decimal import Decimal

    from app.models.enums import PackageStatus
    from app.models.packages.package import Package

    async with sessions() as s:
        package = Package(
            id=uuid.uuid4(), name="Grand Wedding", slug=f"p-{uuid.uuid4().hex[:6]}",
            status=PackageStatus.ACTIVE, base_price=Decimal("1000"),
        )
        s.add(package)
        await s.flush()
        booking = Booking(
            id=uuid.uuid4(), booking_number=f"BK-{uuid.uuid4().hex[:10]}", customer_id=user.id,
            celebration_id=uuid.UUID(str(celebration_id)), package_id=package.id,
            scheduled_date=date.today() + timedelta(days=60), booking_status=status,
            booking_type=BookingType.PACKAGE,
            payment_status=PaymentStatus.COMPLETED, currency=Currency.INR, subtotal=Decimal("1000"),
            discount_amount=Decimal("0"), tax_amount=Decimal("0"), platform_fee=Decimal("0"),
            total_amount=Decimal("1000"), amount_paid=Decimal("1000"), amount_due=Decimal("0"),
        )
        s.add(booking)
        await s.commit()
        return booking


async def test_booked_event_is_prefilled_and_booking_details_are_protected(host, sessions):
    async with sessions() as s:
        occasion = _occasion()
        s.add(occasion)
        await s.flush()
        celebration = _celebration(host.user, occasion, "Grand Wedding booking", venue_address="Taj, Lucknow")
        s.add(celebration)
        await s.commit()
    booking = await _booking(sessions, host.user, celebration.id)
    E = f"{P}/events/{celebration.id}"

    event = (await host.http.get(E)).json()["data"]
    assert event["event_source"] == "tyohaar_booking"
    assert event["venue_address"] == "Taj, Lucknow"  # nothing to re-enter
    assert event["booking"]["status"] == "confirmed" and event["booking"]["package_name"]
    assert event["entitlements"]["vendor_reports"] is True
    assert event["invitations_configured"] is False  # drives "Set up invitations"
    assert set(event["locked_fields"]) == {"celebration_date", "venue_name", "venue_address"}

    moved = await host.http.patch(E, json={"celebration_date": str(date.today() + timedelta(days=61))})
    assert moved.status_code == 409
    # The invitation can say something different without touching the booking.
    r = await host.http.put(f"{E}/invitation", json={"display": {"title": "Ananya weds Rohan", "venue_name": "Taj Mahal Hotel"}})
    assert r.status_code == 200
    async with sessions() as s:
        fresh = await s.get(Celebration, celebration.id)
        same_booking = await s.get(Booking, booking.id)
    assert fresh.title == "Grand Wedding booking" and same_booking.scheduled_date == booking.scheduled_date

    guest = await host.invite(celebration.id, "Booked Guest", "+919800000020")
    page = (await view(host.app, token_of(guest))).json()["data"]
    assert page["event"]["title"] == "Ananya weds Rohan" and page["event"]["venue_name"] == "Taj Mahal Hotel"


async def test_standalone_event_converts_to_booked_keeping_everything(host, sessions):
    event, fns = await _wedding(host)
    guest = await host.invite(event["id"], "Early Guest", "+919800000021", plus=1)
    token = token_of(guest)
    assert (await rsvp(host.app, token, [{"function_id": fns["Wedding"], "status": "attending", "attendee_count": 2}])).status_code == 200

    # A pending booking grants nothing yet.
    pending = await _booking(sessions, host.user, event["id"], status=BookingStatus.PENDING)
    still = (await host.http.get(f"{P}/events/{event['id']}")).json()["data"]
    assert still["event_source"] == "standalone" and still["entitlements"]["vendor_reports"] is False

    service = EventService(sessions)
    async with service._uow() as uow:
        loaded = await uow.bookings.bookings.get_by_id(pending.id)
        await uow.bookings.bookings.update(loaded, {"booking_status": BookingStatus.CONFIRMED})
        await EventService.associate_confirmed_booking(uow, loaded)
    # Running it again is harmless.
    async with service._uow() as uow:
        loaded = await uow.bookings.bookings.get_by_id(pending.id)
        await EventService.associate_confirmed_booking(uow, loaded)

    after = (await host.http.get(f"{P}/events/{event['id']}")).json()["data"]
    assert after["id"] == event["id"] and after["event_source"] == "tyohaar_booking"
    assert after["entitlements"]["vendor_reports"] is True
    assert [f["id"] for f in after["functions"]] == [f["id"] for f in event["functions"]]
    # The same link still works, with the same answer on it.
    page = (await view(host.app, token)).json()["data"]
    assert any(r["status"] == "attending" for r in page["members"][0]["responses"])
    listed = (await host.http.get(f"{P}/celebrations/{event['id']}/invitations")).json()["data"]
    assert [g["id"] for g in listed] == [guest["id"]]

    # A second confirmed booking on the event doesn't take over the first link.
    second = await _booking(sessions, host.user, event["id"])
    async with service._uow() as uow:
        await EventService.associate_confirmed_booking(uow, await uow.bookings.bookings.get_by_id(second.id))
    async with sessions() as s:
        assert (await s.get(Celebration, uuid.UUID(event["id"]))).linked_booking_id == pending.id


async def test_vendor_sees_only_approved_aggregates(host, sessions, monkeypatch):
    async with sessions() as s:
        occasion = _occasion("Reception")
        s.add(occasion)
        await s.flush()
        celebration = _celebration(host.user, occasion, "Booked Do")
        s.add(celebration)
        await s.commit()
    booking = await _booking(sessions, host.user, celebration.id)
    guest = await host.invite(celebration.id, "Secret Name", "+919800000022")
    await host.http.put(f"{P}/events/{celebration.id}/invitation", json={"rsvp": {"ask_food": True, "ask_allergies": True}})
    assert (await rsvp(host.app, token_of(guest), [{"status": "attending", "dietary_type": "jain", "allergies": "Nuts"}])).status_code == 200

    from app.services.bookings.service import BookingService

    vendor_id = uuid.uuid4()

    async def owns(_uow, _booking, candidate):
        return candidate == vendor_id

    monkeypatch.setattr(BookingService, "vendor_owns_booking", staticmethod(owns))

    service = EventService(sessions)
    assert await service.vendor_guest_summary(booking.id, vendor_id) is None  # nothing until approved
    r = await host.http.post(f"{P}/events/{celebration.id}/operations-summary", json={"final_guest_count": 120})
    assert r.status_code == 200, r.text
    summary = await service.vendor_guest_summary(booking.id, vendor_id)
    assert summary.final_guest_count == 120 and summary.functions[0].dietary == {"jain": 1}
    dumped = summary.model_dump_json()
    assert "Secret Name" not in dumped and "Nuts" not in dumped and "+91" not in dumped

    from app.services.bookings.exceptions import BookingNotFoundError

    with pytest.raises(BookingNotFoundError):
        await service.vendor_guest_summary(booking.id, uuid.uuid4())


async def test_standalone_cannot_share_with_vendors(host):
    event = await host.create_event()
    r = await host.http.post(f"{P}/events/{event['id']}/operations-summary", json={})
    assert r.status_code in (400, 403, 409, 422)


# ── Import, reminders, preview, calendar ─────────────────────────────────────

async def test_import_csv_and_excel_with_per_row_results(host, sessions):
    event, fns = await _wedding(host)
    csv_body = (
        "Name,Mobile,Household,Side,Plus Ones,Functions\n"
        "Anu,+919811111111,Kapoor Family,Bride,2,\"Wedding, Reception\"\n"
        "Bina,+919811111112,Kapoor Family,Bride,0,Wedding\n"
        ",+919811111113,,,0,\n"
        "Chetan,+919811111111,,,0,\n"
        "Dev,,,,x,\n"
        "Esha,,,,0,Sangeet\n"
    )
    r = await host.http.post(
        f"{P}/events/{event['id']}/guests/import",
        files={"file": ("guests.csv", csv_body.encode(), "text/csv")},
    )
    assert r.status_code == 200, r.text
    result = r.json()["data"]
    assert result["created"] == 2 and result["groups_created"] == 1
    by_row = {row["row"]: row for row in result["rows"]}
    assert by_row[2]["status"] == "created" and by_row[4]["status"] == "error"
    assert by_row[5]["status"] == "duplicate" and by_row[6]["status"] == "error" and by_row[7]["status"] == "error"

    # Uploading the same file again adds nobody.
    again = await host.http.post(
        f"{P}/events/{event['id']}/guests/import",
        files={"file": ("guests.csv", csv_body.encode(), "text/csv")},
    )
    assert again.json()["data"]["created"] == 0

    stats = {f["name"]: f["invited"] for f in (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]["functions"]}
    assert stats["Wedding"] == 2 and stats["Reception"] == 1 and stats["Haldi"] == 0

    book = Workbook()
    book.active.append(["Guest Name", "Phone"])
    book.active.append(["Farah", "+919822222222"])
    buffer = io.BytesIO()
    book.save(buffer)
    xlsx = await host.http.post(
        f"{P}/events/{event['id']}/guests/import",
        files={"file": ("guests.xlsx", buffer.getvalue(), "application/octet-stream")},
    )
    assert xlsx.status_code == 200 and xlsx.json()["data"]["created"] == 1

    for name, content in (("guests.pdf", b"%PDF"), ("empty.csv", b""), ("no-name.csv", b"Phone\n123\n")):
        bad = await host.http.post(f"{P}/events/{event['id']}/guests/import", files={"file": (name, content, "text/csv")})
        assert bad.status_code in (400, 422), name


async def test_reminders_list_only_people_who_have_not_answered(host, sessions):
    event = await host.create_event()
    await host.publish(event["id"])
    waiting = await host.invite(event["id"], "Waiting", "+919800000023")
    answered = await host.invite(event["id"], "Answered", "+919800000024")
    declined = await host.invite(event["id"], "Declined", "+919800000025")
    await rsvp(host.app, token_of(answered), [{"status": "attending"}])
    await rsvp(host.app, token_of(declined), [{"status": "declined"}])

    data = (await host.http.get(f"{P}/events/{event['id']}/reminders")).json()["data"]
    assert data["automated_available"] is False  # no WhatsApp Business Platform configured
    assert [c["guest_name"] for c in data["candidates"]] == ["Waiting"]
    assert data["candidates"][0]["invite_url"].endswith(token_of(waiting))

    r = await host.http.post(f"{P}/events/{event['id']}/reminders/record", json={"guest_ids": [waiting["id"]], "channel": "whatsapp"})
    assert r.status_code == 200 and r.json()["data"] == 1
    assert (await guest_row(sessions, waiting["id"])).reminder_count == 1
    activity = (await host.http.get(f"{P}/events/{event['id']}/activity")).json()["data"]
    assert activity[0]["event_type"] == "reminder_sent" and activity[0]["channel"] == "whatsapp"


async def test_preview_works_before_publishing_and_takes_no_responses(host):
    event = await host.create_event()
    link = (await host.http.post(f"{P}/events/{event['id']}/invitation/preview-link")).json()["data"]
    path = link["url"].split("site.test", 1)[1]
    token = path.rsplit("/", 1)[1]
    assert event["id"] not in path  # the id stays out of the URL
    async with guest_client(host.app) as c:
        page = await c.get(path)
        assert page.status_code == 200 and "Aarav" in page.text and "Preview" in page.text
        data = await c.get("/i/_api/preview", headers={"X-Invite-Token": token})
        assert data.status_code == 200 and data.json()["data"]["kind"] == "preview"
        assert data.json()["data"]["can_respond"] is False
        assert (await c.get("/i/preview/garbage")).status_code == 404


async def test_calendar_and_page_security(host):
    event, fns = await _wedding(host)
    invitation = await host.invite(event["id"], "Gita", "+919800000026", function_ids=[fns["Wedding"]])
    token = token_of(invitation)
    async with guest_client(host.app) as c:
        cal = await c.get(f"/i/{token}/calendar.ics")
        page = await c.get(f"/i/{token}")
    assert cal.status_code == 200 and "text/calendar" in cal.headers["content-type"]
    assert cal.text.count("BEGIN:VEVENT") == 1 and "Wedding" in cal.text and "Haldi" not in cal.text
    assert "T190000" in cal.text

    csp = page.headers["content-security-policy"]
    assert "default-src 'none'" in csp and "'unsafe-inline'" not in csp.split("style-src")[0]
    assert page.headers["referrer-policy"] == "no-referrer"
    assert "noindex" in page.headers["x-robots-tag"]
    # The promotion comes after everything, and asks for nothing.
    assert page.text.index('id="root"') < page.text.index("Planning your own celebration?")
    assert "Explore Tyohaar" in page.text


async def test_hostile_text_stays_text(host):
    event = await host.create_event(title='<img src=x onerror=alert(1)>"', host_name="</title><script>alert(2)</script>")
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Hari", "+919800000027")
    async with guest_client(host.app) as c:
        page = await c.get(f"/i/{token_of(invitation)}")
    head, _, _ = page.text.partition('<script nonce')
    assert "<img src=x" not in head and "<script>alert" not in head and "</title><script" not in head

    bad_colour = await host.http.put(f"{P}/events/{event['id']}/invitation", json={
        "design": {"primary_color": "red;}</style><script>alert(3)</script>"},
    })
    assert bad_colour.status_code == 422
    bad_map = await host.http.post(f"{P}/events/{event['id']}/functions", json={
        "name": "X", "function_date": str(date.today() + timedelta(days=30)), "map_url": "javascript:alert(1)",
    })
    assert bad_map.status_code == 422


# ── Existing behaviour must not have moved ───────────────────────────────────

async def test_legacy_guest_page_and_rsvp_still_work_alongside(host, sessions):
    event, fns = await _wedding(host)
    invitation = await host.invite(event["id"], "Old Link", "+919800000028", plus=1)
    token = token_of(invitation)
    async with guest_client(host.app) as c:
        assert (await c.get(f"{P}/public/invite/page")).status_code == 200
        legacy_view = await c.get(f"{P}/public/invite/view", headers={"X-Invite-Token": token})
        assert legacy_view.status_code == 200 and legacy_view.json()["data"]["entry_code"]
        legacy = await c.post(f"{P}/public/invite/rsvp", headers={"X-Invite-Token": token}, json={
            "rsvp_status": "attending", "party_size": 2,
        })
    assert legacy.status_code == 200, legacy.text
    # One old-style answer applies to every function, so the numbers stay true.
    page = (await view(host.app, token)).json()["data"]
    assert {r["status"] for r in page["members"][0]["responses"]} == {"attending"}
    assert len(page["members"][0]["responses"]) == 3


async def test_guest_added_through_the_old_guest_screen_gets_invited_to_functions(host, sessions):
    event, _ = await _wedding(host)
    r = await host.http.post(f"{P}/celebrations/{event['id']}/guests", json={
        "celebration_id": event["id"], "name": "Older Screen", "phone": "+919800000029",
    })
    assert r.status_code == 201, r.text
    stats = (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]["functions"]
    assert all(f["invited"] == 1 for f in stats)


async def test_booking_only_celebrations_without_new_fields_still_serialize(host, sessions):
    async with sessions() as s:
        occasion = _occasion("Old")
        s.add(occasion)
        await s.flush()
        s.add(_celebration(
            host.user, occasion, "Pre-existing", event_type=None,
        ))
        await s.commit()
    r = await host.http.get(f"{P}/celebrations")
    assert r.status_code == 200 and any(c["title"] == "Pre-existing" for c in r.json()["data"])
    listed = (await host.http.get(f"{P}/events")).json()["data"]
    assert any(e["title"] == "Pre-existing" and e["event_type_label"] == "Old" for e in listed["upcoming"])


async def test_multi_day_pass_can_come_back_on_a_later_function(host, sessions):
    from app.schemas.invitations import GateCheckIn, GateRequest
    from app.models.enums import GuestEntryAction
    from app.models.enums import GuestVerificationResult as R

    today = date.today()
    event = await host.create_event(functions=[
        {"name": "Haldi", "function_date": str(today)},
        {"name": "Wedding", "function_date": str(today + timedelta(days=2))},
    ])
    await host.publish(event["id"])
    guest = await host.invite(event["id"], "Returning", "+919800000030")
    invites = InvitationService(sessions)

    class U:
        id = host.user.id
        first_name = "Priya"
        last_name = "Host"

    scope = await invites.host_scope(uuid.UUID(event["id"]), U())
    code = guest["entry_code"]
    first = await invites.gate_action(scope, GateCheckIn(code=code, party_size=1), GuestEntryAction.CHECK_IN)
    assert first.result is R.CHECKED_IN and first.recorded
    out = await invites.gate_action(scope, GateRequest(code=code), GuestEntryAction.CHECK_OUT)
    assert out.result is R.CHECKED_OUT
    again = await invites.gate_action(scope, GateCheckIn(code=code, party_size=1), GuestEntryAction.CHECK_IN)
    assert again.result is R.CHECKED_IN and again.recorded  # not "already used"

    funnel = (await host.http.get(f"{P}/events/{event['id']}/analytics")).json()["data"]
    assert funnel["summary"]["arrived_guests"] == 1
    activity = (await host.http.get(f"{P}/events/{event['id']}/activity")).json()["data"]
    assert any(a["event_type"] == "checked_in" for a in activity)


async def test_entitlements_are_data_not_assumptions():
    from app.services.invitations import entitlements as ent

    assert ent.resolve(booked=False, platform=None).vendor_reports is False
    assert ent.resolve(booked=True, platform=None).vendor_reports is True
    off = {"standalone": {"food_preferences": False}, "packages": {"p1": {"qr_check_in": False}}}
    assert ent.resolve(booked=False, platform=off).food_preferences is False
    assert ent.resolve(booked=True, platform=off, package_id="p1").qr_check_in is False
    assert ent.resolve(booked=True, platform=off, package_id="p2").qr_check_in is True
    # Nothing can deliver it, so nobody gets it, whatever the setting says.
    assert ent.resolve(booked=True, platform={"booked": {"automated_reminders": True}}).automated_reminders is False


@pytest.mark.parametrize("event_type,custom,marker", [
    ("wedding", None, "e-wedding"), ("birthday", None, "e-birthday"), ("anniversary", None, "e-anniversary"),
    ("engagement", None, "e-engagement"), ("baby_shower", None, "e-baby_shower"), ("housewarming", None, "e-housewarming"),
    ("religious", None, "e-religious"), ("corporate", None, "e-corporate"), ("custom", "Retirement Party", "e-custom"),
])
async def test_each_kind_of_event_gets_its_own_look(host, event_type, custom, marker):
    event = await host.create_event(event_type=event_type, custom_event_type=custom)
    await host.publish(event["id"])
    invitation = await host.invite(event["id"], "Themed", "+919800000031")
    async with guest_client(host.app) as c:
        page = await c.get(f"/i/{token_of(invitation)}")
    assert page.status_code == 200 and marker in page.text
    assert 'class="scene-art"' in page.text  # drawn scene, because there is no cover photo
    assert "src=\"http" not in page.text.split("<script")[0]  # nothing loaded from elsewhere


async def test_a_cover_photo_replaces_the_scene_and_a_chosen_colour_wins(host):
    event = await host.create_event(event_type="corporate", cover_image_url="https://cdn.example.com/c.jpg")
    await host.publish(event["id"])
    await host.http.put(f"{P}/events/{event['id']}/invitation", json={
        "design": {"primary_color": "#123456", "tagline": "Annual <b>Summit</b>"},
    })
    invitation = await host.invite(event["id"], "Photo", "+919800000032")
    async with guest_client(host.app) as c:
        page = await c.get(f"/i/{token_of(invitation)}")
    assert 'class="scene-art"' not in page.text and "https://cdn.example.com/c.jpg" in page.text
    assert "--primary:#123456" in page.text
    assert "Annual &lt;b&gt;Summit&lt;/b&gt;" in page.text  # the ribbon is the organiser's text, escaped


async def test_booked_events_pick_a_theme_from_their_occasion():
    from app.services.invitations.guest_themes import theme_for

    assert theme_for(None, "Wedding").key == "wedding"
    assert theme_for(None, "Griha Pravesh").key == "housewarming"
    assert theme_for(None, "Birthday Party").key == "birthday"
    assert theme_for(None, "Something Else").key == "custom"
    assert theme_for("birthday", "Wedding").key == "birthday"  # an explicit type wins


async def test_fonts_are_self_hosted_and_only_from_the_list(host):
    async with guest_client(host.app) as c:
        font = await c.get("/i/_font/pf-600-normal.woff2")
        assert font.status_code == 200 and font.headers["content-type"] == "font/woff2"
        assert font.content[:4] == b"wOF2" and "immutable" in font.headers["cache-control"]
        assert (await c.get("/i/_font/..%2F..%2Fconfig.py")).status_code == 404
        assert (await c.get("/i/_font/LICENSE_DEJAVU")).status_code == 404
