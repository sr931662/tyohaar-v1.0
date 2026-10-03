"""
What a customer specifies for a customisable line, and what it costs.

Two shapes, decided by the line itself:

* a fixed `choices` list — the value must be one of them, so a tampered
  client cannot order an option the vendor never offered;
* no `choices` — the line takes a NUMBER. A vendor stocks digits as physical
  characters (a marquee letter set), so "20" is a 2 and a 0: two characters,
  billed at the line's base price each.

The real helpers are exercised here, not a copy of them — create_booking calls
these same functions. Wiring the resolved value onto BookingItem.notes is
covered by the booking creation path.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.bookings.constants import (
    MAX_CUSTOMIZATION_DIGITS,
    MAX_CUSTOMIZATION_LENGTH,
)
from app.services.bookings.helpers import (
    digit_quantity,
    is_numeric_line,
    resolve_customization,
)


def _line(**kwargs):
    fields = {
        "id": uuid.uuid4(),
        "choices": None,
        "is_customizable": False,
        "max_quantity": None,
    }
    fields.update(kwargs)
    return SimpleNamespace(**fields)


@pytest.fixture
def resolve():
    def _resolve(line, supplied: dict) -> str | None:
        return resolve_customization(
            line,
            supplied,
            max_length=MAX_CUSTOMIZATION_LENGTH,
            max_digits=MAX_CUSTOMIZATION_DIGITS,
        )

    return _resolve


class TestFixedChoices:
    def test_accepts_an_offered_value(self, resolve):
        line = _line(choices=["1", "2", "3"])
        assert resolve(line, {str(line.id): "2"}) == "2"

    def test_rejects_a_value_the_vendor_never_offered(self, resolve):
        line = _line(choices=["1", "2", "3"])
        assert resolve(line, {str(line.id): "99"}) is None

    def test_choices_win_over_free_text(self, resolve):
        # is_customizable does not loosen a line that defines its options.
        line = _line(choices=["1", "2"], is_customizable=True)
        assert resolve(line, {str(line.id): "anything"}) is None

    def test_is_not_a_numeric_line(self):
        assert is_numeric_line(_line(choices=["1", "2"], is_customizable=True)) is False


class TestNumericLines:
    def test_takes_the_number_the_customer_set(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "25"}) == "25"

    def test_strips_everything_that_is_not_a_digit(self, resolve):
        # The vendor's characters are stocked digits — letters and symbols are
        # dropped rather than ordered as something that cannot be supplied.
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "A$AP 4EVER"}) == "4"

    def test_keeps_a_leading_zero(self, resolve):
        # "08" is two characters, not the number eight.
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "08"}) == "08"

    def test_trims_surrounding_whitespace(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "  25  "}) == "25"

    def test_caps_the_digit_count(self, resolve):
        line = _line(is_customizable=True)
        long = "1" * (MAX_CUSTOMIZATION_DIGITS + 5)
        assert resolve(line, {str(line.id): long}) == "1" * MAX_CUSTOMIZATION_DIGITS

    def test_ignores_input_with_no_digits_at_all(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "HAPPY"}) is None

    def test_ignores_whitespace_only_input(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "   "}) is None

    def test_is_a_numeric_line(self):
        assert is_numeric_line(_line(is_customizable=True)) is True
        assert is_numeric_line(_line(is_customizable=True, choices=[])) is True


class TestPerCharacterPricing:
    def test_one_character_per_digit(self):
        # The case this was built for: a 25th anniversary is a 2 and a 5, so
        # a 399-a-piece marquee bills 798.
        line = _line(is_customizable=True)
        assert digit_quantity(line, "25") == 2

    def test_a_single_digit_costs_one_character(self):
        assert digit_quantity(_line(is_customizable=True), "7") == 1

    def test_a_repeated_digit_is_still_two_characters(self):
        # The vendor brings two physical 1s for "11".
        assert digit_quantity(_line(is_customizable=True), "11") == 2

    def test_a_year_costs_four_characters(self):
        assert digit_quantity(_line(is_customizable=True), "2026") == 4

    def test_respects_the_vendors_cap(self):
        # A vendor who owns three characters cannot supply four.
        line = _line(is_customizable=True, max_quantity=3)
        assert digit_quantity(line, "2026") == 3

    def test_never_falls_below_one_character(self):
        line = _line(is_customizable=True, max_quantity=0)
        assert digit_quantity(line, "25") == 1


class TestNonCustomisableLines:
    def test_ignores_text_sent_for_a_plain_line(self, resolve):
        line = _line()
        assert resolve(line, {str(line.id): "sneaky"}) is None

    def test_ignores_digits_sent_for_a_plain_line(self, resolve):
        # Otherwise a tampered client could turn any line into a per-character
        # one and move its quantity.
        line = _line()
        assert resolve(line, {str(line.id): "2026"}) is None

    def test_returns_none_when_nothing_was_supplied(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {}) is None

    def test_is_not_a_numeric_line(self):
        assert is_numeric_line(_line()) is False
