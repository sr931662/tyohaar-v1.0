"""
VendorDocument — KYC and compliance document storage for vendor verification.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import VerificationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.vendors.vendor import Vendor


class VendorDocumentType(str, enum.Enum):
    """
    Types of KYC/compliance documents required for vendor verification.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    AADHAAR_CARD = "aadhaar_card"
    TRADE_LICENSE = "trade_license"
    BANK_STATEMENT = "bank_statement"
    CANCELLED_CHEQUE = "cancelled_cheque"
    SHOP_ACT_LICENSE = "shop_act_license"
    FSSAI_LICENSE = "fssai_license"         # For catering/food vendors
    POLICE_VERIFICATION = "police_verification"
    INSURANCE_DOCUMENT = "insurance_document"
    INCORPORATION_CERTIFICATE = "incorporation_certificate"
    OTHER = "other"


class VendorDocument(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single KYC or compliance document uploaded by a vendor.

    One vendor can have multiple documents of the same type (e.g., expired
    + current GST certificate). `is_current` flags the active version of each
    document type for a given vendor.

    Documents are never deleted — they are superseded. This preserves the
    full verification audit trail.

    Files must be stored in a private, access-controlled CDN/S3 bucket.
    `file_url` should be a signed URL or an internal reference resolved
    at request time — never a public URL for sensitive KYC documents.
    """

    __tablename__ = "vendor_documents"

    __table_args__ = (
        Index("ix_vendor_documents_vendor_id", "vendor_id"),
        Index("ix_vendor_documents_type_current", "vendor_id", "document_type", "is_current"),
        Index("ix_vendor_documents_verification_status", "verification_status"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Document Identity ─────────────────────────────────────────────────────

    document_type: Mapped[VendorDocumentType] = mapped_column(
        SAEnum(VendorDocumentType, name="vendor_document_type", native_enum=False),
        nullable=False,
    )

    # ── File Storage ──────────────────────────────────────────────────────────

    file_url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        comment=(
            "Internal storage path or CDN reference. "
            "Must resolve via signed URL — never a public link for KYC documents."
        ),
    )

    original_filename: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Original filename as uploaded by the vendor",
    )

    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mime_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="MIME type (e.g., 'application/pdf', 'image/jpeg')",
    )

    # ── Validity ──────────────────────────────────────────────────────────────

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Document expiry date (e.g., for trade licenses with fixed terms)",
    )

    # ── Verification State ────────────────────────────────────────────────────

    verification_status: Mapped[VerificationStatus] = mapped_column(
        SAEnum(VerificationStatus, name="verification_status", native_enum=False),
        nullable=False,
        default=VerificationStatus.PENDING,
    )

    verified_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="UUID of the Tyohaar staff member who verified this document",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Reason communicated to the vendor when verification is rejected",
    )

    # ── Version Management ────────────────────────────────────────────────────

    is_current: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True for the latest version of this document type for this vendor. "
            "Set to False when a newer document supersedes this one."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    vendor: Mapped[Vendor] = relationship("Vendor", back_populates="documents")

    def __repr__(self) -> str:
        return (
            f"<VendorDocument id={self.id} vendor_id={self.vendor_id} "
            f"type={self.document_type} status={self.verification_status}>"
        )
