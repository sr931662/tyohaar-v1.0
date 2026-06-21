"""Common/platform service domain — CommonService, constants, helpers, validators, exceptions."""

from __future__ import annotations

from app.services.common.service import CommonService
from app.services.common.exceptions import (
    StateNotFoundError,
    CityNotFoundError,
    StateHasCitiesError,
    CityBelongsToWrongStateError,
    BannerNotFoundError,
    ActiveBannerLimitError,
    FAQNotFoundError,
    AppSettingNotFoundError,
    SystemSettingDeleteError,
    TermsNotFoundError,
    PrivacyPolicyNotFoundError,
)

__all__ = [
    "CommonService",
    "StateNotFoundError",
    "CityNotFoundError",
    "StateHasCitiesError",
    "CityBelongsToWrongStateError",
    "BannerNotFoundError",
    "ActiveBannerLimitError",
    "FAQNotFoundError",
    "AppSettingNotFoundError",
    "SystemSettingDeleteError",
    "TermsNotFoundError",
    "PrivacyPolicyNotFoundError",
]
