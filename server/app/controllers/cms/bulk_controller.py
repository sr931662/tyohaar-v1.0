"""Bulk Operations CMS controller functions."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.core.responses import SuccessResponse
from app.schemas.cms.bulk import (
    BulkAvailabilityUpdateRequest,
    BulkCouponGenerateRequest,
    BulkDiscountActionRequest,
    BulkMembershipAssignRequest,
    BulkNotificationRequest,
    BulkOperationResult,
    BulkPackageActionRequest,
    BulkPriceUpdateRequest,
    BulkVendorActionRequest,
)
from app.services.cms.bulk_service import BulkService


def get_bulk_service() -> BulkService:
    return BulkService()


BulkServiceDep = Annotated[BulkService, Depends(get_bulk_service)]


async def approve_vendors(
    request: BulkVendorActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.approve_vendors(request), message="Vendors approved")


async def reject_vendors(
    request: BulkVendorActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.reject_vendors(request), message="Vendors rejected")


async def suspend_vendors(
    request: BulkVendorActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.suspend_vendors(request), message="Vendors suspended")


async def activate_vendors(
    request: BulkVendorActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.activate_vendors(request), message="Vendors activated")


async def publish_packages(
    request: BulkPackageActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.publish_packages(request), message="Packages published")


async def unpublish_packages(
    request: BulkPackageActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.unpublish_packages(request), message="Packages unpublished")


async def archive_packages(
    request: BulkPackageActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.archive_packages(request), message="Packages archived")


async def bulk_price_update(
    request: BulkPriceUpdateRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.bulk_price_update(request), message="Prices updated")


async def bulk_send_notifications(
    request: BulkNotificationRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(
        data=await svc.bulk_send_notifications(request),
        message="Notifications queued",
    )


async def generate_coupons(
    request: BulkCouponGenerateRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.generate_coupons(request), message="Coupons generated")


async def enable_discounts(
    request: BulkDiscountActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.enable_discounts(request), message="Discounts enabled")


async def disable_discounts(
    request: BulkDiscountActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.disable_discounts(request), message="Discounts disabled")


async def archive_discounts(
    request: BulkDiscountActionRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(data=await svc.archive_discounts(request), message="Discounts archived")


async def assign_memberships(
    request: BulkMembershipAssignRequest,
    svc: BulkServiceDep,
) -> SuccessResponse[BulkOperationResult]:
    return SuccessResponse(
        data=await svc.assign_memberships(request),
        message="Memberships assigned",
    )
