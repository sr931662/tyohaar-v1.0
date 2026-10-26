"""Balloon colour palette schemas."""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema

_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class BalloonColorBase(BaseSchema):
    @field_validator("hex_code", check_fields=False)
    @classmethod
    def _hex(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX.match(v.strip()):
            raise ValueError("Use a 6-digit hex colour such as #D4AF37.")
        return v.strip().upper()


class BalloonColorCreate(BalloonColorBase):
    name: str = Field(min_length=2, max_length=60)
    hex_code: str
    is_active: bool = True


class BalloonColorUpdate(BalloonColorBase):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    hex_code: str | None = None
    is_active: bool | None = None


class BalloonColorReorder(BaseSchema):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class BalloonColorResponse(BaseSchema):
    id: uuid.UUID
    name: str
    hex_code: str
    sort_order: int
    is_active: bool
    created_at: datetime


class BalloonFinishCreate(BaseSchema):
    name: str = Field(min_length=2, max_length=60)
    is_active: bool = True


class BalloonFinishUpdate(BaseSchema):
    name: str | None = Field(default=None, min_length=2, max_length=60)
    is_active: bool | None = None


class BalloonFinishResponse(BaseSchema):
    id: uuid.UUID
    name: str
    sort_order: int
    is_active: bool
    created_at: datetime
