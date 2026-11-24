"""
A booking is confirmed only once Razorpay itself has confirmed the money, in full.

No database: the unit of work, the Razorpay client and every side effect that
reaches another service are stubbed, so these assert only the decision to settle
(or not) and what it does to the booking.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace as NS

import pytest

from app.models.enums import BookingStatus, Currency, PaymentStatus
from app.services.bookings.exceptions import BookingPaymentRequiredError
from app.services.bookings.service import BookingService
from app.services.exceptions import ExternalServiceError
from app.services.payments import service as pay
from app.services.payments.exceptions import PaymentAmountMismatchError, PaymentNotConfirmedError
from app.services.payments.service import PaymentService, _booking_settled_by_capture

SECRET = "rzp_secret_test"
ORDER_ID = "order_TESTORDER123"
PAY_ID = "pay_TESTPAYMENT123"
TOTAL = Decimal("50000.00")
PAISE = 5_000_000
NOW = datetime(2026, 11, 20, tzinfo=timezone.utc)


def sig(order=ORDER_ID, pid=PAY_ID):
    return hmac.new(SECRET.encode(), f"{order}|{pid}".encode(), hashlib.sha256).hexdigest()


class Repo:
    def __init__(self, **returns):
        self._r = returns

    async def get_by_id(self, _id):
        return self._r.get("get_by_id")

    async def get_by_id_with_lock(self, _id):
        return self._r.get("get_by_id")

    async def find_by_gateway_order(self, _o):
        return self._r.get("find_by_gateway_order")

    async def find_by_event_id(self, *_a, **_k):
        return None

    async def find_by_payment(self, _p):
        return []

    async def find_by_booking(self, _b):
        return self._r.get("find_by_booking", [])

    async def create(self, data):
        return NS(id=uuid.uuid4(), **data) if isinstance(data, dict) else data

    async def update(self, obj, data):
        for k, v in data.items():
            setattr(obj, k, v)
        return obj


class Uow:
    def __init__(self, payment, booking, *, booking_payments=()):
        self.payments = NS(
            payments=Repo(get_by_id=payment, find_by_gateway_order=payment, find_by_booking=list(booking_payments)),
            transactions=Repo(), ledger=Repo(), attempts=Repo(), webhooks=Repo(),
        )
        self.bookings = NS(bookings=Repo(get_by_id=booking), status_history=Repo(), history=Repo())

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def commit(self):
        return None


def make_booking(**kw):
    base = dict(
        id=uuid.uuid4(), booking_status=BookingStatus.PENDING, payment_status=PaymentStatus.PENDING,
        total_amount=TOTAL, amount_paid=Decimal("0.00"), amount_due=TOTAL, applied_coupon_ids=None,
        confirmed_at=None,
    )
    base.update(kw)
    return NS(**base)


def make_payment(booking, **kw):
    base = dict(
        id=uuid.uuid4(), payer_id=uuid.uuid4(), booking_id=booking.id, payment_number="PAY-1",
        payment_status=PaymentStatus.PENDING, final_amount=TOTAL, discount_amount=Decimal("0.00"),
        currency=Currency.INR, gateway_order_id=ORDER_ID, gateway_payment_id=None, captured_at=None,
    )
    base.update(kw)
    return NS(**base)


class Razorpay:
    """Razorpay's own record of the payment; each test decides what it says."""

    def __init__(self, record=None, *, fetch_error=None, capture_status="captured"):
        self.record = record
        self.fetch_error = fetch_error
        self.captures = []
        self._capture_status = capture_status
        self.payment = NS(fetch=self._fetch, capture=self._capture)

    def _fetch(self, _pid):
        if self.fetch_error:
            raise self.fetch_error
        return dict(self.record)

    def _capture(self, pid, amount, data):
        self.captures.append((pid, amount, data))
        return {**self.record, "status": self._capture_status}


def record(status="captured", amount=PAISE, order=ORDER_ID, currency="INR"):
    return {"id": PAY_ID, "order_id": order, "amount": amount, "currency": currency, "status": status}


@pytest.fixture
def world(monkeypatch):
    """A pending booking + payment, a stubbed Razorpay, and inert side effects."""
    booking = make_booking()
    payment = make_payment(booking)
    svc = PaymentService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(payment, booking), raising=False)
    monkeypatch.setattr(pay, "PaymentResponse", NS(model_validate=lambda p: p), raising=False)

    async def noop(*a, **k):
        return None

    monkeypatch.setattr(pay, "_notify_payment_outcome", noop, raising=False)
    monkeypatch.setattr(pay, "_associate_event", noop, raising=False)
    # Side effects that would otherwise open real database sessions.
    monkeypatch.setattr("app.services.referrals.service.ReferralService.trigger_referral_rewards", noop, raising=False)
    monkeypatch.setattr(BookingService, "notify_vendor_if_confirmed_and_paid", noop, raising=False)
    monkeypatch.setattr(BookingService, "notify_booking_successful", noop, raising=False)

    def install(rz):
        monkeypatch.setattr(pay, "_razorpay_client", lambda: rz, raising=False)
        return rz

    return NS(svc=svc, booking=booking, payment=payment, install=install)


