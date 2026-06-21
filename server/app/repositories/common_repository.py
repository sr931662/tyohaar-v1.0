"""
Common repository — State, City, Banner, FAQ, AppSetting, TermsAndConditions, PrivacyPolicy.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.common.app_setting import AppSetting
from app.models.common.banner import Banner
from app.models.common.city import City
from app.models.common.faq import FAQ
from app.models.common.privacy_policy import PrivacyPolicy
from app.models.common.state import State
from app.models.common.terms import TermsAndConditions
from app.models.enums import BannerTargetAudience, BannerType, ContentStatus, FAQCategory, UserRole
from app.repositories.base import BaseRepository


class StateRepository(BaseRepository[State]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, State)

    async def find_by_country(self, country_code: str) -> list[State]:
        return await self.find_many(
            State.country_code == country_code,
            order_by=State.name.asc(),
        )

    async def find_active(self, country_code: str = "IN") -> list[State]:
        return await self.find_many(
            State.country_code == country_code,
            State.is_active == True,  # noqa: E712
            order_by=State.name.asc(),
        )

    async def find_by_code(self, code: str, country_code: str = "IN") -> State | None:
        return await self.find_one(
            State.code == code,
            State.country_code == country_code,
        )


class CityRepository(BaseRepository[City]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, City)

    async def find_by_state(
        self,
        state_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[City]:
        return await self.find_many(
            City.state_id == state_id,
            order_by=City.name.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_serviceable(self) -> list[City]:
        return await self.find_many(
            City.is_serviceable == True,  # noqa: E712
            City.is_active == True,  # noqa: E712
            order_by=City.name.asc(),
        )

    async def find_by_slug(self, slug: str) -> City | None:
        return await self.find_one(City.slug == slug)

    async def find_metro_cities(self) -> list[City]:
        return await self.find_many(
            City.is_metro == True,  # noqa: E712
            City.is_active == True,  # noqa: E712
            order_by=City.name.asc(),
        )

    async def find_tier_1(self) -> list[City]:
        return await self.find_many(
            City.is_tier_1 == True,  # noqa: E712
            City.is_active == True,  # noqa: E712
            order_by=City.name.asc(),
        )

    async def find_active(
        self,
        *,
        skip: int = 0,
        limit: int = 200,
    ) -> list[City]:
        return await self.find_many(
            City.is_active == True,  # noqa: E712
            order_by=City.name.asc(),
            skip=skip,
            limit=limit,
        )


class BannerRepository(BaseRepository[Banner]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Banner)

    async def find_active_now(
        self,
        banner_type: BannerType | None = None,
        audience: BannerTargetAudience | None = None,
    ) -> list[Banner]:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        filters: list[Any] = [
            Banner.is_active == True,  # noqa: E712
            (Banner.display_start_at.is_(None)) | (Banner.display_start_at <= now),
            (Banner.display_end_at.is_(None)) | (Banner.display_end_at >= now),
        ]
        if banner_type is not None:
            filters.append(Banner.banner_type == banner_type)
        if audience is not None:
            filters.append(
                (Banner.target_audience == audience) |
                (Banner.target_audience == BannerTargetAudience.ALL)
            )
        return await self.find_many(
            *filters,
            order_by=Banner.display_order.asc(),
        )

    async def find_by_type(self, banner_type: BannerType) -> list[Banner]:
        return await self.find_many(
            Banner.banner_type == banner_type,
            Banner.is_active == True,  # noqa: E712
            order_by=Banner.display_order.asc(),
        )

    async def find_scheduled(self) -> list[Banner]:
        from datetime import datetime, timezone
        now = datetime.now(tz=timezone.utc)
        return await self.find_many(
            Banner.is_active == True,  # noqa: E712
            Banner.display_start_at > now,
        )


class FAQRepository(BaseRepository[FAQ]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, FAQ)

    async def find_by_category(
        self,
        category: FAQCategory,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> list[FAQ]:
        return await self.find_many(
            FAQ.faq_category == category,
            FAQ.is_active == True,  # noqa: E712
            order_by=FAQ.display_order.asc(),
            skip=skip,
            limit=limit,
        )

    async def find_active(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[FAQ]:
        return await self.find_many(
            FAQ.is_active == True,  # noqa: E712
            order_by=[FAQ.faq_category.asc(), FAQ.display_order.asc()],
            skip=skip,
            limit=limit,
        )

    async def find_for_role(
        self,
        role: UserRole,
    ) -> list[FAQ]:
        from sqlalchemy import or_
        return await self.find_many(
            FAQ.is_active == True,  # noqa: E712
            or_(
                FAQ.target_role.is_(None),
                FAQ.target_role == role,
            ),
            order_by=FAQ.display_order.asc(),
        )

    async def find_featured(self) -> list[FAQ]:
        return await self.find_many(
            FAQ.is_featured == True,  # noqa: E712
            FAQ.is_active == True,  # noqa: E712
            order_by=FAQ.display_order.asc(),
        )


class AppSettingRepository(BaseRepository[AppSetting]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AppSetting)

    async def get_by_key(self, key: str) -> AppSetting | None:
        return await self.find_one(AppSetting.key == key)

    async def get_by_key_or_raise(self, key: str) -> AppSetting:
        from app.repositories.base import NotFoundError
        setting = await self.get_by_key(key)
        if setting is None:
            raise NotFoundError("AppSetting", key)
        return setting

    async def find_by_group(self, group: str) -> list[AppSetting]:
        return await self.find_many(
            AppSetting.group == group,
            order_by=AppSetting.key.asc(),
        )

    async def find_public(self) -> list[AppSetting]:
        return await self.find_many(
            AppSetting.is_sensitive == False,  # noqa: E712
            order_by=AppSetting.key.asc(),
        )

    async def set_value(self, key: str, value: str) -> None:
        stmt = (
            update(AppSetting)
            .where(AppSetting.key == key)
            .where(AppSetting.is_readonly == False)  # noqa: E712
            .values(value=value)
            .execution_options(synchronize_session="fetch")
        )
        await self._session.execute(stmt)


class TermsRepository(BaseRepository[TermsAndConditions]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TermsAndConditions)

    async def get_current(
        self,
        language: str = "en",
        applicable_role: UserRole | None = None,
    ) -> TermsAndConditions | None:
        from sqlalchemy import or_
        filters: list[Any] = [
            TermsAndConditions.content_status == ContentStatus.PUBLISHED,
            TermsAndConditions.language == language,
            TermsAndConditions.superseded_by_id.is_(None),
        ]
        if applicable_role is not None:
            filters.append(
                or_(
                    TermsAndConditions.applicable_role.is_(None),
                    TermsAndConditions.applicable_role == applicable_role,
                )
            )
        return await self.find_one(*filters)

    async def find_published(self) -> list[TermsAndConditions]:
        return await self.find_many(
            TermsAndConditions.content_status == ContentStatus.PUBLISHED,
            order_by=TermsAndConditions.version.desc(),
        )

    async def find_requiring_acceptance(self) -> list[TermsAndConditions]:
        return await self.find_many(
            TermsAndConditions.content_status == ContentStatus.PUBLISHED,
            TermsAndConditions.must_accept_version == True,  # noqa: E712
            TermsAndConditions.superseded_by_id.is_(None),
        )

    async def find_version(
        self,
        version: str,
        language: str = "en",
    ) -> TermsAndConditions | None:
        return await self.find_one(
            TermsAndConditions.version == version,
            TermsAndConditions.language == language,
        )


class PrivacyPolicyRepository(BaseRepository[PrivacyPolicy]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PrivacyPolicy)

    async def get_current(self, language: str = "en") -> PrivacyPolicy | None:
        return await self.find_one(
            PrivacyPolicy.content_status == ContentStatus.PUBLISHED,
            PrivacyPolicy.language == language,
            PrivacyPolicy.superseded_by_id.is_(None),
        )

    async def find_published(self) -> list[PrivacyPolicy]:
        return await self.find_many(
            PrivacyPolicy.content_status == ContentStatus.PUBLISHED,
            order_by=PrivacyPolicy.version.desc(),
        )

    async def find_version(
        self,
        version: str,
        language: str = "en",
    ) -> PrivacyPolicy | None:
        return await self.find_one(
            PrivacyPolicy.version == version,
            PrivacyPolicy.language == language,
        )


class CommonRepositoryAggregate:
    """Groups common-domain sub-repositories."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.states = StateRepository(session)
        self.cities = CityRepository(session)
        self.banners = BannerRepository(session)
        self.faqs = FAQRepository(session)
        self.settings = AppSettingRepository(session)
        self.terms = TermsRepository(session)
        self.privacy_policies = PrivacyPolicyRepository(session)
