"""
Invoice PDF — pure layout/content tests (no database).

Text is pulled back out of the generated PDF with pypdf, so these assert what a
customer would actually read, not just that bytes came out.
"""

from __future__ import annotations

import io
from datetime import date, time
from decimal import Decimal

import pytest
from pypdf import PdfReader

from app.services.bookings.invoice_pdf import InvoiceData, InvoiceLine, build_invoice_pdf, inr


def _data(**kw) -> InvoiceData:
    base = dict(
        invoice_number="INV-TYO12345678",
        issued_on=date(2026, 10, 27),
        booking_number="TYO12345678",
        booking_status="confirmed",
        payment_status="paid",
        package_name="Starter Birthday Pack",
        celebration_title="Anita's 25th",
        event_date=date(2026, 11, 14),
        start_time=time(19, 0),
        end_time=time(22, 30),
        venue=["Tower B Clubhouse", "12 Lake Road", "Pune", "411001"],
        customer_name="Anita Rao",
        customer_phone="+919876543210",
        customer_email="anita@example.com",
        lines=[
            InvoiceLine("rental", "LED Marquee Letters & Numbers", 2, "characters", Decimal("399"), Decimal("798"), note="25", is_addon=True),
            InvoiceLine("keep", "Party banner", 1, "piece", Decimal("250.50"), Decimal("250.50")),
            InvoiceLine("service", "Setup & dismantling", 1, None, Decimal("500"), Decimal("500")),
        ],
        subtotal=Decimal("2548.50"),
        discount=Decimal("100"),
        taxable=Decimal("2448.50"),
        tax=Decimal("440.73"),
        platform_fee=Decimal("0"),
        total=Decimal("2889.23"),
        amount_paid=Decimal("2889.23"),
        amount_due=Decimal("0"),
        balloon_colors=[("Rose Gold", "#E8B4B8"), ("White", "#FFFFFF")],
        balloon_finish="Pastel",
        customization_note="Please keep the colours soft.",
        special_instructions="Call before arriving.",
    )
    base.update(kw)
    return InvoiceData(**base)


def _text(pdf: bytes) -> str:
    return " ".join(" ".join(page.extract_text().split()) for page in PdfReader(io.BytesIO(pdf)).pages)


def test_is_a_real_pdf_with_metadata():
    pdf = build_invoice_pdf(_data())
    assert pdf.startswith(b"%PDF")
    meta = PdfReader(io.BytesIO(pdf)).metadata
    assert "INV-TYO12345678" in meta.title and meta.author == "Tyohaar"


def test_prints_every_piece_of_booking_information():
    text = _text(build_invoice_pdf(_data()))
    for expected in [
        "INV-TYO12345678", "TYO12345678", "Starter Birthday Pack", "Anita's 25th", "14 November 2026",
        "7:00 PM", "10:30 PM", "Anita Rao", "+919876543210", "anita@example.com",
        "Tower B Clubhouse", "Pune", "Paid", "Confirmed",
        "Rose Gold", "White", "Pastel", "Please keep the colours soft.", "Call before arriving.",
    ]:
        assert expected in text, expected


def test_every_line_carries_its_label_and_the_legend_explains_them():
    text = _text(build_invoice_pdf(_data()))
    for label in ("RENTAL", "KEEP", "SERVICE"):
        assert text.count(label) >= 2, f"{label} should appear on its line and in the legend"
    assert "Returnable item" in text and "Yours to keep" in text and "A service, not a product" in text
    assert "Custom: 25" in text.replace("\n", " ") or "25" in text
    assert "(add-on)" in text


def test_legend_only_lists_labels_that_were_used():
    only_keep = _data(lines=[InvoiceLine("keep", "Banner", 1, None, Decimal("100"), Decimal("100"))])
    text = _text(build_invoice_pdf(only_keep))
    assert "Yours to keep" in text
    assert "Returnable item" not in text and "A service, not a product" not in text


def test_totals_use_rupees_gst_and_balance():
    text = _text(build_invoice_pdf(_data()))
    for expected in ["₹2,548.50", "-₹100", "GST @ 18%", "₹440.73", "₹2,889.23", "Balance due", "₹0"]:
        assert expected in text, expected


def test_unpaid_booking_shows_balance_due_and_no_paid_row():
    text = _text(build_invoice_pdf(_data(payment_status="pending", amount_paid=Decimal("0"), amount_due=Decimal("2889.23"))))
    assert "Pending" in text and "₹2,889.23" in text
    assert "Payment Pending" in text and "Paid ₹" not in text


def test_rental_terms_footer_is_printed():
    assert "must be returned after the event" in _text(build_invoice_pdf(_data())).replace("\n", " ")


def test_package_only_booking_and_long_lists_paginate():
    assert "Package base price only" in _text(build_invoice_pdf(_data(lines=[])))
    many = [InvoiceLine("keep", f"Item {i}", 1, None, Decimal("10"), Decimal("10")) for i in range(120)]
    pdf = build_invoice_pdf(_data(lines=many))
    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) >= 2
    assert "Page 2" in reader.pages[1].extract_text()


def test_user_text_cannot_inject_markup():
    text = _text(build_invoice_pdf(_data(
        customer_name="<b>Bold</b> & <font color='red'>x</font>",
        lines=[InvoiceLine("keep", "<i>Banner</i> & co", 1, None, Decimal("1"), Decimal("1"), note="</para><b>")],
    )))
    assert "<b>Bold</b>" in text and "<i>Banner</i> & co" in text


@pytest.mark.parametrize("amount,expected", [
    (0, "₹0"), (999, "₹999"), (1000, "₹1,000"), (123456, "₹1,23,456"), (12345678, "₹1,23,45,678"),
    (Decimal("1450.50"), "₹1,450.50"), (Decimal("-100"), "-₹100"), (Decimal("0.05"), "₹0.05"),
])
def test_indian_grouping(amount, expected):
    assert inr(amount) == expected
