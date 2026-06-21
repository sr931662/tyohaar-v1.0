"""Paginated response types for the media domain."""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.media.response import ImageResponse, VideoResponse, MemoryResponse

ImagePage = CursorPage[ImageResponse]
VideoPage = CursorPage[VideoResponse]
MemoryPage = CursorPage[MemoryResponse]
