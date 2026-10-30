"""
What a vendor's edit of a (common) service actually writes.

`exclude_unset` is what makes a PUT partial: an omitted key leaves the column
alone, an explicit null clears it. The vendor form relies on that to be able to
clear a unit, description or max quantity.
"""

from __future__ import annotations

from decimal import Decimal

from app.schemas.packages.update import PackageServiceUpdate


def _written(**body) -> dict:
    return PackageServiceUpdate(**body).model_dump(exclude_unset=True)


def test_explicit_null_clears_an_optional_column():
    assert _written(unit=None, description=None, max_quantity=None) == {
        "unit": None, "description": None, "max_quantity": None,
    }


def test_omitted_keys_are_left_alone():
    assert _written(name="DJ") == {"name": "DJ"}


def test_null_for_a_required_column_is_ignored_not_written():
    # name/quantity/base_price are NOT NULL; writing None would be a 500.
    assert _written(name=None, quantity=None, base_price=None, is_mandatory=None) == {}


def test_customisation_fields_round_trip():
    body = _written(is_customizable=True, choices=["1", "2"], customization_prompt="Which name?", character_set="letters")
    assert body["is_customizable"] is True and body["choices"] == ["1", "2"]
    assert body["customization_prompt"] == "Which name?"
    assert body["character_set"].value == "letters"


def test_a_normal_vendor_edit_payload_validates():
    body = _written(
        name="Photography", description=None, quantity=2, max_quantity=None,
        unit="hours", base_price=Decimal("5000"), is_mandatory=False, cover_image_url=None,
    )
    assert body["unit"].value == "hours" and body["description"] is None and body["max_quantity"] is None
