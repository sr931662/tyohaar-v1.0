"""
The admin booking page's data, without a database.

Every relationship on Booking is lazy="noload", so the detail endpoint used to
return empty `items` (and no address, payments or package price) for every
booking. These tests drive BookingService with a fake unit of work and check
that what the page needs is actually filled in.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app.models.enums import BookingStatus, PaymentMethod, PaymentStatus
from app.models.payments.payment import PaymentGateway
from app.schemas.bookings import BookingDetailResponse
from app.services.bookings.service import BookingService
from app.services.exceptions import BusinessRuleError

NOW = datetime(2026, 11, 20, 8, 36, tzinfo=timezone.utc)


def repo(**methods):
    ns = NS()
    for name, value in methods.items():
        async def call(*a, _v=value, **k):
            if isinstance(_v, Exception):
                raise _v
            return _v
        setattr(ns, name, call)
    return ns


def line(name, *, qty=1, unit_price="100", addon=False, returnable=None, notes=None, order=0, service=False):
    base = dict(
        id=uuid.uuid4(), booking_id=uuid.uuid4(), name=name, description=None, quantity=qty, unit="pcs",
        unit_price=Decimal(unit_price), final_price=Decimal(unit_price) * qty, is_addon=addon, notes=notes,
        display_order=order, scheduled_start_at=None, prep_time_minutes=None, created_at=NOW, updated_at=NOW,
    )
    if service:
        return NS(**base, package_service_id=uuid.uuid4())
    return NS(**base, package_item_id=uuid.uuid4(), is_returnable=bool(returnable))


def make_uow(**overrides):
    coupon_id = uuid.uuid4()
    pieces = dict(
        bookings=NS(
            items=repo(find_by_booking=[line("Backdrop", order=1, returnable=True), line("Cake", addon=True, order=0)]),
            service_items=repo(find_by_booking=[line("Setup crew", unit_price="500", service=True)]),
            cancellations=repo(find_by_booking=None),
            reschedules=repo(find_by_booking=[]),
            invoices=repo(find_by_booking=None),
        ),
        packages=NS(packages=repo(get_by_id=NS(base_price=Decimal("2000")))),
        users=NS(addresses=repo(get_by_id=NS(
            id=uuid.uuid4(), label="Home", recipient_name="Asha", recipient_phone="+919876543210",
            address_line_1="Tower A, 12th floor", address_line_2="Sector 93B, Noida", landmark="City Park",
            locality="Sector 93B", city="Noida", state="Uttar Pradesh", postal_code="201304", country="India",
            latitude=Decimal("28.5126128"), longitude=Decimal("77.3900479"),
            delivery_instructions="Google Maps: https://maps.app.goo.gl/abc",
        ))),
        occasions=NS(
            celebrations=repo(get_by_id=NS(venue_name=None, venue_address="12 Lake Road", occasion_id=uuid.uuid4())),
            occasions=repo(get_by_id=NS(name="Birthday")),
        ),
        payments=NS(
            payments=repo(find_by_booking=[NS(
                id=uuid.uuid4(), payment_number="PAY-1", payment_status=PaymentStatus.COMPLETED,
                payment_method=PaymentMethod.UPI, gateway=PaymentGateway.RAZORPAY, final_amount=Decimal("2600"),
                gateway_payment_id="pay_abc", captured_at=NOW, failed_at=None, created_at=NOW,
            )]),
            coupons=repo(get_by_id=NS(code="WELCOME10")),
        ),
    )
    pieces.update(overrides)
    uow = NS(**pieces)
    uow.coupon_id = coupon_id
    return uow


def make_booking(uow):
    return NS(
        id=uuid.uuid4(), package_id=uuid.uuid4(), celebration_id=uuid.uuid4(), address_id=uuid.uuid4(),
        recipient_name="Asha", recipient_phone="+919876543210", applied_coupon_ids=[str(uow.coupon_id)],
    )


async def build(role="admin", **overrides):
    uow = make_uow(**overrides)
    response = BookingDetailResponse.model_construct()
    await BookingService()._attach_booking_detail(uow, make_booking(uow), response, role)
    return response


async def test_the_order_is_filled_in_with_real_labelled_lines():
    r = await build()
    # items first in display order, then services.
    assert [l.name for l in r.lines] == ["Cake", "Backdrop", "Setup crew"]
    by_name = {l.name: l for l in r.lines}
    assert by_name["Backdrop"].kind == "rental"
    assert by_name["Cake"].kind == "keep" and by_name["Cake"].is_addon is True
    assert by_name["Setup crew"].kind == "service"
    assert [i.name for i in r.items] == ["Cake", "Backdrop"], "legacy item-only list is populated too"


async def test_package_price_venue_occasion_and_contact():
    r = await build()
    assert r.package_base_price == Decimal("2000")
    assert r.occasion_name == "Birthday"
    assert r.venue_address == "12 Lake Road"
    assert (r.recipient_name, r.recipient_phone) == ("Asha", "+919876543210")


async def test_address_is_readable_and_the_maps_link_is_split_out():
    a = (await build()).address
    assert a.full_address == "Tower A, 12th floor, Sector 93B, Noida, Near City Park, Noida, Uttar Pradesh 201304"
    assert a.maps_link == "https://maps.app.goo.gl/abc"
    assert a.delivery_instructions is None, "the maps link is not repeated as free-text instructions"
    assert (a.latitude, a.longitude) == (28.5126128, 77.3900479)


async def test_payments_are_plain_values_not_enum_reprs():
    p = (await build()).payments[0]
    assert (p.payment_status, p.payment_method, p.gateway) == ("completed", "upi", "razorpay")
    assert p.final_amount == Decimal("2600") and p.payment_number == "PAY-1"


async def test_coupon_codes_replace_opaque_ids():
    assert (await build()).applied_coupon_codes == ["WELCOME10"]


async def test_a_vendor_sees_what_to_deliver_and_where_but_not_contact_or_money():
    r = await build(role="vendor")
    assert len(r.lines) == 3 and r.address.full_address and r.venue_address == "12 Lake Road"
    assert r.recipient_name is None and r.recipient_phone is None
    assert r.address.recipient_name is None and r.address.recipient_phone is None
    assert r.payments == [] and r.applied_coupon_codes == []


async def test_a_customer_sees_their_own_address_contact_and_payments():
    r = await build(role="customer")
    assert r.recipient_name == "Asha" and r.address.recipient_phone == "+919876543210"
    assert len(r.payments) == 1


async def test_one_unreadable_record_does_not_blank_the_rest_of_the_page():
    r = await build(users=NS(addresses=repo(get_by_id=RuntimeError("boom"))))
    assert r.address is None
    assert len(r.lines) == 3 and r.payments and r.package_base_price == Decimal("2000")


async def test_a_booking_with_nothing_attached_still_loads():
    r = await build(
        bookings=NS(
            items=repo(find_by_booking=[]), service_items=repo(find_by_booking=[]),
            cancellations=repo(find_by_booking=None), reschedules=repo(find_by_booking=[]),
            invoices=repo(find_by_booking=None),
        ),
        payments=NS(payments=repo(find_by_booking=[]), coupons=repo(get_by_id=None)),
    )
    assert r.lines == [] and r.items == [] and r.payments == []


# ── Admin "Cancel" must never confirm an unpaid booking ─────────────────────

class _Uow:
    def __init__(self, booking):
        self.bookings = NS(bookings=repo(get_by_id=booking))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def test_declining_a_cancellation_cannot_confirm_an_unpaid_booking():
    booking = NS(id=uuid.uuid4(), booking_status=BookingStatus.PENDING, payment_status=PaymentStatus.PENDING)
    svc = BookingService()
    svc._uow = lambda: _Uow(booking)
    with pytest.raises(BusinessRuleError):
        await svc.process_cancellation(booking.id, uuid.uuid4(), approved=False)
    assert booking.booking_status == BookingStatus.PENDING


async def test_history_actor_names_prefer_name_then_email_then_phone():
    uid1, uid2, uid3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

    class Rows:
        def all(self):
            return [(uid1, "Karn Goyal", "k@x.com", None), (uid2, None, "a@x.com", None), (uid3, None, None, "+91999")]

    class Session:
        async def execute(self, *_):
            return Rows()

    names = await BookingService._actor_names(NS(session=Session()), {uid1, uid2, uid3})
    assert names == {uid1: "Karn Goyal", uid2: "a@x.com", uid3: "+91999"}


# ── Names and numbers the admin pages show ──────────────────────────────────

def test_a_customer_without_a_name_is_shown_by_email_not_as_blank_or_a_placeholder():
    label = BookingService._customer_label
    assert label(NS(display_name="Karn Goyal", email="k@x.com")) == "Karn Goyal"
    assert label(NS(display_name=None, email="k@x.com")) == "k@x.com"
    assert label(NS(display_name="TMP-1a2b3c", email="k@x.com")) == "k@x.com"
    assert label(NS(display_name=None, email=None)) is None


def test_placeholder_phone_numbers_are_never_shown():
    real = BookingService._real_phone
    assert real("+918860384909") == "+918860384909"
    assert real("TMP-1a2b3c4d") is None and real("") is None and real(None) is None
