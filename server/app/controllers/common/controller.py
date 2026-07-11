"""
Common Controller — geo data, banners, FAQs, settings, terms, and privacy policy.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends

from app.core.dependencies import CommonServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.common.create import (
    AppSettingUpsert,
    BannerCreate,
    CityCreate,
    FAQCreate,
    PrivacyPolicyCreate,
    CancellationPolicyCreate,
    StateCreate,
    TermsVersionCreate,
)
from app.schemas.common.filters import AppSettingFilters, BannerFilters
from app.schemas.common.response import (
    AppSettingResponse,
    BannerResponse,
    CityResponse,
    FAQResponse,
    PrivacyPolicyResponse,
    CancellationPolicyResponse,
    StateResponse,
    TermsVersionResponse,
)
from app.schemas.common.update import BannerUpdate, CityUpdate, FAQUpdate, StateUpdate


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


# ── States ────────────────────────────────────────────────────────────────────

async def list_states(
    service: CommonServiceDep,
) -> SuccessResponse[list[StateResponse]]:
    page = await service.list_states(limit=100)
    return SuccessResponse(data=page.items, message="States retrieved.")


async def get_state(
    state_id: uuid.UUID,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.get_state(state_id=state_id)
    return SuccessResponse(data=result, message="State retrieved.")


async def create_state(
    body: StateCreate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.create_state(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="State created.")


async def update_state(
    state_id: uuid.UUID,
    body: StateUpdate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[StateResponse]:
    result = await service.update_state(state_id=state_id, data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="State updated.")


async def delete_state(
    state_id: uuid.UUID,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_state(state_id=state_id, admin_id=admin.id)
    return SuccessResponse(data=None, message="State deleted.")


# ── Cities ────────────────────────────────────────────────────────────────────

async def list_cities(
    service: CommonServiceDep,
    state_id: uuid.UUID | None = None,
) -> SuccessResponse[list[CityResponse]]:
    page = await service.list_cities(state_id=state_id, limit=500)
    return SuccessResponse(data=page.items, message="Cities retrieved.")


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
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[CityResponse]:
    result = await service.create_city(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="City created.")


async def update_city(
    city_id: uuid.UUID,
    body: CityUpdate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[CityResponse]:
    result = await service.update_city(city_id=city_id, data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="City updated.")


async def delete_city(
    city_id: uuid.UUID,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_city(city_id=city_id, admin_id=admin.id)
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
    filters: Annotated[BannerFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> CursorPaginatedResponse[BannerResponse]:
    page = await service.list_all_banners(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def create_banner(
    body: BannerCreate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.create_banner(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Banner created.")


async def update_banner(
    banner_id: uuid.UUID,
    body: BannerUpdate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.update_banner(banner_id=banner_id, data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Banner updated.")


async def delete_banner(
    banner_id: uuid.UUID,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_banner(banner_id=banner_id, admin_id=admin.id)
    return SuccessResponse(data=None, message="Banner deleted.")


async def toggle_banner_active(
    banner_id: uuid.UUID,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[BannerResponse]:
    result = await service.toggle_banner_active(banner_id=banner_id, admin_id=admin.id)
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
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[FAQResponse]:
    result = await service.create_faq(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="FAQ created.")


async def update_faq(
    faq_id: uuid.UUID,
    body: FAQUpdate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[FAQResponse]:
    result = await service.update_faq(faq_id=faq_id, data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="FAQ updated.")


async def delete_faq(
    faq_id: uuid.UUID,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_faq(faq_id=faq_id, admin_id=admin.id)
    return SuccessResponse(data=None, message="FAQ deleted.")


async def reorder_faqs(
    category: str,
    ordered_ids: list[uuid.UUID],
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[list[FAQResponse]]:
    result = await service.reorder_faqs(category=category, ordered_ids=ordered_ids, admin_id=admin.id)
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
    filters: Annotated[AppSettingFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> CursorPaginatedResponse[AppSettingResponse]:
    page = await service.list_settings(
        filters=filters, cursor=pagination.cursor, limit=pagination.page_size
    )
    return _cursor_resp(page, pagination.page_size)


async def upsert_setting(
    body: AppSettingUpsert,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[AppSettingResponse]:
    result = await service.upsert_setting(key=body.key, value=body.value, data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Setting saved.")


async def delete_setting(
    key: str,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[None]:
    await service.delete_setting(key=key, admin_id=admin.id)
    return SuccessResponse(data=None, message="Setting deleted.")


# ── Terms & Privacy ───────────────────────────────────────────────────────────

async def get_current_terms(
    service: CommonServiceDep,
) -> SuccessResponse[TermsVersionResponse]:
    result = await service.get_current_terms()
    return SuccessResponse(data=result, message="Current terms retrieved.")


async def list_terms_versions(
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> CursorPaginatedResponse[TermsVersionResponse]:
    page = await service.list_terms_versions(cursor=pagination.cursor, limit=pagination.page_size)
    return _cursor_resp(page, pagination.page_size)


async def create_terms_version(
    body: TermsVersionCreate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[TermsVersionResponse]:
    result = await service.create_terms_version(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Terms version created.")


async def get_current_privacy_policy(
    service: CommonServiceDep,
) -> SuccessResponse[PrivacyPolicyResponse]:
    result = await service.get_current_privacy_policy()
    return SuccessResponse(data=result, message="Current privacy policy retrieved.")


async def create_privacy_policy_version(
    body: PrivacyPolicyCreate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[PrivacyPolicyResponse]:
    result = await service.create_privacy_policy_version(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Privacy policy version created.")


async def get_current_cancellation_policy(
    service: CommonServiceDep,
) -> SuccessResponse[CancellationPolicyResponse]:
    result = await service.get_current_cancellation_policy()
    return SuccessResponse(data=result, message="Current cancellation policy retrieved.")


async def list_cancellation_policy_versions(
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    _admin: AdminDep,
    service: CommonServiceDep,
) -> CursorPaginatedResponse[CancellationPolicyResponse]:
    page = await service.list_cancellation_policy_versions(cursor=pagination.cursor, limit=pagination.page_size)
    return _cursor_resp(page, pagination.page_size)


async def create_cancellation_policy_version(
    body: CancellationPolicyCreate,
    admin: AdminDep,
    service: CommonServiceDep,
) -> SuccessResponse[CancellationPolicyResponse]:
    result = await service.create_cancellation_policy_version(data=body, admin_id=admin.id)
    return SuccessResponse(data=result, message="Cancellation policy version created.")
