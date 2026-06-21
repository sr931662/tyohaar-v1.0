"""Bulk Operation endpoints — /admin/cms/bulk/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.bulk_controller import (
    activate_vendors,
    approve_vendors,
    archive_packages,
    assign_memberships,
    bulk_price_update,
    bulk_send_notifications,
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
    "/memberships/assign",
    assign_memberships,
    methods=["POST"],
    summary="Bulk assign membership plans to users",
)
