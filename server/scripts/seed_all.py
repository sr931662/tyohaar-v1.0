"""
Full seed script for Tyohaar backend.

Run from the server/ directory:
    python scripts/seed_all.py

Seeds (in dependency order):
  1.  Admin roles + permissions
  2.  States + Cities
  3.  Common CMS  (Banners, FAQs, AppSettings, Terms, PrivacyPolicy)
  4.  Occasion taxonomy  (Categories, Themes, Moods, Tags, Occasions)
  5.  Vendor categories
  6.  Package categories
  7.  Budget expense categories
  8.  Membership plans
  9.  Notification templates
  10. Demo users  (1 superadmin, 2 customers, 2 vendors, 1 support agent)
  11. Admin record for superadmin
  12. Vendor profiles + services
  13. Wallets for all users
  14. One demo celebration per customer

All operations are idempotent — running the script multiple times is safe.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text

from app.core.config import settings  # noqa: loads .env
from app.db.session import AsyncSessionLocal
from app.models.admin.admin import Admin
from app.models.admin.permission import AdminPermission
from app.models.admin.role import AdminRole
from app.models.admin.role_permission import AdminRolePermission
from app.models.budgets.category import ExpenseCategory
from app.models.common.app_setting import AppSetting
from app.models.common.banner import Banner
from app.models.common.city import City
from app.models.common.faq import FAQ
from app.models.common.privacy_policy import PrivacyPolicy
from app.models.common.cancellation_policy import CancellationRefundPolicy
from app.models.common.state import State
from app.models.common.terms import TermsAndConditions
from app.models.memberships.membership_plan import MembershipPlan
from app.models.notifications.template import NotificationTemplate
from app.models.occasions.celebration import Celebration
from app.models.occasions.occasion import Occasion
from app.models.occasions.occasion_category import OccasionCategory
from app.models.occasions.occasion_mood import OccasionMood
from app.models.occasions.occasion_tag import OccasionTag
from app.models.occasions.occasion_theme import OccasionTheme
from app.models.packages.package_category import PackageCategory
from app.models.users.user import User
from app.models.vendors.vendor import Vendor
from app.models.vendors.vendor_category import VendorCategory
from app.models.vendors.vendor_profile import VendorProfile
from app.models.vendors.vendor_service import VendorService
from app.models.wallets.wallet import Wallet, WalletStatus
from app.models.enums import (
    AccountStatus,
    AdminDepartment,
    AdminStatus,
    AppSettingDataType,
    BannerTargetAudience,
    BannerType,
    BudgetCategory,
    CelebrationStatus,
    ContentStatus,
    Currency,
    FAQCategory,
    Language,
    LoginMethod,
    MembershipBillingCycle,
    MembershipTier,
    NotificationChannel,
    NotificationType,
    OccasionCategory as OccasionCategoryEnum,
    PackagePricingType,
    PermissionAction,
    PermissionResource,
    ServiceStatus,
    UserRole,
    UserType,
    VendorStatus,
    VendorType,
    VendorVerificationStatus,
    VerificationStatus,
    WalletType,
)

now = datetime.now(timezone.utc)

# ─────────────────────────────────────────────────────────────────────────────
# 1. ADMIN ROLES + PERMISSIONS
# ─────────────────────────────────────────────────────────────────────────────

ROLES = [
    dict(name="Super Admin",        slug="super_admin",        description="Full platform access. Bypasses all permission checks.", is_system=True, is_super_admin=True, is_active=True, priority_rank=1),
    dict(name="Operations Manager", slug="operations_manager", description="Booking fulfilment, vendor assignment, SLA management.",  is_system=True, is_super_admin=False, is_active=True, priority_rank=10),
    dict(name="Finance Manager",    slug="finance_manager",    description="Payments, settlements, refunds, invoicing.",              is_system=True, is_super_admin=False, is_active=True, priority_rank=20),
    dict(name="Support Agent",      slug="support_agent",      description="Support tickets, basic customer/vendor data lookup.",     is_system=True, is_super_admin=False, is_active=True, priority_rank=30),
    dict(name="Vendor Manager",     slug="vendor_manager",     description="Vendor onboarding, KYC review, account management.",     is_system=True, is_super_admin=False, is_active=True, priority_rank=40),
    dict(name="Marketing Manager",  slug="marketing_manager",  description="Banners, FAQs, coupons, notifications.",                 is_system=True, is_super_admin=False, is_active=True, priority_rank=50),
    dict(name="Analytics Viewer",   slug="analytics_viewer",   description="Read-only access to reports and dashboards.",            is_system=True, is_super_admin=False, is_active=True, priority_rank=60),
]

PERMISSIONS = [
    # (code, name, resource, action, group, description)
    ("users:read",          "Read Users",          PermissionResource.USERS,          PermissionAction.READ,         "User Management",      "View user accounts and profiles"),
    ("users:update",        "Update Users",        PermissionResource.USERS,          PermissionAction.UPDATE,       "User Management",      "Update user account details"),
    ("users:delete",        "Delete Users",        PermissionResource.USERS,          PermissionAction.DELETE,       "User Management",      "Deactivate or ban user accounts"),
    ("vendors:read",        "Read Vendors",        PermissionResource.VENDORS,        PermissionAction.READ,         "Vendor Management",    "View vendor accounts and profiles"),
    ("vendors:update",      "Update Vendors",      PermissionResource.VENDORS,        PermissionAction.UPDATE,       "Vendor Management",    "Update vendor account details"),
    ("vendors:approve",     "Approve Vendors",     PermissionResource.VENDORS,        PermissionAction.APPROVE,      "Vendor Management",    "Approve vendor KYC verification"),
    ("vendors:reject",      "Reject Vendors",      PermissionResource.VENDORS,        PermissionAction.REJECT,       "Vendor Management",    "Reject vendor KYC verification"),
    ("bookings:read",       "Read Bookings",       PermissionResource.BOOKINGS,       PermissionAction.READ,         "Booking Management",   "View bookings"),
    ("bookings:update",     "Update Bookings",     PermissionResource.BOOKINGS,       PermissionAction.UPDATE,       "Booking Management",   "Modify booking details"),
    ("bookings:assign",     "Assign Vendors",      PermissionResource.BOOKINGS,       PermissionAction.ASSIGN,       "Booking Management",   "Assign vendors to bookings"),
    ("payments:read",       "Read Payments",       PermissionResource.PAYMENTS,       PermissionAction.READ,         "Financial Operations", "View payment records"),
    ("payments:approve",    "Approve Payments",    PermissionResource.PAYMENTS,       PermissionAction.APPROVE,      "Financial Operations", "Approve payment settlements"),
    ("support_tickets:read",  "Read Tickets",      PermissionResource.SUPPORT_TICKETS,PermissionAction.READ,         "Support",              "View support tickets"),
    ("support_tickets:update","Update Tickets",    PermissionResource.SUPPORT_TICKETS,PermissionAction.UPDATE,       "Support",              "Reply to and close support tickets"),
    ("support_tickets:assign","Assign Tickets",    PermissionResource.SUPPORT_TICKETS,PermissionAction.ASSIGN,       "Support",              "Assign tickets to agents"),
    ("banners:read",        "Read Banners",        PermissionResource.BANNERS,        PermissionAction.READ,         "CMS",                  "View banners"),
    ("banners:manage",      "Manage Banners",      PermissionResource.BANNERS,        PermissionAction.MANAGE,       "CMS",                  "Create, update, publish banners"),
    ("faqs:read",           "Read FAQs",           PermissionResource.FAQS,           PermissionAction.READ,         "CMS",                  "View FAQs"),
    ("faqs:manage",         "Manage FAQs",         PermissionResource.FAQS,           PermissionAction.MANAGE,       "CMS",                  "Create, update, publish FAQs"),
    ("app_settings:read",   "Read Settings",       PermissionResource.APP_SETTINGS,   PermissionAction.READ,         "CMS",                  "View app settings"),
    ("app_settings:manage", "Manage Settings",     PermissionResource.APP_SETTINGS,   PermissionAction.MANAGE,       "CMS",                  "Update app configuration settings"),
    ("reports:view_reports","View Reports",        PermissionResource.REPORTS,        PermissionAction.VIEW_REPORTS, "Analytics",            "View reports and dashboards"),
    ("reports:export",      "Export Reports",      PermissionResource.REPORTS,        PermissionAction.EXPORT,       "Analytics",            "Export reports as CSV/Excel"),
    ("admin_users:manage",  "Manage Admins",       PermissionResource.ADMIN_USERS,    PermissionAction.MANAGE,       "Admin Management",     "Create, update, deactivate admin accounts"),
    ("roles:manage",        "Manage Roles",        PermissionResource.ROLES,          PermissionAction.MANAGE,       "Admin Management",     "Create and assign admin roles"),
    ("audit_logs:read",     "Read Audit Logs",     PermissionResource.AUDIT_LOGS,     PermissionAction.READ,         "Audit",                "View audit log entries"),
    ("notifications:manage","Manage Notifications",PermissionResource.NOTIFICATIONS,  PermissionAction.MANAGE,       "CMS",                  "Create and broadcast notifications"),
]

# role slug -> list of permission codes it gets
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "operations_manager": ["users:read", "vendors:read", "vendors:approve", "vendors:reject", "bookings:read", "bookings:update", "bookings:assign", "payments:read", "support_tickets:read", "support_tickets:update", "reports:view_reports"],
    "finance_manager":    ["payments:read", "payments:approve", "bookings:read", "reports:view_reports", "reports:export", "audit_logs:read"],
    "support_agent":      ["users:read", "vendors:read", "bookings:read", "support_tickets:read", "support_tickets:update", "support_tickets:assign"],
    "vendor_manager":     ["vendors:read", "vendors:update", "vendors:approve", "vendors:reject", "users:read"],
    "marketing_manager":  ["banners:read", "banners:manage", "faqs:read", "faqs:manage", "notifications:manage", "users:read", "reports:view_reports"],
    "analytics_viewer":   ["reports:view_reports", "bookings:read", "payments:read", "users:read"],
}


async def seed_roles_and_permissions(session) -> dict[str, AdminRole]:
    role_map: dict[str, AdminRole] = {}

    for r in ROLES:
        res = await session.execute(select(AdminRole).where(AdminRole.slug == r["slug"]))
        role = res.scalar_one_or_none()
        if not role:
            role = AdminRole(**r)
            session.add(role)
            await session.flush()
            print(f"  [+] AdminRole: {r['slug']}")
        else:
            print(f"  [~] AdminRole exists: {r['slug']}")
        role_map[r["slug"]] = role

    perm_map: dict[str, AdminPermission] = {}
    for code, name, resource, action, group, description in PERMISSIONS:
        res = await session.execute(select(AdminPermission).where(AdminPermission.code == code))
        perm = res.scalar_one_or_none()
        if not perm:
            perm = AdminPermission(code=code, name=name, resource=resource, action=action, group=group, description=description, is_active=True, is_system=True)
            session.add(perm)
            await session.flush()
            print(f"  [+] Permission: {code}")
        perm_map[code] = perm

    for role_slug, codes in ROLE_PERMISSIONS.items():
        role = role_map[role_slug]
        for code in codes:
            perm = perm_map[code]
            res = await session.execute(
                select(AdminRolePermission).where(
                    AdminRolePermission.role_id == role.id,
                    AdminRolePermission.permission_id == perm.id,
                )
            )
            if not res.scalar_one_or_none():
                session.add(AdminRolePermission(role_id=role.id, permission_id=perm.id))

    await session.flush()
    return role_map


# ─────────────────────────────────────────────────────────────────────────────
# 2. STATES + CITIES
# ─────────────────────────────────────────────────────────────────────────────

STATES_CITIES = [
    ("Maharashtra", "MH", [
        ("Mumbai",      "Mumbai",      "mumbai"),
        ("Pune",        "Pune",        "pune"),
        ("Nashik",      "Nashik",      "nashik"),
        ("Nagpur",      "Nagpur",      "nagpur"),
        ("Aurangabad",  "Aurangabad",  "aurangabad"),
    ]),
    ("Delhi", "DL", [
        ("New Delhi",   "New Delhi",   "new-delhi"),
        ("Dwarka",      "Dwarka",      "dwarka"),
        ("Rohini",      "Rohini",      "rohini"),
    ]),
    ("Karnataka", "KA", [
        ("Bengaluru",   "Bengaluru",   "bengaluru"),
        ("Mysuru",      "Mysuru",      "mysuru"),
        ("Hubli",       "Hubli",       "hubli"),
    ]),
    ("Tamil Nadu", "TN", [
        ("Chennai",     "Chennai",     "chennai"),
        ("Coimbatore",  "Coimbatore",  "coimbatore"),
        ("Madurai",     "Madurai",     "madurai"),
    ]),
    ("Gujarat", "GJ", [
        ("Ahmedabad",   "Ahmedabad",   "ahmedabad"),
        ("Surat",       "Surat",       "surat"),
        ("Vadodara",    "Vadodara",    "vadodara"),
    ]),
    ("Rajasthan", "RJ", [
        ("Jaipur",      "Jaipur",      "jaipur"),
        ("Jodhpur",     "Jodhpur",     "jodhpur"),
        ("Udaipur",     "Udaipur",     "udaipur"),
    ]),
    ("Telangana", "TG", [
        ("Hyderabad",   "Hyderabad",   "hyderabad"),
        ("Warangal",    "Warangal",    "warangal"),
    ]),
    ("West Bengal", "WB", [
        ("Kolkata",     "Kolkata",     "kolkata"),
        ("Howrah",      "Howrah",      "howrah"),
    ]),
    ("Uttar Pradesh", "UP", [
        ("Lucknow",     "Lucknow",     "lucknow"),
        ("Agra",        "Agra",        "agra"),
        ("Varanasi",    "Varanasi",    "varanasi"),
        ("Kanpur",      "Kanpur",      "kanpur"),
    ]),
    ("Punjab", "PB", [
        ("Amritsar",    "Amritsar",    "amritsar"),
        ("Ludhiana",    "Ludhiana",    "ludhiana"),
        ("Chandigarh",  "Chandigarh",  "chandigarh"),
    ]),
]


async def seed_states_cities(session) -> dict[str, State]:
    state_map: dict[str, State] = {}
    for state_name, code, cities in STATES_CITIES:
        res = await session.execute(select(State).where(State.code == code))
        state = res.scalar_one_or_none()
        if not state:
            state = State(name=state_name, code=code, is_active=True)
            session.add(state)
            await session.flush()
            print(f"  [+] State: {state_name}")
        state_map[code] = state

        for city_name, display_name, slug in cities:
            res = await session.execute(select(City).where(City.slug == slug))
            city = res.scalar_one_or_none()
            if not city:
                session.add(City(
                    state_id=state.id,
                    name=city_name,
                    display_name=display_name,
                    slug=slug,
                    is_active=True,
                    is_metro=city_name in ("Mumbai", "New Delhi", "Bengaluru", "Chennai", "Hyderabad", "Kolkata", "Ahmedabad", "Pune"),
                ))
    await session.flush()
    print(f"  [+] States & Cities seeded")
    return state_map


# ─────────────────────────────────────────────────────────────────────────────
# 3. COMMON CMS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_banners(session) -> None:
    banners = [
        dict(title="Celebrate Every Moment", subtitle="India's #1 event planning platform", banner_type=BannerType.HERO, target_audience=BannerTargetAudience.ALL, image_url="https://cdn.tyohaar.com/banners/hero-01.jpg", cta_label="Explore Packages", display_order=1, status=ContentStatus.PUBLISHED, is_active=True),
        dict(title="Book Your Dream Wedding", subtitle="Verified vendors. Transparent pricing.", banner_type=BannerType.HERO, target_audience=BannerTargetAudience.ALL, image_url="https://cdn.tyohaar.com/banners/hero-02.jpg", cta_label="Plan Now", display_order=2, status=ContentStatus.PUBLISHED, is_active=True),
        dict(title="Diwali Special 15% Off", subtitle="On all decoration packages. Limited time.", banner_type=BannerType.PROMOTIONAL, target_audience=BannerTargetAudience.ALL, image_url="https://cdn.tyohaar.com/banners/diwali-sale.jpg", cta_label="Grab Deal", display_order=1, status=ContentStatus.PUBLISHED, is_active=True),
        dict(title="Premium Member Offer", subtitle="Exclusive packages for Gold & Platinum members.", banner_type=BannerType.PROMOTIONAL, target_audience=BannerTargetAudience.PREMIUM_MEMBERS, image_url="https://cdn.tyohaar.com/banners/premium-offer.jpg", cta_label="Unlock Now", display_order=1, status=ContentStatus.PUBLISHED, is_active=True),
        dict(title="Spotlight: Raj Decorators", subtitle="Rated 4.9 stars across 500+ events.", banner_type=BannerType.VENDOR_SPOTLIGHT, target_audience=BannerTargetAudience.ALL, image_url="https://cdn.tyohaar.com/banners/vendor-spot.jpg", cta_label="View Profile", display_order=1, status=ContentStatus.PUBLISHED, is_active=True),
        dict(title="New: AI Budget Planner", subtitle="Get smart spending suggestions instantly.", banner_type=BannerType.ANNOUNCEMENT, target_audience=BannerTargetAudience.ALL, image_url="https://cdn.tyohaar.com/banners/ai-planner.jpg", cta_label="Try It", display_order=1, status=ContentStatus.PUBLISHED, is_active=True),
    ]
    for b in banners:
        res = await session.execute(select(Banner).where(Banner.title == b["title"]))
        if not res.scalar_one_or_none():
            session.add(Banner(**b))
    await session.flush()
    print(f"  [+] Banners: {len(banners)} seeded")


async def seed_faqs(session) -> None:
    faqs = [
        (FAQCategory.GENERAL,      "Tyohaar kya hai?",                              "Tyohaar ek online event planning platform hai jahan aap apni celebrations ke liye verified vendors book kar sakte hain."),
        (FAQCategory.GENERAL,      "Kya Tyohaar free hai?",                         "Haan, basic account bilkul free hai. Premium features ke liye Silver, Gold ya Platinum plan le sakte hain."),
        (FAQCategory.BOOKING,      "Booking kaise karein?",                          "Package select karein, date aur location choose karein, vendor confirm karein, aur payment karein."),
        (FAQCategory.BOOKING,      "Kya main booking reschedule kar sakta hoon?",   "Haan, event date se 7 din pehle tak reschedule free hai. Uske baad charges apply ho sakte hain."),
        (FAQCategory.PAYMENT,      "Kaunse payment methods accepted hain?",         "UPI, Credit/Debit Card, Net Banking, aur Tyohaar Wallet sab accepted hain."),
        (FAQCategory.PAYMENT,      "EMI available hai?",                             "Haan, 499 se upar ke bookings pe No-Cost EMI available hai select banks ke saath."),
        (FAQCategory.CANCELLATION, "Cancellation policy kya hai?",                  "Event se 15 din pehle — full refund. 7-14 din pehle — 50% refund. 7 din ke andar — refund nahi."),
        (FAQCategory.CANCELLATION, "Refund kab aata hai?",                          "Refund 5-7 business days mein aapke original payment method pe wapas aa jaata hai."),
        (FAQCategory.VENDOR,       "Vendors verified hain?",                        "Haan, har vendor ka KYC, GST verification, aur quality check kiya jaata hai."),
        (FAQCategory.VENDOR,       "Main khud vendor ban sakta hoon?",              "Bilkul! Vendor portal pe register karein, documents upload karein, aur verification ke baad aap live ho jaoge."),
        (FAQCategory.MEMBERSHIP,   "Membership ke kya fayde hain?",                 "Cashback, priority booking, exclusive packages, free digital invitations aur dedicated support — tier ke hisaab se."),
        (FAQCategory.MEMBERSHIP,   "Membership cancel kar sakte hain?",             "Haan, anytime cancel kar sakte hain. Remaining period ka pro-rated refund milega."),
        (FAQCategory.ACCOUNT,      "Password bhool gaya — kya karein?",             "Login page pe 'Forgot Password' click karein. OTP aapke registered phone/email pe aayega."),
        (FAQCategory.REFERRAL,     "Referral program kaise kaam karta hai?",        "Apna unique referral code share karein. Jab koi friend pehli booking kare, aap dono ko wallet credit milega."),
        (FAQCategory.TECHNICAL,    "App crash ho raha hai — kya karein?",          "App update karein ya reinstall karein. Problem persist kare toh support@tyohaar.com pe contact karein."),
    ]
    for category, question, answer in faqs:
        res = await session.execute(select(FAQ).where(FAQ.question == question))
        if not res.scalar_one_or_none():
            session.add(FAQ(faq_category=category, question=question, answer=answer, status=ContentStatus.PUBLISHED, is_active=True, display_order=0))
    await session.flush()
    print(f"  [+] FAQs: {len(faqs)} seeded")


async def seed_app_settings(session) -> None:
    settings_data = [
        ("otp_expiry_minutes",          "auth",         "OTP Expiry (minutes)",              AppSettingDataType.INTEGER, "10",    "OTP ki validity duration minutes mein"),
        ("otp_max_attempts",            "auth",         "OTP Max Attempts",                  AppSettingDataType.INTEGER, "5",     "Ek OTP pe maximum retry attempts"),
        ("login_lockout_minutes",       "auth",         "Login Lockout Duration (minutes)",  AppSettingDataType.INTEGER, "30",    "Failed logins ke baad lockout duration"),
        ("max_failed_login_attempts",   "auth",         "Max Failed Login Attempts",         AppSettingDataType.INTEGER, "5",     "Lockout trigger karne ke liye consecutive failures"),
        ("referral_reward_inr",         "referral",     "Referral Reward (INR)",             AppSettingDataType.FLOAT,   "100.0", "Successful referral pe wallet credit"),
        ("welcome_bonus_inr",           "wallet",       "Welcome Bonus (INR)",               AppSettingDataType.FLOAT,   "50.0",  "New user wallet welcome credit"),
        ("booking_cancellation_days_full_refund", "bookings", "Full Refund Window (days)",  AppSettingDataType.INTEGER, "15",    "Booking se kitne din pehle cancel karne pe full refund"),
        ("booking_cancellation_days_partial",     "bookings", "Partial Refund Window (days)", AppSettingDataType.INTEGER, "7",  "Booking se kitne din pehle cancel karne pe partial refund"),
        ("min_booking_advance_hours",   "bookings",     "Min Booking Advance (hours)",       AppSettingDataType.INTEGER, "24",    "Event se minimum kitne ghante pehle booking ho sakti hai"),
        ("platform_commission_pct",     "payments",     "Platform Commission (%)",           AppSettingDataType.FLOAT,   "10.0",  "Har booking pe platform commission percentage"),
        ("gst_rate_pct",                "payments",     "GST Rate (%)",                      AppSettingDataType.FLOAT,   "18.0",  "GST rate applied on platform fees"),
        ("support_sla_hours",           "support",      "Support SLA (hours)",               AppSettingDataType.INTEGER, "24",    "Ticket response ka SLA in hours"),
        ("max_images_per_vendor",       "media",        "Max Images per Vendor",             AppSettingDataType.INTEGER, "50",    "Vendor gallery mein maximum images"),
        ("invitation_credits_silver",   "memberships",  "Silver Invitation Credits",         AppSettingDataType.INTEGER, "5",     "Silver plan: free digital invitations per cycle"),
        ("invitation_credits_gold",     "memberships",  "Gold Invitation Credits",           AppSettingDataType.INTEGER, "15",    "Gold plan: free digital invitations per cycle"),
        ("invitation_credits_platinum", "memberships",  "Platinum Invitation Credits",       AppSettingDataType.INTEGER, "50",    "Platinum plan: free digital invitations per cycle"),
        ("maintenance_mode",            "system",       "Maintenance Mode",                  AppSettingDataType.BOOLEAN, "false", "True hone pe app read-only mode mein aa jaata hai"),
        ("allowed_origins",             "system",       "Allowed CORS Origins",              AppSettingDataType.LIST,    '["https://tyohaar.com","https://app.tyohaar.com"]', "Allowed CORS origins"),
    ]
    for key, group, label, data_type, value, description in settings_data:
        res = await session.execute(select(AppSetting).where(AppSetting.key == key))
        if not res.scalar_one_or_none():
            session.add(AppSetting(key=key, group=group, label=label, data_type=data_type, value=value, description=description, is_active=True, is_sensitive=False, is_readonly=False))
    await session.flush()
    print(f"  [+] AppSettings: {len(settings_data)} seeded")


async def seed_terms_privacy(session) -> None:
    res = await session.execute(select(TermsAndConditions).where(TermsAndConditions.version == "1.0.0"))
    if not res.scalar_one_or_none():
        session.add(TermsAndConditions(
            version="1.0.0", title="Terms & Conditions", language=Language.ENGLISH,
            content="<h1>Terms & Conditions</h1><p>By using Tyohaar, you agree to these terms. Tyohaar is a marketplace platform connecting customers with event service vendors. All bookings are subject to vendor availability and our cancellation policy.</p>",
            effective_date=date(2024, 1, 1), status=ContentStatus.PUBLISHED,
            summary="Platform usage terms, vendor marketplace rules, cancellation and refund policy.",
        ))
    res = await session.execute(select(TermsAndConditions).where(TermsAndConditions.version == "1.0.0-hi"))
    if not res.scalar_one_or_none():
        session.add(TermsAndConditions(
            version="1.0.0-hi", title="Niyam aur Sharten", language=Language.HINDI,
            content="<h1>Niyam aur Sharten</h1><p>Tyohaar ka upyog karke aap in niyamon se sahmat hain. Tyohaar ek marketplace platform hai jo customers ko event service vendors se jodta hai.</p>",
            effective_date=date(2024, 1, 1), status=ContentStatus.PUBLISHED,
            summary="Platform upyog ke niyam, vendor marketplace ke niyam, cancellation aur refund policy.",
        ))
    res = await session.execute(select(PrivacyPolicy).where(PrivacyPolicy.version == "1.0.0"))
    if not res.scalar_one_or_none():
        session.add(PrivacyPolicy(
            version="1.0.0", title="Privacy Policy", language=Language.ENGLISH,
            content="<h1>Privacy Policy</h1><p>Tyohaar collects only the information necessary to provide its services. We do not sell your personal data. Your phone number and email are used for authentication and booking communications only.</p>",
            effective_date=date(2024, 1, 1), status=ContentStatus.PUBLISHED,
            summary="We collect minimal data, never sell it, and protect it with industry-standard encryption.",
        ))
    res = await session.execute(select(CancellationRefundPolicy).where(CancellationRefundPolicy.version == "1.0.0"))
    if not res.scalar_one_or_none():
        session.add(CancellationRefundPolicy(
            version="1.0.0", title="Cancellation & Refund Policy", language=Language.ENGLISH,
            content=(
                "<h1>Cancellation & Refund Policy</h1>"
                "<p>You may request cancellation of a booking any time up to 48 hours before "
                "the scheduled event. Cancellations made within this window are subject to a "
                "10% cancellation fee, deducted from the refunded amount; the remainder is "
                "refunded to your original payment method.</p>"
                "<p>Members with an active plan that includes cancellation-fee protection have "
                "this fee waived automatically.</p>"
                "<p>Cancellation requests are reviewed by our team before a refund is processed. "
                "Refunds are typically credited within 5-7 business days of approval.</p>"
                "<p>Bookings cancelled within 48 hours of the scheduled event, or after the "
                "event has started, are not eligible for a refund.</p>"
            ),
            effective_date=date(2024, 1, 1), status=ContentStatus.PUBLISHED,
            summary="Cancel up to 48 hours before your event for a refund minus a 10% fee "
                    "(waived for protected members). No refund inside the 48-hour window.",
        ))
    await session.flush()
    print("  [+] Terms & Privacy Policy seeded")


# ─────────────────────────────────────────────────────────────────────────────
# 4. OCCASION TAXONOMY
# ─────────────────────────────────────────────────────────────────────────────

OCC_CATEGORIES = [
    # (name, slug, category_type, sort_order)
    ("Birthday",        "birthday",         OccasionCategoryEnum.LIFE_EVENT,     1),
    ("Wedding",         "wedding",          OccasionCategoryEnum.LIFE_EVENT,     2),
    ("Anniversary",     "anniversary",      OccasionCategoryEnum.LIFE_EVENT,     3),
    ("Baby Shower",     "baby-shower",      OccasionCategoryEnum.LIFE_EVENT,     4),
    ("Graduation",      "graduation",       OccasionCategoryEnum.LIFE_EVENT,     5),
    ("Engagement",      "engagement",       OccasionCategoryEnum.LIFE_EVENT,     6),
    ("Diwali",          "diwali",           OccasionCategoryEnum.MAJOR_FESTIVAL, 7),
    ("Holi",            "holi",             OccasionCategoryEnum.MAJOR_FESTIVAL, 8),
    ("Eid",             "eid",              OccasionCategoryEnum.MAJOR_FESTIVAL, 9),
    ("Christmas",       "christmas",        OccasionCategoryEnum.MAJOR_FESTIVAL, 10),
    ("Navratri",        "navratri",         OccasionCategoryEnum.MAJOR_FESTIVAL, 11),
    ("Ganesh Chaturthi","ganesh-chaturthi", OccasionCategoryEnum.MAJOR_FESTIVAL, 12),
    ("House Warming",   "house-warming",    OccasionCategoryEnum.LIFE_EVENT,     13),
    ("Retirement Party","retirement-party", OccasionCategoryEnum.PERSONAL,       14),
    ("Farewell Party",  "farewell-party",   OccasionCategoryEnum.PERSONAL,       15),
    ("Corporate Event", "corporate-event",  OccasionCategoryEnum.CORPORATE,      16),
    ("Kitty Party",     "kitty-party",      OccasionCategoryEnum.PERSONAL,       17),
    ("Pooja Ceremony",  "pooja-ceremony",   OccasionCategoryEnum.RELIGIOUS,      18),
]

THEMES = [
    ("Floral Fantasy",    "floral-fantasy"),
    ("Royal Rajasthani",  "royal-rajasthani"),
    ("Minimalist Chic",   "minimalist-chic"),
    ("Bollywood Bash",    "bollywood-bash"),
    ("Garden Party",      "garden-party"),
    ("Rustic Outdoor",    "rustic-outdoor"),
    ("Tropical Fiesta",   "tropical-fiesta"),
    ("Vintage Glamour",   "vintage-glamour"),
    ("Pastel Dreams",     "pastel-dreams"),
    ("Galaxy Night",      "galaxy-night"),
]

MOODS = [
    ("Joyful",       "joyful"),
    ("Romantic",     "romantic"),
    ("Elegant",      "elegant"),
    ("Energetic",    "energetic"),
    ("Intimate",     "intimate"),
    ("Traditional",  "traditional"),
    ("Quirky",       "quirky"),
    ("Sentimental",  "sentimental"),
]

TAGS = [
    ("Outdoor",        "outdoor"),
    ("Indoor",         "indoor"),
    ("Budget-Friendly","budget-friendly"),
    ("Luxury",         "luxury"),
    ("Kids",           "kids"),
    ("Adults-Only",    "adults-only"),
    ("Photography",    "photography"),
    ("Live Music",     "live-music"),
    ("DIY",            "diy"),
    ("Destination",    "destination"),
]

OCCASIONS = [
    ("Birthday Party",          "birthday-party",           "birthday"),
    ("Kids Birthday Party",     "kids-birthday-party",      "birthday"),
    ("Milestone Birthday (18+)","milestone-birthday",       "birthday"),
    ("Wedding Ceremony",        "wedding-ceremony",         "wedding"),
    ("Wedding Reception",       "wedding-reception",        "wedding"),
    ("Mehndi Ceremony",         "mehndi-ceremony",          "wedding"),
    ("Sangeet Night",           "sangeet-night",            "wedding"),
    ("Haldi Ceremony",          "haldi-ceremony",           "wedding"),
    ("Anniversary Dinner",      "anniversary-dinner",       "anniversary"),
    ("Baby Shower",             "baby-shower-party",        "baby-shower"),
    ("Graduation Party",        "graduation-party",         "graduation"),
    ("Engagement Party",        "engagement-party",         "engagement"),
    ("Diwali Celebration",      "diwali-celebration",       "diwali"),
    ("Holi Party",              "holi-party",               "holi"),
    ("Corporate Annual Day",    "corporate-annual-day",     "corporate-event"),
    ("House Warming Pooja",     "house-warming-pooja",      "house-warming"),
]


async def seed_occasion_taxonomy(session) -> dict[str, Occasion]:
    # Categories
    cat_map: dict[str, OccasionCategory] = {}
    for name, slug, cat_type, sort_order in OCC_CATEGORIES:
        res = await session.execute(select(OccasionCategory).where(OccasionCategory.slug == slug))
        obj = res.scalar_one_or_none()
        if not obj:
            obj = OccasionCategory(name=name, slug=slug, category_type=cat_type, sort_order=sort_order, is_active=True)
            session.add(obj)
        cat_map[slug] = obj
    await session.flush()

    # Themes
    for name, slug in THEMES:
        res = await session.execute(select(OccasionTheme).where(OccasionTheme.slug == slug))
        if not res.scalar_one_or_none():
            session.add(OccasionTheme(name=name, slug=slug, is_active=True))
    await session.flush()

    # Moods
    for name, slug in MOODS:
        res = await session.execute(select(OccasionMood).where(OccasionMood.slug == slug))
        if not res.scalar_one_or_none():
            session.add(OccasionMood(name=name, slug=slug, is_active=True))
    await session.flush()

    # Tags
    for name, slug in TAGS:
        res = await session.execute(select(OccasionTag).where(OccasionTag.slug == slug))
        if not res.scalar_one_or_none():
            session.add(OccasionTag(name=name, slug=slug))
    await session.flush()

    # Occasions
    occ_map: dict[str, Occasion] = {}
    for name, slug, cat_slug in OCCASIONS:
        res = await session.execute(select(Occasion).where(Occasion.slug == slug))
        obj = res.scalar_one_or_none()
        if not obj:
            obj = Occasion(
                name=name, slug=slug, is_active=True,
                category_id=cat_map[cat_slug].id if cat_slug in cat_map else None,
            )
            session.add(obj)
            await session.flush()
        occ_map[slug] = obj

    print(f"  [+] Occasion taxonomy seeded ({len(OCC_CATEGORIES)} categories, {len(OCCASIONS)} occasions)")
    return occ_map


# ─────────────────────────────────────────────────────────────────────────────
# 5. VENDOR CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

VENDOR_CATEGORIES = [
    ("Photographer",       "photographer",       "Photography & Videography",  1),
    ("Videographer",       "videographer",       "Photography & Videography",  2),
    ("Decorator",          "decorator",          "Decoration & Styling",       3),
    ("Florist",            "florist",            "Decoration & Styling",       4),
    ("Caterer",            "caterer",            "Food & Beverage",            5),
    ("Baker",              "baker",              "Food & Beverage",            6),
    ("DJ & Music",         "dj-music",           "Entertainment",              7),
    ("Live Band",          "live-band",          "Entertainment",              8),
    ("Comedian / Anchor",  "comedian-anchor",    "Entertainment",              9),
    ("Makeup Artist",      "makeup-artist",      "Beauty & Grooming",          10),
    ("Mehndi Artist",      "mehndi-artist",      "Beauty & Grooming",          11),
    ("Venue",              "venue",              "Venue",                      12),
    ("Event Planner",      "event-planner",      "Planning & Coordination",    13),
    ("Invitation Designer","invitation-designer","Stationery & Invites",       14),
    ("Photo Booth",        "photo-booth",        "Entertainment",              15),
    ("Bouncy Castle",      "bouncy-castle",      "Kids Entertainment",         16),
]


async def seed_vendor_categories(session) -> dict[str, VendorCategory]:
    vc_map: dict[str, VendorCategory] = {}
    for name, slug, description, sort_order in VENDOR_CATEGORIES:
        res = await session.execute(select(VendorCategory).where(VendorCategory.slug == slug))
        obj = res.scalar_one_or_none()
        if not obj:
            obj = VendorCategory(name=name, slug=slug, description=description, sort_order=sort_order, is_active=True)
            session.add(obj)
            await session.flush()
        vc_map[slug] = obj
    print(f"  [+] Vendor categories: {len(VENDOR_CATEGORIES)} seeded")
    return vc_map


# ─────────────────────────────────────────────────────────────────────────────
# 6. PACKAGE CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

PKG_CATEGORIES = [
    ("Wedding Packages",         "wedding-packages",         "Complete wedding planning solutions"),
    ("Birthday Packages",        "birthday-packages",        "Birthday celebration bundles"),
    ("Anniversary Packages",     "anniversary-packages",     "Anniversary celebration bundles"),
    ("Festival Packages",        "festival-packages",        "Festive celebration packages"),
    ("Corporate Packages",       "corporate-packages",       "Corporate event solutions"),
    ("Baby Shower Packages",     "baby-shower-packages",     "Baby shower planning bundles"),
    ("Photography Packages",     "photography-packages",     "Photography & videography combos"),
    ("Decoration Packages",      "decoration-packages",      "Decoration & styling bundles"),
    ("Catering Packages",        "catering-packages",        "Food & beverage bundles"),
]


async def seed_package_categories(session) -> dict[str, PackageCategory]:
    pc_map: dict[str, PackageCategory] = {}
    for name, slug, description in PKG_CATEGORIES:
        res = await session.execute(select(PackageCategory).where(PackageCategory.slug == slug))
        obj = res.scalar_one_or_none()
        if not obj:
            obj = PackageCategory(name=name, slug=slug, description=description, is_active=True)
            session.add(obj)
            await session.flush()
        pc_map[slug] = obj
    print(f"  [+] Package categories: {len(PKG_CATEGORIES)} seeded")
    return pc_map


# ─────────────────────────────────────────────────────────────────────────────
# 7. BUDGET EXPENSE CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

EXPENSE_CATS = [
    (BudgetCategory.DECORATION,     "Decoration",     "decoration",     "#FF6B6B", 1),
    (BudgetCategory.CATERING,       "Catering",       "catering",       "#4ECDC4", 2),
    (BudgetCategory.PHOTOGRAPHY,    "Photography",    "photography",    "#45B7D1", 3),
    (BudgetCategory.VIDEOGRAPHY,    "Videography",    "videography",    "#96CEB4", 4),
    (BudgetCategory.CAKE,           "Cake",           "cake",           "#FFEAA7", 5),
    (BudgetCategory.BOUQUET,        "Bouquet",        "bouquet",        "#DDA0DD", 6),
    (BudgetCategory.ENTERTAINMENT,  "Entertainment",  "entertainment",  "#F7DC6F", 7),
    (BudgetCategory.VENUE,          "Venue",          "venue",          "#82E0AA", 8),
    (BudgetCategory.INVITATION,     "Invitation",     "invitation",     "#AED6F1", 9),
    (BudgetCategory.GIFTS,          "Gifts",          "gifts",          "#F1948A", 10),
    (BudgetCategory.TRANSPORT,      "Transport",      "transport",      "#85C1E9", 11),
    (BudgetCategory.ATTIRE,         "Attire",         "attire",         "#C39BD3", 12),
    (BudgetCategory.MAKEUP,         "Makeup",         "makeup",         "#F9E79F", 13),
    (BudgetCategory.MISCELLANEOUS,  "Miscellaneous",  "miscellaneous",  "#BDC3C7", 14),
]


async def seed_budget_categories(session) -> None:
    for system_category, name, slug, color_hex, display_order in EXPENSE_CATS:
        res = await session.execute(select(ExpenseCategory).where(ExpenseCategory.slug == slug))
        if not res.scalar_one_or_none():
            session.add(ExpenseCategory(
                name=name, slug=slug, system_category=system_category,
                is_system=True, is_active=True,
                color_hex=color_hex, display_order=display_order,
            ))
    await session.flush()
    print(f"  [+] Budget expense categories: {len(EXPENSE_CATS)} seeded")


# ─────────────────────────────────────────────────────────────────────────────
# 8. MEMBERSHIP PLANS
# ─────────────────────────────────────────────────────────────────────────────

PLANS = [
    dict(
        tier=MembershipTier.FREE, name="Free",  slug="free",
        tagline="Get started for free",
        description="Access to basic event planning features and standard vendor catalog.",
        monthly_price=Decimal("0"),    yearly_price=Decimal("0"),
        cashback_percentage=Decimal("0"),   discount_percentage=Decimal("0"),
        reward_multiplier=Decimal("1.0"),   wallet_bonus=Decimal("0"),
        free_invitations_count=0, customer_support_priority=1,
        priority_booking=False, has_exclusive_packages=False, cancellation_protection=False,
        is_active=True, display_order=1,
        can_upgrade_to_tier=MembershipTier.SILVER,
    ),
    dict(
        tier=MembershipTier.SILVER, name="Silver", slug="silver",
        tagline="For frequent celebrators",
        description="Cashback on bookings, 5 free digital invitations, and priority support.",
        monthly_price=Decimal("199"),  yearly_price=Decimal("1999"),
        cashback_percentage=Decimal("3"),    discount_percentage=Decimal("5"),
        reward_multiplier=Decimal("1.5"),   wallet_bonus=Decimal("100"),
        free_invitations_count=5, customer_support_priority=2,
        priority_booking=False, has_exclusive_packages=False, cancellation_protection=False,
        is_active=True, display_order=1,
        can_upgrade_to_tier=MembershipTier.GOLD,
        can_downgrade_to_tier=MembershipTier.FREE,
    ),
    dict(
        tier=MembershipTier.GOLD, name="Gold", slug="gold",
        tagline="For the true celebration enthusiast",
        description="5% cashback, exclusive packages, 15 free invitations, and double rewards.",
        monthly_price=Decimal("499"),  yearly_price=Decimal("4999"),
        cashback_percentage=Decimal("5"),    discount_percentage=Decimal("10"),
        reward_multiplier=Decimal("2.0"),   wallet_bonus=Decimal("250"),
        free_invitations_count=15, customer_support_priority=2,
        priority_booking=True, has_exclusive_packages=True, cancellation_protection=False,
        is_active=True, display_order=2,
        can_upgrade_to_tier=MembershipTier.PLATINUM,
        can_downgrade_to_tier=MembershipTier.SILVER,
    ),
    dict(
        tier=MembershipTier.PLATINUM, name="Platinum", slug="platinum",
        tagline="The ultimate celebration experience",
        description="10% cashback, dedicated CSR, unlimited invitations, and cancellation protection.",
        monthly_price=Decimal("999"),  yearly_price=Decimal("9999"),
        cashback_percentage=Decimal("10"),   discount_percentage=Decimal("15"),
        reward_multiplier=Decimal("3.0"),   wallet_bonus=Decimal("500"),
        free_invitations_count=50, customer_support_priority=3,
        priority_booking=True, has_exclusive_packages=True, cancellation_protection=True,
        is_active=True, display_order=1,
        can_downgrade_to_tier=MembershipTier.GOLD,
    ),
]


async def seed_membership_plans(session) -> None:
    for plan_data in PLANS:
        res = await session.execute(select(MembershipPlan).where(MembershipPlan.slug == plan_data["slug"]))
        if not res.scalar_one_or_none():
            session.add(MembershipPlan(**plan_data))
    await session.flush()
    print(f"  [+] Membership plans: {len(PLANS)} seeded (Free / Silver / Gold / Platinum)")


# ─────────────────────────────────────────────────────────────────────────────
# 9. NOTIFICATION TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

NOTIF_TEMPLATES = [
    # (template_key, channel, language, notification_category, title, body)
    ("otp",              NotificationChannel.EMAIL,    "en", NotificationType.OTP,              "Your Tyohaar OTP",           "Hi {{name}}, your OTP is {{otp}}. Valid for {{expiry_minutes}} minutes. Do not share it with anyone."),
    ("otp",              NotificationChannel.SMS,      "en", NotificationType.OTP,              "Tyohaar OTP",                "{{otp}} is your Tyohaar OTP. Valid for {{expiry_minutes}} mins. Do NOT share. -Tyohaar"),
    ("otp",              NotificationChannel.EMAIL,    "hi", NotificationType.OTP,              "Aapka Tyohaar OTP",          "Namaste {{name}}, aapka OTP hai {{otp}}. Yeh {{expiry_minutes}} minute mein expire ho jaega. Kisi ke saath share mat karein."),
    ("booking_confirmed",NotificationChannel.EMAIL,    "en", NotificationType.BOOKING_CONFIRMED,"Booking Confirmed!",          "Hi {{name}}, your booking #{{booking_number}} for {{occasion}} on {{event_date}} is confirmed. Vendor: {{vendor_name}}. Total: {{amount}}."),
    ("booking_confirmed",NotificationChannel.SMS,      "en", NotificationType.BOOKING_CONFIRMED,"Booking Confirmed",           "Tyohaar: Booking #{{booking_number}} confirmed for {{event_date}}. Vendor: {{vendor_name}}. Details on app."),
    ("booking_confirmed",NotificationChannel.PUSH,     "en", NotificationType.BOOKING_CONFIRMED,"Booking Confirmed!",          "Your {{occasion}} booking for {{event_date}} is all set!"),
    ("booking_confirmed",NotificationChannel.WHATSAPP, "en", NotificationType.BOOKING_CONFIRMED,"Booking Confirmed!",          "Congratulations! Your booking #{{booking_number}} for *{{occasion}}* on {{event_date}} is confirmed.\n\n*Vendor:* {{vendor_name}}\n*Amount:* {{amount}}\n\nView details: {{booking_url}}"),
    ("booking_cancelled",NotificationChannel.EMAIL,    "en", NotificationType.BOOKING_CANCELLED,"Booking Cancelled",           "Hi {{name}}, your booking #{{booking_number}} has been cancelled. Refund of {{refund_amount}} will be processed in 5-7 business days."),
    ("booking_cancelled",NotificationChannel.PUSH,     "en", NotificationType.BOOKING_CANCELLED,"Booking Cancelled",           "Booking #{{booking_number}} cancelled. Refund: {{refund_amount}}."),
    ("payment_received", NotificationChannel.EMAIL,    "en", NotificationType.PAYMENT_RECEIVED, "Payment Received",            "Hi {{name}}, we received your payment of {{amount}} for booking #{{booking_number}}. Transaction ID: {{transaction_id}}."),
    ("payment_received", NotificationChannel.PUSH,     "en", NotificationType.PAYMENT_RECEIVED, "Payment Successful!",         "Payment of {{amount}} received for booking #{{booking_number}}."),
    ("payment_failed",   NotificationChannel.EMAIL,    "en", NotificationType.PAYMENT_FAILED,   "Payment Failed",              "Hi {{name}}, your payment of {{amount}} for booking #{{booking_number}} failed. Please retry or contact support."),
    ("payment_failed",   NotificationChannel.PUSH,     "en", NotificationType.PAYMENT_FAILED,   "Payment Failed",              "Payment of {{amount}} failed. Tap to retry."),
    ("refund_initiated", NotificationChannel.EMAIL,    "en", NotificationType.REFUND_INITIATED, "Refund Initiated",            "Hi {{name}}, refund of {{refund_amount}} for booking #{{booking_number}} has been initiated. Expected: 5-7 business days."),
    ("wallet_credit",    NotificationChannel.PUSH,     "en", NotificationType.WALLET_CREDIT,    "Wallet Credited!",            "{{amount}} added to your Tyohaar Wallet. New balance: {{balance}}."),
    ("celebration_upcoming",NotificationChannel.PUSH,  "en", NotificationType.CELEBRATION_UPCOMING,"Celebration Coming Up!",  "{{occasion}} is in {{days}} days! Check your bookings and make sure everything is set."),
    ("membership_expiring",NotificationChannel.EMAIL,  "en", NotificationType.MEMBERSHIP_EXPIRING,"Your Membership is Expiring","Hi {{name}}, your {{tier}} membership expires on {{expiry_date}}. Renew now to keep your benefits."),
    ("membership_expiring",NotificationChannel.PUSH,   "en", NotificationType.MEMBERSHIP_EXPIRING,"Membership Expiring Soon",  "Your {{tier}} plan expires in {{days}} days. Renew now!"),
    ("support_update",   NotificationChannel.EMAIL,    "en", NotificationType.SUPPORT_UPDATE,   "Support Ticket Updated",      "Hi {{name}}, your support ticket #{{ticket_number}} has been updated. Status: {{status}}. Reply: {{agent_message}}."),
    ("support_update",   NotificationChannel.PUSH,     "en", NotificationType.SUPPORT_UPDATE,   "Ticket Update",               "Ticket #{{ticket_number}}: {{status}}. Tap to view."),
    ("vendor_assigned",  NotificationChannel.PUSH,     "en", NotificationType.VENDOR_ASSIGNED,  "Vendor Assigned!",            "{{vendor_name}} has been assigned to your {{occasion}} on {{event_date}}."),
    ("review_request",   NotificationChannel.EMAIL,    "en", NotificationType.REVIEW_REQUEST,   "How was your experience?",    "Hi {{name}}, your {{occasion}} is over! Share your experience with {{vendor_name}} and help others plan their celebrations."),
    ("review_request",   NotificationChannel.PUSH,     "en", NotificationType.REVIEW_REQUEST,   "Rate your experience",        "How was {{vendor_name}} for your {{occasion}}? Tap to rate."),
]


async def seed_notification_templates(session) -> None:
    for key, channel, lang, notif_type, title, body in NOTIF_TEMPLATES:
        res = await session.execute(
            select(NotificationTemplate).where(
                NotificationTemplate.template_key == key,
                NotificationTemplate.channel == channel,
                NotificationTemplate.language == lang,
            )
        )
        if not res.scalar_one_or_none():
            session.add(NotificationTemplate(
                template_key=key, channel=channel, language=lang,
                notification_category=notif_type,
                title_template=title, body_template=body,
                version=1, is_active=True,
            ))
    await session.flush()
    print(f"  [+] Notification templates: {len(NOTIF_TEMPLATES)} seeded")


# ─────────────────────────────────────────────────────────────────────────────
# 10. DEMO USERS
# ─────────────────────────────────────────────────────────────────────────────

DEMO_USERS = [
    # (phone, email, full_name, role, type)
    ("+919999999999", "admin@tyohaar.com",    "Arjun Sharma",    UserRole.SUPER_ADMIN, UserType.INDIVIDUAL),
    ("+919876543210", "priya@example.com",    "Priya Mehta",     UserRole.CUSTOMER,    UserType.INDIVIDUAL),
    ("+919876543211", "rahul@example.com",    "Rahul Gupta",     UserRole.CUSTOMER,    UserType.INDIVIDUAL),
    ("+919876543212", "vendor1@example.com",  "Raj Decorators",  UserRole.VENDOR,      UserType.BUSINESS),
    ("+919876543213", "vendor2@example.com",  "Capture Moments", UserRole.VENDOR,      UserType.BUSINESS),
    ("+919876543214", "support@tyohaar.com",  "Sneha Joshi",     UserRole.SUPPORT,     UserType.INDIVIDUAL),
]


async def seed_users(session) -> dict[str, User]:
    user_map: dict[str, User] = {}
    for phone, email, full_name, role, user_type in DEMO_USERS:
        res = await session.execute(select(User).where(User.phone == phone))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                phone=phone, email=email, full_name=full_name,
                role=role, user_type=user_type,
                account_status=AccountStatus.ACTIVE,
                verification_status=VerificationStatus.VERIFIED,
                primary_login_provider=LoginMethod.OTP_EMAIL,
                phone_verified=True, email_verified=True, mfa_enabled=False,
            )
            session.add(user)
            await session.flush()
            print(f"  [+] User: {full_name} ({role.value})")
        user_map[phone] = user
    return user_map


# ─────────────────────────────────────────────────────────────────────────────
# 11. ADMIN RECORD FOR SUPERADMIN
# ─────────────────────────────────────────────────────────────────────────────

async def seed_admin_record(session, user_map: dict[str, User], role_map: dict[str, AdminRole]) -> None:
    superadmin_user = user_map["+919999999999"]
    superadmin_role = role_map["super_admin"]

    async def _create_admin_if_not_exists(user, role, employee_id, department, designation, work_email, **flags):
        res = await session.execute(select(Admin).where(Admin.user_id == user.id))
        if res.scalar_one_or_none():
            print(f"  [~] Admin record exists for {work_email}")
            return
        # Also check employee_id uniqueness to avoid conflict with seed_admin.py
        res2 = await session.execute(select(Admin).where(Admin.employee_id == employee_id))
        eid = None if res2.scalar_one_or_none() else employee_id
        session.add(Admin(
            user_id=user.id, role_id=role.id,
            employee_id=eid, department=department,
            designation=designation, work_email=work_email,
            admin_status=AdminStatus.ACTIVE, mfa_enforced=False, **flags,
        ))
        await session.flush()
        print(f"  [+] Admin record created for {work_email}")

    await _create_admin_if_not_exists(
        superadmin_user, superadmin_role, "TYH-001",
        AdminDepartment.MANAGEMENT, "Superadmin", "admin@tyohaar.com",
        can_impersonate=True, can_access_financials=True, can_export_data=True,
    )

    support_user = user_map["+919876543214"]
    support_role = role_map["support_agent"]
    await _create_admin_if_not_exists(
        support_user, support_role, "TYH-002",
        AdminDepartment.SUPPORT, "Support Agent", "support@tyohaar.com",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 12. VENDOR PROFILES + SERVICES
# ─────────────────────────────────────────────────────────────────────────────

async def seed_vendors(session, user_map: dict[str, User], vc_map: dict[str, VendorCategory]) -> dict[str, Vendor]:
    vendor_data = [
        ("+919876543212", "Raj Decorators Pvt. Ltd.", VendorType.DECORATOR, "GST27ABCDE1234F1Z5", "Mumbai", [
            ("Grand Floral Setup",       "decorator",    PackagePricingType.FIXED,      Decimal("15000")),
            ("Stage & Backdrop Design",  "decorator",    PackagePricingType.CUSTOM_QUOTE, Decimal("25000")),
            ("Table Centrepiece Setup",  "decorator",    PackagePricingType.PER_PERSON,  Decimal("300")),
        ]),
        ("+919876543213", "Capture Moments Studio",  VendorType.PHOTOGRAPHER, "GST29XYZAB1234G2H6", "Bengaluru", [
            ("Wedding Photography",      "photographer", PackagePricingType.FIXED,      Decimal("35000")),
            ("Birthday Photo Shoot",     "photographer", PackagePricingType.FIXED,      Decimal("8000")),
            ("Videography + Editing",    "videographer", PackagePricingType.FIXED,      Decimal("20000")),
        ]),
    ]

    vendor_map: dict[str, Vendor] = {}
    for phone, biz_name, vendor_type, gst, city, services in vendor_data:
        user = user_map[phone]
        res = await session.execute(select(Vendor).where(Vendor.user_id == user.id))
        vendor = res.scalar_one_or_none()
        if not vendor:
            vendor = Vendor(
                user_id=user.id, business_name=biz_name, vendor_type=vendor_type,
                status=VendorStatus.ACTIVE, verification_status=VendorVerificationStatus.VERIFIED,
                gst_number=gst, is_active=True, average_rating=4.7, review_count=0,
            )
            session.add(vendor)
            await session.flush()
            print(f"  [+] Vendor: {biz_name}")

            session.add(VendorProfile(
                vendor_id=vendor.id,
                about=f"{biz_name} — trusted by 500+ happy customers across India.",
                tagline=f"Making your celebrations unforgettable.",
                operating_cities=[city],
            ))
            await session.flush()

        vendor_map[phone] = vendor

        for svc_name, cat_slug, pricing_type, base_price in services:
            cat = vc_map.get(cat_slug)
            if not cat:
                continue
            res = await session.execute(
                select(VendorService).where(
                    VendorService.vendor_id == vendor.id,
                    VendorService.name == svc_name,
                )
            )
            if not res.scalar_one_or_none():
                session.add(VendorService(
                    vendor_id=vendor.id, category_id=cat.id,
                    name=svc_name, pricing_type=pricing_type, base_price=base_price,
                    status=ServiceStatus.ACTIVE, is_active=True,
                ))
    await session.flush()
    return vendor_map


# ─────────────────────────────────────────────────────────────────────────────
# 13. WALLETS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_wallets(session, user_map: dict[str, User]) -> None:
    wallet_balances = {
        "+919999999999": (Decimal("0"),      WalletType.CUSTOMER),
        "+919876543210": (Decimal("350.00"), WalletType.CUSTOMER),
        "+919876543211": (Decimal("100.00"), WalletType.CUSTOMER),
        "+919876543212": (Decimal("0"),      WalletType.VENDOR),
        "+919876543213": (Decimal("0"),      WalletType.VENDOR),
        "+919876543214": (Decimal("0"),      WalletType.CUSTOMER),
    }
    for phone, (balance, wallet_type) in wallet_balances.items():
        user = user_map[phone]
        res = await session.execute(select(Wallet).where(Wallet.user_id == user.id))
        if not res.scalar_one_or_none():
            session.add(Wallet(
                user_id=user.id, wallet_type=wallet_type,
                wallet_status=WalletStatus.ACTIVE, currency=Currency.INR,
                available_balance=balance, pending_balance=Decimal("0"),
                locked_balance=Decimal("0"), promotional_balance=Decimal("0"),
                lifetime_credits=balance, lifetime_debits=Decimal("0"),
                lifetime_cashback=Decimal("0"), reward_points=0, is_on_hold=False,
            ))
    await session.flush()
    print(f"  [+] Wallets seeded for {len(wallet_balances)} users")


# ─────────────────────────────────────────────────────────────────────────────
# 14. DEMO CELEBRATIONS
# ─────────────────────────────────────────────────────────────────────────────

async def seed_celebrations(session, user_map: dict[str, User], occ_map: dict[str, Occasion]) -> None:
    celebrations = [
        ("+919876543210", "birthday-party",     "Priya's 30th Birthday Bash",    date(2026, 8, 15), CelebrationStatus.PLANNING, Decimal("50000")),
        ("+919876543210", "wedding-reception",  "Priya & Rohan's Reception",      date(2026, 12, 5), CelebrationStatus.DRAFT,    Decimal("300000")),
        ("+919876543211", "anniversary-dinner", "Our 5th Anniversary Dinner",     date(2026, 9, 20), CelebrationStatus.CONFIRMED,Decimal("25000")),
    ]
    for phone, occ_slug, title, event_date, status, budget in celebrations:
        user = user_map[phone]
        occasion = occ_map.get(occ_slug)
        if not occasion:
            continue
        res = await session.execute(
            select(Celebration).where(
                Celebration.customer_id == user.id,
                Celebration.title == title,
            )
        )
        if not res.scalar_one_or_none():
            session.add(Celebration(
                customer_id=user.id, occasion_id=occasion.id,
                title=title, celebration_date=event_date,
                status=status, currency=Currency.INR,
                guest_count=50, estimated_budget=budget,
            ))
    await session.flush()
    print("  [+] Demo celebrations: 3 seeded")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n=== Tyohaar — Full Seed ===\n")

    async with AsyncSessionLocal() as session:
        async with session.begin():
            print(">> Admin roles & permissions")
            role_map = await seed_roles_and_permissions(session)

            print("\n>> States & Cities")
            state_map = await seed_states_cities(session)

            print("\n>> Common CMS")
            await seed_banners(session)
            await seed_faqs(session)
            await seed_app_settings(session)
            await seed_terms_privacy(session)

            print("\n>> Occasion taxonomy")
            occ_map = await seed_occasion_taxonomy(session)

            print("\n>> Vendor categories")
            vc_map = await seed_vendor_categories(session)

            print("\n>> Package categories")
            await seed_package_categories(session)

            print("\n>> Budget expense categories")
            await seed_budget_categories(session)

            print("\n>> Membership plans")
            await seed_membership_plans(session)

            print("\n>> Notification templates")
            await seed_notification_templates(session)

            print("\n>> Demo users")
            user_map = await seed_users(session)

            print("\n>> Admin records")
            await seed_admin_record(session, user_map, role_map)

            print("\n>> Vendors & services")
            await seed_vendors(session, user_map, vc_map)

            print("\n>> Wallets")
            await seed_wallets(session, user_map)

            print("\n>> Demo celebrations")
            await seed_celebrations(session, user_map, occ_map)

    print("\n=== Seed complete! ===")
    print("\nDemo accounts (all login via OTP to their email):")
    print("  Superadmin  : admin@tyohaar.com       (+919999999999)")
    print("  Customer 1  : priya@example.com        (+919876543210)")
    print("  Customer 2  : rahul@example.com        (+919876543211)")
    print("  Vendor 1    : vendor1@example.com      (+919876543212)")
    print("  Vendor 2    : vendor2@example.com      (+919876543213)")
    print("  Support     : support@tyohaar.com      (+919876543214)")
    print()


if __name__ == "__main__":
    asyncio.run(main())
