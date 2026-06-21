"""
UserMembership — a customer's subscription to a Tyohaar membership plan.

Tracks the full lifecycle: purchase, renewal, upgrade/downgrade, grace period,
cancellation, and historical changes via renewal_history JSONB.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import text

from app.models.base import Base
from app.models.enums import MembershipBillingCycle, MembershipStatus
from app.models.mixins import MetadataMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.memberships.membership_plan import MembershipPlan
    from app.models.payments.payment import Payment


class MembershipCancellationReason(str, enum.Enum):
    """
    Why a UserMembership was cancelled or not renewed.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    CUSTOMER_REQUEST = "customer_request"
    NON_PAYMENT = "non_payment"
    UPGRADED = "upgraded"                 # Cancelled because of upgrade to higher tier
    DOWNGRADED = "downgraded"             # Cancelled because of downgrade to lower tier
    PLAN_DISCONTINUED = "plan_discontinued"
    FRAUD_DETECTED = "fraud_detected"
    ADMIN_ACTION = "admin_action"
    EXPIRED_NO_RENEWAL = "expired_no_renewal"


class UserMembership(UUIDPrimaryKeyMixin, TimestampMixin, MetadataMixin, Base):
    """
    A single subscription record for a customer's membership plan.

    One row per subscription period. A customer can have:
    - Exactly one ACTIVE membership at a time (enforced by partial unique index).
    - Multiple historical rows (CANCELLED, EXPIRED).

    Lifecycle:
    1. Customer purchases plan → status=PENDING, activated_at set.
    2. Payment confirmed → status=ACTIVE.
    3. Near expiry (if auto_renew=True) → service renews, increments renewal_count,
       appends to renewal_history, updates expires_at.
    4. Expired with no renewal → grace_period_until set; status=GRACE_PERIOD.
    5. Grace period elapsed → status=EXPIRED; tier downgrades to FREE.
    6. Customer cancels → status=CANCELLED, cancellation fields set.
    7. Customer upgrades → this record CANCELLED; new record created for higher tier.

    Upgrade tracking:
    - `upgraded_from_plan_id`: the plan this membership superseded (on upgrade).
    - Together with the CANCELLED predecessor record, this reconstructs the
      full upgrade chain without a separate history table.

    `renewal_history` JSONB structure:
    [
      {
        "renewed_at": "2024-03-01T10:00:00Z",
        "payment_id": "uuid",
        "from_expires_at": "2024-03-01",
        "to_expires_at": "2024-04-01",
        "billing_cycle": "monthly"
      },
      ...
    ]

    `extra_metadata` (from MetadataMixin) stores feature flags, promo codes
    applied at signup, A/B test variants, and platform-specific context.
    """

    __tablename__ = "user_memberships"

    __table_args__ = (
        # A user can have at most one ACTIVE membership at a time.
        Index(
            "ix_user_memberships_unique_active",
            "user_id",
            unique=True,
            postgresql_where=text("membership_status = 'active'"),
        ),
        Index("ix_user_memberships_user_id", "user_id"),
        Index("ix_user_memberships_plan_id", "plan_id"),
        Index("ix_user_memberships_status", "membership_status"),
        Index("ix_user_memberships_expires_at", "expires_at"),
        CheckConstraint("renewal_count >= 0", name="ck_user_memberships_renewal_count_non_negative"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Customer holding this membership subscription.",
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("membership_plans.id", ondelete="RESTRICT"),
        nullable=False,
        comment="The plan this subscription is on.",
    )

    # ── Status & Billing ──────────────────────────────────────────────────────

    membership_status: Mapped[MembershipStatus] = mapped_column(
        SAEnum(MembershipStatus, name="membership_status", native_enum=False),
        nullable=False,
        default=MembershipStatus.PENDING,
    )

    billing_cycle: Mapped[MembershipBillingCycle] = mapped_column(
        SAEnum(MembershipBillingCycle, name="membership_billing_cycle", native_enum=False),
        nullable=False,
        comment="Monthly or annual billing cadence selected at purchase.",
    )

    is_lifetime: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True for one-time lifetime purchases. expires_at is NULL when is_lifetime=True.",
    )

    # ── Timing ────────────────────────────────────────────────────────────────

    activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the membership became ACTIVE (payment confirmed).",
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this subscription period ends. NULL for lifetime memberships.",
    )

    next_renewal_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "When the auto-renewal job should attempt to charge the customer. "
            "Typically set to 3–7 days before expires_at to allow retry time."
        ),
    )

    grace_period_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment=(
            "Post-expiry window during which the customer retains tier benefits. "
            "After this timestamp, the service downgrades the user to FREE tier."
        ),
    )

    # ── Auto-Renewal ──────────────────────────────────────────────────────────

    auto_renew: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="True if the service should automatically charge for renewal before expiry.",
    )

    renewal_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of successful renewals since initial activation.",
    )

    renewal_history: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Append-only list of renewal events. Each entry: "
            "{renewed_at, payment_id, from_expires_at, to_expires_at, billing_cycle}."
        ),
    )

    # ── Purchase ──────────────────────────────────────────────────────────────

    payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        nullable=True,
        comment="The initial purchase payment. Renewal payments are in renewal_history.",
    )

    # ── Upgrade Tracking ──────────────────────────────────────────────────────

    upgraded_from_plan_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("membership_plans.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "The plan the customer was on before upgrading to this one. "
            "NULL for fresh subscriptions (not upgrades)."
        ),
    )

    upgrade_reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Optional customer-provided or admin-noted reason for upgrading.",
    )

    # ── Cancellation ──────────────────────────────────────────────────────────

    cancellation_reason: Mapped[MembershipCancellationReason | None] = mapped_column(
        SAEnum(MembershipCancellationReason, name="membership_cancellation_reason", native_enum=False),
        nullable=True,
    )

    cancellation_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Admin or customer notes explaining the cancellation.",
    )

    cancelled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    cancelled_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin user who performed the cancellation. NULL for customer self-cancellation.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="noload",
    )

    plan: Mapped[MembershipPlan] = relationship(
        "MembershipPlan",
        foreign_keys=[plan_id],
        back_populates="subscriptions",
        lazy="noload",
    )

    upgraded_from_plan: Mapped[MembershipPlan | None] = relationship(
        "MembershipPlan",
        foreign_keys=[upgraded_from_plan_id],
        lazy="noload",
    )

    payment: Mapped[Payment | None] = relationship(
        "Payment",
        lazy="noload",
    )

    cancelled_by: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[cancelled_by_id],
        lazy="noload",
    )

    # ── Computed Property ─────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        return self.membership_status == MembershipStatus.ACTIVE

    def __repr__(self) -> str:
        return (
            f"<UserMembership id={self.id} user_id={self.user_id} "
            f"plan_id={self.plan_id} status={self.membership_status}>"
        )
