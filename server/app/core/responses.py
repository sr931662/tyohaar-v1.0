from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SuccessResponse(BaseModel, Generic[T]):
    data: T
    message: str = "Success"


class PaginatedMeta(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: PaginatedMeta


class CursorMeta(BaseModel):
    cursor: str | None = None
    has_next: bool
    page_size: int


class CursorPaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: CursorMeta


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
