"""Media domain schemas — Image, Video, Memory."""

from __future__ import annotations

from app.schemas.media.common import (
    ImageOwnerType,
    ModerationStatus,
    VideoTranscodingStatus,
    MemoryVisibility,
)
from app.schemas.media.create import (
    ImageCreate,
    VideoCreate,
    MemoryCreate,
)
from app.schemas.media.update import (
    ImageUpdate,
    VideoUpdate,
    MemoryUpdate,
)
from app.schemas.media.response import (
    ImageResponse,
    VideoResponse,
    MemoryResponse,
    MemoryShareResponse,
)
from app.schemas.media.filters import (
    ImageFilters,
    VideoFilters,
    MemoryFilters,
)
from app.schemas.media.pagination import (
    ImagePage,
    VideoPage,
    MemoryPage,
)
from app.schemas.media.internal import (
    ImageInternal,
    VideoInternal,
    MemoryInternal,
    MediaModerationUpdate,
)

__all__ = [
    # common
    "ImageOwnerType",
    "ModerationStatus",
    "VideoTranscodingStatus",
    "MemoryVisibility",
    # create
    "ImageCreate",
    "VideoCreate",
    "MemoryCreate",
    # update
    "ImageUpdate",
    "VideoUpdate",
    "MemoryUpdate",
    # response
    "ImageResponse",
    "VideoResponse",
    "MemoryResponse",
    "MemoryShareResponse",
    # filters
    "ImageFilters",
    "VideoFilters",
    "MemoryFilters",
    # pagination
    "ImagePage",
    "VideoPage",
    "MemoryPage",
    # internal
    "ImageInternal",
    "VideoInternal",
    "MemoryInternal",
    "MediaModerationUpdate",
]
