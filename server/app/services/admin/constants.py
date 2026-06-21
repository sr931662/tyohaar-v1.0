"""Admin service constants."""

from __future__ import annotations

MAX_FAILED_LOGIN_ATTEMPTS = 5
ADMIN_LOCKOUT_DURATION_MINUTES = 30
ADMIN_SESSION_EXPIRY_SECONDS = 28800  # 8 hours
MIN_ADMIN_PASSWORD_LENGTH = 12
MAX_AUDIT_LOG_RETENTION_DAYS = 365
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

# Permission codes (non-exhaustive)
PERM_VENDOR_APPROVE = "vendors.approve"
PERM_BOOKING_MANAGE = "bookings.manage"
PERM_USER_MANAGE = "users.manage"
PERM_PAYMENT_MANAGE = "payments.manage"
PERM_COUPON_MANAGE = "coupons.manage"
PERM_CONTENT_MANAGE = "content.manage"
PERM_ADMIN_MANAGE = "admin.manage"
PERM_SUPPORT_MANAGE = "support.manage"
