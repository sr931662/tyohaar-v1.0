"""
Managed balloon palette and booking totals against a real Postgres.

Skipped without TEST_DATABASE_URL (same convention and the same
disposable-database guard as the other integration suites):

    TEST_DATABASE_URL=postgresql+asyncpg://user@localhost:5432/tyohaar_test \
        python -m pytest tests/test_palette_and_totals_integration.py
"""

from __future__ import annotations

import os
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import *  # noqa: F401,F403 - registers every table on Base
from app.models.base import Base
from app.models.bookings.booking_item import BookingItem
from app.models.common.balloon_color import BalloonColor
from app.models.common.balloon_finish import BalloonFinish
from app.models.enums import (
    AccountStatus,
    CharacterSet,
    Currency,
    PackageStatus,
    UserRole,
    UserType,
)
from app.models.occasions.occasion import Occasion
from app.models.packages.package import Package, package_occasions
from app.models.packages.package_item import PackageItem, package_item_links
from app.models.packages.package_service import PackageServiceLine
from app.models.users.user import User
from app.schemas.bookings.create import BookingCreate
from app.schemas.colors import BalloonColorCreate, BalloonColorUpdate
from app.services.bookings.service import BookingService
from app.services.colors.service import BalloonColorService
from app.services.bookings.exceptions import BookingOwnershipError
from app.services.exceptions import BusinessRuleError, ConflictError

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")

pytestmark = [
    pytest.mark.asyncio(loop_scope="module"),
    pytest.mark.skipif(not TEST_DATABASE_URL, reason="TEST_DATABASE_URL not set — needs Postgres"),
]