async def verify(w):
    return await w.svc.verify_payment(
        payment_id=w.payment.id, customer_id=w.payment.payer_id,
        gateway_payment_id=PAY_ID, gateway_signature=sig(), secret=SECRET,
    )


def untouched(w):
    assert w.payment.payment_status == PaymentStatus.PENDING
    assert w.booking.booking_status == BookingStatus.PENDING
    assert w.booking.payment_status == PaymentStatus.PENDING
    assert w.booking.amount_paid == Decimal("0.00")


# ── Client verification must be backed by Razorpay's own record ─────────────

async def test_captured_on_razorpay_confirms_the_booking(world):
    world.install(Razorpay(record()))
    await verify(world)
    assert world.payment.payment_status == PaymentStatus.COMPLETED
    assert world.booking.payment_status == PaymentStatus.COMPLETED
    assert world.booking.booking_status == BookingStatus.CONFIRMED
    assert world.booking.amount_paid == TOTAL and world.booking.amount_due == Decimal("0.00")


@pytest.mark.parametrize("status", ["created", "failed", "refunded"])
async def test_a_valid_signature_is_not_enough_if_razorpay_does_not_show_it_captured(world, status):
    world.install(Razorpay(record(status=status)))
    with pytest.raises(PaymentNotConfirmedError):
        await verify(world)
    untouched(world)


async def test_authorized_is_captured_for_the_exact_amount_then_confirmed(world):
    rz = world.install(Razorpay(record(status="authorized")))
    await verify(world)
    assert rz.captures == [(PAY_ID, PAISE, {"currency": "INR"})]
    assert world.booking.booking_status == BookingStatus.CONFIRMED


async def test_authorized_that_cannot_be_captured_does_not_confirm(world):
    world.install(Razorpay(record(status="authorized"), capture_status="authorized"))
    with pytest.raises(PaymentNotConfirmedError):
        await verify(world)
    untouched(world)


async def test_an_underpaid_payment_is_refused(world):
    world.install(Razorpay(record(amount=PAISE - 100)))
    with pytest.raises(PaymentAmountMismatchError):
        await verify(world)
    untouched(world)


async def test_a_payment_from_a_different_order_is_refused(world):
    world.install(Razorpay(record(order="order_SOMEONE_ELSE")))
    with pytest.raises(PaymentAmountMismatchError):
        await verify(world)
    untouched(world)


async def test_if_razorpay_cannot_be_reached_nothing_is_confirmed(world):
    world.install(Razorpay(fetch_error=TimeoutError("network down")))
    with pytest.raises(ExternalServiceError):
        await verify(world)
    untouched(world)


async def test_if_razorpay_is_not_configured_nothing_is_confirmed(world, monkeypatch):
    def unconfigured():
        raise ExternalServiceError("razorpay", "not configured")

    monkeypatch.setattr(pay, "_razorpay_client", unconfigured, raising=False)
    with pytest.raises(ExternalServiceError):
        await verify(world)
    untouched(world)


# ── The booking is only "paid" when the bill is covered in full ─────────────

def test_full_payment_confirms_a_pending_booking():
    b, p = make_booking(), make_payment(make_booking())
    u = _booking_settled_by_capture(b, p, NOW)
    assert u["payment_status"] == PaymentStatus.COMPLETED and u["booking_status"] == BookingStatus.CONFIRMED
    assert u["amount_paid"] == TOTAL and u["amount_due"] == Decimal("0.00") and u["confirmed_at"] == NOW


def test_a_short_payment_records_the_money_but_neither_pays_nor_confirms():
    b = make_booking()
    p = make_payment(b, final_amount=Decimal("30000.00"))
    u = _booking_settled_by_capture(b, p, NOW)
    assert u == {"amount_paid": Decimal("30000.00"), "amount_due": Decimal("20000.00")}
    assert "payment_status" not in u and "booking_status" not in u


def test_two_part_payments_confirm_only_on_the_second():
    b = make_booking(amount_paid=Decimal("30000.00"), amount_due=Decimal("20000.00"))
    p = make_payment(b, final_amount=Decimal("20000.00"))
    u = _booking_settled_by_capture(b, p, NOW)
    assert u["payment_status"] == PaymentStatus.COMPLETED and u["amount_paid"] == TOTAL


