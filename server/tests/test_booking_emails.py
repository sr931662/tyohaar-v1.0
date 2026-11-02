"""
Booking-success emails and notifications.

No database and no SMTP: the unit of work, NotificationService and the email
client are stubbed, so these assert who is told what, with which attachment,
and that a repeat call does nothing.
"""

from __future__ import annotations

import email
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.models.enums import BookingStatus, PaymentStatus
from app.services.bookings.invoice_pdf import InvoiceData, InvoiceLine
from app.services.bookings.service import BookingService
from app.services.notifications import email_client
from app.services.notifications.email_templates import booking_success_email, otp_email, shell


def _data(**kw) -> InvoiceData:
    base = dict(
        invoice_number="INV-TYO1",
        issued_on=date(2026, 11, 2),
        booking_number="TYO1",
        booking_status="confirmed",
        payment_status="completed",
        package_name="Starter Birthday Pack",
        celebration_title="Anita's 25th",
        event_date=date(2026, 11, 14),
        start_time=time(19, 0),
        end_time=time(22, 30),
        venue=["Tower B Clubhouse", "Pune"],
        customer_name="Anita Rao",
        customer_phone="+919876543210",
        customer_email="anita@example.com",
        lines=[InvoiceLine("keep", "Party banner", 1, "piece", Decimal("250"), Decimal("250"))],
        subtotal=Decimal("250"),
        discount=Decimal("0"),
        taxable=Decimal("250"),
        tax=Decimal("0"),
        platform_fee=Decimal("0"),
        total=Decimal("250"),
        amount_paid=Decimal("250"),
        amount_due=Decimal("0"),
        balloon_colors=[("Gold", "#D4AF37")],
        special_instructions="Call before arriving.",
    )
    base.update(kw)
    return InvoiceData(**base)


# ── Templates ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("role", ["customer", "vendor", "owner"])
def test_every_role_gets_the_booking_basics(role):
    subject, html, text = booking_success_email(role, _data(), vendor_name="Pune Decor", payment_reference="pay_X1")
    assert "TYO1" in subject
    for needle in ["TYO1", "Starter Birthday Pack", "Party banner", "14 November 2026", "Tower B Clubhouse"]:
        assert needle in html and (needle in text or needle == "14 November 2026" or needle == "Party banner")
    assert html.lstrip().lower().startswith("<!doctype html>")


def test_customer_email_mentions_the_invoice_and_payment_reference():
    _, html, text = booking_success_email("customer", _data(), vendor_name="Pune Decor", payment_reference="pay_X1")
    assert "invoice" in html.lower() and "attached" in html.lower()
    assert "pay_X1" in html and "Pune Decor" in html
    assert "Anita" in html


def test_vendor_email_has_the_customer_contact_but_no_payment_reference():
    _, html, text = booking_success_email("vendor", _data(), vendor_name="Pune Decor", payment_reference="pay_X1")
    assert "+919876543210" in html and "anita@example.com" in html
    assert "pay_X1" not in html and "pay_X1" not in text


def test_owner_email_names_the_vendor():
    _, html, _ = booking_success_email("owner", _data(), vendor_name="Pune Decor", payment_reference="pay_X1")
    assert "Pune Decor" in html and "pay_X1" in html


def test_no_gst_row_when_no_tax():
    _, html, _ = booking_success_email("customer", _data(), vendor_name=None)
    assert "GST" not in html
    _, html, _ = booking_success_email("customer", _data(tax=Decimal("45"), total=Decimal("295"), amount_paid=Decimal("295")))
    assert "GST @ 18%" in html


def test_user_supplied_text_is_escaped():
    d = _data(
        customer_name="<script>alert(1)</script>",
        special_instructions='"><img src=x onerror=alert(1)>',
        lines=[InvoiceLine("keep", "<b>Banner</b>", 1, None, Decimal("1"), Decimal("1"), note="<i>x</i>")],
    )
    for role in ("customer", "vendor", "owner"):
        _, html, _ = booking_success_email(role, d, vendor_name="<u>V</u>")
        assert "<script>" not in html and "<img" not in html
        assert "<b>Banner</b>" not in html and "<u>V</u>" not in html


