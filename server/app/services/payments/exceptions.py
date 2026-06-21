"""
Payments domain exceptions.
"""

from __future__ import annotations

from app.services.exceptions import (
    BusinessRuleError,
    ConflictError,
    CouponError,
    NotFoundError,
    PaymentError,
    ValidationError,
)


class PaymentNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Payment", identifier)


class PaymentAlreadyCompletedError(ConflictError):
    default_message = "Payment has already been completed."


class PaymentAlreadyFailedError(ConflictError):
    default_message = "Payment has already failed."


class PaymentExpiredError(BusinessRuleError):
    default_message = "Payment window has expired."


class InvalidGatewaySignatureError(PaymentError):
    default_message = "Gateway signature verification failed."


class RefundExceedsPaymentError(BusinessRuleError):
    default_message = "Refund amount exceeds the original payment amount."


class CouponNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Coupon", identifier)


class CouponExpiredError(CouponError):
    def __init__(self, message: str = "Coupon has expired.", field: str | None = None) -> None:
        super().__init__(message, field)


class CouponExhaustedError(CouponError):
    def __init__(self, message: str = "Coupon usage limit has been reached.", field: str | None = None) -> None:
        super().__init__(message, field)


class CouponMinOrderNotMetError(CouponError):
    def __init__(self, message: str = "Order amount does not meet the coupon minimum.", field: str | None = None) -> None:
        super().__init__(message, field)


class CouponUserLimitReachedError(CouponError):
    def __init__(self, message: str = "You have reached the per-user redemption limit for this coupon.", field: str | None = None) -> None:
        super().__init__(message, field)


class UnsupportedGatewayError(ValidationError):
    def __init__(self, gateway: str) -> None:
        super().__init__(f"Payment gateway '{gateway}' is not supported.", field="gateway")


class RefundNotFoundError(NotFoundError):
    def __init__(self, identifier: str | None = None) -> None:
        super().__init__("Refund", identifier)
