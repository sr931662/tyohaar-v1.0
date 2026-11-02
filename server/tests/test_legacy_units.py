"""
Older rows store free-text units ("hrs", "Pieces", "2"). Editing such a row
used to 422 because the form sends the stored value back. These pin the fix.
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

import pytest

from app.models.enums import PackageUnit
from app.schemas.packages.create import (
    CommonPackageItemCreate,
    CommonPackageServiceCreate,
    PackageItemCreate,
    PackageServiceCreate,
)
from app.schemas.packages.update import PackageItemUpdate, PackageServiceUpdate
from app.services.packages.service import _normalize_unit_cell

# The body the vendor form sends for the "Bartender" service in the bug report,
# with a legacy unit the dropdown could not display.
BARTENDER = {
    "name": "Bartender", "description": None, "quantity": 1, "max_quantity": 2,
    "unit": "Person", "base_price": 4999, "is_mandatory": False,
    "cover_image_url": "https://res.cloudinary.com/x/image/upload/v1/tyohaar/b.png",
    "is_customizable": False, "choices": None, "customization_prompt": None,
    "character_set": "digits", "marquee_style": "led",
}


@pytest.mark.parametrize("schema", [PackageServiceUpdate, PackageItemUpdate])
@pytest.mark.parametrize("raw,expected", [
    ("Person", PackageUnit.PERSONS), ("hrs", PackageUnit.HOURS), ("Pieces", PackageUnit.PIECES),
    ("PCS", PackageUnit.PIECES), ("sq.ft", PackageUnit.SQ_FT), ("Sq Ft", PackageUnit.SQ_FT),
    ("kg", PackageUnit.KG), ("hours", PackageUnit.HOURS),
])
def test_legacy_spellings_are_mapped_and_the_edit_saves(schema, raw, expected):
    body = schema.model_validate_json(json.dumps({**BARTENDER, "unit": raw}))  # JSON mode, like FastAPI
    assert body.model_dump(exclude_unset=True)["unit"] is expected


@pytest.mark.parametrize("schema", [PackageServiceUpdate, PackageItemUpdate])
@pytest.mark.parametrize("raw", ["2", "6 nos each", "per event"])
def test_an_unmappable_legacy_unit_no_longer_blocks_the_edit(schema, raw):
    body = schema.model_validate_json(json.dumps({**BARTENDER, "unit": raw}))
    written = body.model_dump(exclude_unset=True)
    assert "unit" not in written                       # stored unit left untouched
    assert written["name"] == "Bartender" and written["base_price"] == Decimal("4999")


@pytest.mark.parametrize("schema", [PackageServiceUpdate, PackageItemUpdate])
@pytest.mark.parametrize("raw", [None, ""])
def test_blank_or_null_unit_clears_it(schema, raw):
    assert schema.model_validate({"unit": raw}).model_dump(exclude_unset=True) == {"unit": None}


def _create_kwargs(schema):
    kw = {"name": "Bartender", "base_price": Decimal("4999")}
    if schema in (PackageItemCreate, PackageServiceCreate):
        kw["package_id"] = uuid.uuid4()
    return kw


@pytest.mark.parametrize("schema", [PackageItemCreate, CommonPackageItemCreate, PackageServiceCreate, CommonPackageServiceCreate])
def test_create_maps_spellings_and_rejects_nonsense_clearly(schema):
    assert schema(**_create_kwargs(schema), unit="Hrs").unit is PackageUnit.HOURS
    assert schema(**_create_kwargs(schema), unit="").unit is None
    with pytest.raises(ValueError, match="Unrecognised unit '2'"):
        schema(**_create_kwargs(schema), unit="2")


def test_import_uses_the_same_table():
    assert _normalize_unit_cell("Hrs") == "hours"
    with pytest.raises(ValueError):
        _normalize_unit_cell("2")
