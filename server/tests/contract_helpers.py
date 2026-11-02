"""
Build a realistic, fully-populated ORM instance without a database, so a
response schema can be validated against it exactly the way a service does
(`Schema.model_validate(row)`).
"""

from __future__ import annotations

import datetime as dt
import enum
import uuid
from decimal import Decimal

from sqlalchemy import inspect as sa_inspect
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.types import (
    JSON,
    ARRAY as SAARRAY,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    Integer,
    Interval,
    LargeBinary,
    Numeric,
    String,
    Text,
    Time,
    Uuid,
)


def sample_for(column) -> object:
    t = column.type
    if isinstance(t, SAEnum):
        enum_cls = t.enum_class
        return next(iter(enum_cls)) if enum_cls else (t.enums[0] if t.enums else "x")
    if isinstance(t, (JSONB, JSON)):
        return {}
    if isinstance(t, (ARRAY, SAARRAY)):
        return []
    if isinstance(t, Boolean):
        return True
    if isinstance(t, Uuid) or "UUID" in type(t).__name__.upper():
        return uuid.uuid4()
    if isinstance(t, DateTime):
        return dt.datetime(2026, 1, 2, 3, 4, 5, tzinfo=dt.timezone.utc)
    if isinstance(t, Date):
        return dt.date(2026, 1, 2)
    if isinstance(t, Time):
        return dt.time(10, 30)
    if isinstance(t, Interval):
        return dt.timedelta(hours=1)
    if isinstance(t, Numeric):
        return Decimal("12.50")
    if isinstance(t, Float):
        return 1.5
    if isinstance(t, Integer):
        return 1
    if isinstance(t, LargeBinary):
        return b"x"
    if isinstance(t, (String, Text)):
        length = getattr(t, "length", None) or 20
        return "x" * min(length, 6)
    return "x"


def build_row(model_cls):
    """An instance with every column set to a type-appropriate sample."""
    obj = model_cls.__new__(model_cls)
    # Initialise SQLAlchemy instance state so attribute assignment works.
    from sqlalchemy.orm import attributes

    attributes.instance_state(obj) if hasattr(obj, "_sa_instance_state") else None
    row = model_cls()
    for attr in sa_inspect(model_cls).column_attrs:
        col = attr.columns[0]
        setattr(row, attr.key, sample_for(col))
    return row
