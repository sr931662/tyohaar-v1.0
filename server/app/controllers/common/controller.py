"""
Common Controller — geo data, banners, FAQs, settings, terms, and privacy policy.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.dependencies import CommonServiceDep
from app.core.pagination import OffsetPaginationParams, get_offset_pagination
from app.core.permissions import AdminDep
from app.core.responses import PaginatedResponse, SuccessResponse
from app.schemas.common.create import (
    AppSettingUpsert,
    BannerCreate,
    CityCreate,
    FAQCreate,
    PrivacyPolicyCreate,
    StateCreate,
    TermsVersionCreate,
)
from app.schemas.common.response import (
    AppSettingResponse,
    BannerResponse,
    CityResponse,
    FAQResponse,
    PrivacyPolicyResponse,
    StateResponse,
    TermsVersionResponse,
)
from app.schemas.common.update import BannerUpdate, CityUpdate, FAQUpdate, StateUpdate


# ── States ────────────────────────────────────────────────────────────────────

async def list_states(
    service: CommonServiceDep,
) -> SuccessResponse[list[StateResponse]]:
    states = await service.list_states()
    return SuccessResponse(data=states, message="States retrieved.")


async def get_state(
    state_id: uuid.UUID,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.get_state(state_id=state_id)
    return SuccessResponse(data=result, message="State retrieved.")


async def create_state(
    body: StateCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.create_state(data=body)
    return SuccessResponse(data=result, message="State created.")


async def update_state(
    state_id: uuid.UUID,
    body: StateUpdate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.update_state(state_id=state_id, data=body)
    return SuccessResponse(data=result, message="State updated.")


async def delete_state(
    state_id: uuid.UUID,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_state(state_id=state_id)
    return SuccessResponse(data=None, message="State deleted.")


# ── Cities ────────────────────────────────────────────────────────────────────

async def list_cities(
    service: CommonServiceDep,
    state_id: uuid.UUID | None = None,
) -> SuccessResponse[list[CityResponse]]:
    cities = await service.list_cities(state_id=state_id)
    return SuccessResponse(data=cities, message="Cities retrieved.")


async def get_city(
    city_id: uuid.UUID,
    service: CommonServiceDep,
) -> SuccessResponse[CityResponse]:
    result = await service.get_city(city_id=city_id)
    return SuccessResponse(data=result, message="City retrieved.")


async def search_cities(
    q: str,
    service: CommonServiceDep,
) -> SuccessResponse[list[CityResponse]]:
    cities = await service.search_cities(query=q)
    return SuccessResponse(data=cities, message="Cities found.")


async def create_city(
    body: CityCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[CityResponse]:
    result = await service.create_city(data=body)
    return SuccessResponse(data=result, message="City created.")


async def update_city(
    city_id: uuid.UUID,
    body: CityUpdate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[CityResponse]:
    result = await service.update_city(city_id=city_id, data=body)
    return SuccessResponse(data=result, message="City updated.")


async def delete_city(
    city_id: uuid.UUID,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_city(city_id=city_id)
    return SuccessResponse(data=None, message="City deleted.")


# ── Banners ───────────────────────────────────────────────────────────────────

async def list_active_banners(
    service: CommonServiceDep,
) -> SuccessResponse[list[BannerResponse]]:
    banners = await service.list_active_banners()
    return SuccessResponse(data=banners, message="Banners retrieved.")


async def get_banner(
    banner_id: uuid.UUID,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.get_banner(banner_id=banner_id)
    return SuccessResponse(data=result, message="Banner retrieved.")


async def list_all_banners(
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[list[BannerResponse]]:
    banners = await service.list_all_banners()
    return SuccessResponse(data=banners, message="All banners retrieved.")


async def create_banner(
    body: BannerCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.create_banner(data=body)
    return SuccessResponse(data=result, message="Banner created.")


async def update_banner(
    banner_id: uuid.UUID,
    body: BannerUpdate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.update_banner(banner_id=banner_id, data=body)
    return SuccessResponse(data=result, message="Banner updated.")


async def delete_banner(
    banner_id: uuid.UUID,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_banner(banner_id=banner_id)
    return SuccessResponse(data=None, message="Banner deleted.")


async def toggle_banner_active(
    banner_id: uuid.UUID,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.toggle_banner_active(banner_id=banner_id)
    return SuccessResponse(data=result, message="Banner toggled.")


# ── FAQs ──────────────────────────────────────────────────────────────────────

async def list_faqs(
    service: CommonServiceDep,
) -> SuccessResponse[list[FAQResponse]]:
    faqs = await service.list_faqs()
    return SuccessResponse(data=faqs, message="FAQs retrieved.")


async def get_faq(
    faq_id: uuid.UUID,
    service: CommonServiceDep,
) -> SuccessResponse[FAQResponse]:
    result = await service.get_faq(faq_id=faq_id)
    return SuccessResponse(data=result, message="FAQ retrieved.")


async def create_faq(
    body: FAQCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[FAQResponse]:
    result = await service.create_faq(data=body)
    return SuccessResponse(data=result, message="FAQ created.")


async def update_faq(
    faq_id: uuid.UUID,
    body: FAQUpdate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[FAQResponse]:
    result = await service.update_faq(faq_id=faq_id, data=body)
    return SuccessResponse(data=result, message="FAQ updated.")


async def delete_faq(
    faq_id: uuid.UUID,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_faq(faq_id=faq_id)
    return SuccessResponse(data=None, message="FAQ deleted.")


async def reorder_faqs(
    ordered_ids: list[uuid.UUID],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[list[FAQResponse]]:
    result = await service.reorder_faqs(ordered_ids=ordered_ids)
    return SuccessResponse(data=result, message="FAQs reordered.")


# ── App Settings ──────────────────────────────────────────────────────────────

async def get_setting(
    key: str,
    service: CommonServiceDep,
) -> SuccessResponse[AppSettingResponse]:
    result = await service.get_setting(key=key)
    return SuccessResponse(data=result, message="Setting retrieved.")


async def get_setting_admin(
    key: str,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[AppSettingResponse]:
    result = await service.get_setting_admin(key=key)
    return SuccessResponse(data=result, message="Setting retrieved.")


async def list_settings(
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[list[AppSettingResponse]]:
    settings = await service.list_settings()
    return SuccessResponse(data=settings, message="Settings retrieved.")


async def upsert_setting(
    body: AppSettingUpsert,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[AppSettingResponse]:
    result = await service.upsert_setting(data=body)
    return SuccessResponse(data=result, message="Setting saved.")


async def delete_setting(
    key: str,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_setting(key=key)
    return SuccessResponse(data=None, message="Setting deleted.")


# ── Terms & Privacy ───────────────────────────────────────────────────────────

async def get_current_terms(
    service: CommonServiceDep,
) -> SuccessResponse[TermsVersionResponse]:
    result = await service.get_current_terms()
    return SuccessResponse(data=result, message="Current terms retrieved.")


async def list_terms_versions(
    pagination: Annotated[OffsetPaginationParams, Depends(get_offset_pagination)],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> PaginatedResponse[TermsVersionResponse]:
    result = await service.list_terms_versions(
        page=pagination.page, page_size=pagination.page_size
    )
    return result


async def create_terms_version(
    body: TermsVersionCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[TermsVersionResponse]:
    result = await service.create_terms_version(data=body)
    return SuccessResponse(data=result, message="Terms version created.")


async def get_current_privacy_policy(
    service: CommonServiceDep,
) -> SuccessResponse[PrivacyPolicyResponse]:
    result = await service.get_current_privacy_policy()
    return SuccessResponse(data=result, message="Current privacy policy retrieved.")


async def create_privacy_policy_version(
    body: PrivacyPolicyCreate,
    _admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[PrivacyPolicyResponse]:
    result = await service.create_privacy_policy_version(data=body)
    return SuccessResponse(data=result, message="Privacy policy version created.")
