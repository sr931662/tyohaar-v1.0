"""Common/platform domain schemas — State, City, Banner, FAQ, AppSetting, Terms, PrivacyPolicy."""

from __future__ import annotations

from app.schemas.common.common import BannerType, BannerTargetAudience, LocalizedText
from app.schemas.common.create import (
    StateCreate,
    CityCreate,
    BannerCreate,
    FAQCreate,
    AppSettingCreate,
    TermsCreate,
    PrivacyPolicyCreate,
    CancellationPolicyCreate,
)
from app.schemas.common.update import (
    StateUpdate,
    CityUpdate,
    BannerUpdate,
    FAQUpdate,
    AppSettingUpdate,
    TermsUpdate,
    PrivacyPolicyUpdate,
)
from app.schemas.common.response import (
    StateResponse,
    CityResponse,
    BannerResponse,
    FAQResponse,
    AppSettingResponse,
    AppSettingAdminResponse,
    TermsResponse,
    PrivacyPolicyResponse,
    CancellationPolicyResponse,
)
from app.schemas.common.filters import (
    CityFilters,
    BannerFilters,
    FAQFilters,
    AppSettingFilters,
)
from app.schemas.common.pagination import (
    StatePage,
    CityPage,
    BannerPage,
    FAQPage,
    AppSettingPage,
)
from app.schemas.common.internal import (
    BannerInternal,
    AppSettingInternal,
    FAQFeedbackUpdate,
)

__all__ = [
    # common
    "BannerType",
    "BannerTargetAudience",
    "LocalizedText",
    # create
    "StateCreate",
    "CityCreate",
    "BannerCreate",
    "FAQCreate",
    "AppSettingCreate",
    "TermsCreate",
    "PrivacyPolicyCreate",
    "CancellationPolicyCreate",
    # update
    "StateUpdate",
    "CityUpdate",
    "BannerUpdate",
    "FAQUpdate",
    "AppSettingUpdate",
    "TermsUpdate",
    "PrivacyPolicyUpdate",
    # response
    "StateResponse",
    "CityResponse",
    "BannerResponse",
    "FAQResponse",
    "AppSettingResponse",
    "AppSettingAdminResponse",
    "TermsResponse",
    "PrivacyPolicyResponse",
    "CancellationPolicyResponse",
    # filters
    "CityFilters",
    "BannerFilters",
    "FAQFilters",
    "AppSettingFilters",
    # pagination
    "StatePage",
    "CityPage",
    "BannerPage",
    "FAQPage",
    "AppSettingPage",
    # internal
    "BannerInternal",
    "AppSettingInternal",
    "FAQFeedbackUpdate",
]
