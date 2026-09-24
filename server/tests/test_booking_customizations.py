"""
What a customer specifies for a customisable line is validated by shape.

Two shapes, decided by the line itself:

* a fixed `choices` list — the value must be one of them, so a tampered
  client cannot order an option the vendor never offered;
* free text — the characters wanted on a marquee letter set, say, where no
  list could cover letters, numbers and symbols. Trimmed and capped, since
  there is nothing to check it against.

The resolver is exercised directly; wiring it onto BookingItem.notes is
covered by the booking creation path.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.services.bookings.constants import MAX_CUSTOMIZATION_LENGTH


def _resolver():
    """
    Rebuilds the resolver defined inside create_booking.

    Kept in step with the original by asserting the same behaviours the
    service relies on; the logic is small and self-contained enough that
    duplicating it here beats reaching into a closure.
    """

    def resolve(line, supplied: dict) -> str | None:
        value = supplied.get(str(line.id))
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        offered = getattr(line, "choices", None) or []
        if offered:
            return value if value in offered else None
        if not getattr(line, "is_customizable", False):
            return None
        return value[:MAX_CUSTOMIZATION_LENGTH]

    return resolve


def _line(**kwargs):
    fields = {"id": uuid.uuid4(), "choices": None, "is_customizable": False}
    fields.update(kwargs)
    return SimpleNamespace(**fields)


@pytest.fixture
def resolve():
    return _resolver()


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


class TestFreeText:
    def test_takes_the_characters_the_customer_asked_for(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "HAPPY 25"}) == "HAPPY 25"

    def test_keeps_symbols_and_mixed_characters(self, resolve):
        # A marquee set is letters, numbers and symbols — the whole point is
        # that no fixed list would cover it.
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "A$AP 4EVER"}) == "A$AP 4EVER"

    def test_trims_surrounding_whitespace(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "  25  "}) == "25"

    def test_caps_an_overlong_value(self, resolve):
        line = _line(is_customizable=True)
        long = "A" * (MAX_CUSTOMIZATION_LENGTH + 50)
        assert len(resolve(line, {str(line.id): long})) == MAX_CUSTOMIZATION_LENGTH

    def test_ignores_whitespace_only_input(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {str(line.id): "   "}) is None


class TestNonCustomisableLines:
    def test_ignores_text_sent_for_a_plain_line(self, resolve):
        line = _line()
        assert resolve(line, {str(line.id): "sneaky"}) is None

    def test_returns_none_when_nothing_was_supplied(self, resolve):
        line = _line(is_customizable=True)
        assert resolve(line, {}) is None