def test_a_referral_discount_counts_toward_the_bill():
    b = make_booking()
    p = make_payment(b, final_amount=Decimal("45000.00"), discount_amount=Decimal("5000.00"))
    u = _booking_settled_by_capture(b, p, NOW)
    assert u["payment_status"] == PaymentStatus.COMPLETED and u["amount_due"] == Decimal("0.00")
    assert u["amount_paid"] == Decimal("45000.00"), "only the money actually received is recorded as paid"


async def test_a_short_payment_never_confirms_via_the_verify_path(world):
    world.payment.final_amount = Decimal("30000.00")
    world.install(Razorpay(record(amount=3_000_000)))
    await verify(world)
    assert world.payment.payment_status == PaymentStatus.COMPLETED  # the payment itself did go through
    assert world.booking.booking_status == BookingStatus.PENDING
    assert world.booking.payment_status == PaymentStatus.PENDING
    assert world.booking.amount_due == Decimal("20000.00")


# ── Webhooks: signed, and also the right status and amount ──────────────────

def webhook(world, *, amount=PAISE, status="captured", event="payment.captured"):
    body = {"id": f"evt_{uuid.uuid4().hex[:6]}", "event": event, "payload": {"payment": {"entity": {
        "id": PAY_ID, "order_id": ORDER_ID, "amount": amount, "status": status}}}}
    payload = json.dumps(body).encode()
    return world.svc.handle_webhook(
        gateway="razorpay", payload=payload,
        signature=hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest(), secret=SECRET,
    )


async def test_webhook_capture_for_the_right_amount_confirms(world):
    await webhook(world)
    assert world.booking.booking_status == BookingStatus.CONFIRMED


async def test_webhook_capture_for_the_wrong_amount_is_ignored(world):
    await webhook(world, amount=PAISE - 1)
    untouched(world)


async def test_webhook_that_is_not_actually_captured_is_ignored(world):
    await webhook(world, status="failed")
    untouched(world)


# ── The admin "Confirm" button cannot be a shortcut round all of this ───────

def booking_service(monkeypatch, booking, payments):
    svc = BookingService()
    monkeypatch.setattr(svc, "_uow", lambda: Uow(None, booking, booking_payments=payments), raising=False)
    return svc


def paid_row(**kw):
    base = dict(payment_status=PaymentStatus.COMPLETED, gateway_payment_id=PAY_ID, captured_at=NOW)
    base.update(kw)
    return NS(**base)


async def test_admin_confirm_refuses_an_unpaid_booking(monkeypatch):
    b = make_booking()
    svc = booking_service(monkeypatch, b, [])
    with pytest.raises(BookingPaymentRequiredError):
        await svc.confirm_booking(b.id, uuid.uuid4())
    assert b.booking_status == BookingStatus.PENDING


async def test_admin_confirm_refuses_a_part_paid_booking(monkeypatch):
    b = make_booking(payment_status=PaymentStatus.COMPLETED, amount_paid=Decimal("30000"), amount_due=Decimal("20000"))
    svc = booking_service(monkeypatch, b, [paid_row()])
    with pytest.raises(BookingPaymentRequiredError):
        await svc.confirm_booking(b.id, uuid.uuid4())
    assert b.booking_status == BookingStatus.PENDING


@pytest.mark.parametrize("row", [
    paid_row(gateway_payment_id=None),               # no Razorpay payment reference
    paid_row(captured_at=None),                      # never captured
    paid_row(payment_status=PaymentStatus.PENDING),  # not completed
])
async def test_admin_confirm_needs_razorpays_capture_on_record_not_just_a_flag(monkeypatch, row):
    b = make_booking(payment_status=PaymentStatus.COMPLETED, amount_paid=TOTAL, amount_due=Decimal("0.00"))
    svc = booking_service(monkeypatch, b, [row])
    with pytest.raises(BookingPaymentRequiredError):
        await svc.confirm_booking(b.id, uuid.uuid4())
    assert b.booking_status == BookingStatus.PENDING


async def test_admin_confirm_works_once_razorpay_has_confirmed_in_full(monkeypatch):
    async def noop(*a, **k):
        return None

    monkeypatch.setattr("app.services.invitations.events.EventService.associate_confirmed_booking", noop, raising=False)
    monkeypatch.setattr(BookingService, "notify_vendor_if_confirmed_and_paid", noop, raising=False)
    monkeypatch.setattr("app.services.bookings.service.BookingResponse", NS(model_validate=lambda b: b), raising=False)
    b = make_booking(payment_status=PaymentStatus.COMPLETED, amount_paid=TOTAL, amount_due=Decimal("0.00"))
    svc = booking_service(monkeypatch, b, [paid_row()])
    await svc.confirm_booking(b.id, uuid.uuid4())
    assert b.booking_status == BookingStatus.CONFIRMED

