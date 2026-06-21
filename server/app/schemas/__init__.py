"""
Schema Layer — the only public interface for data entering or leaving the Tyohaar backend.

Import path convention:
    from app.schemas.users.response import UserResponse
    from app.schemas.bookings.create import BookingCreate
    from app.schemas.base import CursorPage, MoneyAmount

Domain structure (16 domains × 8 files each = 128 schema files):
    auth/           — OTP, Session, RefreshToken
    users/          — User, UserProfile, UserAddress, UserDevice
    vendors/        — Vendor, VendorProfile, VendorService, VendorCategory, etc.
    occasions/      — Occasion, Celebration, CelebrationGuest, etc.
    packages/       — Package, PackageCategory, PackageItem, PackagePricing, etc.
    bookings/       — Booking, BookingItem, BookingCancellation, etc.
    payments/       — Payment, Refund, Coupon, PaymentWebhook
    wallets/        — Wallet, WalletTransaction, UserReward
    memberships/    — MembershipPlan, UserMembership
    notifications/  — Notification, NotificationTemplate
    support/        — SupportTicket, SupportMessage, SupportAttachment
    media/          — Image, Video, Memory
    referrals/      — Referral, ReferralReward
    budgets/        — Budget, BudgetExpense, BudgetCategory
    admin/          — Admin, AdminRole, AdminPermission, AuditLog
    common/         — State, City, Banner, FAQ, AppSetting, Terms, PrivacyPolicy

Base types (shared across all domains):
    base.py         — BaseSchema, CursorPage, MoneyAmount, PhoneNumber, etc.

Security contract:
    Public Response schemas NEVER expose:
    - password_hash, otp_hash, token_hash, gateway_signature
    - device_fingerprint, push_notification_token
    - internal_notes, extra_metadata (exposed only in Internal/Admin schemas)
    - deleted_at, is_deleted (soft-delete internals)
    - gst_number, pan_number, legal_name (vendor compliance — admin only)
    - failed_login_count, account_locked_until (security internals)
    - gateway_signature (payment verification — never expose)
"""

from app.schemas.base import (
    BaseSchema,
    CursorPage,
    OffsetPage,
    CoordinateSchema,
    MoneyAmount,
    MoneySchema,
    PhoneNumber,
    EmailStr,
    Percentage,
    Latitude,
    Longitude,
    PaginationCursor,
    decode_cursor,
    encode_cursor,
)

__all__ = [
    # Base types
    "BaseSchema",
    "CursorPage",
    "OffsetPage",
    "CoordinateSchema",
    "MoneyAmount",
    "MoneySchema",
    "PhoneNumber",
    "EmailStr",
    "Percentage",
    "Latitude",
    "Longitude",
    "PaginationCursor",
    "decode_cursor",
    "encode_cursor",
]
