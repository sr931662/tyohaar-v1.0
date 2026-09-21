"""
Verification and abandonment are scoped to the payment's owner.

The regression these cover: verify_payment took `current_user` but never used
it, and its already-COMPLETED branch returns the full PaymentResponse before
any signature is checked. Together those let any signed-in user read back
another customer's payment by guessing its ID, with a throwaway signature.

Not-found rather than forbidden is asserted on purpose — a distinct
"forbidden" would confirm which payment IDs exist.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import Currency, PaymentStatus
from app.services.exceptions import NotFoundError
from app.services.payments.service import PaymentService

SECRET = "rzp_secret_test"
ORDER_ID = "order_TESTORDER123"
GATEWAY_PAYMENT_ID = "pay_TESTPAYMENT123"


def _valid_signature() -> str:
    raw = f"{ORDER_ID}|{GATEWAY_PAYMENT_ID}".encode()
    return hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


class _Repo:
    def __init__(self, **returns):
        self._returns = returns
        self.created: list[dict] = []

    async def get_by_id(self, _id):
        return self._returns.get("get_by_id")

    async def find_by_payment(self, _payment_id):
        return self._returns.get("find_by_payment", [])

    async def create(self, data: dict):
        self.created.append(data)
        return SimpleNamespace(id=uuid.uuid4(), **data)

    async def update(self, obj, data: dict):
        for k, v in data.items():
            setattr(obj, k, v)
        return obj


class _FakeUow:
    def __init__(self, payment, booking, attempts):
        self.payments = SimpleNamespace(
            payments=_Repo(get_by_id=payment),
            transactions=_Repo(),
            ledger=_Repo(),
            attempts=_Repo(find_by_payment=attempts),
        )
        self.bookings = SimpleNamespace(bookings=_Repo(get_by_id=booking))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


async def _noop(*args, **kwargs):
    return None


def _make(monkeypatch, status=PaymentStatus.PENDING):
    owner_id = uuid.uuid4()
    payment = SimpleNamespace(
        id=uuid.uuid4(),
        payer_id=owner_id,
        booking_id=uuid.uuid4(),
        payment_number="PAYTEST123456",
        payment_status=status,
        final_amount=Decimal("50000.00"),
        currency=Currency.INR,
        gateway_order_id=ORDER_ID,
        created_at=datetime.now(tz=timezone.utc),
    )
    booking = SimpleNamespace(
        id=payment.booking_id,
        booking_status=None,
        payment_status=PaymentStatus.PENDING,
        applied_coupon_ids=None,
    )
    attempt = SimpleNamespace(id=uuid.uuid4())
    svc = PaymentService()
    monkeypatch.setattr(
        svc, "_uow", lambda: _FakeUow(payment, booking, [attempt]), raising=False
    )
    monkeypatch.setattr(
        "app.services.payments.service._notify_payment_outcome", _noop, raising=False
    )
    monkeypatch.setattr(
        "app.services.payments.service.PaymentResponse",
        SimpleNamespace(model_validate=lambda p: p),
        raising=False,
    )
    return svc, payment, owner_id, attempt


@pytest.mark.asyncio
async def test_verify_rejects_a_non_owner(monkeypatch):
    svc, payment, _owner, _attempt = _make(monkeypatch)
    with pytest.raises(NotFoundError):
        await svc.verify_payment(
            payment_id=payment.id,
            customer_id=uuid.uuid4(),  # someone else
            gateway_payment_id=GATEWAY_PAYMENT_ID,
            gateway_signature=_valid_signature(),
            secret=SECRET,
        )
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_verify_does_not_leak_a_completed_payment_to_a_non_owner(monkeypatch):
    """The already-COMPLETED branch returns early; ownership must precede it."""
    svc, payment, _owner, _attempt = _make(monkeypatch, status=PaymentStatus.COMPLETED)
    with pytest.raises(NotFoundError):
        await svc.verify_payment(
            payment_id=payment.id,
            customer_id=uuid.uuid4(),
            gateway_payment_id="anything",
            gateway_signature="not-a-real-signature",
            secret=SECRET,
        )


@pytest.mark.asyncio
async def test_verify_completes_for_the_owner_with_a_valid_signature(monkeypatch):
    svc, payment, owner, _attempt = _make(monkeypatch)
    await svc.verify_payment(
        payment_id=payment.id,
        customer_id=owner,
        gateway_payment_id=GATEWAY_PAYMENT_ID,
        gateway_signature=_valid_signature(),
        secret=SECRET,
    )
    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_verify_rejects_a_forged_signature_from_the_owner(monkeypatch):
    from app.services.payments.exceptions import InvalidGatewaySignatureError

    svc, payment, owner, _attempt = _make(monkeypatch)
    with pytest.raises(InvalidGatewaySignatureError):
        await svc.verify_payment(
            payment_id=payment.id,
            customer_id=owner,
            gateway_payment_id=GATEWAY_PAYMENT_ID,
            gateway_signature="deadbeef",
            secret=SECRET,
        )
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_abandon_rejects_a_non_owner(monkeypatch):
    svc, payment, _owner, _attempt = _make(monkeypatch)
    with pytest.raises(NotFoundError):
        await svc.abandon_payment(payment_id=payment.id, customer_id=uuid.uuid4())
    assert payment.payment_status == PaymentStatus.PENDING


@pytest.mark.asyncio
async def test_abandon_closes_an_open_payment(monkeypatch):
    svc, payment, owner, attempt = _make(monkeypatch)
    await svc.abandon_payment(
        payment_id=payment.id,
        customer_id=owner,
        reason_code="BAD_REQUEST_ERROR",
        reason_description="Customer dismissed checkout",
    )
    assert payment.payment_status == PaymentStatus.FAILED
    assert attempt.failure_code == "BAD_REQUEST_ERROR"


@pytest.mark.asyncio
async def test_abandon_never_overrides_a_captured_payment(monkeypatch):
    """A client claim must not undo what the gateway already confirmed."""
    svc, payment, owner, _attempt = _make(monkeypatch, status=PaymentStatus.COMPLETED)
    await svc.abandon_payment(payment_id=payment.id, customer_id=owner)
    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_valid_signature_corrects_an_abandoned_payment(monkeypatch):
    """Razorpay's signature outranks the client's own abandonment claim."""
    svc, payment, owner, _attempt = _make(monkeypatch, status=PaymentStatus.FAILED)
    await svc.verify_payment(
        payment_id=payment.id,
        customer_id=owner,
        gateway_payment_id=GATEWAY_PAYMENT_ID,
        gateway_signature=_valid_signature(),
        secret=SECRET,
    )
    assert payment.payment_status == PaymentStatus.COMPLETED


@pytest.mark.asyncio
async def test_failed_payment_stays_failed_without_a_valid_signature(monkeypatch):
    """The promotion above must not be reachable by an unsigned caller."""
    from app.services.payments.exceptions import PaymentAlreadyFailedError

    svc, payment, owner, _attempt = _make(monkeypatch, status=PaymentStatus.FAILED)
    with pytest.raises(PaymentAlreadyFailedError):
        await svc.verify_payment(
            payment_id=payment.id,
            customer_id=owner,
            gateway_payment_id=GATEWAY_PAYMENT_ID,
            gateway_signature="deadbeef",
            secret=SECRET,
        )
    assert payment.payment_status == PaymentStatus.FAILED
