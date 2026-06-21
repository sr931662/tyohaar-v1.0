"""CRM endpoints — /admin/cms/crm/"""

from __future__ import annotations

from fastapi import APIRouter

from app.controllers.cms.crm_controller import (
    get_customer_crm,
    get_vendor_crm,
    list_customers_crm,
    list_vendors_crm,
)

router = APIRouter(prefix="/crm", tags=["CMS — CRM"])

router.add_api_route(
    "/vendors",
    list_vendors_crm,
    methods=["GET"],
    summary="Paginated vendor CRM list with filters",
)
router.add_api_route(
    "/vendors/{vendor_id}",
    get_vendor_crm,
    methods=["GET"],
    summary="360° vendor CRM profile",
)
router.add_api_route(
    "/customers",
    list_customers_crm,
    methods=["GET"],
    summary="Paginated customer CRM list with filters",
)
router.add_api_route(
    "/customers/{user_id}",
    get_customer_crm,
    methods=["GET"],
    summary="360° customer CRM profile",
)
