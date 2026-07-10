"""
Vendor — the internal business entity behind every service delivery on Tyohaar.

Customers never interact with this model directly. They see curated packages
and experiences; Tyohaar maps their requests to vendors behind the scenes.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    VendorStatus,
    VendorType,
    VendorVerificationStatus,
)
from app.models.mixins import (
    AuditMixin,
    MetadataMixin,
    NotesMixin,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
)

if TYPE_CHECKING:
    from app.models.users.user import User
    from app.models.vendors.vendor_availability import VendorBlockedPeriod, VendorWorkSchedule
    from app.models.vendors.vendor_bank import VendorBankAccount
    from app.models.vendors.vendor_document import VendorDocument
    from app.models.vendors.vendor_gallery import VendorGalleryItem
    from app.models.vendors.vendor_profile import VendorProfile
    from app.models.vendors.vendor_review import VendorReview
    from app.models.vendors.vendor_service import VendorService
    from app.models.vendors.vendor_settlement import VendorSettlement
    from app.models.vendors.vendor_team import VendorTeamMember


class Vendor(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, NotesMixin, MetadataMixin, Base):
    """
    Represents a vendor business registered on the Tyohaar platform.

    Key design principles:
    - Vendor identity is completely hidden from customers. Customers only see
      Tyohaar-branded packages and experiences.
    - A Vendor is linked to exactly one User account (the business owner/operator).
    - Performance metrics (rating, completion_count, etc.) are denormalized here
      for fast sorting/filtering. They are recalculated asynchronously from the
      reviews and bookings tables.
    - `assigned_account_manager_id` links to a User with role=ADMIN or SUPPORT,
      enabling dedicated account management at scale.
    """

    __tablename__ = "vendors"

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_vendors_user_id"),
        UniqueConstraint("gst_number", name="uq_vendors_gst_number"),
        UniqueConstraint("pan_number", name="uq_vendors_pan_number"),
        Index("ix_vendors_status_type", "status", "vendor_type"),
        Index("ix_vendors_verification_status", "verification_status"),
        Index("ix_vendors_average_rating", "average_rating"),
        Index("ix_vendors_priority_score", "priority_score"),
        CheckConstraint("average_rating >= 0 AND average_rating <= 5", name="ck_vendors_rating_range"),
        CheckConstraint("acceptance_rate_pct >= 0 AND acceptance_rate_pct <= 100", name="ck_vendors_acceptance_rate_range"),
        CheckConstraint("review_count >= 0", name="ck_vendors_review_count_non_negative"),
        CheckConstraint("completion_count >= 0", name="ck_vendors_completion_count_non_negative"),
    )

    # ── Owner Account ─────────────────────────────────────────────────────────

    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        comment="The User account that operates this vendor business",
    )

    # ── Business Identity ─────────────────────────────────────────────────────

    business_name: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
        comment="Trading/brand name used for internal records and staff communication",
    )

    legal_name: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Registered legal entity name as per government documents",
    )

    vendor_type: Mapped[VendorType] = mapped_column(
        SAEnum(VendorType, name="vendor_type", native_enum=False),
        nullable=False,
        index=True,
    )

    registration_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Business registration / company incorporation number",
    )

    gst_number: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="15-character GST Identification Number (GSTIN)",
    )

    pan_number: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        comment="10-character Permanent Account Number for TDS processing",
    )

    # ── Verification & Status ─────────────────────────────────────────────────

    verification_status: Mapped[VendorVerificationStatus] = mapped_column(
        SAEnum(VendorVerificationStatus, name="vendor_verification_status", native_enum=False),
        nullable=False,
        default=VendorVerificationStatus.UNVERIFIED,
    )

    status: Mapped[VendorStatus] = mapped_column(
        SAEnum(VendorStatus, name="vendor_status", native_enum=False),
        nullable=False,
        default=VendorStatus.PENDING,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # ── Operations ────────────────────────────────────────────────────────────

    service_radius_km: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Maximum distance in km the vendor is willing to travel for an event",
    )

    years_of_experience: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
    )

    established_year: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="Year the business was founded (e.g., 2018)",
    )

    # ── Performance Metrics (denormalized, recalculated async) ────────────────

    average_rating: Mapped[float] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=0.0,
        comment="Running average rating 0.00–5.00. Recomputed after each review.",
    )

    review_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    completion_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total bookings successfully completed",
    )

    cancellation_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total bookings cancelled by this vendor",
    )

    acceptance_rate_pct: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=100.0,
        comment="Percentage of booking requests accepted. Affects priority_score.",
    )

    avg_response_time_minutes: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Average time (in minutes) to accept or reject a booking request",
    )

    # ── Internal Management ───────────────────────────────────────────────────

    assigned_account_manager_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Tyohaar staff member responsible for this vendor relationship",
    )

    priority_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        comment=(
            "Internal score 0–100 used for vendor ranking in assignment algorithms. "
            "Influenced by rating, acceptance rate, completion count, and manual overrides."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    owner: Mapped[User] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="noload",
    )

    account_manager: Mapped[User | None] = relationship(
        "User",
        foreign_keys=[assigned_account_manager_id],
        lazy="noload",
    )

    profile: Mapped[VendorProfile] = relationship(
        "VendorProfile",
        back_populates="vendor",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="noload",
    )

    services: Mapped[list[VendorService]] = relationship(
        "VendorService",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    gallery: Mapped[list[VendorGalleryItem]] = relationship(
        "VendorGalleryItem",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    documents: Mapped[list[VendorDocument]] = relationship(
        "VendorDocument",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    bank_accounts: Mapped[list[VendorBankAccount]] = relationship(
        "VendorBankAccount",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    work_schedule: Mapped[list[VendorWorkSchedule]] = relationship(
        "VendorWorkSchedule",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    blocked_periods: Mapped[list[VendorBlockedPeriod]] = relationship(
        "VendorBlockedPeriod",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    team: Mapped[list[VendorTeamMember]] = relationship(
        "VendorTeamMember",
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="noload",
    )

    reviews: Mapped[list[VendorReview]] = relationship(
        "VendorReview",
        back_populates="vendor",
        lazy="noload",
    )

    settlements: Mapped[list[VendorSettlement]] = relationship(
        "VendorSettlement",
        back_populates="vendor",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Vendor id={self.id} business_name={self.business_name!r} "
            f"type={self.vendor_type} status={self.status}>"
        )
