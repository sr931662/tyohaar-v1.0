"""
marquee_style is presentation only: it must default to LED so every existing
line is unchanged, round-trip through the API schemas, and be stored as the
enum member *name* in a column wide enough for it.
"""

from __future__ import annotations

import re
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.enums import MarqueeStyle
from app.models.packages.package_item import PackageItem
from app.models.packages.package_service import PackageServiceLine
from app.schemas.packages.create import (
    CommonPackageItemCreate,
    CommonPackageServiceCreate,
    PackageItemCreate,
    PackageServiceCreate,
)
from app.schemas.packages.update import PackageItemUpdate, PackageServiceUpdate

MIGRATION = Path(__file__).resolve().parents[1] / "migrations/versions/c4e7a19b0d52_marquee_style_on_character_lines.py"


def _stored(column, member):
    processor = column.type.bind_processor(None) or (lambda v: v)
    return processor(member)


@pytest.mark.parametrize("model", [PackageItem, PackageServiceLine])
def test_column_stores_member_names_and_defaults_to_led(model):
    column = model.__table__.c.marquee_style
    assert _stored(column, MarqueeStyle.LED) == "LED"
    assert _stored(column, MarqueeStyle.BALLOON) == "BALLOON"
    assert column.nullable is False
    assert str(column.server_default.arg) == "LED"
    assert column.type.length >= len("BALLOON")


def test_migration_matches_the_models():
    text = MIGRATION.read_text(encoding="utf-8")
    assert 'server_default="LED"' in text
    width = int(re.search(r"sa\.String\((\d+)\)", text).group(1))
    assert width >= len("BALLOON")
    assert "package_items" in text and "package_services" in text


@pytest.mark.parametrize(
    "schema,kwargs",
    [
        (PackageItemCreate, {"package_id": uuid.uuid4(), "name": "Letters", "base_price": Decimal("10")}),
        (CommonPackageItemCreate, {"name": "Letters", "base_price": Decimal("10")}),
        (PackageServiceCreate, {"package_id": uuid.uuid4(), "name": "Letters", "base_price": Decimal("10")}),
        (CommonPackageServiceCreate, {"name": "Letters", "base_price": Decimal("10")}),
    ],
)
def test_create_defaults_to_led_and_accepts_balloon(schema, kwargs):
    assert schema(**kwargs).marquee_style is MarqueeStyle.LED
    assert schema(**kwargs, marquee_style="balloon").marquee_style is MarqueeStyle.BALLOON


def test_unknown_style_is_rejected():
    with pytest.raises(ValueError):
        PackageServiceCreate(package_id=uuid.uuid4(), name="x", base_price=Decimal("1"), marquee_style="neon")


@pytest.mark.parametrize("schema", [PackageItemUpdate, PackageServiceUpdate])
def test_update_is_partial(schema):
    assert schema(name="x").model_dump(exclude_unset=True) == {"name": "x"}
    assert schema(marquee_style="balloon").model_dump(exclude_unset=True)["marquee_style"] is MarqueeStyle.BALLOON


def test_null_style_on_a_service_update_is_ignored_not_written():
    assert PackageServiceUpdate(marquee_style=None).model_dump(exclude_unset=True) == {}