PALETTE = [
    ("Red", "#E63946"), ("Gold", "#D4AF37"), ("Pink", "#F48FB1"), ("Sky Blue", "#87CEEB"),
    ("Navy Blue", "#1E3A5F"),
]


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def engine():
    from test_deletion_lifecycle_integration import _assert_disposable

    _assert_disposable(TEST_DATABASE_URL)
    from app.db.session import _build_engine_args

    url, connect_args = _build_engine_args(TEST_DATABASE_URL)
    engine = create_async_engine(url, connect_args=connect_args, future=True)
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
        await conn.execute(text("TRUNCATE users, occasions, packages, balloon_colors, balloon_finishes RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture(loop_scope="module")
async def sf(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


async def seed_palette(sf, names=PALETTE):
    async with sf() as s:
        for i, (name, hex_code) in enumerate(names):
            s.add(BalloonColor(name=name, hex_code=hex_code, sort_order=i, is_active=True))
        await s.commit()


async def make_user(sf, role=UserRole.CUSTOMER):
    async with sf() as s:
        user = User(id=uuid.uuid4(), phone=f"+9198{uuid.uuid4().int % 10**8:08d}", first_name="Asha",
                    last_name="Test", role=role, user_type=UserType.INDIVIDUAL, account_status=AccountStatus.ACTIVE)
        s.add(user)
        await s.commit()
        return user


# ── Palette management ────────────────────────────────────────────────────────

async def test_palette_crud_ordering_and_guards(sf):
    svc = BalloonColorService(sf)
    a = await svc.create(BalloonColorCreate(name="Coral", hex_code="#ff7f50"))
    b = await svc.create(BalloonColorCreate(name="Teal", hex_code="#008080"))
    assert a.hex_code == "#FF7F50"  # normalised
    with pytest.raises(ConflictError):
        await svc.create(BalloonColorCreate(name="coral", hex_code="#111111"))  # name, case-insensitive
    with pytest.raises(ConflictError):
        await svc.create(BalloonColorCreate(name="Other", hex_code="#008080"))  # hex
    with pytest.raises(ValueError):
        BalloonColorCreate(name="Bad", hex_code="orange")

    await svc.update(a.id, BalloonColorUpdate(is_active=False))
    assert [c.name for c in await svc.list(active_only=True)] == ["Teal"]
    assert {c.name for c in await svc.list(active_only=False)} == {"Coral", "Teal"}
    from app.repositories.unit_of_work import UnitOfWork

    async with UnitOfWork(sf) as uow:
        assert await BalloonColorService.active_hex_codes(uow) == {"#008080"}

    ordered = await svc.reorder([b.id, a.id])
    assert [c.name for c in ordered] == ["Teal", "Coral"]

    # One active colour left can't be removed: a dual combo would be impossible.
    with pytest.raises(BusinessRuleError):
        await svc.delete(b.id)
    await svc.delete(a.id)  # inactive: fine


async def test_http_public_list_and_admin_gate(sf):
    from app.core.current_user import get_current_user
    from app.core.dependencies import get_balloon_color_service
    from app.main import create_app
    from app.schemas.users.response import UserResponse
    from fastapi import HTTPException

    await seed_palette(sf)
    admin, customer = await make_user(sf, UserRole.ADMIN), await make_user(sf)
    app = create_app()
    state = {"user": None}

    async def current():
        if state["user"] is None:
            raise HTTPException(status_code=401, detail="no")
        return state["user"]

    app.dependency_overrides[get_current_user] = current
    app.dependency_overrides[get_balloon_color_service] = lambda: BalloonColorService(sf)

    async def as_(user):
        async with sf() as s:
            row = (await s.execute(select(User).where(User.id == user.id))).scalar_one()
        state["user"] = UserResponse.model_validate(row, from_attributes=True)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        pub = await c.get("/api/v1/balloon-colors")
        assert pub.status_code == 200 and [x["name"] for x in pub.json()["data"]][:2] == ["Red", "Gold"]
        await as_(customer)
        assert (await c.get("/api/v1/admin/balloon-colors")).status_code == 403
        assert (await c.post("/api/v1/admin/balloon-colors", json={"name": "Lime", "hex_code": "#00FF00"})).status_code == 403
        await as_(admin)
        created = await c.post("/api/v1/admin/balloon-colors", json={"name": "Lime", "hex_code": "#00ff00"})
        assert created.status_code == 201 and created.json()["data"]["hex_code"] == "#00FF00"
        assert (await c.post("/api/v1/admin/balloon-colors", json={"name": "X", "hex_code": "#00ff00"})).status_code == 422
        dup = await c.post("/api/v1/admin/balloon-colors", json={"name": "Lime2", "hex_code": "#00FF00"})
        assert dup.status_code == 409
        cid = created.json()["data"]["id"]
        off = await c.patch(f"/api/v1/admin/balloon-colors/{cid}", json={"is_active": False})
        assert off.status_code == 200
        assert "Lime" not in [x["name"] for x in (await c.get("/api/v1/balloon-colors")).json()["data"]]


# ── Booking totals ────────────────────────────────────────────────────────────

async def make_package(sf, *, base=Decimal("1000")):
    async with sf() as s:
        occasion = Occasion(id=uuid.uuid4(), name="Birthday", slug=f"b-{uuid.uuid4().hex[:6]}", display_order=0,
                            popularity_score=0, is_active=True, is_featured=False, is_seasonal=False,
                            allow_balloon_theme=True)
        package = Package(id=uuid.uuid4(), name="Starter", slug=f"p-{uuid.uuid4().hex[:6]}",
                          status=PackageStatus.ACTIVE, base_price=base)
        s.add_all([occasion, package])
        await s.flush()
        await s.execute(insert(package_occasions).values(package_id=package.id, occasion_id=occasion.id))
        await s.commit()
        return package, occasion


async def add_item(sf, package, **kw):
    common = kw.pop("common", False)
    async with sf() as s:
        item = PackageItem(id=uuid.uuid4(), package_id=None if common else package.id, is_common=common, **kw)
        s.add(item)
        await s.flush()
        if common:
            await s.execute(insert(package_item_links).values(package_id=package.id, package_item_id=item.id))
        await s.commit()
        return item


def booking(package, occasion, **kw):
    return BookingCreate(package_id=package.id, occasion_id=occasion.id,
                         scheduled_date=date.today() + timedelta(days=30), venue_address="12 Lake Road", **kw)


async def run_booking(sf, customer, data):
    return await BookingService(sf).create_booking(customer.id, data)


async def test_included_and_optional_lines_sum_correctly(sf):
    await seed_palette(sf)
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    included = await add_item(sf, package, name="Backdrop", base_price=Decimal("100"), quantity=2, is_mandatory=True)
    optional = await add_item(sf, package, name="Cake", base_price=Decimal("250.50"), quantity=1, is_mandatory=False)
    result = await run_booking(sf, customer, booking(package, occasion, item_ids=[optional.id]))
    # 1000 base + 2 x 100 included + 250.50 add-on
    assert Decimal(str(result.subtotal)) == Decimal("1450.50")
    assert Decimal(str(result.tax_amount)) == Decimal("261.09")  # 18% of 1450.50 = 261.09
    assert Decimal(str(result.total_amount)) == Decimal("1711.59")
    assert included.id and optional.id


async def test_common_items_are_never_billed_unless_the_customer_adds_them(sf):
    # The bug: a common item flagged is_mandatory was charged on every booking
    # while the app presented (and totalled) it as an opt-in add-on.
    await seed_palette(sf)
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    common = await add_item(sf, package, name="Extra lights", base_price=Decimal("500"), is_mandatory=True, common=True)

    without = await run_booking(sf, customer, booking(package, occasion))
    assert Decimal(str(without.subtotal)) == Decimal("1000.00")

    # A different date so the 5-minute duplicate guard doesn't return the first.
    data = booking(package, occasion, item_ids=[common.id]).model_copy(
        update={"scheduled_date": date.today() + timedelta(days=31)})
    with_it = await run_booking(sf, customer, data)
    assert Decimal(str(with_it.subtotal)) == Decimal("1500.00")

    async with sf() as s:
        rows = (await s.execute(select(BookingItem).where(BookingItem.booking_id == with_it.id))).scalars().all()
        assert [r.final_price for r in rows] == [Decimal("500.00")]


async def test_alphanumeric_line_bills_per_character_and_stores_the_text(sf):
    await seed_palette(sf)
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    letters = await add_item(sf, package, name="Foil letters", base_price=Decimal("40"), is_mandatory=False,
                             is_customizable=True, character_set=CharacterSet.ALPHANUMERIC)
    result = await run_booking(sf, customer, booking(
        package, occasion, item_ids=[letters.id], item_customizations={str(letters.id): "Anita 30"}))
    assert Decimal(str(result.subtotal)) == Decimal("1280.00")  # 1000 + 7 x 40
    async with sf() as s:
        row = (await s.execute(select(BookingItem).where(BookingItem.booking_id == result.id))).scalar_one()
        assert (row.notes, row.quantity, row.final_price) == ("ANITA 30", 7, Decimal("280.00"))


async def test_digit_line_still_drops_letters(sf):
    await seed_palette(sf)
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    marquee = await add_item(sf, package, name="Marquee", base_price=Decimal("399"), is_mandatory=False, is_customizable=True)
    result = await run_booking(sf, customer, booking(
        package, occasion, item_ids=[marquee.id], item_customizations={str(marquee.id): "A2b5"}))
    assert Decimal(str(result.subtotal)) == Decimal("1798.00")  # 1000 + 2 x 399


async def test_balloon_colours_must_be_in_the_live_palette(sf):
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    await seed_palette(sf)

    three = booking(package, occasion, balloon_color_mode="triple",
                    balloon_colors=["#E63946", "#D4AF37", "#F48FB1"])
    ok = await run_booking(sf, customer, three)
    assert ok.balloon_color_mode.value == "triple" and ok.balloon_colors == ["#e63946", "#d4af37", "#f48fb1"]

    # Disable Gold in the portal: it can no longer be ordered, but the
    # existing booking keeps its snapshot.
    async with sf() as s:
        gold = (await s.execute(select(BalloonColor).where(BalloonColor.name == "Gold"))).scalar_one()
        gold.is_active = False
        await s.commit()
    retry = booking(package, occasion, balloon_color_mode="dual", balloon_colors=["#E63946", "#D4AF37"]).model_copy(
        update={"scheduled_date": date.today() + timedelta(days=33)})
    with pytest.raises(BusinessRuleError):
        await run_booking(sf, customer, retry)

    quad = booking(package, occasion, balloon_color_mode="quad",
                   balloon_colors=["#E63946", "#F48FB1", "#87CEEB", "#1E3A5F"]).model_copy(
        update={"scheduled_date": date.today() + timedelta(days=34)})
    assert (await run_booking(sf, customer, quad)).balloon_color_mode.value == "quad"



# ── Rental / keep / service labels, finish, invoice PDF ──────────────────────

async def seed_finishes(sf, names=("Standard matte", "Pastel", "Chrome / metallic")):
    async with sf() as s:
        for i, name in enumerate(names):
            s.add(BalloonFinish(name=name, sort_order=i, is_active=True))
        await s.commit()


async def add_service(sf, package, **kw):
    async with sf() as s:
        line = PackageServiceLine(id=uuid.uuid4(), package_id=package.id, **kw)
        s.add(line)
        await s.commit()
        return line


async def labelled_booking(sf, *, finish=None):
    await seed_palette(sf)
    await seed_finishes(sf)
    customer = await make_user(sf)
    package, occasion = await make_package(sf)
    await add_item(sf, package, name="LED letters", base_price=Decimal("399"), quantity=1, is_mandatory=True,
                   is_returnable=True, is_customizable=True)
    await add_item(sf, package, name="Party banner", base_price=Decimal("250.50"), quantity=1, is_mandatory=True,
                   is_returnable=False)
    await add_service(sf, package, name="Setup & dismantling", base_price=Decimal("500"), quantity=1, is_mandatory=True)
    kwargs = {}
    if finish:
        kwargs = dict(balloon_color_mode="dual", balloon_colors=["#E63946", "#D4AF37"], balloon_finish=finish)
    result = await run_booking(sf, customer, booking(package, occasion, **kwargs))
    return customer, result


async def test_lines_carry_rental_keep_and_service_labels(sf):
    customer, result = await labelled_booking(sf)
    lines = await BookingService(sf).get_booking_lines(result.id, customer.id, "customer")
    assert [(l.kind, l.name) for l in lines] == [
        ("rental", "LED letters"), ("keep", "Party banner"), ("service", "Setup & dismantling"),
    ]
    assert Decimal(str(lines[1].final_price)) == Decimal("250.50")


async def test_the_flag_is_a_snapshot_not_a_live_lookup(sf):
    customer, result = await labelled_booking(sf)
    async with sf() as s:
        await s.execute(text("UPDATE package_items SET is_returnable = NOT is_returnable"))
        await s.commit()
    lines = await BookingService(sf).get_booking_lines(result.id, customer.id, "customer")
    assert [l.kind for l in lines][:2] == ["rental", "keep"]  # unchanged by the later package edit


async def test_invoice_pdf_is_owner_or_admin_only(sf):
    customer, result = await labelled_booking(sf)
    svc = BookingService(sf)
    pdf, name = await svc.get_invoice_pdf(result.id, customer.id, "customer")
    assert pdf.startswith(b"%PDF") and name == f"INV-{result.booking_number}.pdf"

    stranger, admin = await make_user(sf), await make_user(sf, UserRole.ADMIN)
    with pytest.raises(BookingOwnershipError):
        await svc.get_invoice_pdf(result.id, stranger.id, "customer")
    with pytest.raises(BookingOwnershipError):
        await svc.get_booking_lines(result.id, stranger.id, "customer")
    with pytest.raises(BookingOwnershipError):
        await svc.get_invoice_pdf(result.id, stranger.id, "vendor")
    assert (await svc.get_invoice_pdf(result.id, admin.id, "admin"))[0].startswith(b"%PDF")


async def test_invoice_pdf_reads_correctly_end_to_end(sf):
    import io
    from pypdf import PdfReader

    customer, result = await labelled_booking(sf, finish="pastel")
    pdf, _ = await BookingService(sf).get_invoice_pdf(result.id, customer.id, "customer")
    text_ = " ".join(" ".join(p.extract_text().split()) for p in PdfReader(io.BytesIO(pdf)).pages)
    for expected in ["RENTAL", "KEEP", "SERVICE", "LED letters", "Party banner", "Setup & dismantling",
                     "1. Red", "2. Gold", "Pastel", result.booking_number, "GST @ 18%", "Asha Test"]:
        assert expected in text_, expected
    # 1000 base + 399 + 250.50 + 500 = 2149.50 ; GST 386.91 ; total 2536.41
    assert "₹2,149.50" in text_ and "₹386.91" in text_ and "₹2,536.41" in text_


async def test_finish_must_be_active_and_is_stored_canonically(sf):
    customer, result = await labelled_booking(sf, finish="pastel")
    assert result.balloon_finish == "Pastel"

    package, occasion = await make_package(sf)
    with pytest.raises(BusinessRuleError):
        await run_booking(sf, customer, booking(
            package, occasion, balloon_color_mode="single", balloon_colors=["#E63946"], balloon_finish="Glitter"))
    async with sf() as s:
        await s.execute(text("UPDATE balloon_finishes SET is_active = false WHERE name = 'Pastel'"))
        await s.commit()
    with pytest.raises(BusinessRuleError):
        await run_booking(sf, customer, booking(
            package, occasion, balloon_color_mode="single", balloon_colors=["#E63946"], balloon_finish="Pastel"))
    # A finish with no colours chosen is simply ignored.
    ok = await run_booking(sf, customer, booking(package, occasion, balloon_finish="Glitter"))
    assert ok.balloon_finish is None


async def test_http_invoice_download_headers_and_errors(sf):
    from app.core.current_user import get_current_user
    from app.core.dependencies import get_booking_service
    from app.main import create_app
    from app.schemas.users.response import UserResponse
    from fastapi import HTTPException

    customer, result = await labelled_booking(sf)
    stranger = await make_user(sf)
    app = create_app()
    state = {"user": None}

    async def current():
        if state["user"] is None:
            raise HTTPException(status_code=401, detail="no")
        return state["user"]

    async def as_(user):
        async with sf() as s:
            row = (await s.execute(select(User).where(User.id == user.id))).scalar_one()
        state["user"] = UserResponse.model_validate(row, from_attributes=True)

    app.dependency_overrides[get_current_user] = current
    app.dependency_overrides[get_booking_service] = lambda: BookingService(sf)
    url = f"/api/v1/bookings/{result.id}/invoice.pdf"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        assert (await c.get(url)).status_code == 401
        await as_(customer)
        ok = await c.get(url)
        assert ok.status_code == 200 and ok.headers["content-type"] == "application/pdf"
        assert "attachment" in ok.headers["content-disposition"] and ".pdf" in ok.headers["content-disposition"]
        assert ok.headers["cache-control"] == "private, no-store" and ok.content.startswith(b"%PDF")
        lines = await c.get(f"/api/v1/bookings/{result.id}/lines")
        assert [l["kind"] for l in lines.json()["data"]] == ["rental", "keep", "service"]
        await as_(stranger)
        assert (await c.get(url)).status_code == 403
        assert (await c.get(f"/api/v1/bookings/{result.id}/lines")).status_code == 403
