"""
Base exception hierarchy for the Tyohaar service layer.

All domain-specific exceptions inherit from these base classes.
FastAPI exception handlers map these to appropriate HTTP responses.

Hierarchy:
    ServiceError (base)
    ├── NotFoundError          → 404
    ├── ConflictError          → 409
    ├── ValidationError        → 422
    ├── PermissionError        → 403
    ├── AuthenticationError    → 401
    ├── RateLimitError         → 429
    ├── PaymentError           → 402 / 422
    ├── BusinessRuleError      → 422
    └── ExternalServiceError   → 502
"""

from __future__ import annotations


class ServiceError(Exception):
    """Root base class for all service-layer errors."""

    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, detail: dict | None = None) -> None:
        self.message = message or self.default_message
        self.detail = detail or {}
        super().__init__(self.message)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(message={self.message!r})"


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""
    default_message = "Resource not found."

    def __init__(self, resource: str, identifier: str | None = None) -> None:
        msg = f"{resource} not found."
        if identifier:
            msg = f"{resource} '{identifier}' not found."
        super().__init__(msg, {"resource": resource, "identifier": identifier})


class ConflictError(ServiceError):
    """Raised when an operation conflicts with existing state (e.g. duplicate)."""
    default_message = "A conflict occurred with the current resource state."


class ValidationError(ServiceError):
    """Raised when input data fails business-rule validation."""
    default_message = "Input validation failed."

    def __init__(self, message: str, field: str | None = None) -> None:
        detail = {"field": field} if field else {}
        super().__init__(message, detail)


class PermissionError(ServiceError):
    """Raised when the caller lacks permission to perform an action."""
    default_message = "You do not have permission to perform this action."


class AuthenticationError(ServiceError):
    """Raised for authentication failures (invalid credentials, expired tokens)."""
    default_message = "Authentication failed."


class RateLimitError(ServiceError):
    """Raised when a rate limit is exceeded (OTP resend, login attempts, etc.)."""
    default_message = "Too many requests. Please wait before trying again."

    def __init__(self, message: str | None = None, retry_after_seconds: int | None = None) -> None:
        super().__init__(message or self.default_message)
        self.retry_after_seconds = retry_after_seconds


class PaymentError(ServiceError):
    """Raised for payment-specific failures."""
    default_message = "Payment processing failed."


class BusinessRuleError(ServiceError):
    """
    Raised when a business rule is violated (e.g. wallet would go negative,
    vendor not available, booking cutoff exceeded).
    """
    default_message = "This action violates a business rule."


class ExternalServiceError(ServiceError):
    """Raised when an upstream service (SMS gateway, payment gateway) fails."""
    default_message = "An external service is unavailable. Please try again."

    def __init__(self, service_name: str, message: str | None = None) -> None:
        super().__init__(message or f"{service_name} is unavailable.")
        self.service_name = service_name


class AccountLockedError(AuthenticationError):
    """Raised when an account is temporarily or permanently locked."""
    default_message = "Your account is temporarily locked."

    def __init__(self, message: str | None = None, locked_until: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.locked_until = locked_until


class InsufficientBalanceError(BusinessRuleError):
    """Raised when a wallet debit would result in a negative balance."""
    default_message = "Insufficient wallet balance."


class BookingConflictError(ConflictError):
    """Raised when a booking conflicts with existing bookings or vendor schedule."""
    default_message = "A booking conflict exists for the requested time slot."


class CouponError(ValidationError):
    """Raised for coupon validation failures (expired, exhausted, ineligible)."""
    pass
