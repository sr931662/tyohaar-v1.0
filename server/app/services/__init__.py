"""
Service Layer — all business logic for the Tyohaar backend.

Import convention:
    from app.services.auth.service import AuthService
    from app.services.bookings.service import BookingService
    from app.services.exceptions import NotFoundError, BusinessRuleError

Base infrastructure:
    app.services.base        — BaseService (UoW factory injection)
    app.services.exceptions  — Root exception hierarchy

Domain services (16 domains × 6 files each = 96 files):
    auth/           bookings/       media/
    users/          payments/       referrals/
    vendors/        wallets/        budgets/
    occasions/      memberships/    admin/
    packages/       notifications/  common/
                    support/

Each domain contains:
    service.py      — Main service class
    validators.py   — Business-rule validators (async, use repos)
    helpers.py      — Pure helper functions (no I/O)
    constants.py    — Domain-specific limits and constants
    exceptions.py   — Domain exceptions (inherit from services.exceptions)
    __init__.py     — Re-exports
"""

from app.services.base import BaseService
from app.services.exceptions import (
    ServiceError,
    NotFoundError,
    ConflictError,
    ValidationError,
    PermissionError,
    AuthenticationError,
    RateLimitError,
    PaymentError,
    BusinessRuleError,
    ExternalServiceError,
    AccountLockedError,
    InsufficientBalanceError,
    BookingConflictError,
    CouponError,
)

__all__ = [
    "BaseService",
    "ServiceError",
    "NotFoundError",
    "ConflictError",
    "ValidationError",
    "PermissionError",
    "AuthenticationError",
    "RateLimitError",
    "PaymentError",
    "BusinessRuleError",
    "ExternalServiceError",
    "AccountLockedError",
    "InsufficientBalanceError",
    "BookingConflictError",
    "CouponError",
]
