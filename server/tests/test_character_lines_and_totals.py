"""
Per-character lines (letters / alphanumeric) and booking totals — pure logic.

The DB-backed half (palette management, common-item billing) lives in
test_palette_and_totals_integration.py.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.enums import BalloonColorMode, CharacterSet
from app.schemas.bookings.create import BookingCreate
from app.services.bookings.constants import (
    MAX_CUSTOMIZATION_CHARACTERS,
    MAX_CUSTOMIZATION_DIGITS,
    MAX_CUSTOMIZATION_LENGTH,
)
from app.services.bookings.helpers import (
    billable_characters,
    compute_booking_amounts,
    digit_quantity,
    money,
    normalize_characters,
    resolve_customization,
    truncate_billable,
)


def _line(**kw):
    fields = {"id": uuid.uuid4(), "choices": None, "is_customizable": True, "max_quantity": None,
              "character_set": CharacterSet.DIGITS}
    fields.update(kw)
    return SimpleNamespace(**fields)


def _resolve(line, text):
    return resolve_customization(
        line, {str(line.id): text},
        max_length=MAX_CUSTOMIZATION_LENGTH,
        max_digits=MAX_CUSTOMIZATION_DIGITS,
        max_chars=MAX_CUSTOMIZATION_CHARACTERS,
    )


class TestLetters:
    def test_uppercases_and_keeps_only_letters(self):
        line = _line(character_set=CharacterSet.LETTERS)
        assert _resolve(line, "anita 30!") == "ANITA"

    def test_spaces_separate_words_and_are_not_billed(self):
        line = _line(character_set=CharacterSet.LETTERS)
        value = _resolve(line, "  happy    birthday ")
        assert value == "HAPPY BIRTHDAY"
        assert billable_characters(value) == 13
        assert digit_quantity(line, value) == 13

    def test_digits_only_input_is_rejected_for_letters(self):
        assert _resolve(_line(character_set=CharacterSet.LETTERS), "2026") is None

    def test_accents_and_symbols_are_dropped_not_ordered(self):
        line = _line(character_set=CharacterSet.LETTERS)
        assert _resolve(line, "Zoë & Ä") == "ZO"


class TestAlphanumeric:
    def test_names_and_numbers_together(self):
        line = _line(character_set=CharacterSet.ALPHANUMERIC)
        value = _resolve(line, "Anita 30")
        assert value == "ANITA 30"
        assert digit_quantity(line, value) == 7

    def test_cap_counts_billable_characters_not_spaces(self):
        line = _line(character_set=CharacterSet.ALPHANUMERIC)
        value = _resolve(line, "A B C D E F G H I J K L M N O P Q R S T U V")
        assert billable_characters(value) == MAX_CUSTOMIZATION_CHARACTERS
        assert not value.endswith(" ")

    def test_vendor_cap_truncates_the_stored_text_too(self):
        # The note on the booking and the quantity billed must agree: a vendor
        # with 5 letters in stock gets "HAPPY", billed 5, not "HAPPY BIRTHDAY"
        # billed 5.
        line = _line(character_set=CharacterSet.ALPHANUMERIC, max_quantity=5)
        value = _resolve(line, "happy birthday")
        assert value == "HAPPY"
        assert digit_quantity(line, value) == 5


class TestDigitsUnchanged:
    def test_digits_ignore_letters_and_spaces(self):
        assert _resolve(_line(), "2 0 x 2 6") == "2026"

    def test_digits_keep_the_four_digit_cap(self):
        assert _resolve(_line(), "1" * 9) == "1" * MAX_CUSTOMIZATION_DIGITS

    def test_a_line_without_the_attribute_is_digits(self):
        line = SimpleNamespace(id=uuid.uuid4(), choices=None, is_customizable=True, max_quantity=None)
        assert _resolve(line, "a1b2") == "12"

    def test_plain_line_still_ignores_everything(self):
        assert _resolve(_line(is_customizable=False, character_set=CharacterSet.ALPHANUMERIC), "ANITA") is None

    def test_choices_still_win(self):
        line = _line(choices=["1", "2"], character_set=CharacterSet.ALPHANUMERIC)
        assert _resolve(line, "ANITA") is None


def test_helpers_edges():
    assert normalize_characters("", "letters") == ""
    assert truncate_billable("AB CD", 3) == "AB C"
    assert truncate_billable("AB CD", 2) == "AB"
    assert billable_characters(None) == 0


# ── Totals ────────────────────────────────────────────────────────────────────

class TestTotals:
    def test_tax_is_on_the_post_discount_base(self):
        a = compute_booking_amounts(Decimal("10000"), Decimal("1000"))
        assert (a["taxable"], a["tax"], a["total"]) == (Decimal("9000.00"), Decimal("1620.00"), Decimal("10620.00"))

    def test_tax_rounds_half_up_to_paise(self):
        # 0.125 * 0.18 -> 0.0225 -> 0.02 ; 0.25 * 0.18 -> 0.045 -> 0.05 (half-up).
        # Banker's rounding (the Decimal default) would give 0.04.
        assert compute_booking_amounts(Decimal("0.25"), Decimal("0"))["tax"] == Decimal("0.05")

    def test_an_oversized_discount_cannot_make_a_negative_total(self):
        a = compute_booking_amounts(Decimal("500"), Decimal("900"))
        assert (a["discount"], a["taxable"], a["tax"], a["total"]) == (Decimal("500.00"),) + (Decimal("0.00"),) * 3

    def test_paise_survive(self):
        a = compute_booking_amounts(Decimal("1999.99"), Decimal("0"))
        assert a["tax"] == Decimal("360.00") and a["total"] == Decimal("2359.99")

    def test_negative_discount_is_ignored(self):
        assert compute_booking_amounts(Decimal("100"), Decimal("-5"))["discount"] == Decimal("0.00")

    def test_money_is_half_up(self):
        assert money(Decimal("2.675")) == Decimal("2.68")


# ── Balloon colour structure (1 to 4) ─────────────────────────────────────────

BASE = {"package_id": str(uuid.uuid4()), "scheduled_date": "2030-01-01"}
HEX = ["#e63946", "#d4af37", "#f48fb1", "#87ceeb", "#1e3a5f"]


@pytest.mark.parametrize("mode,count", [("single", 1), ("dual", 2), ("triple", 3), ("quad", 4)])
def test_each_mode_accepts_its_own_count(mode, count):
    booking = BookingCreate(**BASE, balloon_color_mode=mode, balloon_colors=[c.upper() for c in HEX[:count]])
    assert booking.balloon_colors == HEX[:count]  # normalised to lower-case
    assert BalloonColorMode(mode).colour_count == count


@pytest.mark.parametrize("mode,count", [("single", 2), ("dual", 3), ("triple", 2), ("quad", 5), ("quad", 3)])
def test_count_must_match_the_mode(mode, count):
    with pytest.raises(ValidationError):
        BookingCreate(**BASE, balloon_color_mode=mode, balloon_colors=HEX[:count])


def test_colours_must_differ_and_be_hex():
    with pytest.raises(ValidationError):
        BookingCreate(**BASE, balloon_color_mode="triple", balloon_colors=[HEX[0], HEX[1], HEX[0]])
    with pytest.raises(ValidationError):
        BookingCreate(**BASE, balloon_color_mode="single", balloon_colors=["red"])


def test_colours_need_a_mode_and_vice_versa():
    with pytest.raises(ValidationError):
        BookingCreate(**BASE, balloon_colors=[HEX[0]])
    with pytest.raises(ValidationError):
        BookingCreate(**BASE, balloon_color_mode="single")
    assert BookingCreate(**BASE).balloon_colors is None
