"""
InvitationTemplate — a reusable, versioned invitation design.

System-provided and customer-created templates for rendering digital invitation
cards. Templates support multi-language content, placeholder substitution,
per-occasion targeting, and iterative versioning.
"""

from __future__ import annotations

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

from app.models.base import Base
from app.models.enums import Language, OccasionCategory
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.users.user import User


class InvitationTemplate(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    A versioned design template for invitation cards.

    Templates are either system-provided (is_system_template=True, curated by
    Tyohaar) or user-created (is_system_template=False, owned by a customer).
    Only system templates are shared platform-wide; user templates are private.

    Template rendering:
    1. Customer selects a template and fills in placeholder values.
    2. The render service merges `placeholder_values` into `html_content`,
       substituting {{key}} tokens with the provided values.
    3. The resulting HTML is served as the invitation card page.

    Versioning:
    - `version` is incremented on every significant content change.
    - Creating a new version does NOT update existing Invitation records —
      snapshots are taken at invitation creation time via `placeholder_values`.
    - A template can be retired (is_active=False) without deleting it so that
      existing invitations that reference it continue to render correctly.

    `placeholders` JSONB defines the substitution tokens available in this template:
        [
          {
            "key": "host_name",
            "label": "Host Name(s)",
            "required": true,
            "example": "Priya & Arjun",
            "type": "text",
            "max_length": 100
          },
          {
            "key": "venue_map_url",
            "label": "Venue Map Link",
            "required": false,
            "type": "url"
          }
        ]

    `supported_channels` lists the InvitationShareChannel values this template
    is optimised for (e.g., a rich HTML template is unsuitable for SMS).
    """

    __tablename__ = "invitation_templates"

    __table_args__ = (
        UniqueConstraint(
            "name", "language", "version",
            name="uq_invitation_templates_name_lang_version",
        ),
        Index("ix_invitation_templates_occasion_category", "occasion_category"),
        Index("ix_invitation_templates_language", "language"),
        Index("ix_invitation_templates_is_active", "is_active"),
        Index("ix_invitation_templates_system_active", "is_system_template", "is_active"),
        CheckConstraint("version >= 1", name="ck_invitation_templates_version_positive"),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Internal and display name of the template e.g. 'Classic Wedding - Hindi'.",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Customer-facing description shown in the template gallery.",
    )

    # ── Ownership & Access ────────────────────────────────────────────────────

    is_system_template: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for platform-curated templates visible to all customers. "
            "False for privately-created templates visible only to the owner."
        ),
    )

    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "User who created this template. NULL for system templates "
            "created via migrations or the admin panel."
        ),
    )

    # ── Targeting ─────────────────────────────────────────────────────────────

    occasion_category: Mapped[OccasionCategory | None] = mapped_column(
        SAEnum(OccasionCategory, name="occasion_category", native_enum=False),
        nullable=True,
        comment=(
            "The occasion type this template is designed for. "
            "NULL means it is generic and applies to all occasions."
        ),
    )

    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language", native_enum=False),
        nullable=False,
        default=Language.ENGLISH,
        comment="Primary language of the template content.",
    )

    # ── Status & Versioning ───────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "False to retire the template from the gallery. "
            "Existing invitations that use it continue to render correctly."
        ),
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True for the recommended default template for its occasion_category. "
            "At most one template per (occasion_category, language) should be default."
        ),
    )

    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Monotonically increasing version counter. Incremented on content changes.",
    )

    # ── Content ───────────────────────────────────────────────────────────────

    html_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Full HTML/CSS of the invitation card. "
            "Placeholder tokens use {{key}} syntax e.g. {{host_name}}."
        ),
    )

    text_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Plain-text version of the invitation for SMS and WhatsApp channels. "
            "Placeholder tokens use the same {{key}} syntax."
        ),
    )

    # ── Placeholder Schema ────────────────────────────────────────────────────

    placeholders: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Array of placeholder definitions: "
            "[{key, label, required, type, example, max_length}]. "
            "Drives the invitation customization form in the app."
        ),
    )

    # ── Media ─────────────────────────────────────────────────────────────────

    thumbnail_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="CDN URL of the template thumbnail shown in the gallery grid.",
    )

    preview_image_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="CDN URL of the full-size template preview image.",
    )

    # ── Channel Support ───────────────────────────────────────────────────────

    supported_channels: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "InvitationShareChannel values this template supports. "
            "Example: ['whatsapp', 'email', 'link']. NULL means all channels."
        ),
    )

    # ── Discovery ─────────────────────────────────────────────────────────────

    tags: Mapped[list[str] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Searchable tags for template discovery e.g. ['floral', 'minimalist', 'premium'].",
    )

    category_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "Display category shown in the gallery e.g. 'Premium', 'Free', 'Seasonal'. "
            "Distinct from occasion_category — this is for billing/tier grouping."
        ),
    )

    usage_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Denormalized count of how many invitations have used this template.",
    )

    # ── Changelog ─────────────────────────────────────────────────────────────

    last_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the template content was last materially changed.",
    )

    change_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Internal notes describing what changed in this version.",
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    created_by: Mapped[User | None] = relationship(
        "User",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<InvitationTemplate id={self.id} name={self.name!r} "
            f"v{self.version} lang={self.language} system={self.is_system_template}>"
        )
