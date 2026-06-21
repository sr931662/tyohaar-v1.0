"""
PrivacyPolicy — versioned privacy policy document for the platform.

Mirrors the TermsAndConditions versioning pattern.  A new row is inserted for
every material update to the privacy policy; superseded rows are kept
permanently for compliance and audit purposes.

Privacy policy scope is broader than Terms — there is typically only one active
policy per language (not scoped to a user role), so the unique constraint is
on (version, language) without a role dimension.

`sections` JSONB allows the policy to be structured into named sections that
the mobile app can deep-link to and render as a table-of-contents:
    [
      {"order": 1, "anchor": "data_collection",
       "title": "Data We Collect", "content": "..."},
      {"order": 2, "anchor": "data_use",
       "title": "How We Use Your Data", "content": "..."},
      {"order": 3, "anchor": "third_parties",
       "title": "Third-Party Sharing", "content": "..."}
    ]

GDPR / DPDPA compliance notes:
- `must_accept_version = True` triggers a re-consent modal on next login.
- `effective_date` gives users the required advance-notice period.
- The policy version and acceptance timestamp must be stored per-user
  (tracked in the users domain, not here).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ContentStatus, Language
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin


class PrivacyPolicy(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """
    A versioned Privacy Policy document.

    One row per (version, language) combination.
    The `superseded_by_id` self-reference creates a version chain:
        v1.0 → v1.1 → v2.0

    The service layer enforces that only ONE row per language is in PUBLISHED
    status at any time (business rule, not a DB constraint, to allow scheduled
    future versions in SCHEDULED state alongside the current PUBLISHED version).

    `sections` enables section-anchored deep linking from the privacy settings
    screen (e.g. "Your Data Rights" → jump to the data_rights anchor).

    `author_id` is a bare UUID referencing the Admin record that authored the
    document, stored without a FK to avoid domain coupling.
    """

    __tablename__ = "privacy_policies"

    __table_args__ = (
        UniqueConstraint(
            "version", "language",
            name="uq_privacy_policies_version_language",
        ),
        Index("ix_privacy_policies_status", "status"),
        Index("ix_privacy_policies_effective_date", "effective_date"),
        Index("ix_privacy_policies_language", "language"),
        Index("ix_privacy_policies_status_effective", "status", "effective_date"),
    )

    # ── Versioning ────────────────────────────────────────────────────────────

    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Semantic version string (e.g. '1.0', '2.1')",
    )

    version_label: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="Human-readable version name (e.g. 'DPDPA Compliance Update 2025')",
    )

    # ── Content ───────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Policy document title shown in the privacy settings screen",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Full privacy policy text. Supports HTML/Markdown. "
            "Rendered in the in-app WebView."
        ),
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Plain-language summary of key changes in this version",
    )

    sections: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Structured array of policy sections for table-of-contents rendering. "
            "Structure: [{order, anchor, title, content}]"
        ),
    )

    # ── Multilingual ──────────────────────────────────────────────────────────

    language: Mapped[Language] = mapped_column(
        SAEnum(Language, name="language", native_enum=False),
        nullable=False,
        default=Language.ENGLISH,
        comment="Primary language of this document (BCP-47 tag)",
    )

    translations: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Localised versions keyed by BCP-47 language tag. "
            'Structure: {"hi": {"title": "...", "content": "...", "summary": "..."}}'
        ),
    )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", native_enum=False),
        nullable=False,
        default=ContentStatus.DRAFT,
        comment="CMS publication state of this policy version",
    )

    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "Legal effective date. May be in the future to give users advance notice "
            "as required by DPDPA and similar regulations."
        ),
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when this version was published on the platform",
    )

    superseded_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date this version was replaced by a newer version",
    )

    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("privacy_policies.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to the PrivacyPolicy row that replaced this version",
    )

    # ── User Acceptance ───────────────────────────────────────────────────────

    must_accept_version: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True triggers a re-consent modal on next user login. "
            "Set False for minor editorial corrections."
        ),
    )

    # ── Authorship ────────────────────────────────────────────────────────────

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the Admin who authored or approved this document. "
            "Bare UUID — no FK to avoid coupling with the admin domain."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    superseded_by: Mapped[PrivacyPolicy | None] = relationship(
        "PrivacyPolicy",
        foreign_keys=[superseded_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PrivacyPolicy id={self.id} version={self.version!r} "
            f"language={self.language} status={self.status} "
            f"effective={self.effective_date}>"
        )
