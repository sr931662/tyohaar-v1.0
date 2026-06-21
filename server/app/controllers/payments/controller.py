"""
Payments Controller — payment initiation, verification, refunds, coupons, splits, and invoices.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, Header, Query, Request

from app.core.current_user import CurrentUserDep
from app.core.dependencies import PaymentServiceDep
from app.core.pagination import CursorPaginationParams, get_cursor_pagination
from app.core.permissions import AdminDep
from app.core.responses import CursorMeta, CursorPaginatedResponse, SuccessResponse
from app.schemas.base import CursorPage
from app.schemas.payments.create import CouponCreate, PaymentCreate, RefundCreate
from app.schemas.payments.filters import PaymentFilters
from app.schemas.payments.response import (
    CouponResponse,
    CouponValidationResponse,
    PaymentResponse,
    RefundResponse,
)
from app.services.payments.service import (
    InvoiceResponse,
    PaymentInitResponse,
    PaymentSplitCreate,
    PaymentSplitResponse,
    PaymentTransactionResponse,
)


def _cursor_resp(page: CursorPage, page_size: int) -> CursorPaginatedResponse:
    return CursorPaginatedResponse(
        data=page.items,
        meta=CursorMeta(cursor=page.next_cursor, has_next=page.has_more, page_size=page_size),
    )


async def initiate_payment(
    booking_id: uuid.UUID,
    body: PaymentCreate,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[PaymentInitResponse]:
    result = await service.initiate_payment(
        booking_id=booking_id, customer_id=current_user.id, data=body
    )
    return SuccessResponse(data=result, message="Payment initiated.")


async def initiate_wallet_payment(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    amount: Decimal = Query(...),
) -> SuccessResponse[PaymentResponse]:
    result = await service.initiate_wallet_payment(
        booking_id=booking_id, customer_id=current_user.id, amount=amount
    )
    return SuccessResponse(data=result, message="Wallet payment completed.")


async def handle_webhook(
    gateway: str,
    request: Request,
    service: PaymentServiceDep,
    x_razorpay_signature: str | None = Header(default=None),
    x_gateway_signature: str | None = Header(default=None),
) -> SuccessResponse[None]:
    payload = await request.body()
    signature = x_razorpay_signature or x_gateway_signature or ""
    from app.core.config import settings
    await service.handle_webhook(
        gateway=gateway, payload=payload, signature=signature, secret=settings.PAYMENT_WEBHOOK_SECRET
    )
    return SuccessResponse(data=None, message="Webhook processed.")


async def verify_payment(
    payment_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    gateway_payment_id: str = Query(...),
    gateway_signature: str = Query(...),
    gateway: str = Query(default="razorpay"),
) -> SuccessResponse[PaymentResponse]:
    from app.core.config import settings
    result = await service.verify_payment(
        payment_id=payment_id,
        gateway_payment_id=gateway_payment_id,
        gateway_signature=gateway_signature,
        secret=settings.PAYMENT_WEBHOOK_SECRET,
        gateway=gateway,
    )
    return SuccessResponse(data=result, message="Payment verified.")


async def get_payment(
    payment_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[PaymentResponse]:
    result = await service.get_payment(payment_id=payment_id, customer_id=current_user.id)
    return SuccessResponse(data=result, message="Payment retrieved.")


async def list_payments(
    current_user: CurrentUserDep,
    filters: Annotated[PaymentFilters, Depends()],
    pagination: Annotated[CursorPaginationParams, Depends(get_cursor_pagination)],
    service: PaymentServiceDep,
) -> CursorPaginatedResponse[PaymentResponse]:
    page = await service.list_payments(
        customer_id=current_user.id,
        filters=filters,
        cursor=pagination.cursor,
        limit=pagination.page_size,
    )
    return _cursor_resp(page, pagination.page_size)


async def get_payment_transactions(
    payment_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[list[PaymentTransactionResponse]]:
    txns = await service.get_payment_transactions(payment_id=payment_id)
    return SuccessResponse(data=txns, message="Transactions retrieved.")


async def initiate_refund(
    payment_id: uuid.UUID,
    body: RefundCreate,
    current_user: AdminDep,
    service: PaymentServiceDep,
) -> SuccessResponse[RefundResponse]:
    result = await service.initiate_refund(
        payment_id=payment_id, data=body, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Refund initiated.")


async def list_refunds(
    booking_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[list[RefundResponse]]:
    refunds = await service.list_refunds(booking_id=booking_id)
    return SuccessResponse(data=refunds, message="Refunds retrieved.")


async def validate_coupon(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    code: str = Query(...),
    booking_id: uuid.UUID = Query(...),
    amount: Decimal = Query(...),
) -> SuccessResponse[CouponValidationResponse]:
    result = await service.validate_coupon(
        code=code, user_id=current_user.id, booking_id=booking_id, amount=amount
    )
    return SuccessResponse(data=result, message="Coupon validated.")


async def list_active_coupons(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[list[CouponResponse]]:
    coupons = await service.list_active_coupons(user_id=current_user.id)
    return SuccessResponse(data=coupons, message="Coupons retrieved.")


async def create_coupon(
    body: CouponCreate,
    current_user: AdminDep,
    service: PaymentServiceDep,
) -> SuccessResponse[CouponResponse]:
    result = await service.create_coupon(data=body, admin_id=current_user.id)
    return SuccessResponse(data=result, message="Coupon created.")


async def deactivate_coupon(
    coupon_id: uuid.UUID,
    current_user: AdminDep,
    service: PaymentServiceDep,
) -> SuccessResponse[None]:
    await service.deactivate_coupon(coupon_id=coupon_id, admin_id=current_user.id)
    return SuccessResponse(data=None, message="Coupon deactivated.")


async def create_payment_split(
    payment_id: uuid.UUID,
    body: PaymentSplitCreate,
    current_user: AdminDep,
    service: PaymentServiceDep,
) -> SuccessResponse[PaymentSplitResponse]:
    result = await service.create_payment_split(
        payment_id=payment_id, data=body, admin_id=current_user.id
    )
    return SuccessResponse(data=result, message="Payment split created.")


async def list_payment_splits(
    payment_id: uuid.UUID,
    current_user: AdminDep,
    service: PaymentServiceDep,
) -> SuccessResponse[list[PaymentSplitResponse]]:
    splits = await service.list_payment_splits(payment_id=payment_id)
    return SuccessResponse(data=splits, message="Payment splits retrieved.")


async def get_invoice(
    invoice_id: uuid.UUID,
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
) -> SuccessResponse[InvoiceResponse]:
    result = await service.get_invoice(invoice_id=invoice_id)
    return SuccessResponse(data=result, message="Invoice retrieved.")


async def list_invoices(
    current_user: CurrentUserDep,
    service: PaymentServiceDep,
    entity_id: uuid.UUID = Query(...),
    entity_type: str = Query(...),
) -> SuccessResponse[list[InvoiceResponse]]:
    invoices = await service.list_invoices(entity_id=entity_id, entity_type=entity_type)
    return SuccessResponse(data=invoices, message="Invoices retrieved.")
