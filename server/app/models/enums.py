"""
Central enum registry for the entire Tyohaar backend.

All SQLAlchemy models and Pydantic schemas must import enums from this module.
Never define domain enums inside individual model files — add them here instead.

Design:
- All enums inherit from (str, enum.Enum) so their values:
    • Serialize as plain strings in JSON (no extra Pydantic config needed).
    • Are stored as readable VARCHAR values in PostgreSQL (not integers).
    • Work natively with SQLAlchemy's Enum column type.
    • Are directly comparable to string literals in Python code.

- SQLAlchemy column declaration pattern:
    from sqlalchemy import Enum as SAEnum
    from app.models.enums import BookingStatus

    status: Mapped[BookingStatus] = mapped_column(
        SAEnum(BookingStatus, name="booking_status", native_enum=False),
        nullable=False,
    )

  Using native_enum=False stores as VARCHAR + check constraint, avoiding
  the operational overhead of altering PostgreSQL ENUM types when new
  values are added. This is the recommended approach for fast-moving backends.

Sections:
    Authentication · Users · Devices · Vendors · Occasions · Packages
    Bookings · Payments · Wallets · Memberships · Invitations
    Notifications · Support · Media · Referrals · Budgets · Common · Admin
"""

import enum


# ──────────────────────────────────────────────────────────────────────────────
# Authentication
# ──────────────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    """Authorization role assigned to a user account."""
    CUSTOMER = "customer"
    VENDOR = "vendor"
    SUPPORT = "support"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class UserType(str, enum.Enum):
    """Nature of the account holder."""
    INDIVIDUAL = "individual"
    BUSINESS = "business"


class LoginMethod(str, enum.Enum):
    """Authentication mechanism used to create a session."""
    OTP_PHONE = "otp_phone"
    OTP_EMAIL = "otp_email"
    GOOGLE = "google"
    APPLE = "apple"
    FACEBOOK = "facebook"


class OTPPurpose(str, enum.Enum):
    """Declares why an OTP was issued. Prevents cross-purpose OTP reuse."""
    LOGIN = "login"
    REGISTRATION = "registration"
    PHONE_VERIFICATION = "phone_verification"
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    TRANSACTION_VERIFICATION = "transaction_verification"
    ACCOUNT_DELETION = "account_deletion"
    VENDOR_ONBOARDING = "vendor_onboarding"
    TWO_FACTOR_AUTH = "two_factor_auth"


class OTPDeliveryChannel(str, enum.Enum):
    """Channel through which the OTP is dispatched to the user."""
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    VOICE = "voice"


class OTPStatus(str, enum.Enum):
    """Lifecycle state of an OTP record."""
    PENDING = "pending"          # Issued and awaiting user input
    VERIFIED = "verified"        # Successfully verified by the user
    EXPIRED = "expired"          # TTL elapsed before verification
    EXHAUSTED = "exhausted"      # Maximum incorrect attempts reached
    SUPERSEDED = "superseded"    # A newer OTP was issued for the same identifier+purpose


class SessionStatus(str, enum.Enum):
    """Lifecycle state of a user session."""
    ACTIVE = "active"
    EXPIRED = "expired"
    LOGGED_OUT = "logged_out"
    REVOKED = "revoked"          # Admin-forced or triggered by security event
    LOCKED = "locked"            # Suspicious activity detected; pending review


class TokenType(str, enum.Enum):
    ACCESS = "access"
    REFRESH = "refresh"


class TokenRevocationReason(str, enum.Enum):
    """Why a token or session was invalidated."""
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    SECURITY_BREACH = "security_breach"
    ADMIN_REVOKED = "admin_revoked"
    TOKEN_ROTATION = "token_rotation"           # Normal rotation; predecessor superseded
    REUSE_DETECTED = "reuse_detected"           # Already-used token presented again → theft
    ACCOUNT_SUSPENDED = "account_suspended"
    SESSION_EXPIRED = "session_expired"
    DEVICE_UNREGISTERED = "device_unregistered"


# ──────────────────────────────────────────────────────────────────────────────
# Users
# ──────────────────────────────────────────────────────────────────────────────

