"""
Common Routes — geo data, banners, FAQs, settings, terms, and privacy policy.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.controllers.common import controller as ctrl
from app.core.responses import PaginatedResponse, SuccessResponse
from app.schemas.common.response import (
    AppSettingResponse,
    BannerResponse,
    CityResponse,
    FAQResponse,
    PrivacyPolicyResponse,
    StateResponse,
    TermsVersionResponse,
)

router = APIRouter(prefix="/common", tags=["Common"])

# ── States ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/states",
    ctrl.list_states,
    methods=["GET"],
    response_model=SuccessResponse[list[StateResponse]],
    status_code=status.HTTP_200_OK,
    summary="List States",
    description="Return all active states/provinces. Public endpoint.",
    operation_id="common_list_states",
)

router.add_api_route(
    "/states",
    ctrl.create_state,
    methods=["POST"],
    response_model=SuccessResponse[StateResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create State (Admin)",
    description="Create a new state/province record. Admin access required.",
    operation_id="common_create_state",
)

router.add_api_route(
    "/states/{state_id}",
    ctrl.get_state,
    methods=["GET"],
    response_model=SuccessResponse[StateResponse],
    status_code=status.HTTP_200_OK,
    summary="Get State",
    description="Return a single state by ID. Public endpoint.",
    operation_id="common_get_state",
)

router.add_api_route(
    "/states/{state_id}",
    ctrl.update_state,
    methods=["PUT"],
    response_model=SuccessResponse[StateResponse],
    status_code=status.HTTP_200_OK,
    summary="Update State (Admin)",
    description="Update a state record. Admin access required.",
    operation_id="common_update_state",
)

router.add_api_route(
    "/states/{state_id}",
    ctrl.delete_state,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete State (Admin)",
    description="Soft-delete a state record. Admin access required.",
    operation_id="common_delete_state",
)

# ── Cities ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/cities/search",
    ctrl.search_cities,
    methods=["GET"],
    response_model=SuccessResponse[list[CityResponse]],
    status_code=status.HTTP_200_OK,
    summary="Search Cities",
    description="Full-text search for cities by name. Pass `q` as a query parameter. Public endpoint.",
    operation_id="common_search_cities",
)

router.add_api_route(
    "/cities",
    ctrl.list_cities,
    methods=["GET"],
    response_model=SuccessResponse[list[CityResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Cities",
    description="Return all cities, optionally filtered by `state_id`. Public endpoint.",
    operation_id="common_list_cities",
)

router.add_api_route(
    "/cities",
    ctrl.create_city,
    methods=["POST"],
    response_model=SuccessResponse[CityResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create City (Admin)",
    description="Create a new city record. Admin access required.",
    operation_id="common_create_city",
)

router.add_api_route(
    "/cities/{city_id}",
    ctrl.get_city,
    methods=["GET"],
    response_model=SuccessResponse[CityResponse],
    status_code=status.HTTP_200_OK,
    summary="Get City",
    description="Return a single city by ID. Public endpoint.",
    operation_id="common_get_city",
)

router.add_api_route(
    "/cities/{city_id}",
    ctrl.update_city,
    methods=["PUT"],
    response_model=SuccessResponse[CityResponse],
    status_code=status.HTTP_200_OK,
    summary="Update City (Admin)",
    description="Update a city record. Admin access required.",
    operation_id="common_update_city",
)

router.add_api_route(
    "/cities/{city_id}",
    ctrl.delete_city,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete City (Admin)",
    description="Soft-delete a city record. Admin access required.",
    operation_id="common_delete_city",
)

# ── Banners ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/banners/admin/all",
    ctrl.list_all_banners,
    methods=["GET"],
    response_model=SuccessResponse[list[BannerResponse]],
    status_code=status.HTTP_200_OK,
    summary="List All Banners (Admin)",
    description="Return all banners including inactive ones. Admin access required.",
    operation_id="common_list_all_banners",
)

router.add_api_route(
    "/banners",
    ctrl.list_active_banners,
    methods=["GET"],
    response_model=SuccessResponse[list[BannerResponse]],
    status_code=status.HTTP_200_OK,
    summary="List Active Banners",
    description="Return all currently active promotional banners. Public endpoint.",
    operation_id="common_list_active_banners",
)

router.add_api_route(
    "/banners",
    ctrl.create_banner,
    methods=["POST"],
    response_model=SuccessResponse[BannerResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Banner (Admin)",
    description="Create a new promotional banner. Admin access required.",
    operation_id="common_create_banner",
)

router.add_api_route(
    "/banners/{banner_id}",
    ctrl.get_banner,
    methods=["GET"],
    response_model=SuccessResponse[BannerResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Banner",
    description="Return a single banner by ID. Public endpoint.",
    operation_id="common_get_banner",
)

router.add_api_route(
    "/banners/{banner_id}",
    ctrl.update_banner,
    methods=["PUT"],
    response_model=SuccessResponse[BannerResponse],
    status_code=status.HTTP_200_OK,
    summary="Update Banner (Admin)",
    description="Update a banner record. Admin access required.",
    operation_id="common_update_banner",
)

router.add_api_route(
    "/banners/{banner_id}",
    ctrl.delete_banner,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete Banner (Admin)",
    description="Soft-delete a banner. Admin access required.",
    operation_id="common_delete_banner",
)

router.add_api_route(
    "/banners/{banner_id}/toggle",
    ctrl.toggle_banner_active,
    methods=["PATCH"],
    response_model=SuccessResponse[BannerResponse],
    status_code=status.HTTP_200_OK,
    summary="Toggle Banner Active (Admin)",
    description="Toggle the active/inactive state of a banner. Admin access required.",
    operation_id="common_toggle_banner_active",
)

# ── FAQs ──────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/faqs/reorder",
    ctrl.reorder_faqs,
    methods=["POST"],
    response_model=SuccessResponse[list[FAQResponse]],
    status_code=status.HTTP_200_OK,
    summary="Reorder FAQs (Admin)",
    description="Set the display order of FAQs by supplying an ordered list of IDs. Admin access required.",
    operation_id="common_reorder_faqs",
)

router.add_api_route(
    "/faqs",
    ctrl.list_faqs,
    methods=["GET"],
    response_model=SuccessResponse[list[FAQResponse]],
    status_code=status.HTTP_200_OK,
    summary="List FAQs",
    description="Return all active FAQs in display order. Public endpoint.",
    operation_id="common_list_faqs",
)

router.add_api_route(
    "/faqs",
    ctrl.create_faq,
    methods=["POST"],
    response_model=SuccessResponse[FAQResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create FAQ (Admin)",
    description="Create a new FAQ entry. Admin access required.",
    operation_id="common_create_faq",
)

router.add_api_route(
    "/faqs/{faq_id}",
    ctrl.get_faq,
    methods=["GET"],
    response_model=SuccessResponse[FAQResponse],
    status_code=status.HTTP_200_OK,
    summary="Get FAQ",
    description="Return a single FAQ by ID. Public endpoint.",
    operation_id="common_get_faq",
)

router.add_api_route(
    "/faqs/{faq_id}",
    ctrl.update_faq,
    methods=["PUT"],
    response_model=SuccessResponse[FAQResponse],
    status_code=status.HTTP_200_OK,
    summary="Update FAQ (Admin)",
    description="Update a FAQ entry. Admin access required.",
    operation_id="common_update_faq",
)

router.add_api_route(
    "/faqs/{faq_id}",
    ctrl.delete_faq,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete FAQ (Admin)",
    description="Soft-delete a FAQ entry. Admin access required.",
    operation_id="common_delete_faq",
)

# ── App settings ──────────────────────────────────────────────────────────────

router.add_api_route(
    "/settings",
    ctrl.list_settings,
    methods=["GET"],
    response_model=SuccessResponse[list[AppSettingResponse]],
    status_code=status.HTTP_200_OK,
    summary="List App Settings (Admin)",
    description="Return all application settings. Admin access required.",
    operation_id="common_list_settings",
)

router.add_api_route(
    "/settings",
    ctrl.upsert_setting,
    methods=["PUT"],
    response_model=SuccessResponse[AppSettingResponse],
    status_code=status.HTTP_200_OK,
    summary="Upsert App Setting (Admin)",
    description="Create or update an application setting. Admin access required.",
    operation_id="common_upsert_setting",
)

router.add_api_route(
    "/settings/admin/{key}",
    ctrl.get_setting_admin,
    methods=["GET"],
    response_model=SuccessResponse[AppSettingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get App Setting (Admin)",
    description="Return a single setting including internal metadata. Admin access required.",
    operation_id="common_get_setting_admin",
)

router.add_api_route(
    "/settings/{key}",
    ctrl.get_setting,
    methods=["GET"],
    response_model=SuccessResponse[AppSettingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get App Setting",
    description="Return a public application setting by key. Public endpoint.",
    operation_id="common_get_setting",
)

router.add_api_route(
    "/settings/{key}",
    ctrl.delete_setting,
    methods=["DELETE"],
    response_model=SuccessResponse[None],
    status_code=status.HTTP_200_OK,
    summary="Delete App Setting (Admin)",
    description="Delete an application setting by key. Admin access required.",
    operation_id="common_delete_setting",
)

# ── Terms & Conditions ────────────────────────────────────────────────────────

router.add_api_route(
    "/terms",
    ctrl.get_current_terms,
    methods=["GET"],
    response_model=SuccessResponse[TermsVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current Terms",
    description="Return the currently active Terms & Conditions version. Public endpoint.",
    operation_id="common_get_current_terms",
)

router.add_api_route(
    "/terms/versions",
    ctrl.list_terms_versions,
    methods=["GET"],
    response_model=PaginatedResponse[TermsVersionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Terms Versions (Admin)",
    description="Return paginated history of all Terms & Conditions versions. Admin access required.",
    operation_id="common_list_terms_versions",
)

router.add_api_route(
    "/terms/versions",
    ctrl.create_terms_version,
    methods=["POST"],
    response_model=SuccessResponse[TermsVersionResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Terms Version (Admin)",
    description="Publish a new Terms & Conditions version. Admin access required.",
    operation_id="common_create_terms_version",
)

# ── Privacy Policy ────────────────────────────────────────────────────────────

router.add_api_route(
    "/privacy-policy",
    ctrl.get_current_privacy_policy,
    methods=["GET"],
    response_model=SuccessResponse[PrivacyPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="Get Current Privacy Policy",
    description="Return the currently active Privacy Policy version. Public endpoint.",
    operation_id="common_get_current_privacy_policy",
)

router.add_api_route(
    "/privacy-policy/versions",
    ctrl.create_privacy_policy_version,
    methods=["POST"],
    response_model=SuccessResponse[PrivacyPolicyResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create Privacy Policy Version (Admin)",
    description="Publish a new Privacy Policy version. Admin access required.",
    operation_id="common_create_privacy_policy_version",
)
