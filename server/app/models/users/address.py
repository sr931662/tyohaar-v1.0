"""
UserAddress — saved addresses for event delivery and venue coordination.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import AddressType
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class UserAddress(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A saved address belonging to a user.

    Users may save multiple addresses (home, office, event venue, parents, etc.).
    Exactly one address per user can be flagged is_default=True.
    Geolocation (latitude, longitude) enables map integrations and delivery
    distance calculations for vendor assignment and logistics.

    delivery_instructions carries last-mile context (gate number, floor, landmark
    notes) that don't fit into the structured address fields.
    """

    __tablename__ = "user_addresses"

    __table_args__ = (
        Index("ix_user_addresses_user_id", "user_id"),
        Index("ix_user_addresses_user_default", "user_id", "is_default"),
        Index("ix_user_addresses_city_state", "city", "state"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Classification ────────────────────────────────────────────────────────

    address_type: Mapped[AddressType] = mapped_column(
        SAEnum(AddressType, name="address_type", native_enum=False),
        nullable=False,
        default=AddressType.HOME,
    )

    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Custom name given by the user (e.g., 'Mom's House', 'Office Terrace')",
    )

    # ── Recipient ─────────────────────────────────────────────────────────────

    recipient_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Name of the person who will receive the delivery or host the event",
    )

    recipient_phone: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="Contact number at this address",
    )

    alternate_phone: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # ── Structured Address ────────────────────────────────────────────────────

    address_line_1: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="House/flat number, building name, street name",
    )

    address_line_2: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Area, sector, colony, layout name",
    )

    landmark: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Nearby landmark for easier navigation",
    )

    locality: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="Neighbourhood or locality name",
    )

    city: Mapped[str] = mapped_column(String(100), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="India")
    postal_code: Mapped[str] = mapped_column(String(10), nullable=False)

    # ── Geolocation ───────────────────────────────────────────────────────────

    latitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="WGS-84 latitude. Populated via geocoding on save.",
    )

    longitude: Mapped[float | None] = mapped_column(
        Numeric(10, 7),
        nullable=True,
        comment="WGS-84 longitude. Populated via geocoding on save.",
    )

    # ── Delivery Context ──────────────────────────────────────────────────────

    delivery_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Free-text last-mile instructions for vendors/delivery partners "
            "(e.g., 'Ring bell twice', 'Gate passcode: 1234', 'Third floor no lift')"
        ),
    )

    # ── Flags ─────────────────────────────────────────────────────────────────

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="At most one address per user should have this set to True",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    user: Mapped[User] = relationship("User", back_populates="addresses")

    def __repr__(self) -> str:
        return (
            f"<UserAddress id={self.id} user_id={self.user_id} "
            f"city={self.city!r} type={self.address_type}>"
        )