class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class Language(str, enum.Enum):
    """BCP-47 language tags for the languages supported by the app."""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    TELUGU = "te"
    KANNADA = "kn"
    MALAYALAM = "ml"
    MARATHI = "mr"
    GUJARATI = "gu"
    BENGALI = "bn"
    PUNJABI = "pa"


class AccountStatus(str, enum.Enum):
    """Overall health state of a user account."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"               # Admin-imposed temporary suspension
    DEACTIVATED = "deactivated"           # User-initiated deactivation
    PENDING_VERIFICATION = "pending_verification"
    BANNED = "banned"                     # Permanent, non-reversible ban


class VerificationStatus(str, enum.Enum):
    """Identity or document verification state."""
    UNVERIFIED = "unverified"
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"                   # Verified credential has lapsed


# ──────────────────────────────────────────────────────────────────────────────
# Devices & Platforms
# ──────────────────────────────────────────────────────────────────────────────

class Platform(str, enum.Enum):
    """OS platform of the client device."""
    IOS = "ios"
    ANDROID = "android"
    WEB = "web"
    DESKTOP = "desktop"


class DeviceType(str, enum.Enum):
    """Physical form factor of the client device."""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"
    SMARTWATCH = "smartwatch"
    OTHER = "other"


# ──────────────────────────────────────────────────────────────────────────────
# Vendors
# ──────────────────────────────────────────────────────────────────────────────

class VendorStatus(str, enum.Enum):
    """Operational status of a vendor account on the platform."""
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    REJECTED = "rejected"
    UNDER_REVIEW = "under_review"
    DEACTIVATED = "deactivated"


class VendorType(str, enum.Enum):
    """Primary service category of the vendor."""
    DECORATOR = "decorator"
    CATERER = "caterer"
    PHOTOGRAPHER = "photographer"
    VIDEOGRAPHER = "videographer"
    BAKER = "baker"
    FLORIST = "florist"
    ENTERTAINER = "entertainer"
    VENUE = "venue"
    PLANNER = "planner"
    MAKEUP_ARTIST = "makeup_artist"
    MEHNDI_ARTIST = "mehndi_artist"
    MUSIC = "music"
    MULTI_SERVICE = "multi_service"
    OTHER = "other"


class VendorVerificationStatus(str, enum.Enum):
    """KYC/document verification pipeline state for a vendor."""
    UNVERIFIED = "unverified"
    DOCUMENTS_SUBMITTED = "documents_submitted"
    UNDER_REVIEW = "under_review"
    VERIFIED = "verified"
    REJECTED = "rejected"
    RE_VERIFICATION_REQUIRED = "re_verification_required"


class ServiceStatus(str, enum.Enum):
    """Availability state of a specific service offered by a vendor."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SEASONAL = "seasonal"
    SOLD_OUT = "sold_out"
    COMING_SOON = "coming_soon"


class AvailabilityStatus(str, enum.Enum):
    """Calendar-level availability state for a vendor on a given date."""
    AVAILABLE = "available"
    PARTIALLY_AVAILABLE = "partially_available"
    FULLY_BOOKED = "fully_booked"
    BLOCKED = "blocked"
    ON_LEAVE = "on_leave"


# ──────────────────────────────────────────────────────────────────────────────
# Occasions & Celebrations
# ──────────────────────────────────────────────────────────────────────────────

class OccasionCategory(str, enum.Enum):
    LIFE_EVENT = "life_event"
    MAJOR_FESTIVAL = "major_festival"
    MINOR_FESTIVAL = "minor_festival"
    PERSONAL = "personal"
    CORPORATE = "corporate"
    RELIGIOUS = "religious"
    SEASONAL = "seasonal"


class CelebrationStatus(str, enum.Enum):
    """Planning and execution lifecycle of a customer's celebration."""
    DRAFT = "draft"
    PLANNING = "planning"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POSTPONED = "postponed"


# ──────────────────────────────────────────────────────────────────────────────
# Packages
# ──────────────────────────────────────────────────────────────────────────────

class PackageStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class PackagePricingType(str, enum.Enum):
    FIXED = "fixed"
    PER_PERSON = "per_person"
    TIERED = "tiered"               # Price steps based on guest count ranges
    CUSTOM_QUOTE = "custom_quote"


