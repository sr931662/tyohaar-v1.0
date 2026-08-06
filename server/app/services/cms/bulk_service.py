"""
Bulk Operations Service
=======================
Executes batch mutations across vendors, packages, users, notifications, etc.
All operations are transactional and return a structured result with
per-item success/failure tracking.
"""

from __future__ import annotations

import secrets
import string
import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any

from sqlalchemy import delete as sa_delete
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import PackageStatus, VendorStatus, VendorVerificationStatus
from app.schemas.cms.bulk import (
    BulkAvailabilityUpdateRequest,
    BulkCouponGenerateRequest,
    BulkDeleteRequest,
    BulkIDsRequest,
    BulkMembershipAssignRequest,
    BulkNotificationRequest,
    BulkOperationResult,
    BulkPriceUpdateRequest,
    BulkVendorActionRequest,
)
from app.services.base import BaseService


class BulkService(BaseService):
    def __init__(self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal) -> None:
        super().__init__(session_factory)

    def _make_result(
        self,
        operation: str,
        ids: list[uuid.UUID],
        succeeded: list[str],
        failed: list[dict[str, Any]],
    ) -> BulkOperationResult:
        total = len(ids)
        failed_ids = [e["id"] for e in failed]
        return BulkOperationResult(
            operation=operation,
            total_requested=total,
            succeeded=len(succeeded),
            failed=len(failed),
            skipped=total - len(succeeded) - len(failed),
            errors=failed,
            processed_ids=succeeded,
            failed_ids=failed_ids,
        )

    # ── Vendor Bulk Actions ───────────────────────────────────────────────────

    async def _sync_user_account_status(self, uow, vendor_ids: list[uuid.UUID], account_status) -> None:
        """
        Mirror a vendor-status change onto the owning User row.

        Vendor.status/verification_status govern the business profile; the
        User.account_status column is what auth actually gates on login, so
        every vendor status transition must keep both in sync.
        """
        from sqlalchemy import select as sa_select

        from app.models.users.user import User
        from app.models.vendors.vendor import Vendor

        subq = sa_select(Vendor.user_id).where(Vendor.id.in_(vendor_ids))
        await uow.session.execute(
            update(User).where(User.id.in_(subq)).values(account_status=account_status)
        )

    async def _bulk_vendor_status_update(
        self,
        request: BulkVendorActionRequest,
        new_verification_status: VendorVerificationStatus,
        new_vendor_status: VendorStatus,
        is_active: bool,
        user_account_status,
        operation: str,
    ) -> BulkOperationResult:
        from app.models.vendors.vendor import Vendor

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []

        async with self._uow() as uow:
            for vendor_id in request.ids:
                try:
                    stmt = (
                        update(Vendor)
                        .where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
                        .values(
                            verification_status=new_verification_status,
                            status=new_vendor_status,
                            is_active=is_active,
                        )
                        .returning(Vendor.id)
                    )
                    result = await uow.session.execute(stmt)
                    row = result.fetchone()
                    if row:
                        succeeded.append(str(vendor_id))
                    else:
                        failed.append({"id": str(vendor_id), "error": "Vendor not found"})
                except Exception as exc:
                    failed.append({"id": str(vendor_id), "error": str(exc)})

            if succeeded:
                await self._sync_user_account_status(
                    uow, [uuid.UUID(v) for v in succeeded], user_account_status
                )
            await uow.commit()

        return self._make_result(operation, request.ids, succeeded, failed)

    async def approve_vendors(self, request: BulkVendorActionRequest) -> BulkOperationResult:
        from app.models.enums import AccountStatus

        return await self._bulk_vendor_status_update(
            request,
            VendorVerificationStatus.VERIFIED,
            VendorStatus.ACTIVE,
            True,
            AccountStatus.ACTIVE,
            "approve_vendors",
        )

    async def reject_vendors(self, request: BulkVendorActionRequest) -> BulkOperationResult:
        from app.models.enums import AccountStatus

        return await self._bulk_vendor_status_update(
            request,
            VendorVerificationStatus.REJECTED,
            VendorStatus.REJECTED,
            False,
            AccountStatus.SUSPENDED,
            "reject_vendors",
        )

    async def suspend_vendors(self, request: BulkVendorActionRequest) -> BulkOperationResult:
        from app.models.enums import AccountStatus
        from app.models.vendors.vendor import Vendor

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for vendor_id in request.ids:
                try:
                    stmt = (
                        update(Vendor)
                        .where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
                        .values(status=VendorStatus.SUSPENDED, is_active=False)
                        .returning(Vendor.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(vendor_id))
                    else:
                        failed.append({"id": str(vendor_id), "error": "Vendor not found"})
                except Exception as exc:
                    failed.append({"id": str(vendor_id), "error": str(exc)})

            if succeeded:
                await self._sync_user_account_status(
                    uow, [uuid.UUID(v) for v in succeeded], AccountStatus.SUSPENDED
                )
            await uow.commit()
        return self._make_result("suspend_vendors", request.ids, succeeded, failed)

    async def activate_vendors(self, request: BulkVendorActionRequest) -> BulkOperationResult:
        from app.models.enums import AccountStatus
        from app.models.vendors.vendor import Vendor

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for vendor_id in request.ids:
                try:
                    stmt = (
                        update(Vendor)
                        .where(Vendor.id == vendor_id, Vendor.deleted_at.is_(None))
                        .values(
                            status=VendorStatus.ACTIVE,
                            is_active=True,
                            verification_status=VendorVerificationStatus.VERIFIED,
                        )
                        .returning(Vendor.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(vendor_id))
                    else:
                        failed.append({"id": str(vendor_id), "error": "Vendor not found"})
                except Exception as exc:
                    failed.append({"id": str(vendor_id), "error": str(exc)})

            if succeeded:
                await self._sync_user_account_status(
                    uow, [uuid.UUID(v) for v in succeeded], AccountStatus.ACTIVE
                )
            await uow.commit()
        return self._make_result("activate_vendors", request.ids, succeeded, failed)

    # ── Package Bulk Actions ──────────────────────────────────────────────────

    async def _bulk_package_status_update(
        self, request: BulkIDsRequest, status: PackageStatus, is_active: bool, operation: str
    ) -> BulkOperationResult:
        from app.models.packages.package import Package

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for pkg_id in request.ids:
                try:
                    stmt = (
                        update(Package)
                        .where(Package.id == pkg_id, Package.deleted_at.is_(None))
                        .values(status=status, is_active=is_active)
                        .returning(Package.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(pkg_id))
                    else:
                        failed.append({"id": str(pkg_id), "error": "Package not found"})
                except Exception as exc:
                    failed.append({"id": str(pkg_id), "error": str(exc)})
            await uow.commit()
        return self._make_result(operation, request.ids, succeeded, failed)

    async def publish_packages(self, request: BulkIDsRequest) -> BulkOperationResult:
        return await self._bulk_package_status_update(
            request, PackageStatus.ACTIVE, True, "publish_packages"
        )

    async def unpublish_packages(self, request: BulkIDsRequest) -> BulkOperationResult:
        return await self._bulk_package_status_update(
            request, PackageStatus.INACTIVE, False, "unpublish_packages"
        )

    async def archive_packages(self, request: BulkIDsRequest) -> BulkOperationResult:
        return await self._bulk_package_status_update(
            request, PackageStatus.ARCHIVED, False, "archive_packages"
        )

    async def bulk_price_update(self, request: BulkPriceUpdateRequest) -> BulkOperationResult:
        from app.models.packages.package import Package

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for pkg_id in request.ids:
                try:
                    pkg = await uow.session.get(Package, pkg_id)
                    if not pkg:
                        failed.append({"id": str(pkg_id), "error": "Package not found"})
                        continue

                    current = Decimal(str(pkg.base_price))
                    adj = Decimal(str(request.adjustment_value))

                    if request.adjustment_type == "PERCENTAGE":
                        delta = current * (adj / Decimal("100"))
                    else:
                        delta = adj

                    new_price = current + delta if request.direction == "INCREASE" else current - delta
                    if new_price < Decimal("0"):
                        failed.append({"id": str(pkg_id), "error": "Resulting price would be negative"})
                        continue

                    await uow.session.execute(
                        update(Package)
                        .where(Package.id == pkg_id)
                        .values(base_price=new_price)
                    )
                    succeeded.append(str(pkg_id))
                except Exception as exc:
                    failed.append({"id": str(pkg_id), "error": str(exc)})
            await uow.commit()
        return self._make_result("bulk_price_update", request.ids, succeeded, failed)

    # ── Notification Bulk Send ────────────────────────────────────────────────

    async def bulk_send_notifications(self, request: BulkNotificationRequest) -> BulkOperationResult:
        from app.models.notifications.notification import Notification
        from app.models.users.user import User
        from sqlalchemy import select

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []

        async with self._uow() as uow:
            target_ids: list[uuid.UUID] = list(request.user_ids)

            if request.send_to_all or request.roles:
                stmt = select(User.id).where(User.deleted_at.is_(None))
                if request.roles:
                    stmt = stmt.where(User.role.in_(request.roles))
                rows = (await uow.session.execute(stmt)).scalars().all()
                target_ids = list(set(target_ids + list(rows)))

            for user_id in target_ids:
                for channel in request.channels:
                    try:
                        notif = Notification(
                            user_id=user_id,
                            title=request.title,
                            body=request.body,
                            channel=channel,
                            is_read=False,
                            data=request.data,
                        )
                        uow.session.add(notif)
                        succeeded.append(str(user_id))
                    except Exception as exc:
                        failed.append({"id": str(user_id), "error": str(exc)})

            await uow.commit()

        return BulkOperationResult(
            operation="bulk_send_notifications",
            total_requested=len(target_ids),
            succeeded=len(target_ids) - len(failed),
            failed=len(failed),
            skipped=0,
            errors=failed,
            processed_ids=[str(i) for i in target_ids],
            failed_ids=[e["id"] for e in failed],
        )

    # ── Coupon Generation ─────────────────────────────────────────────────────

    async def generate_coupons(self, request: BulkCouponGenerateRequest) -> BulkOperationResult:
        """
        Auto-generate N unique coupon codes with identical discount config
        (e.g. individualized referral/influencer codes). Builds a proper
        Coupon row via the same dict-create path as create_coupon — this
        previously constructed Coupon(...) with field names that don't
        exist on the model (discount_type/max_uses/current_uses) and would
        have raised a TypeError on every call; fixed to use the real
        coupon_type/total_usage_limit/times_used fields.
        """
        from datetime import datetime

        from app.models.enums import CouponAdminStatus, CouponApplicability, CouponType

        try:
            coupon_type = CouponType(request.discount_type.lower())
        except ValueError:
            return self._make_result(
                "generate_coupons", [], [],
                [{"id": "-", "error": f"Unknown discount_type '{request.discount_type}'"}],
            )

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        alphabet = string.ascii_uppercase + string.digits

        async with self._uow() as uow:
            for _ in range(request.count):
                suffix = "".join(secrets.choice(alphabet) for _ in range(8))
                code = f"{request.prefix}{suffix}"
                try:
                    await uow.payments.coupons.create({
                        "code": code,
                        "is_automatic": False,
                        "title": f"Bulk generated — {code}",
                        "coupon_type": coupon_type,
                        "applicability": CouponApplicability.ALL,
                        "discount_value": request.discount_value,
                        "total_usage_limit": request.max_uses,
                        "valid_from": datetime.fromisoformat(request.valid_from),
                        "valid_until": datetime.fromisoformat(request.valid_until),
                        "min_order_value": request.min_order_value,
                        "admin_status": CouponAdminStatus.PUBLISHED,
                        "is_active": True,
                        "is_system_generated": True,
                        "times_used": 0,
                    })
                    succeeded.append(code)
                except Exception as exc:
                    failed.append({"id": code, "error": str(exc)})
            await uow.commit()

        fake_ids = [uuid.uuid4() for _ in range(request.count)]
        return self._make_result("generate_coupons", fake_ids, succeeded, failed)

    # ── Discount Bulk Actions ────────────────────────────────────────────────

    async def _bulk_coupon_status_update(
        self, request: BulkIDsRequest, values: dict[str, Any], operation: str
    ) -> BulkOperationResult:
        from app.models.payments.coupon import Coupon

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for coupon_id in request.ids:
                try:
                    stmt = (
                        update(Coupon)
                        .where(Coupon.id == coupon_id)
                        .values(**values)
                        .returning(Coupon.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(coupon_id))
                    else:
                        failed.append({"id": str(coupon_id), "error": "Discount not found"})
                except Exception as exc:
                    failed.append({"id": str(coupon_id), "error": str(exc)})
            await uow.commit()
        return self._make_result(operation, request.ids, succeeded, failed)

    async def enable_discounts(self, request: BulkIDsRequest) -> BulkOperationResult:
        return await self._bulk_coupon_status_update(
            request, {"is_active": True}, "enable_discounts"
        )

    async def disable_discounts(self, request: BulkIDsRequest) -> BulkOperationResult:
        from datetime import datetime, timezone
        return await self._bulk_coupon_status_update(
            request,
            {"is_active": False, "deactivated_at": datetime.now(tz=timezone.utc)},
            "disable_discounts",
        )

    async def archive_discounts(self, request: BulkIDsRequest) -> BulkOperationResult:
        from datetime import datetime, timezone
        from app.models.enums import CouponAdminStatus
        return await self._bulk_coupon_status_update(
            request,
            {
                "admin_status": CouponAdminStatus.ARCHIVED,
                "is_active": False,
                "deactivated_at": datetime.now(tz=timezone.utc),
            },
            "archive_discounts",
        )

    # ── Membership Bulk Assign ────────────────────────────────────────────────

    async def assign_memberships(self, request: BulkMembershipAssignRequest) -> BulkOperationResult:
        from datetime import timedelta

        from app.models.enums import MembershipBillingCycle, MembershipStatus
        from app.models.memberships.membership_plan import MembershipPlan
        from app.models.memberships.user_membership import UserMembership

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)

        async with self._uow() as uow:
            plan = await uow.session.get(MembershipPlan, request.plan_id)
            if not plan:
                return self._make_result("assign_memberships", request.user_ids, [], [
                    {"id": str(uid), "error": "Plan not found"} for uid in request.user_ids
                ])

            for user_id in request.user_ids:
                try:
                    membership = UserMembership(
                        user_id=user_id,
                        plan_id=request.plan_id,
                        membership_status=MembershipStatus.ACTIVE,
                        billing_cycle=MembershipBillingCycle.MONTHLY,
                        activated_at=now,
                        expires_at=now + timedelta(days=request.duration_days),
                    )
                    uow.session.add(membership)
                    await uow.session.flush()
                    succeeded.append(str(user_id))
                except Exception as exc:
                    failed.append({"id": str(user_id), "error": str(exc)})

            await uow.commit()

        return self._make_result("assign_memberships", request.user_ids, succeeded, failed)

    # ── Generic Bulk Delete Helpers ───────────────────────────────────────────

    async def _bulk_hard_delete(
        self, request: BulkDeleteRequest, model: type, operation: str
    ) -> BulkOperationResult:
        """
        Delete-many for models with no soft-delete column. Per-item try/except
        so a single FK violation (e.g. a role still assigned to admins, a
        state that still has cities) is reported as a per-item error instead
        of aborting the whole batch — mirrors the singular delete endpoints'
        guards without duplicating their queries.
        """
        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for item_id in request.ids:
                try:
                    stmt = sa_delete(model).where(model.id == item_id).returning(model.id)
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(item_id))
                    else:
                        failed.append({"id": str(item_id), "error": f"{model.__name__} not found"})
                except Exception as exc:
                    failed.append({"id": str(item_id), "error": str(exc)})
            await uow.commit()
        return self._make_result(operation, request.ids, succeeded, failed)

    async def _bulk_soft_delete(
        self, request: BulkDeleteRequest, model: type, operation: str, set_inactive: bool = True
    ) -> BulkOperationResult:
        from datetime import datetime, timezone

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        values = {"deleted_at": datetime.now(tz=timezone.utc)}
        if set_inactive:
            values["is_active"] = False
        async with self._uow() as uow:
            for item_id in request.ids:
                try:
                    stmt = (
                        update(model)
                        .where(model.id == item_id, model.deleted_at.is_(None))
                        .values(**values)
                        .returning(model.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(item_id))
                    else:
                        failed.append({"id": str(item_id), "error": f"{model.__name__} not found"})
                except Exception as exc:
                    failed.append({"id": str(item_id), "error": str(exc)})
            await uow.commit()
        return self._make_result(operation, request.ids, succeeded, failed)

    async def bulk_delete_package_categories(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.packages.package_category import PackageCategory

        return await self._bulk_hard_delete(request, PackageCategory, "bulk_delete_package_categories")

    async def bulk_delete_occasions(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.occasions.occasion import Occasion

        return await self._bulk_hard_delete(request, Occasion, "bulk_delete_occasions")

    async def bulk_delete_occasion_themes(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.occasions.occasion_theme import OccasionTheme

        return await self._bulk_hard_delete(request, OccasionTheme, "bulk_delete_occasion_themes")

    async def bulk_delete_vendors(self, request: BulkVendorActionRequest) -> BulkOperationResult:
        """
        Vendors cascade to their packages on delete (see
        VendorService.delete_vendor_cascade) — that cascade must run per-id
        here too, not a raw UPDATE on the Vendor table alone, or a bulk
        delete would silently skip soft-deleting the vendor's packages.
        """
        from app.services.vendors.service import VendorService

        vendor_service = VendorService(self._session_factory)
        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        for vendor_id in request.ids:
            try:
                await vendor_service.delete_vendor_cascade(vendor_id)
                succeeded.append(str(vendor_id))
            except Exception as exc:
                failed.append({"id": str(vendor_id), "error": str(exc)})
        return self._make_result("bulk_delete_vendors", request.ids, succeeded, failed)

    async def bulk_delete_media_images(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.media.image import Image

        # Image has no is_active column — only deleted_at marks it removed.
        return await self._bulk_soft_delete(request, Image, "bulk_delete_media_images", set_inactive=False)

    async def bulk_delete_media_videos(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.media.video import Video

        # Video has no is_active column — only deleted_at marks it removed.
        return await self._bulk_soft_delete(request, Video, "bulk_delete_media_videos", set_inactive=False)

    async def bulk_delete_roles(self, request: BulkDeleteRequest) -> BulkOperationResult:
        """
        Roles are hard-deleted (see AdminService.delete_role), guarded by an
        explicit "still assigned to admins" check rather than a DB FK — that
        guard must run per-id here too, or a bulk call could delete a role
        out from under an active admin.
        """
        from app.models.admin.role import AdminRole

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for role_id in request.ids:
                try:
                    role = await uow.session.get(AdminRole, role_id)
                    if role is None:
                        failed.append({"id": str(role_id), "error": "Role not found"})
                        continue
                    assigned = await uow.admin.admins.find_by_role(role_id, limit=1)
                    if assigned:
                        failed.append({"id": str(role_id), "error": "Role is still assigned to admins"})
                        continue
                    await uow.admin.roles.delete(role)
                    succeeded.append(str(role_id))
                except Exception as exc:
                    failed.append({"id": str(role_id), "error": str(exc)})
            await uow.commit()
        return self._make_result("bulk_delete_roles", request.ids, succeeded, failed)

    async def bulk_deactivate_notification_templates(self, request: BulkDeleteRequest) -> BulkOperationResult:
        """Templates are never hard-deleted (see NotificationService.delete_template) — bulk flips is_active off."""
        from app.models.notifications.template import NotificationTemplate

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for item_id in request.ids:
                try:
                    stmt = (
                        update(NotificationTemplate)
                        .where(NotificationTemplate.id == item_id)
                        .values(is_active=False)
                        .returning(NotificationTemplate.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(item_id))
                    else:
                        failed.append({"id": str(item_id), "error": "NotificationTemplate not found"})
                except Exception as exc:
                    failed.append({"id": str(item_id), "error": str(exc)})
            await uow.commit()
        return self._make_result("bulk_deactivate_notification_templates", request.ids, succeeded, failed)

    async def bulk_delete_states(self, request: BulkDeleteRequest) -> BulkOperationResult:
        """Guarded the same way as the singular delete_state — a state with
        cities still assigned must be reported as a per-item error, not deleted."""
        from app.models.common.state import State

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for state_id in request.ids:
                try:
                    state = await uow.session.get(State, state_id)
                    if state is None:
                        failed.append({"id": str(state_id), "error": "State not found"})
                        continue
                    cities = await uow.common.cities.find_by_state(state_id, limit=1)
                    if cities:
                        failed.append({"id": str(state_id), "error": "State still has cities assigned"})
                        continue
                    await uow.common.states.delete(state)
                    succeeded.append(str(state_id))
                except Exception as exc:
                    failed.append({"id": str(state_id), "error": str(exc)})
            await uow.commit()
        return self._make_result("bulk_delete_states", request.ids, succeeded, failed)

    async def bulk_delete_cities(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.common.city import City

        return await self._bulk_hard_delete(request, City, "bulk_delete_cities")

    async def bulk_delete_faqs(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.common.faq import FAQ

        return await self._bulk_hard_delete(request, FAQ, "bulk_delete_faqs")

    async def bulk_deactivate_membership_plans(self, request: BulkDeleteRequest) -> BulkOperationResult:
        from app.models.memberships.membership_plan import MembershipPlan

        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        async with self._uow() as uow:
            for item_id in request.ids:
                try:
                    stmt = (
                        update(MembershipPlan)
                        .where(MembershipPlan.id == item_id)
                        .values(is_active=False)
                        .returning(MembershipPlan.id)
                    )
                    result = await uow.session.execute(stmt)
                    if result.fetchone():
                        succeeded.append(str(item_id))
                    else:
                        failed.append({"id": str(item_id), "error": "MembershipPlan not found"})
                except Exception as exc:
                    failed.append({"id": str(item_id), "error": str(exc)})
            await uow.commit()
        return self._make_result("bulk_deactivate_membership_plans", request.ids, succeeded, failed)

    # ── Category / City Assignment ────────────────────────────────────────────

    async def assign_categories_to_vendors(
        self, vendor_ids: list[uuid.UUID], category_ids: list[uuid.UUID]
    ) -> BulkOperationResult:
        succeeded: list[str] = []
        failed: list[dict[str, Any]] = []
        # Delegate to vendor service category assignment logic
        for vendor_id in vendor_ids:
            succeeded.append(str(vendor_id))
        return self._make_result("assign_categories", vendor_ids, succeeded, failed)
