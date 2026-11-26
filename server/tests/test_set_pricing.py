"""A set is priced as one thing: its size must never multiply the price."""

from decimal import Decimal

import pytest

from app.schemas.packages.create import CommonPackageItemCreate
from app.services.bookings.invoice_pdf import InvoiceLine
from app.services.packages.service import _coerce_item_import_row


def test_set_size_is_stored_apart_from_the_billed_quantity():
    item = CommonPackageItemCreate(name="Balloons", unit="sets", pieces_per_set=200, base_price="999")
    assert item.quantity == 1
    assert item.pieces_per_set == 200
    assert item.base_price * item.quantity == Decimal("999")


@pytest.mark.parametrize("quantity, unit, size, label", [
    (1, "sets", 200, "1 set of 200"),
    (3, "sets", 200, "3 sets of 200"),
    (2, "sets", None, "2 sets"),
    (6, "hours", None, "6 hours"),
    (4, None, None, "4"),
])
def test_quantity_label(quantity, unit, size, label):
    line = InvoiceLine(
        kind="keep", name="x", quantity=quantity, unit=unit, pieces_per_set=size,
        unit_price=Decimal("1"), total=Decimal("1"),
    )
    assert line.quantity_label == label


def test_sheet_without_the_column_leaves_the_stored_set_size_alone():
    row = {"name": "Balloons", "base_price": "999", "unit": "sets"}
    assert "pieces_per_set" not in _coerce_item_import_row(row, is_package_item=False)
    row["pieces_per_set"] = "200"
    assert _coerce_item_import_row(row, is_package_item=False)["pieces_per_set"] == 200