def test_otp_email_shows_the_code_and_is_html_safe():
    html = otp_email("123456", "verify your email", 10)
    assert "123456" in html and "10 minutes" in html and "Never share" in html
    assert "<script" not in shell(preheader="x", heading="<script>", body_html="")


# ── Email client: attachments ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pdf_attachment_is_a_proper_mime_part(monkeypatch):
    sent = {}

    async def fake_send(message, **kwargs):
        sent["message"] = message

    monkeypatch.setattr(email_client.settings, "SMTP_USERNAME", "a@b.c", raising=False)
    monkeypatch.setattr(email_client.settings, "SMTP_PASSWORD", "pw", raising=False)
    monkeypatch.setattr(email_client.aiosmtplib, "send", fake_send)

    await email_client.send_email(
        "to@example.com", "Hi", "<p>x</p>", "x", attachments=[("INV-1.pdf", b"%PDF-1.4 test", "pdf")]
    )
    parsed = email.message_from_bytes(sent["message"].as_bytes())
    assert parsed.get_content_type() == "multipart/mixed"
    kinds = [p.get_content_type() for p in parsed.walk()]
    assert "text/html" in kinds and "text/plain" in kinds and "application/pdf" in kinds
    pdf = next(p for p in parsed.walk() if p.get_content_type() == "application/pdf")
    assert pdf.get_filename() == "INV-1.pdf" and pdf.get_payload(decode=True) == b"%PDF-1.4 test"


@pytest.mark.asyncio
async def test_without_attachments_the_message_stays_a_plain_alternative(monkeypatch):
    sent = {}

    async def fake_send(message, **kwargs):
        sent["message"] = message

    monkeypatch.setattr(email_client.settings, "SMTP_USERNAME", "a@b.c", raising=False)
    monkeypatch.setattr(email_client.settings, "SMTP_PASSWORD", "pw", raising=False)
    monkeypatch.setattr(email_client.aiosmtplib, "send", fake_send)

    await email_client.send_email("to@example.com", "Hi", "<p>x</p>", "x")
    assert sent["message"].get_content_type() == "multipart/alternative"


# ── Notifier ──────────────────────────────────────────────────────────────────

class _Repo:
    def __init__(self, **returns):
        self._r = returns
        self._model = SimpleNamespace(
            recipient_id=None, reference_type=None, reference_id=None, notification_type=None,
            booking_id=None, payment_status=None, role=None, account_status=None,
            email=SimpleNamespace(isnot=lambda _x: None),
        )

    async def get_by_id(self, _id):
        return self._r.get("get_by_id")

    async def find_many(self, *a, **k):
        return self._r.get("find_many", [])


class _Uow:
    def __init__(self, booking, already, payments, admins):
        vendor = SimpleNamespace(id=uuid.uuid4(), user_id=uuid.uuid4(), business_name="Pune Decor")
        self.bookings = SimpleNamespace(bookings=_Repo(get_by_id=booking))
        self.notifications = SimpleNamespace(notifications=_Repo(find_many=already))
        self.packages = SimpleNamespace(packages=_Repo(get_by_id=SimpleNamespace(vendor_id=vendor.id)))
        self.vendors = SimpleNamespace(vendors=_Repo(get_by_id=vendor))
        self.payments = SimpleNamespace(payments=_Repo(find_many=payments))
        users = _Repo(get_by_id=SimpleNamespace(email="vendor@example.com"), find_many=admins)
        self.users = SimpleNamespace(users=users)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


