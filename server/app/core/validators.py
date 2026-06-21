from __future__ import annotations

import re
import uuid
from typing import Annotated

from fastapi import HTTPException, Query, status

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")


def validate_e164_phone(phone: str) -> str:
    """Validate and return a normalized E.164 phone number. Raises 422 on failure."""
    normalized = phone.strip()
    if not _E164_RE.match(normalized):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "field": "phone",
                "message": "Phone must be in E.164 format (e.g. +919876543210).",
            },
        )
    return normalized


def parse_uuid_param(value: str, field_name: str = "id") -> uuid.UUID:
    """Parse a path-parameter string as UUID. Raises 400 on failure."""
    try:
        return uuid.UUID(value)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{field_name}' must be a valid UUID.",
        )


async def get_search_query(
    q: Annotated[
        str | None,
        Query(min_length=1, max_length=200, description="Full-text search query"),
    ] = None,
) -> str | None:
    """FastAPI dependency — extracts and returns the optional ?q= search query."""
    return q
