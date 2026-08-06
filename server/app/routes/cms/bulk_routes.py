"""Bulk Operation endpoints — /admin/cms/bulk/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.bulk_controller import (
    activate_vendors,
    approve_vendors,
    archive_discounts,
    archive_packages,
    assign_memberships,
    bulk_deactivate_membership_plans,
    bulk_deactivate_notification_templates,
    bulk_delete_cities,
    bulk_delete_faqs,
    bulk_delete_media_images,
    bulk_delete_media_videos,
    bulk_delete_occasion_themes,
    bulk_delete_occasions,
    bulk_delete_package_categories,
    bulk_delete_roles,
    bulk_delete_states,
    bulk_delete_vendors,
    bulk_price_update,
    bulk_send_notifications,
    disable_discounts,
    enable_discounts,
    generate_coupons,
    publish_packages,
    reject_vendors,
    suspend_vendors,
    unpublish_packages,
)

router = APIRouter(prefix="/bulk", tags=["CMS — Bulk Operations"])

# ── Vendors ───────────────────────────────────────────────────────────────────

router.add_api_route(
    "/vendors/approve",
    approve_vendors,
    methods=["POST"],
    summary="Bulk approve vendors",
)
router.add_api_route(
    "/vendors/reject",
    reject_vendors,
    methods=["POST"],
    summary="Bulk reject vendors",
)
router.add_api_route(
    "/vendors/suspend",
    suspend_vendors,
    methods=["POST"],
    summary="Bulk suspend vendors",
)
router.add_api_route(
    "/vendors/activate",
    activate_vendors,
    methods=["POST"],
    summary="Bulk activate suspended vendors",
)
router.add_api_route(
    "/vendors/delete",
    bulk_delete_vendors,
    methods=["POST"],
    summary="Bulk delete vendors (cascades to their packages)",
)

# ── Packages ──────────────────────────────────────────────────────────────────

router.add_api_route(
    "/packages/publish",
    publish_packages,
    methods=["POST"],
    summary="Bulk publish packages",
)
router.add_api_route(
    "/packages/unpublish",
    unpublish_packages,
    methods=["POST"],
    summary="Bulk unpublish packages",
)
router.add_api_route(
    "/packages/archive",
    archive_packages,
    methods=["POST"],
    summary="Bulk archive packages",
)
router.add_api_route(
    "/packages/price",
    bulk_price_update,
    methods=["POST"],
    summary="Bulk update package prices (% or fixed amount)",
)

# ── Other ─────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/notifications/send",
    bulk_send_notifications,
    methods=["POST"],
    summary="Bulk send notifications to users / roles / all",
)
router.add_api_route(
    "/coupons/generate",
    generate_coupons,
    methods=["POST"],
    summary="Bulk generate coupon codes",
)
router.add_api_route(
    "/coupons/enable",
    enable_discounts,
    methods=["POST"],
    summary="Bulk enable discounts",
)
router.add_api_route(
    "/coupons/disable",
    disable_discounts,
    methods=["POST"],
    summary="Bulk disable discounts",
)
router.add_api_route(
    "/coupons/archive",
    archive_discounts,
    methods=["POST"],
    summary="Bulk archive discounts",
)
router.add_api_route(
    "/memberships/assign",
    assign_memberships,
    methods=["POST"],
    summary="Bulk assign membership plans to users",
)

# ── Delete ────────────────────────────────────────────────────────────────────

router.add_api_route(
    "/packages/categories/delete",
    bulk_delete_package_categories,
    methods=["POST"],
    summary="Bulk delete package categories",
)
router.add_api_route(
    "/occasions/delete",
    bulk_delete_occasions,
    methods=["POST"],
    summary="Bulk delete occasions",
)
router.add_api_route(
    "/occasions/themes/delete",
    bulk_delete_occasion_themes,
    methods=["POST"],
    summary="Bulk delete occasion themes",
)
router.add_api_route(
    "/media/images/delete",
    bulk_delete_media_images,
    methods=["POST"],
    summary="Bulk delete media images",
)
router.add_api_route(
    "/media/videos/delete",
    bulk_delete_media_videos,
    methods=["POST"],
    summary="Bulk delete media videos",
)
router.add_api_route(
    "/roles/delete",
    bulk_delete_roles,
    methods=["POST"],
    summary="Bulk delete admin roles (super-admin only)",
)
router.add_api_route(
    "/notifications/templates/deactivate",
    bulk_deactivate_notification_templates,
    methods=["POST"],
    summary="Bulk deactivate notification templates",
)
router.add_api_route(
    "/states/delete",
    bulk_delete_states,
    methods=["POST"],
    summary="Bulk delete states",
)
router.add_api_route(
    "/cities/delete",
    bulk_delete_cities,
    methods=["POST"],
    summary="Bulk delete cities",
)
router.add_api_route(
    "/faqs/delete",
    bulk_delete_faqs,
    methods=["POST"],
    summary="Bulk delete FAQs",
)
router.add_api_route(
    "/memberships/plans/deactivate",
    bulk_deactivate_membership_plans,
    methods=["POST"],
    summary="Bulk deactivate membership plans",
)
