"""
CouponRedemption — one row per successful coupon application to a payment.

Source of truth for enforcing `Coupon.per_user_limit`. `Coupon.times_used` is
the denormalized total counter; this table lets the service layer count how
many times a *specific* user has redeemed a *specific* coupon.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.payments.coupon import Coupon
    from app.models.payments.payment import Payment
    from app.models.users.user import User


class CouponRedemption(UUIDPrimaryKeyMixin, Base):
    """A single user's redemption of a coupon against one payment."""

    __tablename__ = "coupon_redemptions"

    __table_args__ = (
        Index("ix_coupon_redemptions_coupon_id", "coupon_id"),
        Index("ix_coupon_redemptions_user_id", "user_id"),
        Index("ix_coupon_redemptions_coupon_user", "coupon_id", "user_id"),
    )

    coupon_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("coupons.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    payment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
    )

    redeemed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    coupon: Mapped[Coupon] = relationship("Coupon", lazy="noload")
    user: Mapped[User] = relationship("User", lazy="noload")
    payment: Mapped[Payment] = relationship("Payment", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<CouponRedemption id={self.id} coupon_id={self.coupon_id} "
            f"user_id={self.user_id}>"
        )