# ──────────────────────────────────────────────────────────────────────────────
# Bookings
# ──────────────────────────────────────────────────────────────────────────────

class BookingStatus(str, enum.Enum):
    """End-to-end lifecycle state of a customer booking."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class BookingType(str, enum.Enum):
    PACKAGE = "package"
    CUSTOM = "custom"
    ADD_ON = "add_on"
    CONSULTATION = "consultation"


class AssignmentStatus(str, enum.Enum):
    """Status of a vendor being assigned to fulfil a booking."""
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"
    REASSIGNED = "reassigned"


class CancellationReason(str, enum.Enum):
    CUSTOMER_REQUEST = "customer_request"
    VENDOR_UNAVAILABLE = "vendor_unavailable"
    WEATHER = "weather"
    PAYMENT_FAILURE = "payment_failure"
    DUPLICATE_BOOKING = "duplicate_booking"
    ADMIN_ACTION = "admin_action"
    FORCE_MAJEURE = "force_majeure"
    CHANGE_OF_PLANS = "change_of_plans"
    FOUND_BETTER_OPTION = "found_better_option"
    OTHER = "other"


# ──────────────────────────────────────────────────────────────────────────────
# Payments
# ──────────────────────────────────────────────────────────────────────────────

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    PARTIALLY_REFUNDED = "partially_refunded"
    DISPUTED = "disputed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PaymentMethod(str, enum.Enum):
    UPI = "upi"
    CREDIT_CARD = "credit_card"
    DEBIT_CARD = "debit_card"
    NET_BANKING = "net_banking"
    WALLET = "wallet"
    CASH = "cash"
    EMI = "emi"
    TYOHAAR_CREDITS = "tyohaar_credits"
    BNPL = "bnpl"                       # Buy Now Pay Later


class RefundStatus(str, enum.Enum):
    PENDING = "pending"
    INITIATED = "initiated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class TransactionType(str, enum.Enum):
    PAYMENT = "payment"
    REFUND = "refund"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"
    FEE = "fee"
    COMMISSION = "commission"
    PAYOUT = "payout"
    CHARGEBACK = "chargeback"


class SettlementStatus(str, enum.Enum):
    """Status of vendor payout settlement after a booking is completed."""
    PENDING = "pending"
    PROCESSING = "processing"
    SETTLED = "settled"
    ON_HOLD = "on_hold"
    DISPUTED = "disputed"
    FAILED = "failed"


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    VOID = "void"


class CouponType(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SERVICE = "free_service"
    CASHBACK = "cashback"


class CouponApplicability(str, enum.Enum):
    ALL = "all"
    FIRST_BOOKING = "first_booking"
    SPECIFIC_CATEGORY = "specific_category"
    SPECIFIC_VENDOR = "specific_vendor"
    SPECIFIC_PACKAGE = "specific_package"
    MEMBERSHIP_ONLY = "membership_only"


# ──────────────────────────────────────────────────────────────────────────────
# Wallets
# ──────────────────────────────────────────────────────────────────────────────

class WalletType(str, enum.Enum):
    CUSTOMER = "customer"
    VENDOR = "vendor"


class WalletTransactionType(str, enum.Enum):
    CREDIT = "credit"
    DEBIT = "debit"
    REFUND = "refund"
    REWARD = "reward"
    CASHBACK = "cashback"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    ADJUSTMENT = "adjustment"
    EXPIRY = "expiry"               # Reward/credit balance expiring


class RewardType(str, enum.Enum):
    REFERRAL_BONUS = "referral_bonus"
    BOOKING_CASHBACK = "booking_cashback"
    LOYALTY_POINTS = "loyalty_points"
    PROMOTIONAL = "promotional"
    ANNIVERSARY_BONUS = "anniversary_bonus"
    WELCOME_BONUS = "welcome_bonus"
    REVIEW_REWARD = "review_reward"


# ──────────────────────────────────────────────────────────────────────────────
# Memberships
# ──────────────────────────────────────────────────────────────────────────────

class MembershipTier(str, enum.Enum):
    FREE = "free"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"


class MembershipStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    PENDING = "pending"
    GRACE_PERIOD = "grace_period"   # Post-expiry window before tier downgrade


class MembershipBillingCycle(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


# ──────────────────────────────────────────────────────────────────────────────
# Invitations
# ──────────────────────────────────────────────────────────────────────────────

class InvitationStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    VIEWED = "viewed"
    EXPIRED = "expired"


class RSVPStatus(str, enum.Enum):
    PENDING = "pending"
    ATTENDING = "attending"
    DECLINED = "declined"
    MAYBE = "maybe"
    NO_RESPONSE = "no_response"


# ──────────────────────────────────────────────────────────────────────────────
# Notifications
# ──────────────────────────────────────────────────────────────────────────────

class NotificationType(str, enum.Enum):
    BOOKING_CONFIRMED = "booking_confirmed"
    BOOKING_CANCELLED = "booking_cancelled"
    BOOKING_UPDATED = "booking_updated"
    PAYMENT_RECEIVED = "payment_received"
    PAYMENT_FAILED = "payment_failed"
    REFUND_INITIATED = "refund_initiated"
    REFUND_COMPLETED = "refund_completed"
    OTP = "otp"
    REMINDER = "reminder"
    PROMOTIONAL = "promotional"
    SYSTEM = "system"
    REVIEW_REQUEST = "review_request"
    VENDOR_ASSIGNED = "vendor_assigned"
    RSVP_UPDATE = "rsvp_update"
    CELEBRATION_UPCOMING = "celebration_upcoming"
    WALLET_CREDIT = "wallet_credit"
    MEMBERSHIP_EXPIRING = "membership_expiring"
    SUPPORT_UPDATE = "support_update"


class NotificationChannel(str, enum.Enum):
    PUSH = "push"
    SMS = "sms"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────────────────────
# Support
# ──────────────────────────────────────────────────────────────────────────────

class TicketStatus(str, enum.Enum):
    OPEN = "open"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_ON_CUSTOMER = "waiting_on_customer"
    WAITING_ON_VENDOR = "waiting_on_vendor"
    ESCALATED = "escalated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"


class TicketPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, enum.Enum):
    BOOKING = "booking"
    PAYMENT = "payment"
    VENDOR = "vendor"
    TECHNICAL = "technical"
    ACCOUNT = "account"
    MEMBERSHIP = "membership"
    REFUND = "refund"
    GENERAL = "general"


# ──────────────────────────────────────────────────────────────────────────────
# Media
# ──────────────────────────────────────────────────────────────────────────────

class MediaType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"


class MediaUsage(str, enum.Enum):
    """Describes which feature context a media asset belongs to."""
    PROFILE_PHOTO = "profile_photo"
    VENDOR_GALLERY = "vendor_gallery"
    BOOKING_EVIDENCE = "booking_evidence"
    INVITATION = "invitation"
    MEMORY = "memory"
    SUPPORT_ATTACHMENT = "support_attachment"
    PRODUCT_IMAGE = "product_image"
    PACKAGE_IMAGE = "package_image"
    OCCASION_COVER = "occasion_cover"
    VENDOR_DOCUMENT = "vendor_document"
    BANNER = "banner"


class MediaStatus(str, enum.Enum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"
    FAILED = "failed"


# ──────────────────────────────────────────────────────────────────────────────
# Referrals
# ──────────────────────────────────────────────────────────────────────────────

class ReferralStatus(str, enum.Enum):
    PENDING = "pending"             # Referred user has not yet signed up
    SIGNED_UP = "signed_up"         # Referred user completed registration
    CONVERTED = "converted"         # Referred user made their first booking
    REWARDED = "rewarded"           # Reward has been issued to the referrer
    EXPIRED = "expired"             # Link expired before conversion
    INVALID = "invalid"             # Self-referral or fraud detected


# ──────────────────────────────────────────────────────────────────────────────
# Budgets
# ──────────────────────────────────────────────────────────────────────────────

class BudgetCategory(str, enum.Enum):
    DECORATION = "decoration"
    CATERING = "catering"
    PHOTOGRAPHY = "photography"
    VIDEOGRAPHY = "videography"
    CAKE = "cake"
    BOUQUET = "bouquet"
    ENTERTAINMENT = "entertainment"
    VENUE = "venue"
    INVITATION = "invitation"
    GIFTS = "gifts"
    TRANSPORT = "transport"
    ATTIRE = "attire"
    MAKEUP = "makeup"
    MISCELLANEOUS = "miscellaneous"


class BudgetLifecycleStatus(str, enum.Enum):
    """Operational phase of a budget plan within the Budgets domain."""
    DRAFT = "draft"           # Created but not yet activated for tracking
    ACTIVE = "active"         # In use; expenses are being tracked against it
    PAUSED = "paused"         # Temporarily suspended; no new expenses tracked
    COMPLETED = "completed"   # Celebration has occurred; budget finalised
    ARCHIVED = "archived"     # Stored for reference; effectively read-only


class BudgetHealthStatus(str, enum.Enum):
    """
    Real-time comparison of actual spending against planned budget.

    Computed and cached by the service layer whenever expenses change.
    Drives home-screen budget health indicators and alert triggers.
    """
    ON_TRACK = "on_track"             # Actual < alert_threshold_pct of planned
    SLIGHTLY_OVER = "slightly_over"   # Actual between threshold and 100% of planned
    OVER_BUDGET = "over_budget"       # Actual > planned
    UNDER_BUDGET = "under_budget"     # Actual < 50% of planned (potential saving)


class ExpenseType(str, enum.Enum):
    """Nature of a budget expense entry in the planning lifecycle."""
    PLANNED = "planned"       # Entered during initial budget planning
    ESTIMATED = "estimated"   # Rough cost estimate before vendor confirmation
    ACTUAL = "actual"         # Confirmed and/or paid expense
    RECURRING = "recurring"   # Repeats at a defined interval (e.g. daily tent hire)


class ExpenseSource(str, enum.Enum):
    """How the expense record was created — by the user or automatically by the platform."""
    MANUAL = "manual"                           # Customer entered directly in budget planner
    BOOKING = "booking"                         # Auto-created when a Booking is confirmed
    PAYMENT = "payment"                         # Auto-created when a Payment is captured
    VENDOR_ALLOCATION = "vendor_allocation"     # Derived from an internal vendor assignment
    PACKAGE_ALLOCATION = "package_allocation"   # Derived from a package item's pricing


class BudgetAlertLevel(str, enum.Enum):
    """Severity of a budget threshold alert sent to the customer."""
    INFO = "info"           # Healthy spend; informational nudge only
    WARNING = "warning"     # Approaching planned limit
    CRITICAL = "critical"   # At or exceeding planned budget


# ──────────────────────────────────────────────────────────────────────────────
# Common / Shared
# ──────────────────────────────────────────────────────────────────────────────

class AddressType(str, enum.Enum):
    HOME = "home"
    WORK = "work"
    EVENT_VENUE = "event_venue"
    BILLING = "billing"
    OTHER = "other"


class DayOfWeek(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    AED = "AED"
    SGD = "SGD"


class SortDirection(str, enum.Enum):
    """Generic sort direction for paginated list endpoints."""
    ASC = "asc"
    DESC = "desc"


class BannerType(str, enum.Enum):
    """Display style and purpose of a CMS-managed promotional banner."""
    HERO = "hero"                           # Full-width home-screen hero carousel
    PROMOTIONAL = "promotional"             # Discount, offer, or seasonal deal
    ANNOUNCEMENT = "announcement"           # Platform news or policy update
    VENDOR_SPOTLIGHT = "vendor_spotlight"   # Featured vendor promotion
    CATEGORY_FEATURE = "category_feature"  # Occasion or service-category highlight


class BannerTargetAudience(str, enum.Enum):
    """Customer segment that should see a given banner."""
    ALL = "all"
    CUSTOMERS = "customers"
    VENDORS = "vendors"
    PREMIUM_MEMBERS = "premium_members"     # Gold / Platinum tier members only
    NEW_USERS = "new_users"                 # Registered within the last 30 days
    RETURNING_USERS = "returning_users"     # Have at least one past booking


class FAQCategory(str, enum.Enum):
    """Topic domain that an FAQ entry belongs to."""
    GENERAL = "general"
    BOOKING = "booking"
    PAYMENT = "payment"
    VENDOR = "vendor"
    ACCOUNT = "account"
    MEMBERSHIP = "membership"
    CANCELLATION = "cancellation"
    REFERRAL = "referral"
    TECHNICAL = "technical"


class AppSettingDataType(str, enum.Enum):
    """
    Declared data type of an AppSetting value column.

    Used by the settings service to deserialize the TEXT-stored value
    into the appropriate Python type before handing it to callers.
    """
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    JSON = "json"
    LIST = "list"


class ContentStatus(str, enum.Enum):
    """
    Publication lifecycle state for CMS-managed content models
    (Banner, FAQ, TermsAndConditions, PrivacyPolicy).
    """
    DRAFT = "draft"           # Being authored; not visible to end-users
    PUBLISHED = "published"   # Live and visible to the target audience
    ARCHIVED = "archived"     # Withdrawn from public view; kept for history
    SCHEDULED = "scheduled"   # Set to auto-publish at display_start_at / effective_date


# ──────────────────────────────────────────────────────────────────────────────
# Admin
# ──────────────────────────────────────────────────────────────────────────────

class AdminStatus(str, enum.Enum):
    """Operational status of an Admin account."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"     # Access blocked pending investigation
    DEACTIVATED = "deactivated" # Off-boarded; soft-deleted record preserved


