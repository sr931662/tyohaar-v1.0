"""
ReferralMilestoneRule / ReferralMilestoneGrant — admin-configurable referral
milestone rewards.

Design: admin edits a small set of named variables (referrals_required,
discount_percentage, applicable_plan_count, min_plan_price) rather than
code. When a referrer's successful-referral count crosses a fresh multiple
of `referrals_required`, a ReferralMilestoneGrant is created recording how
many future bookings ("plans") get the discount and the minimum booking
size that qualifies — both snapshotted from the rule at grant time so a
later rule edit never changes benefits already earned.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class ReferralMilestoneRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    Admin-configurable referral milestone reward definition.

    Only one rule is expected to be is_active=True at a time — the service
    layer deactivates any previously-active rule when a new one is created,
    so admins edit "the current referral offer" rather than juggling tiers.
    """

    __tablename__ = "referral_milestone_rules"

    __table_args__ = (
        CheckConstraint("referrals_required > 0", name="ck_referral_milestone_referrals_required_positive"),
        CheckConstraint("discount_percentage >= 0 AND discount_percentage <= 100", name="ck_referral_milestone_discount_range"),
        CheckConstraint("applicable_plan_count > 0", name="ck_referral_milestone_plan_count_positive"),
        Index("ix_referral_milestone_rules_is_active", "is_active"),
    )

    referrals_required: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="'For every N referrals' — how many successful referrals unlock the reward.",
    )

    discount_percentage: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="Discount % applied to qualifying bookings once unlocked.",
    )

    applicable_plan_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of future bookings ('plans') the discount applies to.",
    )

    min_plan_price: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Minimum booking subtotal required for the discount to apply.",
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    def __repr__(self) -> str:
        return (
            f"<ReferralMilestoneRule id={self.id} every={self.referrals_required} "
            f"discount={self.discount_percentage}% active={self.is_active}>"
        )


class ReferralMilestoneGrant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A milestone benefit a specific user has unlocked. Values are snapshotted
    from the rule at grant time; plans_remaining decrements as the customer
    checks out with the discount applied, until it reaches zero.
    """

    __tablename__ = "referral_milestone_grants"

    __table_args__ = (
        CheckConstraint("plans_remaining >= 0", name="ck_referral_milestone_grant_plans_non_negative"),
        Index("ix_referral_milestone_grants_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("referral_milestone_rules.id", ondelete="RESTRICT"),
        nullable=False,
    )

    referral_count_at_grant: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Referrer's successful-referral count at the moment this milestone was crossed — prevents double-granting the same milestone.",
    )

    discount_percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    min_plan_price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    plans_remaining: Mapped[int] = mapped_column(Integer, nullable=False)

    user: Mapped[User] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<ReferralMilestoneGrant id={self.id} user_id={self.user_id} "
            f"remaining={self.plans_remaining}>"
        )
