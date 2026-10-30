"""
A webhook event may only move a payment in the direction it actually means.

The regression these cover: `is_success = event == "payment.captured"` with an
`else` that marked the payment FAILED treated every other Razorpay event as a
failure. Razorpay sends payment.authorized before payment.captured on the
normal card flow, so a successful payment was failed on the first event and
the idempotency guard then made payment.captured a no-op — leaving captured
money recorded as a failed payment and its booking marked FAILED.

No database: the UnitOfWork is stubbed, so these assert the dispatch decision
in isolation.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import Currency, PaymentStatus
from app.services.payments.service import PaymentService

SECRET = "whsec_test_secret"
ORDER_ID = "order_TESTORDER123"
GATEWAY_PAYMENT_ID = "pay_TESTPAYMENT123"


def _sign(payload: bytes) -> str:
    return hmac.new(SECRET.encode(), payload, hashlib.sha256).hexdigest()


def _event(event: str, event_id: str = "evt_1") -> tuple[bytes, str]:
    body = {
        "id": event_id,
        "event": event,
        "payload": {
            "payment": {
                "entity": {"id": GATEWAY_PAYMENT_ID, "order_id": ORDER_ID}
            }
        },
    }
    payload = json.dumps(body).encode()
    return payload, _sign(payload)


class _Repo:
    def __init__(self, **returns):
        self._returns = returns
        self.created: list[dict] = []

    async def find_by_event_id(self, _event_id, gateway=None):
        return self._returns.get("find_by_event_id")

    async def find_by_gateway_order(self, _order_id):
        return self._returns.get("find_by_gateway_order")

    async def find_by_payment(self, _payment_id):
        return []

    async def get_by_id(self, _id):
        return self._returns.get("get_by_id")

    async def create(self, data: dict):
        self.created.append(data)
        return SimpleNamespace(id=uuid.uuid4(), **data)

    async def update(self, obj, data: dict):
        for k, v in data.items():
            setattr(obj, k, v)
        return obj


class _FakeUow:
    def __init__(self, payment, booking):
        self.payments = SimpleNamespace(
            webhooks=_Repo(find_by_event_id=None),
            payments=_Repo(find_by_gateway_order=payment),
            transactions=_Repo(),
            ledger=_Repo(),
            attempts=_Repo(),
        )
        self.bookings = SimpleNamespace(bookings=_Repo(get_by_id=booking))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def payment():
    return SimpleNamespace(
        id=uuid.uuid4(),
        payer_id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        payment_number="PAYTEST123456",
        payment_status=PaymentStatus.PENDING,
        final_amount=Decimal("50000.00"),
        currency=Currency.INR,
        gateway_order_id=ORDER_ID,
    )


@pytest.fixture
def service(monkeypatch, payment):
    booking = SimpleNamespace(
        id=payment.booking_id,
        booking_status=None,
        payment_status=PaymentStatus.PENDING,
        amount_paid=Decimal("0.00"),
        amount_due=Decimal("500.00"),
        applied_coupon_ids=None,
    )
    svc = PaymentService()
    monkeypatch.setattr(svc, "_uow", lambda: _FakeUow(payment, booking), raising=False)
    # Side effects that reach other services are irrelevant to dispatch.
    monkeypatch.setattr(
        "app.services.payments.service._notify_payment_outcome",
        _noop,
        raising=False,
    )
    svc._test_booking = booking
    return svc


async def _noop(*args, **kwargs):
    return None


@pytest.mark.asyncio
async def test_captured_completes_the_payment(service, payment):
    payload, signature = _event("payment.captured")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_failed_fails_the_payment(service, payment):
    payload, signature = _event("payment.failed")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    assert payment.payment_status == PaymentStatus.FAILED


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "event",
    ["payment.authorized", "payment.pending", "payment.dispute.created", "refund.speed_changed"],
)
async def test_other_events_leave_the_payment_pending(service, payment, event):
    payload, signature = _event(event)
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_authorized_then_captured_still_completes(service, payment):
    """The exact production sequence the old dispatch got wrong."""
    payload, signature = _event("payment.authorized", event_id="evt_auth")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    assert payment.payment_status == PaymentStatus.PENDING

    payload, signature = _event("payment.captured", event_id="evt_cap")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_bad_signature_is_rejected(service, payment):
    payload, _ = _event("payment.captured")
    from app.services.payments.exceptions import InvalidGatewaySignatureError

    with pytest.raises(InvalidGatewaySignatureError):
        await service.handle_webhook(
            gateway="razorpay",
            payload=payload,
            signature="deadbeef",
            secret=SECRET,
        )
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_unknown_gateway_fails_closed(service, payment):
    payload, signature = _event("payment.captured")
    from app.services.payments.exceptions import InvalidGatewaySignatureError

    with pytest.raises(InvalidGatewaySignatureError):
        await service.handle_webhook(
            gateway="not_a_gateway",
            payload=payload,
            signature=signature,
            secret=SECRET,
        )
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_capture_corrects_a_payment_the_client_reported_abandoned(
    service, payment
):
    """
    The customer paid, dismissed the sheet before the callback, and the app
    reported the attempt abandoned — then payment.captured arrived.

    Skipping it there left captured money recorded as a failure with the
    booking unconfirmed, so the capture must win.
    """
    payment.payment_status = PaymentStatus.FAILED

    payload, signature = _event("payment.captured")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )

    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_failure_never_undoes_a_capture(service, payment):
    payment.payment_status = PaymentStatus.COMPLETED

    payload, signature = _event("payment.failed")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )

    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_capture_never_rewrites_a_refunded_payment(service, payment):
    payment.payment_status = PaymentStatus.REFUNDED

    payload, signature = _event("payment.captured")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )

    assert payment.payment_status == PaymentStatus.REFUNDED


@pytest.mark.asyncio
async def test_capture_records_the_money_on_the_booking(service, payment):
    """A paid booking must read as paid in full, not as still fully due."""
    payload, signature = _event("payment.captured")
    await service.handle_webhook(
        gateway="razorpay", payload=payload, signature=signature, secret=SECRET
    )
    booking = service._test_booking
    assert booking.payment_status == PaymentStatus.COMPLETED
    assert booking.amount_paid == payment.final_amount
    assert booking.amount_due == Decimal("0.00")


@pytest.mark.asyncio
async def test_repeated_capture_does_not_double_count(service, payment):
    for event_id in ("evt_a", "evt_b"):
        payload, signature = _event("payment.captured", event_id=event_id)
        await service.handle_webhook(
            gateway="razorpay", payload=payload, signature=signature, secret=SECRET
        )
    assert service._test_booking.amount_paid == payment.final_amount


@pytest.mark.asyncio
async def test_blank_webhook_secret_rejects_a_forged_capture(service, payment):
    """
    HMAC with an empty key is perfectly computable, so before the Razorpay
    credentials are connected anyone could post a self-signed "captured" event.
    """
    from app.services.payments.exceptions import InvalidGatewaySignatureError

    body = {
        "id": "evt_forged",
        "event": "payment.captured",
        "payload": {"payment": {"entity": {"id": "pay_x", "order_id": ORDER_ID}}},
    }
    payload = json.dumps(body).encode()
    forged = hmac.new(b"", payload, hashlib.sha256).hexdigest()

    with pytest.raises(InvalidGatewaySignatureError):
        await service.handle_webhook(
            gateway="razorpay", payload=payload, signature=forged, secret=""
        )
    assert payment.payment_status == PaymentStatus.PENDING
