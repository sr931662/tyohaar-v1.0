"""
The charged amount must come from the booking, never from the request body.

No database required: the UnitOfWork and the Razorpay client are both stubbed,
so these assert the arithmetic and the gateway call in isolation.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import Currency
from app.schemas.payments.create import PaymentCreate
from app.services.payments import service as payments_service
from app.services.payments.service import PaymentService

BOOKING_TOTAL = Decimal("50000.00")


class _Repo:
    """Stands in for a repository; records what it was asked to create."""

    def __init__(self, **returns):
        self._returns = returns
        self.created: list[dict] = []
        self._last = None

    async def get_by_id(self, _id):
        # Falls back to the last created row so the service's post-commit
        # re-fetch of the new Payment resolves.
        return self._returns.get("get_by_id") or self._last

    async def get_active_for_user(self, _id):
        return None

    async def find_usable_for_user(self, _id):
        return []

    async def count_for_payment(self, _id):
        return 0

    async def create(self, data: dict):
        self.created.append(data)
        self._last = SimpleNamespace(
            id=uuid.uuid4(),
            currency=data.get("currency", Currency.INR),
            **{k: v for k, v in data.items() if k != "currency"},
        )
        return self._last

    async def update(self, obj, data: dict):
        for k, v in data.items():
            setattr(obj, k, v)
        return obj


class _FakeUow:
    def __init__(self, booking, payments_repo):
        self.bookings = SimpleNamespace(
            bookings=_Repo(get_by_id=booking)
        )
        self.memberships = SimpleNamespace(memberships=_Repo(), plans=_Repo())
        self.referrals = SimpleNamespace(milestone_grants=_Repo())
        self.payments = SimpleNamespace(
            payments=payments_repo, attempts=_Repo(), ledger=_Repo()
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeRazorpay:
    """Captures the order payload the service sends to the gateway."""

    def __init__(self):
        self.orders: list[dict] = []
        self.order = SimpleNamespace(create=self._create)

    def _create(self, payload: dict):
        self.orders.append(payload)
        return {"id": "order_TESTORDER123"}


@pytest.fixture
def gateway(monkeypatch):
    fake = _FakeRazorpay()
    monkeypatch.setattr(payments_service, "_razorpay_client", lambda: fake)
    return fake


@pytest.fixture
def customer_id():
    return uuid.uuid4()


@pytest.fixture
def service(monkeypatch, customer_id):
    booking = SimpleNamespace(
        id=uuid.uuid4(),
        customer_id=customer_id,
        total_amount=BOOKING_TOTAL,
    )
    payments_repo = _Repo()
    svc = PaymentService()
    monkeypatch.setattr(
        svc, "_uow", lambda: _FakeUow(booking, payments_repo), raising=False
    )
    svc._test_booking = booking
    svc._test_payments_repo = payments_repo
    return svc


def _payload(subtotal: Decimal) -> PaymentCreate:
    return PaymentCreate(
        currency=Currency.INR,
        subtotal=subtotal,
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        platform_fee=Decimal("0.00"),
        final_amount=subtotal,
        gateway="razorpay",
    )


@pytest.mark.asyncio
async def test_charges_booking_total_when_client_is_honest(
    service, gateway, customer_id
):
    result = await service.initiate_payment(
        booking_id=service._test_booking.id,
        customer_id=customer_id,
        data=_payload(BOOKING_TOTAL),
    )

    assert result.amount == BOOKING_TOTAL
    assert result.amount_paise == 5_000_000
    assert gateway.orders[0]["amount"] == 5_000_000


@pytest.mark.asyncio
async def test_understated_subtotal_cannot_lower_the_gateway_order(
    service, gateway, customer_id
):
    """
    The regression this guards: PaymentCreate only checks that the client's
    own numbers add up, so `subtotal: 1.00 / final_amount: 1.00` is a valid
    body. If the service ever trusts it again, a ₹50,000 booking opens a ₹1
    Razorpay order and still verifies successfully.
    """
    result = await service.initiate_payment(
        booking_id=service._test_booking.id,
        customer_id=customer_id,
        data=_payload(Decimal("1.00")),
    )

    assert result.amount == BOOKING_TOTAL
    assert gateway.orders[0]["amount"] == 5_000_000
    # The persisted Payment row must record the real figure too, or refunds
    # and the ledger would reconcile against the tampered one.
    assert service._test_payments_repo.created[0]["final_amount"] == BOOKING_TOTAL
    assert service._test_payments_repo.created[0]["subtotal"] == BOOKING_TOTAL


@pytest.mark.asyncio
async def test_rejects_a_booking_owned_by_someone_else(service, gateway):
    from app.core.exceptions import BusinessRuleError

    with pytest.raises(BusinessRuleError):
        await service.initiate_payment(
            booking_id=service._test_booking.id,
            customer_id=uuid.uuid4(),  # not the booking's customer
            data=_payload(BOOKING_TOTAL),
        )
    assert gateway.orders == []
