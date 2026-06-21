"""Paginated response types for the common/platform domain."""

from __future__ import annotations

from app.schemas.base import CursorPage
from app.schemas.common.response import (
    StateResponse,
    CityResponse,
    BannerResponse,
    FAQResponse,
    AppSettingAdminResponse,
)

StatePage = CursorPage[StateResponse]
CityPage = CursorPage[CityResponse]
BannerPage = CursorPage[BannerResponse]
FAQPage = CursorPage[FAQResponse]
AppSettingPage = CursorPage[AppSettingAdminResponse]