@pytest.fixture
def harness(monkeypatch):
    booking = SimpleNamespace(
        id=uuid.uuid4(), customer_id=uuid.uuid4(), package_id=uuid.uuid4(), booking_number="TYO1",
        booking_status=BookingStatus.CONFIRMED, payment_status=PaymentStatus.COMPLETED,
    )
    state = SimpleNamespace(
        already=[], booking=booking, pushes=[], emails=[], admins=[SimpleNamespace(email="owner@example.com")],
        payments=[SimpleNamespace(gateway_payment_id="pay_X1", payment_number="PAY1")],
    )
    svc = BookingService()
    monkeypatch.setattr(svc, "_uow", lambda: _Uow(state.booking, state.already, state.payments, state.admins), raising=False)

    async def build(self_, uow, b):
        return _data()

    monkeypatch.setattr(BookingService, "_build_invoice_data", build)

    class FakeNotifications:
        async def send_notification(self, user_id, data):
            state.pushes.append((user_id, data))

    monkeypatch.setattr("app.services.notifications.service.NotificationService", FakeNotifications)

    async def fake_email(to, subject, html, text=None, attachments=None):
        state.emails.append(SimpleNamespace(to=to, subject=subject, attachments=attachments))

    monkeypatch.setattr(email_client, "send_email", fake_email)
    monkeypatch.setattr(email_client, "is_configured", lambda: True)
    monkeypatch.setattr("app.core.config.settings.OWNER_NOTIFICATION_EMAILS", "", raising=False)
    return svc, state


@pytest.mark.asyncio
async def test_customer_vendor_and_owner_are_all_told(harness):
    svc, state = harness
    await svc.notify_booking_successful(state.booking.id)

    # customer push
    assert len(state.pushes) == 1
    user_id, data = state.pushes[0]
    assert user_id == state.booking.customer_id
    assert data.channel.value == "push" and "TYO1" in data.body

    # three emails, invoice only on the customer's
    by_to = {e.to: e for e in state.emails}
    assert set(by_to) == {"anita@example.com", "vendor@example.com", "owner@example.com"}
    assert by_to["anita@example.com"].attachments[0][0] == "INV-TYO1.pdf"
    assert by_to["anita@example.com"].attachments[0][1].startswith(b"%PDF")
    assert by_to["vendor@example.com"].attachments is None
    assert by_to["owner@example.com"].attachments is None


@pytest.mark.asyncio
async def test_a_repeat_call_does_nothing(harness):
    svc, state = harness
    state.already = [object()]  # the customer's BOOKING_CONFIRMED marker exists
    await svc.notify_booking_successful(state.booking.id)
    assert state.pushes == [] and state.emails == []


@pytest.mark.asyncio
async def test_unpaid_or_unconfirmed_bookings_send_nothing(harness):
    svc, state = harness
    state.booking.payment_status = PaymentStatus.PENDING
    await svc.notify_booking_successful(state.booking.id)
    assert state.pushes == [] and state.emails == []


@pytest.mark.asyncio
async def test_configured_owner_emails_win_over_super_admins(harness, monkeypatch):
    svc, state = harness
    monkeypatch.setattr("app.core.config.settings.OWNER_NOTIFICATION_EMAILS", "boss@example.com, ops@example.com", raising=False)
    await svc.notify_booking_successful(state.booking.id)
    assert {e.to for e in state.emails} >= {"boss@example.com", "ops@example.com"}
    assert "owner@example.com" not in {e.to for e in state.emails}


@pytest.mark.asyncio
async def test_smtp_not_configured_still_pushes_but_sends_no_email(harness, monkeypatch):
    svc, state = harness
    monkeypatch.setattr(email_client, "is_configured", lambda: False)
    await svc.notify_booking_successful(state.booking.id)
    assert len(state.pushes) == 1 and state.emails == []


@pytest.mark.asyncio
async def test_one_failing_email_does_not_stop_the_rest(harness, monkeypatch):
    svc, state = harness

    async def flaky(to, subject, html, text=None, attachments=None):
        if to == "anita@example.com":
            raise RuntimeError("smtp down")
        state.emails.append(SimpleNamespace(to=to))

    monkeypatch.setattr(email_client, "send_email", flaky)
    await svc.notify_booking_successful(state.booking.id)
    assert {e.to for e in state.emails} == {"vendor@example.com", "owner@example.com"}


@pytest.mark.asyncio
async def test_the_same_address_is_never_emailed_twice(harness):
    svc, state = harness
    state.admins = [SimpleNamespace(email="ANITA@example.com")]  # owner is also the customer
    await svc.notify_booking_successful(state.booking.id)
    assert [e.to for e in state.emails].count("anita@example.com") == 1
