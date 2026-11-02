"""
Who may read or act on a booking / payment. Found in QA: vendors could read
any booking and complete any booking, and several payment endpoints answered
any logged-in user. No database: units of work are stubbed.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.bookings.exceptions import BookingOwnershipError, VendorAssignmentOwnershipError
from app.services.bookings.service import BookingService
from app.services.exceptions import NotFoundError
from app.services.payments.service import PaymentService


class _Repo:
    def __init__(self, **kw):
        self.kw = kw

    async def get_by_id(self, _id):
        return self.kw.get("get_by_id")

    async def find_by_user(self, _uid):
        return self.kw.get("find_by_user")

    async def find_many(self, *a, **k):
        return self.kw.get("find_many", [])


def _uow(*, booking, package_vendor_id=None, vendor_for_user=None, assigned=()):
    package = SimpleNamespace(vendor_id=package_vendor_id)
    return SimpleNamespace(
        bookings=SimpleNamespace(
            bookings=_Repo(get_by_id=booking),
            assignments=SimpleNamespace(_model=SimpleNamespace(booking_id=None, vendor_id=None),
                                        find_many=_Repo(find_many=list(assigned)).find_many),
        ),
        packages=SimpleNamespace(packages=_Repo(get_by_id=package)),
        vendors=SimpleNamespace(vendors=_Repo(find_by_user=vendor_for_user)),
    )


@pytest.fixture
def ids():
    return SimpleNamespace(customer=uuid.uuid4(), stranger=uuid.uuid4(), vendor_user=uuid.uuid4(),
                           vendor=uuid.uuid4(), other_vendor=uuid.uuid4())


def _booking(ids):
    return SimpleNamespace(id=uuid.uuid4(), customer_id=ids.customer, package_id=uuid.uuid4())


async def _can_read(uow, booking, user_id, role):
    try:
        await BookingService.assert_can_read_booking(uow, booking, user_id, role)
        return True
    except BookingOwnershipError:
        return False


@pytest.mark.asyncio
async def test_customer_reads_only_their_own_booking(ids):
    b = _booking(ids)
    uow = _uow(booking=b)
    assert await _can_read(uow, b, ids.customer, "customer")
    assert not await _can_read(uow, b, ids.stranger, "customer")


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["admin", "super_admin", "support"])
async def test_staff_read_any_booking(ids, role):
    b = _booking(ids)
    assert await _can_read(_uow(booking=b), b, ids.stranger, role)


@pytest.mark.asyncio
async def test_the_package_owner_vendor_can_read(ids):
    b = _booking(ids)
    uow = _uow(booking=b, package_vendor_id=ids.vendor, vendor_for_user=SimpleNamespace(id=ids.vendor))
    assert await _can_read(uow, b, ids.vendor_user, "vendor")


@pytest.mark.asyncio
async def test_an_assigned_vendor_can_read(ids):
    b = _booking(ids)
    uow = _uow(booking=b, package_vendor_id=ids.other_vendor, vendor_for_user=SimpleNamespace(id=ids.vendor),
               assigned=[SimpleNamespace()])
    assert await _can_read(uow, b, ids.vendor_user, "vendor")


@pytest.mark.asyncio
async def test_another_vendor_cannot_read_it(ids):
    """The bug: this used to return True for every vendor."""
    b = _booking(ids)
    uow = _uow(booking=b, package_vendor_id=ids.other_vendor, vendor_for_user=SimpleNamespace(id=ids.vendor))
    assert not await _can_read(uow, b, ids.vendor_user, "vendor")


@pytest.mark.asyncio
async def test_a_vendor_user_without_a_vendor_profile_is_refused(ids):
    b = _booking(ids)
    assert not await _can_read(_uow(booking=b, vendor_for_user=None), b, ids.vendor_user, "vendor")


@pytest.mark.asyncio
async def test_unknown_roles_are_refused(ids):
    b = _booking(ids)
    assert not await _can_read(_uow(booking=b), b, ids.customer, "guest")


# ── complete_booking ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_vendor_cannot_complete_someone_elses_booking(ids, monkeypatch):
    b = _booking(ids)
    uow = _uow(booking=b, package_vendor_id=ids.other_vendor)

    class Ctx:
        async def __aenter__(self_):
            return uow

        async def __aexit__(self_, *e):
            return False

    async def exists(booking_id, u):
        return b

    monkeypatch.setattr("app.services.bookings.service.validate_booking_exists", exists)
    svc = BookingService()
    monkeypatch.setattr(svc, "_uow", lambda: Ctx(), raising=False)
    with pytest.raises(VendorAssignmentOwnershipError):
        await svc.complete_booking(b.id, ids.vendor)


# ── payments ─────────────────────────────────────────────────────────────────

def _payments(monkeypatch, payment=None, booking=None):
    uow = SimpleNamespace(
        payments=SimpleNamespace(payments=_Repo(get_by_id=payment)),
        bookings=SimpleNamespace(bookings=_Repo(get_by_id=booking)),
    )

    class Ctx:
        async def __aenter__(self_):
            return uow

        async def __aexit__(self_, *e):
            return False

    svc = PaymentService()
    monkeypatch.setattr(svc, "_uow", lambda: Ctx(), raising=False)

    async def txns(self_, payment_id):
        return ["txn"]

    async def refunds(self_, booking_id):
        return ["refund"]

    monkeypatch.setattr(PaymentService, "get_payment_transactions", txns)
    monkeypatch.setattr(PaymentService, "list_refunds", refunds)
    return svc


@pytest.mark.asyncio
async def test_only_the_payer_or_an_admin_sees_a_payments_transactions(ids, monkeypatch):
    payment = SimpleNamespace(payer_id=ids.customer)
    svc = _payments(monkeypatch, payment=payment)
    assert await svc.get_payment_transactions_for(uuid.uuid4(), ids.customer, "customer") == ["txn"]
    assert await svc.get_payment_transactions_for(uuid.uuid4(), ids.stranger, "admin") == ["txn"]
    with pytest.raises(NotFoundError):
        await svc.get_payment_transactions_for(uuid.uuid4(), ids.stranger, "customer")


@pytest.mark.asyncio
async def test_a_missing_payment_looks_the_same_as_someone_elses(ids, monkeypatch):
    svc = _payments(monkeypatch, payment=None)
    with pytest.raises(NotFoundError):
        await svc.get_payment_transactions_for(uuid.uuid4(), ids.customer, "customer")


@pytest.mark.asyncio
async def test_only_the_customer_or_an_admin_sees_a_bookings_refunds(ids, monkeypatch):
    booking = SimpleNamespace(customer_id=ids.customer)
    svc = _payments(monkeypatch, booking=booking)
    assert await svc.list_refunds_for(uuid.uuid4(), ids.customer, "customer") == ["refund"]
    assert await svc.list_refunds_for(uuid.uuid4(), ids.stranger, "super_admin") == ["refund"]
    with pytest.raises(NotFoundError):
        await svc.list_refunds_for(uuid.uuid4(), ids.stranger, "vendor")


def test_finance_invoices_are_admin_only():
    import inspect

    from app.controllers.payments import controller

    for fn in (controller.get_invoice, controller.list_invoices):
        annotation = str(inspect.signature(fn).parameters["current_user"].annotation)
        assert "AdminDep" in annotation, fn.__name__


# ── Unpublished packages are not public ──────────────────────────────────────

def _pkg_service(monkeypatch, status, owner_vendor_id, vendor_for_user=None):
    from app.models.enums import PackageStatus

    package = SimpleNamespace(status=PackageStatus(status), vendor_id=owner_vendor_id)
    uow = SimpleNamespace(
        packages=SimpleNamespace(packages=_Repo(get_by_id=package)),
        vendors=SimpleNamespace(vendors=_Repo(find_by_user=vendor_for_user)),
    )

    class Ctx:
        async def __aenter__(self_):
            return uow

        async def __aexit__(self_, *e):
            return False

    from app.services.packages.service import PackageService

    svc = PackageService()
    monkeypatch.setattr(svc, "_uow", lambda: Ctx(), raising=False)
    return svc


@pytest.mark.asyncio
async def test_active_packages_are_public(ids, monkeypatch):
    svc = _pkg_service(monkeypatch, "active", ids.vendor)
    await svc.assert_package_visible(uuid.uuid4())  # anonymous


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["draft", "pending_review", "inactive", "archived"])
async def test_unpublished_packages_look_nonexistent_to_the_public(ids, monkeypatch, status):
    from app.services.packages.exceptions import PackageNotFoundError

    svc = _pkg_service(monkeypatch, status, ids.vendor)
    with pytest.raises(PackageNotFoundError):
        await svc.assert_package_visible(uuid.uuid4())
    with pytest.raises(PackageNotFoundError):
        await svc.assert_package_visible(uuid.uuid4(), ids.customer, "customer")


@pytest.mark.asyncio
async def test_staff_and_the_owning_vendor_can_see_a_draft(ids, monkeypatch):
    svc = _pkg_service(monkeypatch, "draft", ids.vendor, vendor_for_user=SimpleNamespace(id=ids.vendor))
    await svc.assert_package_visible(uuid.uuid4(), ids.stranger, "admin")
    await svc.assert_package_visible(uuid.uuid4(), ids.stranger, "support")
    await svc.assert_package_visible(uuid.uuid4(), ids.vendor_user, "vendor")


@pytest.mark.asyncio
async def test_another_vendor_cannot_see_a_draft(ids, monkeypatch):
    from app.services.packages.exceptions import PackageNotFoundError

    svc = _pkg_service(monkeypatch, "draft", ids.vendor, vendor_for_user=SimpleNamespace(id=ids.other_vendor))
    with pytest.raises(PackageNotFoundError):
        await svc.assert_package_visible(uuid.uuid4(), ids.vendor_user, "vendor")
