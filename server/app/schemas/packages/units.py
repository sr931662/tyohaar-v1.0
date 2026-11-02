"""
One place that maps what people type as a unit onto the fixed PackageUnit list.

Units used to be free text, so older rows hold values like "Pieces", "hrs",
"pcs" or even a quantity such as "2". The vendor form loads that stored value,
can't show it in the unit dropdown, and sends it straight back on save. Before
this, the strict enum then rejected the whole edit with a 422, which is why only
*some* items and services refused to save.
"""

from __future__ import annotations

from typing import Any

from app.models.enums import PackageUnit

# Common spellings, keyed after normalisation: lower-case, '.' removed,
# spaces turned into '_' (so "sq.ft" -> "sqft" and "sq ft" -> "sq_ft").
UNIT_SYNONYMS: dict[str, str] = {
    "piece": "pieces", "pieces": "pieces", "pc": "pieces", "pcs": "pieces",
    "nos": "pieces", "no": "pieces", "unit": "pieces", "units": "pieces",
    "set": "sets", "sets": "sets",
    "hour": "hours", "hours": "hours", "hr": "hours", "hrs": "hours",
    "day": "days", "days": "days",
    "person": "persons", "persons": "persons", "pax": "persons",
    "guest": "persons", "guests": "persons",
    "plate": "plates", "plates": "plates", "serving": "plates", "servings": "plates",
    "sqft": "sq ft", "sq_ft": "sq ft",
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
}


class _Unrecognised:
    """Sentinel: the value is a unit nobody can map (e.g. the quantity '2')."""


UNRECOGNISED = _Unrecognised()


def canonical_unit(value: Any) -> str | None | _Unrecognised:
    """
    None/blank -> None; a known spelling -> its PackageUnit value; anything
    else -> UNRECOGNISED. Enum members pass straight through.
    """
    if value is None:
        return None
    if isinstance(value, PackageUnit):
        return value.value
    text = str(value).strip()
    if not text:
        return None
    key = text.lower().replace(".", "").replace(" ", "_")
    return UNIT_SYNONYMS.get(key, UNRECOGNISED)


def normalise_unit_on_create(values: Any) -> Any:
    """For create payloads: map spellings, blank -> None, reject the rest clearly."""
    if isinstance(values, dict) and "unit" in values:
        unit = canonical_unit(values["unit"])
        if unit is UNRECOGNISED:
            allowed = ", ".join(u.value for u in PackageUnit)
            raise ValueError(f"Unrecognised unit '{values['unit']}'. Choose one of: {allowed}.")
        values = {**values, "unit": unit}
    return values


def normalise_unit_on_update(values: Any) -> Any:
    """
    For partial updates: map spellings and blank -> None as on create, but an
    unrecognisable legacy value is dropped (treated as "not changed") rather
    than rejected, so the rest of the edit saves and the stored unit is left
    exactly as it was until the vendor picks a real one.
    """
    if isinstance(values, dict) and "unit" in values:
        unit = canonical_unit(values["unit"])
        values = dict(values)
        if unit is UNRECOGNISED:
            values.pop("unit")
        else:
            values["unit"] = unit
    return values
