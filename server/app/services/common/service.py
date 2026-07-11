"""
CommonService — geography, banners, FAQs, app settings, and terms/privacy for the Tyohaar platform.

Field-name rules (enforced here):
- FAQ model uses `faq_category` (NOT `category`) and `is_active` (NOT `is_published`).
- Banner activity check: is_active=True AND display_start_at <= now AND display_end_at >= now.
- AppSetting: sensitive values are masked in AppSettingResponse; full values only via
  AppSettingAdminResponse.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.enums import ContentStatus
from app.schemas.common import (
    AppSettingAdminResponse,
    AppSettingCreate,
    AppSettingFilters,
    AppSettingResponse,
    BannerCreate,
    BannerFilters,
    BannerResponse,
    BannerUpdate,
    CityCreate,
    CityFilters,
    CityResponse,
    CityUpdate,
    FAQCreate,
    FAQFilters,
    FAQResponse,
    FAQUpdate,
    PrivacyPolicyCreate,
    PrivacyPolicyResponse,
    CancellationPolicyCreate,
    CancellationPolicyResponse,
    StateCreate,
    StateResponse,
    StateUpdate,
    TermsCreate,
    TermsResponse,
    TermsUpdate,
    PrivacyPolicyUpdate,
    AppSettingUpdate,
)
from app.schemas.base import CursorPage
from app.services.base import BaseService
from app.services.common.constants import MAX_FAQ_ITEMS
from app.services.common.exceptions import (
    AppSettingNotFoundError,
    BannerNotFoundError,
    CityNotFoundError,
    FAQNotFoundError,
    PrivacyPolicyNotFoundError,
    CancellationPolicyNotFoundError,
    StateHasCitiesError,
    StateNotFoundError,
    SystemSettingDeleteError,
    TermsNotFoundError,
)
from app.services.common.validators import (
    validate_active_banner_limit,
    validate_banner_exists,
    validate_city_belongs_to_state,
    validate_city_exists,
    validate_faq_exists,
    validate_setting_exists,
    validate_state_exists,
)

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


class CommonService(BaseService):
    def __init__(
        self, session_factory: Callable[[], AsyncSession] = AsyncSessionLocal
    ) -> None:
        super().__init__(session_factory)

    # ── States (read) ─────────────────────────────────────────────────────────

    async def list_states(
        self,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[StateResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            states = await uow.common.states.find_active()
            items = [StateResponse.model_validate(s) for s in states[:limit]]
            return CursorPage(items=items, has_more=len(states) > limit)

    async def get_state(self, state_id: UUID) -> StateResponse:
        async with self._uow() as uow:
            state = await validate_state_exists(state_id, uow)
            return StateResponse.model_validate(state)

    async def list_cities(
        self,
        state_id: UUID | None = None,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[CityResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            if state_id is not None:
                cities = await uow.common.cities.find_by_state(state_id, limit=limit)
            else:
                cities = await uow.common.cities.find_active(limit=limit)
            items = [CityResponse.model_validate(c) for c in cities]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def get_city(self, city_id: UUID) -> CityResponse:
        async with self._uow() as uow:
            city = await validate_city_exists(city_id, uow)
            return CityResponse.model_validate(city)

    async def search_cities(
        self,
        query: str,
        state_id: UUID | None = None,
        limit: int = 20,
    ) -> list[CityResponse]:
        limit = min(limit, _MAX_LIMIT)
        query_lower = query.lower()
        async with self._uow() as uow:
            if state_id is not None:
                cities = await uow.common.cities.find_by_state(state_id, limit=500)
            else:
                cities = await uow.common.cities.find_active(limit=500)
            matched = [
                c for c in cities if query_lower in c.name.lower()
            ]
            return [CityResponse.model_validate(c) for c in matched[:limit]]

    # ── States (admin write) ──────────────────────────────────────────────────

    async def create_state(
        self, data: StateCreate, admin_id: UUID
    ) -> StateResponse:
        async with self._uow() as uow:
            state = await uow.common.states.create(data.model_dump(exclude_unset=True))
            await uow.commit()
            return StateResponse.model_validate(state)

    async def update_state(
        self,
        state_id: UUID,
        data: StateUpdate,
        admin_id: UUID,
    ) -> StateResponse:
        async with self._uow() as uow:
            state = await validate_state_exists(state_id, uow)
            updated = await uow.common.states.update(
                state, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return StateResponse.model_validate(updated)

    async def delete_state(self, state_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            state = await validate_state_exists(state_id, uow)
            cities = await uow.common.cities.find_by_state(state_id, limit=1)
            if cities:
                raise StateHasCitiesError(
                    f"State '{state.name}' cannot be deleted while it has cities assigned."
                )
            await uow.common.states.delete(state)
            await uow.commit()

    async def create_city(
        self, data: CityCreate, admin_id: UUID
    ) -> CityResponse:
        async with self._uow() as uow:
            await validate_state_exists(data.state_id, uow)
            city = await uow.common.cities.create(data.model_dump(exclude_unset=True))
            await uow.commit()
            return CityResponse.model_validate(city)

    async def update_city(
        self,
        city_id: UUID,
        data: CityUpdate,
        admin_id: UUID,
    ) -> CityResponse:
        async with self._uow() as uow:
            city = await validate_city_exists(city_id, uow)
            updated = await uow.common.cities.update(
                city, data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return CityResponse.model_validate(updated)

    async def delete_city(self, city_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            city = await validate_city_exists(city_id, uow)
            await uow.common.cities.delete(city)
            await uow.commit()

    # ── Banners ───────────────────────────────────────────────────────────────

    async def list_active_banners(
        self,
        target_audience: str | None = None,
    ) -> list[BannerResponse]:
        async with self._uow() as uow:
            from app.models.enums import BannerTargetAudience
            audience = None
            if target_audience is not None:
                try:
                    audience = BannerTargetAudience(target_audience)
                except ValueError:
                    audience = None
            banners = await uow.common.banners.find_active_now(audience=audience)
            return [BannerResponse.model_validate(b) for b in banners]

    async def get_banner(self, banner_id: UUID) -> BannerResponse:
        async with self._uow() as uow:
            banner = await validate_banner_exists(banner_id, uow)
            return BannerResponse.model_validate(banner)

    async def list_all_banners(
        self,
        filters: BannerFilters,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[BannerResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            banners = await uow.common.banners.find_many(
                order_by=None,
                skip=0,
                limit=limit,
            )
            items = [BannerResponse.model_validate(b) for b in banners]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def create_banner(
        self, data: BannerCreate, admin_id: UUID
    ) -> BannerResponse:
        async with self._uow() as uow:
            if data.is_active:
                await validate_active_banner_limit(uow)
            banner = await uow.common.banners.create(
                data.model_dump(exclude_unset=True)
            )
            await uow.commit()
            return BannerResponse.model_validate(banner)

    async def update_banner(
        self,
        banner_id: UUID,
        data: BannerUpdate,
        admin_id: UUID,
    ) -> BannerResponse:
        async with self._uow() as uow:
            banner = await validate_banner_exists(banner_id, uow)
            payload = data.model_dump(exclude_unset=True)
            # If activating a currently-inactive banner, enforce limit
            if payload.get("is_active") is True and not banner.is_active:
                await validate_active_banner_limit(uow)
            updated = await uow.common.banners.update(banner, payload)
            await uow.commit()
            return BannerResponse.model_validate(updated)

    async def delete_banner(self, banner_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            banner = await validate_banner_exists(banner_id, uow)
            await uow.common.banners.delete(banner)
            await uow.commit()

    async def toggle_banner_active(
        self, banner_id: UUID, admin_id: UUID
    ) -> BannerResponse:
        async with self._uow() as uow:
            banner = await validate_banner_exists(banner_id, uow)
            new_state = not banner.is_active
            if new_state:
                await validate_active_banner_limit(uow)
            updated = await uow.common.banners.update(
                banner, {"is_active": new_state}
            )
            await uow.commit()
            return BannerResponse.model_validate(updated)

    # ── FAQs ──────────────────────────────────────────────────────────────────

    async def list_faqs(
        self,
        category: str | None = None,
        active_only: bool = True,
    ) -> list[FAQResponse]:
        async with self._uow() as uow:
            if category is not None:
                from app.models.enums import FAQCategory
                try:
                    faq_cat = FAQCategory(category)
                except ValueError:
                    return []
                faqs = await uow.common.faqs.find_by_category(faq_cat)
            elif active_only:
                faqs = await uow.common.faqs.find_active()
            else:
                faqs = await uow.common.faqs.find_many(order_by=None, limit=MAX_FAQ_ITEMS)
            # Filter by is_active if active_only (find_by_category already filters, but guard here)
            if active_only:
                faqs = [f for f in faqs if f.is_active]
            return [FAQResponse.model_validate(f) for f in faqs]

    async def get_faq(self, faq_id: UUID) -> FAQResponse:
        async with self._uow() as uow:
            faq = await validate_faq_exists(faq_id, uow)
            return FAQResponse.model_validate(faq)

    async def create_faq(self, data: FAQCreate, admin_id: UUID) -> FAQResponse:
        async with self._uow() as uow:
            payload = data.model_dump(exclude_unset=True)
            # Schema uses `category`; model stores `faq_category` — remap
            if "category" in payload:
                payload["faq_category"] = payload.pop("category")
            faq = await uow.common.faqs.create(payload)
            await uow.commit()
            return FAQResponse.model_validate(faq)

    async def update_faq(
        self,
        faq_id: UUID,
        data: FAQUpdate,
        admin_id: UUID,
    ) -> FAQResponse:
        async with self._uow() as uow:
            faq = await validate_faq_exists(faq_id, uow)
            payload = data.model_dump(exclude_unset=True)
            if "category" in payload:
                payload["faq_category"] = payload.pop("category")
            updated = await uow.common.faqs.update(faq, payload)
            await uow.commit()
            return FAQResponse.model_validate(updated)

    async def delete_faq(self, faq_id: UUID, admin_id: UUID) -> None:
        async with self._uow() as uow:
            faq = await validate_faq_exists(faq_id, uow)
            await uow.common.faqs.delete(faq)
            await uow.commit()

    async def reorder_faqs(
        self,
        category: str,
        ordered_ids: list[UUID],
        admin_id: UUID,
    ) -> list[FAQResponse]:
        async with self._uow() as uow:
            updated_faqs = []
            for display_order, faq_id in enumerate(ordered_ids):
                faq = await validate_faq_exists(faq_id, uow)
                updated = await uow.common.faqs.update(
                    faq, {"display_order": display_order}
                )
                updated_faqs.append(updated)
            await uow.commit()
            return [FAQResponse.model_validate(f) for f in updated_faqs]

    # ── App Settings ──────────────────────────────────────────────────────────

    async def get_setting(self, key: str) -> AppSettingResponse:
        """Public endpoint — returns masked value for sensitive settings."""
        async with self._uow() as uow:
            setting = await validate_setting_exists(key, uow)
            if setting.is_sensitive:
                # Return masked value for public consumers
                masked = setting.model_copy(update={"value": "***"})
                return AppSettingResponse.model_validate(masked)
            return AppSettingResponse.model_validate(setting)

    async def get_setting_admin(self, key: str) -> AppSettingAdminResponse:
        """Admin endpoint — returns full value including sensitive settings."""
        async with self._uow() as uow:
            setting = await validate_setting_exists(key, uow)
            return AppSettingAdminResponse.model_validate(setting)

    async def list_settings(
        self,
        filters: AppSettingFilters,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[AppSettingAdminResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            settings_list = await uow.common.settings.find_many(
                order_by=None,
                skip=0,
                limit=limit,
            )
            items = [AppSettingAdminResponse.model_validate(s) for s in settings_list]
            return CursorPage(items=items, has_more=len(items) == limit)

    async def upsert_setting(
        self,
        key: str,
        value: str,
        data: AppSettingCreate,
        admin_id: UUID,
    ) -> AppSettingAdminResponse:
        async with self._uow() as uow:
            existing = await uow.common.settings.get_by_key(key)
            if existing is not None:
                updated = await uow.common.settings.update(
                    existing, {"value": value}
                )
                await uow.commit()
                return AppSettingAdminResponse.model_validate(updated)
            payload = data.model_dump(exclude_unset=True)
            payload["key"] = key
            payload["value"] = value
            created = await uow.common.settings.create(payload)
            await uow.commit()
            return AppSettingAdminResponse.model_validate(created)

    async def delete_setting(self, key: str, admin_id: UUID) -> None:
        async with self._uow() as uow:
            setting = await validate_setting_exists(key, uow)
            # Cannot delete readonly/system-critical settings
            if setting.is_readonly:
                raise SystemSettingDeleteError(
                    f"Setting '{key}' is system-critical and cannot be deleted."
                )
            await uow.common.settings.delete(setting)
            await uow.commit()

    # ── Terms & Conditions ────────────────────────────────────────────────────

    async def get_current_terms(self) -> TermsResponse:
        """Return the latest active (published) Terms & Conditions version."""
        async with self._uow() as uow:
            terms = await uow.common.terms.get_current()
            if terms is None:
                raise TermsNotFoundError(
                    "TermsAndConditions", "current"
                )
            return TermsResponse.model_validate(terms)

    async def list_terms_versions(
        self,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[TermsResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            versions = await uow.common.terms.find_published()
            items = [TermsResponse.model_validate(t) for t in versions[:limit]]
            return CursorPage(items=items, has_more=len(versions) > limit)

    async def create_terms_version(
        self,
        data: TermsCreate,
        admin_id: UUID,
    ) -> TermsResponse:
        """
        Publish a new Terms version.  The previous active version is archived
        (is_active=False / content_status=ARCHIVED) before creating the new one.
        """
        async with self._uow() as uow:
            # Archive existing current version
            current = await uow.common.terms.get_current()
            if current is not None:
                await uow.common.terms.update(
                    current, {"status": ContentStatus.ARCHIVED}
                )

            payload = data.model_dump(exclude_unset=True)
            payload["status"] = ContentStatus.PUBLISHED
            new_terms = await uow.common.terms.create_from_dict(payload)
            await uow.commit()
            return TermsResponse.model_validate(new_terms)

    # ── Privacy Policy ────────────────────────────────────────────────────────

    async def get_current_privacy_policy(self) -> PrivacyPolicyResponse:
        """Return the latest active (published) Privacy Policy version."""
        async with self._uow() as uow:
            policy = await uow.common.privacy_policies.get_current()
            if policy is None:
                raise PrivacyPolicyNotFoundError("PrivacyPolicy", "current")
            return PrivacyPolicyResponse.model_validate(policy)

    async def create_privacy_policy_version(
        self,
        data: PrivacyPolicyCreate,
        admin_id: UUID,
    ) -> PrivacyPolicyResponse:
        """
        Publish a new Privacy Policy version.  The previous active version is
        archived before creating the new one.
        """
        async with self._uow() as uow:
            current = await uow.common.privacy_policies.get_current()
            if current is not None:
                await uow.common.privacy_policies.update(
                    current, {"status": ContentStatus.ARCHIVED}
                )

            payload = data.model_dump(exclude_unset=True)
            payload["status"] = ContentStatus.PUBLISHED
            new_policy = await uow.common.privacy_policies.create_from_dict(payload)
            await uow.commit()
            return PrivacyPolicyResponse.model_validate(new_policy)

    # ── Cancellation & Refund Policy ────────────────────────────────────────────

    async def get_current_cancellation_policy(self) -> CancellationPolicyResponse:
        """Return the latest active (published) Cancellation & Refund Policy version."""
        async with self._uow() as uow:
            policy = await uow.common.cancellation_policies.get_current()
            if policy is None:
                raise CancellationPolicyNotFoundError("CancellationRefundPolicy", "current")
            return CancellationPolicyResponse.model_validate(policy)

    async def list_cancellation_policy_versions(
        self,
        cursor: str | None = None,
        limit: int = _DEFAULT_LIMIT,
    ) -> CursorPage[CancellationPolicyResponse]:
        limit = min(limit, _MAX_LIMIT)
        async with self._uow() as uow:
            versions = await uow.common.cancellation_policies.find_published()
            items = [CancellationPolicyResponse.model_validate(p) for p in versions[:limit]]
            return CursorPage(items=items, has_more=len(versions) > limit)

    async def create_cancellation_policy_version(
        self,
        data: CancellationPolicyCreate,
        admin_id: UUID,
    ) -> CancellationPolicyResponse:
        """
        Publish a new Cancellation & Refund Policy version. The previous
        active version is archived before creating the new one.
        """
        async with self._uow() as uow:
            current = await uow.common.cancellation_policies.get_current()
            if current is not None:
                await uow.common.cancellation_policies.update(
                    current, {"status": ContentStatus.ARCHIVED}
                )

            payload = data.model_dump(exclude_unset=True)
            payload["status"] = ContentStatus.PUBLISHED
            payload["author_id"] = admin_id
            new_policy = await uow.common.cancellation_policies.create_from_dict(payload)
            await uow.commit()
            return CancellationPolicyResponse.model_validate(new_policy)
