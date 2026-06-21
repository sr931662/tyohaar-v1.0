"""Common service validators — raise domain exceptions on constraint violations."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from app.models.common.app_setting import AppSetting
from app.models.common.banner import Banner
from app.models.common.city import City
from app.models.common.faq import FAQ
from app.models.common.state import State
from app.repositories.unit_of_work import UnitOfWork
from app.services.common.constants import MAX_BANNERS_ACTIVE
from app.services.common.exceptions import (
    ActiveBannerLimitError,
    BannerNotFoundError,
    AppSettingNotFoundError,
    CityBelongsToWrongStateError,
    CityNotFoundError,
    FAQNotFoundError,
    StateNotFoundError,
)


async def validate_state_exists(state_id: UUID, uow: UnitOfWork) -> State:
    """Fetch the State by PK; raise StateNotFoundError if absent."""
    state = await uow.common.states.get_by_id(state_id)
    if state is None:
        raise StateNotFoundError("State", str(state_id))
    return state


async def validate_city_exists(city_id: UUID, uow: UnitOfWork) -> City:
    """Fetch the City by PK; raise CityNotFoundError if absent."""
    city = await uow.common.cities.get_by_id(city_id)
    if city is None:
        raise CityNotFoundError("City", str(city_id))
    return city


async def validate_city_belongs_to_state(
    city_id: UUID,
    state_id: UUID,
    uow: UnitOfWork,
) -> City:
    """
    Verify that the City exists and belongs to *state_id*.
    Raise CityBelongsToWrongStateError if the city is in a different state.
    """
    city = await validate_city_exists(city_id, uow)
    if city.state_id != state_id:
        raise CityBelongsToWrongStateError(
            f"City '{city_id}' does not belong to state '{state_id}'."
        )
    return city


async def validate_banner_exists(banner_id: UUID, uow: UnitOfWork) -> Banner:
    """Fetch the Banner by PK; raise BannerNotFoundError if absent."""
    banner = await uow.common.banners.get_by_id(banner_id)
    if banner is None:
        raise BannerNotFoundError("Banner", str(banner_id))
    return banner


async def validate_faq_exists(faq_id: UUID, uow: UnitOfWork) -> FAQ:
    """Fetch the FAQ by PK; raise FAQNotFoundError if absent."""
    faq = await uow.common.faqs.get_by_id(faq_id)
    if faq is None:
        raise FAQNotFoundError("FAQ", str(faq_id))
    return faq


async def validate_setting_exists(key: str, uow: UnitOfWork) -> AppSetting:
    """Fetch the AppSetting by key; raise AppSettingNotFoundError if absent."""
    setting = await uow.common.settings.get_by_key(key)
    if setting is None:
        raise AppSettingNotFoundError("AppSetting", key)
    return setting


async def validate_active_banner_limit(uow: UnitOfWork) -> None:
    """
    Raise ActiveBannerLimitError if the number of currently-active banners
    would exceed MAX_BANNERS_ACTIVE after adding one more.
    """
    now = datetime.now(tz=timezone.utc)
    active = await uow.common.banners.find_active_now()
    if len(active) >= MAX_BANNERS_ACTIVE:
        raise ActiveBannerLimitError(
            f"Cannot activate banner: maximum of {MAX_BANNERS_ACTIVE} active banners reached."
        )
