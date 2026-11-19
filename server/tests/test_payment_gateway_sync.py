"""
A payment Razorpay shows as paid must be settled even when neither the app's
verify call nor the webhook reached the server.

No database required: the UnitOfWork, the payment lookup, the Razorpay client
and the settlement step are stubbed, so these assert only the decision of
whether, and with which gateway payment, to settle.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import Currency, PaymentStatus
from app.services.payments import service as payments_service
from app.services.payments.service import PaymentService


class _Uow:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeRazorpay:
    def __init__(self, items, capture_status="captured"):
        self.items = items
        self.captures: list[tuple] = []
        self._capture_status = capture_status
        self.order = SimpleNamespace(payments=lambda order_id: {"items": self.items})
        self.payment = SimpleNamespace(capture=self._capture)

    def _capture(self, pay_id, amount, data):
        self.captures.append((pay_id, amount, data))
        return {"id": pay_id, "status": self._capture_status}


def _setup(monkeypatch, status, items, order_id="order_ABC", capture_status="captured"):
    payment = SimpleNamespace(
        id=uuid.uuid4(),
        payment_status=status,
        gateway_order_id=order_id,
        final_amount=Decimal("1.00"),
        currency=Currency.INR,
    )

    async def _exists(_pid, _uow):
        return payment

    gateway = _FakeRazorpay(items, capture_status)
    monkeypatch.setattr(payments_service, "validate_payment_exists", _exists)
    monkeypatch.setattr(payments_service, "_razorpay_client", lambda: gateway)

    svc = PaymentService()
    monkeypatch.setattr(svc, "_uow", lambda: _Uow(), raising=False)
    settled: list[dict] = []

    async def _settle(**kwargs):
        settled.append(kwargs)
        return "SETTLED"

    monkeypatch.setattr(svc, "_settle_captured_payment", _settle)
    return svc, payment, gateway, settled


@pytest.mark.asyncio
async def test_captured_order_is_settled(monkeypatch):
    svc, payment, gateway, settled = _setup(
        monkeypatch, PaymentStatus.PENDING, [{"id": "pay_1", "status": "captured", "amount": 100}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) == "SETTLED"
    assert settled[0]["gateway_payment_id"] == "pay_1"
    assert settled[0]["gateway_signature"] is None
    assert gateway.captures == []


@pytest.mark.asyncio
async def test_authorized_full_amount_is_captured_then_settled(monkeypatch):
    svc, payment, gateway, settled = _setup(
        monkeypatch, PaymentStatus.PENDING, [{"id": "pay_2", "status": "authorized", "amount": 100}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) == "SETTLED"
    assert gateway.captures == [("pay_2", 100, {"currency": "INR"})]
    assert settled[0]["gateway_payment_id"] == "pay_2"


@pytest.mark.asyncio
async def test_authorized_wrong_amount_is_left_alone(monkeypatch):
    svc, payment, gateway, settled = _setup(
        monkeypatch, PaymentStatus.PENDING, [{"id": "pay_3", "status": "authorized", "amount": 50}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) is None
    assert gateway.captures == [] and settled == []


@pytest.mark.asyncio
async def test_unpaid_order_is_not_settled(monkeypatch):
    svc, payment, _gateway, settled = _setup(
        monkeypatch, PaymentStatus.PENDING, [{"id": "pay_4", "status": "failed", "amount": 100}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) is None
    assert settled == []


@pytest.mark.asyncio
async def test_abandoned_but_actually_paid_is_settled(monkeypatch):
    svc, payment, _gateway, settled = _setup(
        monkeypatch, PaymentStatus.FAILED, [{"id": "pay_5", "status": "captured", "amount": 100}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) == "SETTLED"
    assert settled[0]["gateway_payment_id"] == "pay_5"


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [PaymentStatus.COMPLETED, PaymentStatus.REFUNDED])
async def test_settled_payments_are_not_touched(monkeypatch, status):
    svc, payment, _gateway, settled = _setup(
        monkeypatch, status, [{"id": "pay_6", "status": "captured", "amount": 100}]
    )
    assert await svc.sync_payment_with_gateway(payment.id) is None
    assert settled == []


@pytest.mark.asyncio
async def test_placeholder_order_id_is_skipped(monkeypatch):
    svc, payment, _gateway, settled = _setup(
        monkeypatch, PaymentStatus.PENDING, [], order_id=""
    )
    assert await svc.sync_payment_with_gateway(payment.id) is None
    assert settled == []
