"""
TermsAndConditions — versioned legal agreement text for the platform.

A new row is inserted for every version update; superseded rows are never
deleted (compliance requirement).  The `superseded_by_id` self-reference
forms an explicit linked list of the version chain:
    v1.0 → v1.1 → v2.0

`applicable_role` scopes a T&C to a specific user type:
    NULL → applies to all roles (general platform T&C)
    CUSTOMER → customer-specific terms
    VENDOR → vendor agreement / service-level terms

When a new version is published:
1. `status` → PUBLISHED, `published_at` set.
2. The previous active version: `superseded_at` set, `superseded_by_id` points
   to the new row.
3. Users see a "Re-accept Terms" modal on next login if `must_accept_version = True`.

User acceptance is tracked in a separate `user_term_acceptances` table
(implemented in the users domain — not part of this model).

Multilingual:
`language` selects the primary locale of this document.
`translations` holds alternative language versions of the same content:
    {
      "hi": {"title": "नियम एवं शर्तें", "content": "...", "summary": "..."},
      "ta": {"title": "விதிமுறைகள்", "content": "...", "summary": "..."}
    }
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
from app.models.enums import ContentStatus, Language, UserRole
from app.models.mixins import AuditMixin, TimestampMixin, UUIDPrimaryKeyMixin


class TermsAndConditions(UUIDPrimaryKeyMixin, TimestampMixin, AuditMixin, Base):
    """
    A versioned Terms & Conditions document.

    One row per (version, language, applicable_role) combination.
    The uniqueness constraint ensures no two active T&C rows occupy the same
    version slot for the same audience and language.

    Version string convention: semantic versioning "MAJOR.MINOR" (e.g. "2.1").
    MAJOR bump = material change requiring explicit re-acceptance.
    MINOR bump = editorial correction; `must_accept_version` may be False.

    `effective_date` is the legal effective date of this version,
    which may differ from `published_at` (the platform publication date).
    Law firms may require a future effective date to give users notice time.

    `author_id` is a bare UUID referencing an Admin record (not a FK to avoid
    cross-domain coupling between the common and admin domains at model level).
    """

    __tablename__ = "terms_and_conditions"

    __table_args__ = (
        UniqueConstraint(
            "version", "language", "applicable_role",
            name="uq_terms_version_language_role",
        ),
        Index("ix_terms_status", "status"),
        Index("ix_terms_effective_date", "effective_date"),
        Index("ix_terms_applicable_role", "applicable_role"),
        Index("ix_terms_language", "language"),
        Index("ix_terms_status_effective", "status", "effective_date"),
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
        comment="Human-readable version name shown to users (e.g. 'GST Compliance Update 2024')",
    )

    # ── Scope ─────────────────────────────────────────────────────────────────

    applicable_role: Mapped[UserRole | None] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False),
        nullable=True,
        comment=(
            "NULL = applies to all user roles. "
            "Set to 'customer' or 'vendor' for role-specific agreements."
        ),
    )

    # ── Content ───────────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Document title shown on the terms acceptance screen",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Full terms text. Supports HTML/Markdown. "
            "Rendered in the in-app WebView for terms acceptance flow."
        ),
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "Plain-language summary of key points for quick review. "
            "Not a legal substitute for full content."
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
        comment="CMS publication state of this document version",
    )

    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment=(
            "Legal effective date of this version. "
            "May be in the future (gives users advance notice of upcoming changes)."
        ),
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this version was published on the platform (status → PUBLISHED)",
    )

    superseded_at: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="Date this version was superseded by a newer version",
    )

    superseded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("terms_and_conditions.id", ondelete="SET NULL"),
        nullable=True,
        comment="FK to the newer TermsAndConditions row that replaced this version",
    )

    # ── User Acceptance ───────────────────────────────────────────────────────

    must_accept_version: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment=(
            "True requires users to explicitly re-accept these terms on next login. "
            "Set False for minor editorial corrections that do not require re-consent."
        ),
    )

    # ── Authorship ────────────────────────────────────────────────────────────

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment=(
            "UUID of the Admin who authored this document. "
            "Stored as bare UUID (no FK) to avoid coupling with the admin domain."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    superseded_by: Mapped[TermsAndConditions | None] = relationship(
        "TermsAndConditions",
        foreign_keys=[superseded_by_id],
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<TermsAndConditions id={self.id} version={self.version!r} "
            f"language={self.language} role={self.applicable_role} "
            f"status={self.status}>"
        )
