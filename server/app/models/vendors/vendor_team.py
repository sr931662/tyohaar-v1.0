"""
VendorTeamMember — employees and contractors registered under a vendor.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Date,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorTeamRole(str, enum.Enum):
    """
    Operational role of a team member within a vendor organization.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    OWNER = "owner"
    MANAGER = "manager"
    PHOTOGRAPHER = "photographer"
    VIDEOGRAPHER = "videographer"
    DECORATOR = "decorator"
    MAKEUP_ARTIST = "makeup_artist"
    MEHNDI_ARTIST = "mehndi_artist"
    DRIVER = "driver"
    COORDINATOR = "coordinator"
    SUPPORT_STAFF = "support_staff"
    CATERER = "caterer"
    OTHER = "other"


class VendorTeamMember(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    An individual working under a vendor for event execution.

    Team members may be assigned to specific bookings by the Tyohaar
    coordination team. Their contact details are used for on-ground
    coordination and are never shared with customers.

    `employee_id` is the vendor's own internal reference number, if any.
    """

    __tablename__ = "vendor_team_members"

    __table_args__ = (
        Index("ix_vendor_team_members_vendor_id", "vendor_id"),
        Index("ix_vendor_team_members_role", "vendor_id", "role", "is_active"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(String(200), nullable=False)

    role: Mapped[VendorTeamRole] = mapped_column(
        SAEnum(VendorTeamRole, name="vendor_team_role", native_enum=False),
        nullable=False,
    )

    employee_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Vendor's internal staff ID for this person",
    )

    specialization: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment=(
            "Free-text specialization note (e.g., 'Candid Wedding Photography', "
            "'Drone Operator', 'Senior Decorator')"
        ),
    )

    # ── Contact ───────────────────────────────────────────────────────────────

    phone: Mapped[str | None] = mapped_column(
        String(15),
        nullable=True,
        comment="On-ground contact number. Used only by Tyohaar coordination staff.",
    )

    email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    # ── Employment ────────────────────────────────────────────────────────────

    joining_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # ── Emergency Contact ─────────────────────────────────────────────────────

    emergency_contact_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    emergency_contact_phone: Mapped[str | None] = mapped_column(String(15), nullable=True)

    # ── Notes ─────────────────────────────────────────────────────────────────

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes about this team member (availability, skills, etc.)",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="team")

    def __repr__(self) -> str:
        return (
            f"<VendorTeamMember id={self.id} vendor_id={self.vendor_id} "
            f"name={self.name!r} role={self.role}>"
        )
