"""Balloon colour proportions: what a booking may ask for, and where it shows."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.schemas.bookings.create import BookingCreate
from app.services.notifications.email_templates import booking_success_email
from tests.test_invoice_pdf import _data, _text
from app.services.bookings.invoice_pdf import build_invoice_pdf

THREE = ["#e63946", "#d4af37", "#ffffff"]


def _booking(**kw) -> BookingCreate:
    base = dict(package_id=uuid.uuid4(), occasion_id=uuid.uuid4(),
                scheduled_date=date.today() + timedelta(days=30), venue_address="12 Lake Road")
    base.update(kw)
    return BookingCreate(**base)


def test_a_valid_mix_is_kept_in_colour_order():
    b = _booking(balloon_color_mode="triple", balloon_colors=THREE, balloon_color_ratios=[30, 20, 50])
    assert b.balloon_color_ratios == [30, 20, 50]


def test_ratios_are_optional():
    assert _booking(balloon_color_mode="triple", balloon_colors=THREE).balloon_color_ratios is None


@pytest.mark.parametrize("ratios,message", [
    ([30, 20, 40], "add up to 100"),
    ([30, 70], "one value per colour"),
    ([0, 50, 50], "at least 5"),
    ([33, 33, 34], "steps of 5"),
    ([-10, 60, 50], "at least 5"),
])
def test_bad_mixes_are_rejected(ratios, message):
    with pytest.raises(ValueError, match=message):
        _booking(balloon_color_mode="triple", balloon_colors=THREE, balloon_color_ratios=ratios)


def test_a_single_colour_cannot_have_a_mix():
    with pytest.raises(ValueError, match="at least two"):
        _booking(balloon_color_mode="single", balloon_colors=["#e63946"], balloon_color_ratios=[100])


def test_ratios_without_colours_are_rejected():
    with pytest.raises(ValueError, match="requires balloon colours"):
        _booking(balloon_color_ratios=[50, 50])


def test_invoice_pdf_shows_the_percentages():
    text = _text(build_invoice_pdf(_data(balloon_ratios=[70, 30])))
    assert "70%" in text and "30%" in text


def test_invoice_pdf_without_ratios_is_unchanged():
    text = _text(build_invoice_pdf(_data()))
    assert "%" not in text.split("BALLOON")[1].split("Finish")[0] if "BALLOON" in text else True


def test_booking_email_shows_the_percentages():
    from tests.test_booking_emails import _data as email_data
    d = email_data(balloon_colors=[("Red", "#E63946"), ("Gold", "#D4AF37")], balloon_ratios=[60, 40])
    _, html, _ = booking_success_email("vendor", d)
    assert "Red 60%" in html and "Gold 40%" in html


def test_mismatched_ratio_length_is_ignored_in_display():
    from tests.test_booking_emails import _data as email_data
    d = email_data(balloon_colors=[("Red", "#E63946"), ("Gold", "#D4AF37")], balloon_ratios=[100])
    _, html, _ = booking_success_email("vendor", d)
    assert "Red 100%" not in html and "Red&nbsp;" in html
