"""
GST is an admin switch, off by default. No database: the unit of work is stubbed.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.bookings.helpers import compute_booking_amounts
from app.services.common.finance_settings import (
    GST_ENABLED_KEY,
    GST_RATE,
    parse_bool,
    read_gst_enabled,
    write_gst_enabled,
)


class _Settings:
    def __init__(self, row=None):
        self.row = row
        self.created: list[dict] = []

    async def get_by_key(self, key):
        assert key == GST_ENABLED_KEY
        return self.row

    async def update(self, obj, data):
        for k, v in data.items():
            setattr(obj, k, v)
        return obj

    async def create(self, data):
        self.created.append(data)
        self.row = SimpleNamespace(is_active=True, **data)  # column default
        return self.row


def _uow(row=None):
    return SimpleNamespace(common=SimpleNamespace(settings=_Settings(row)))


def _row(value, *, active=True, default="false"):
    return SimpleNamespace(value=value, default_value=default, is_active=active)


@pytest.mark.asyncio
async def test_off_when_the_setting_does_not_exist_yet():
    assert await read_gst_enabled(_uow()) is False


@pytest.mark.asyncio
@pytest.mark.parametrize("raw,expected", [("true", True), ("True", True), ("1", True), ("false", False), ("", False), ("nonsense", False)])
async def test_reads_the_stored_value(raw, expected):
    assert await read_gst_enabled(_uow(_row(raw))) is expected


@pytest.mark.asyncio
async def test_inactive_setting_reads_as_off():
    assert await read_gst_enabled(_uow(_row("true", active=False))) is False


@pytest.mark.asyncio
async def test_null_value_falls_back_to_the_default():
    assert await read_gst_enabled(_uow(_row(None, default="true"))) is True


@pytest.mark.asyncio
async def test_write_creates_then_updates_the_same_row():
    uow, admin = _uow(), uuid.uuid4()
    await write_gst_enabled(uow, True, admin)
    created = uow.common.settings.created[0]
    assert created["key"] == GST_ENABLED_KEY and created["value"] == "true"
    assert created["default_value"] == "false"          # a fresh install stays off
    assert await read_gst_enabled(uow) is True

    await write_gst_enabled(uow, False, admin)
    assert len(uow.common.settings.created) == 1         # updated in place
    assert await read_gst_enabled(uow) is False


def test_parse_bool():
    assert parse_bool(None) is False and parse_bool(" YES ") is True


def test_zero_rate_charges_no_tax():
    a = compute_booking_amounts(Decimal("1000"), Decimal("100"), tax_rate=Decimal("0"))
    assert (a["taxable"], a["tax"], a["total"]) == (Decimal("900.00"), Decimal("0.00"), Decimal("900.00"))


def test_enabled_rate_is_eighteen_percent_of_the_post_discount_base():
    a = compute_booking_amounts(Decimal("1000"), Decimal("100"), tax_rate=GST_RATE)
    assert (a["tax"], a["total"]) == (Decimal("162.00"), Decimal("1062.00"))
