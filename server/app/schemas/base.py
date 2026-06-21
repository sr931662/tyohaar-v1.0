"""
Shared base types and utilities for all schema modules.

All domain schemas import from here for consistent typing, validation,
and pagination primitives. Do NOT import from ORM models in this file.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ── Annotated scalar types ─────────────────────────────────────────────────────

MoneyAmount = Annotated[
    Decimal,
    Field(
        ge=Decimal("0"),
        decimal_places=2,
        description="Non-negative monetary value with 2 decimal places",
    ),
]

PhoneNumber = Annotated[
    str,
    Field(
        min_length=10,
        max_length=15,
        pattern=r"^\+[1-9]\d{9,14}$",
        description="E.164 formatted phone number (e.g. +919876543210)",
    ),
]

EmailStr = Annotated[
    str,
    Field(max_length=320, description="RFC-5322 email address"),
]

UUIDStr = Annotated[
    uuid.UUID,
    Field(description="UUID identifier"),
]

PaginationCursor = Annotated[
    str | None,
    Field(default=None, description="Opaque base64-encoded keyset pagination cursor"),
]

Latitude = Annotated[
    Decimal | None,
    Field(default=None, ge=Decimal("-90"), le=Decimal("90"), decimal_places=7),
]

Longitude = Annotated[
    Decimal | None,
    Field(default=None, ge=Decimal("-180"), le=Decimal("180"), decimal_places=7),
]

Percentage = Annotated[
    Decimal,
    Field(ge=Decimal("0"), le=Decimal("100"), decimal_places=2),
]


T = TypeVar("T")


# ── Base model config ──────────────────────────────────────────────────────────

class BaseSchema(BaseModel):
    """Root base for all Tyohaar schemas. ORM-compatible via from_attributes."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        use_enum_values=False,
        str_strip_whitespace=True,
    )


class IDSchema(BaseSchema):
    """Mixin providing the standard `id` field."""

    id: uuid.UUID


class TimestampSchema(BaseSchema):
    """Mixin providing created_at / updated_at read fields."""

    created_at: datetime
    updated_at: datetime


# ── Cursor pagination ──────────────────────────────────────────────────────────

class CursorPage(BaseSchema, Generic[T]):
    """
    Generic keyset-paginated list response.

    next_cursor is an opaque base64-encoded (created_at ISO + UUID) string.
    Clients must pass it verbatim as the `cursor` query parameter to fetch
    the next page. A None next_cursor means there are no more results.
    """

    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = Field(
        default=None,
        description="Total record count. Present only when count=true is passed.",
    )


class OffsetPage(BaseSchema, Generic[T]):
    """Offset-based paginated list for admin dashboards (simpler but slower at scale)."""

    items: list[T]
    total: int
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=200)
    pages: int


# ── Common nested types ────────────────────────────────────────────────────────

class CoordinateSchema(BaseSchema):
    """WGS-84 coordinate pair."""

    latitude: Decimal = Field(ge=Decimal("-90"), le=Decimal("90"), decimal_places=7)
    longitude: Decimal = Field(ge=Decimal("-180"), le=Decimal("180"), decimal_places=7)


class MoneySchema(BaseSchema):
    """A monetary amount with its currency."""

    amount: MoneyAmount
    currency: str = Field(description="ISO 4217 currency code")


class PriceRangeSchema(BaseSchema):
    """Min/max price range filter."""

    min_price: MoneyAmount | None = None
    max_price: MoneyAmount | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "PriceRangeSchema":
        if self.min_price is not None and self.max_price is not None:
            if self.min_price > self.max_price:
                raise ValueError("min_price must be ≤ max_price")
        return self


class DateRangeSchema(BaseSchema):
    """ISO 8601 date string range filter."""

    from_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    to_date: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")


# ── Utility helpers ────────────────────────────────────────────────────────────

def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a base64 keyset cursor into (created_at, id)."""
    try:
        raw = base64.b64decode(cursor.encode()).decode()
        ts_str, id_str = raw.split(",", 1)
        return datetime.fromisoformat(ts_str), uuid.UUID(id_str)
    except Exception as exc:
        raise ValueError(f"Invalid pagination cursor: {exc}") from exc


def encode_cursor(created_at: datetime, record_id: uuid.UUID) -> str:
    """Encode a (created_at, id) pair as a base64 keyset cursor."""
    raw = f"{created_at.isoformat()},{record_id}"
    return base64.b64encode(raw.encode()).decode()