class AdminDepartment(str, enum.Enum):
    """Functional team within Tyohaar that the admin belongs to."""
    OPERATIONS = "operations"
    FINANCE = "finance"
    SUPPORT = "support"
    VENDOR_MANAGEMENT = "vendor_management"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    ENGINEERING = "engineering"
    MANAGEMENT = "management"


class PermissionAction(str, enum.Enum):
    """
    Granular action verbs for RBAC permission definitions.

    Every AdminPermission is a (resource, action) pair.
    'manage' is a meta-action meaning full CRUD + all sub-actions.
    """
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    ASSIGN = "assign"
    EXPORT = "export"
    IMPORT = "import"
    MANAGE = "manage"                       # Full access including special operations
    VIEW_REPORTS = "view_reports"
    SEND_NOTIFICATIONS = "send_notifications"


class PermissionResource(str, enum.Enum):
    """
    Platform entity types that can be governed by RBAC permissions.

    Each value maps to a distinct resource group in the admin panel.
    """
    USERS = "users"
    VENDORS = "vendors"
    BOOKINGS = "bookings"
    PAYMENTS = "payments"
    PACKAGES = "packages"
    OCCASIONS = "occasions"
    MEMBERSHIPS = "memberships"
    NOTIFICATIONS = "notifications"
    SUPPORT_TICKETS = "support_tickets"
    MEDIA = "media"
    REFERRALS = "referrals"
    BUDGETS = "budgets"
    ADMIN_USERS = "admin_users"
    ROLES = "roles"
    PERMISSIONS = "permissions"
    AUDIT_LOGS = "audit_logs"
    REPORTS = "reports"
    APP_SETTINGS = "app_settings"
    BANNERS = "banners"
    FAQS = "faqs"
    TERMS = "terms"
    CITIES = "cities"
    STATES = "states"
    COUPONS = "coupons"


class AuditAction(str, enum.Enum):
    """
    Action verbs recorded in the AuditLog.

    Every admin-initiated or system-initiated state change must produce
    an AuditLog row with one of these values.
    """
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    SOFT_DELETE = "soft_delete"
    RESTORE = "restore"           # Reverting a soft-delete
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    APPROVE = "approve"
    REJECT = "reject"
    EXPORT = "export"
    IMPORT = "import"
    ASSIGN = "assign"
    REVOKE = "revoke"
    SUSPEND = "suspend"
    ACTIVATE = "activate"
    ARCHIVE = "archive"
    VIEW_SENSITIVE = "view_sensitive"  # Explicit access to PII or financial data
    BULK_ACTION = "bulk_action"        # Batch operation on multiple entities
