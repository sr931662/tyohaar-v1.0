"""CRM CMS controller functions."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, Query

from app.core.responses import PaginatedResponse, PaginatedMeta, SuccessResponse
from app.schemas.cms.crm import CustomerCRMProfile, VendorCRMProfile
from app.services.cms.crm_service import CRMService


def get_crm_service() -> CRMService:
    return CRMService()


CRMServiceDep = Annotated[CRMService, Depends(get_crm_service)]


async def get_vendor_crm(
    vendor_id: uuid.UUID,
    svc: CRMServiceDep,
) -> SuccessResponse[VendorCRMProfile]:
    return SuccessResponse(data=await svc.get_vendor_crm_profile(vendor_id))


async def get_customer_crm(
    user_id: uuid.UUID,
    svc: CRMServiceDep,
) -> SuccessResponse[CustomerCRMProfile]:
    return SuccessResponse(data=await svc.get_customer_crm_profile(user_id))


async def list_vendors_crm(
    svc: CRMServiceDep,
    verification_status: str | None = Query(default=None),
    city: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    items, total = await svc.list_vendors_crm(
        verification_status=verification_status, city=city, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=items,
        meta=PaginatedMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


async def list_customers_crm(
    svc: CRMServiceDep,
    account_status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse:
    skip = (page - 1) * page_size
    items, total = await svc.list_customers_crm(
        account_status=account_status, skip=skip, limit=page_size
    )
    total_pages = (total + page_size - 1) // page_size
    return PaginatedResponse(
        data=items,
        meta=PaginatedMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )
