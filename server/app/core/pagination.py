from __future__ import annotations

import base64
from typing import Annotated

from fastapi import HTTPException, Query, status
from pydantic import BaseModel

from app.core.constants import (
    DEFAULT_CURSOR_SIZE,
    DEFAULT_PAGE_SIZE,
    MAX_CURSOR_SIZE,
    MAX_PAGE_SIZE,
    MIN_PAGE_SIZE,
)


class OffsetPaginationParams(BaseModel):
    """Validated offset/limit pagination parameters for a single request."""

    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class CursorPaginationParams(BaseModel):
    """Validated keyset (cursor) pagination parameters for a single request."""

    cursor: str | None
    page_size: int


async def get_offset_pagination(
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)."),
    ] = 1,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_PAGE_SIZE,
            description=f"Items per page (max {MAX_PAGE_SIZE}).",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> OffsetPaginationParams:
    """FastAPI dependency — resolves and validates offset pagination params."""
    return OffsetPaginationParams(page=page, page_size=page_size)


async def get_cursor_pagination(
    cursor: Annotated[
        str | None,
        Query(description="Opaque base64-encoded pagination cursor."),
    ] = None,
    page_size: Annotated[
        int,
        Query(
            ge=MIN_PAGE_SIZE,
            le=MAX_CURSOR_SIZE,
            description=f"Items per page (max {MAX_CURSOR_SIZE}).",
        ),
    ] = DEFAULT_CURSOR_SIZE,
) -> CursorPaginationParams:
    """FastAPI dependency — resolves and validates cursor pagination params."""
    if cursor is not None:
        try:
            base64.b64decode(cursor.encode(), validate=True)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid pagination cursor.",
            )
    return CursorPaginationParams(cursor=cursor, page_size=page_size)


OffsetPageDep = Annotated[OffsetPaginationParams, None]
CursorPageDep = Annotated[CursorPaginationParams, None]
