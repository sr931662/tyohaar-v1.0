"""
FAQ — Frequently Asked Questions managed through the CMS.

FAQs are displayed across multiple surfaces in the app:
- Help Center (full list, grouped by category)
- Checkout flow (booking-specific questions inline)
- Vendor onboarding flow (vendor-specific questions)
- Support chat pre-escalation (relevant FAQs suggested before ticket creation)

`target_role` gates visibility by user type: null = everyone, or a specific
UserRole so vendor-specific FAQs do not clutter the customer help centre.

Multilingual support via `translations`:
    {
      "hi": {"question": "बुकिंग कैसे करें?", "answer": "..."},
      "ta": {"question": "எவ்வாறு முன்பதிவு செய்வது?", "answer": "..."}
    }
The app uses the authenticated user's preferred_language from UserProfile
to select the appropriate translation, falling back to English when absent.

`search_keywords` is a PostgreSQL ARRAY of terms that boost this FAQ in the
help-centre search (e.g. ["refund", "money back", "cancellation charge"]).
A GIN index on this column enables fast contains-any queries.

Helpfulness counters (`helpful_count`, `not_helpful_count`) power the
"Was this helpful?" widget and are used to rank FAQs within their category.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SAEnum,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.enums import ContentStatus, FAQCategory, UserRole
from app.models.mixins import AuditMixin, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class FAQ(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditMixin, Base):
    """
    A single Frequently Asked Question entry in the Tyohaar Help Centre.

    Display priority within a category:
        1. is_featured = True (pinned to top)
        2. display_order ASC
        3. helpful_count DESC (most helpful first within same order)

    CMS lifecycle:
        DRAFT → (review) → PUBLISHED → (retire) → ARCHIVED

    Admin users author FAQs in the CMS; marketing team reviews and publishes.
    `created_by_id` and `updated_by_id` (from AuditMixin) track authorship.

    `view_count` is incremented asynchronously each time the FAQ is opened
    in the help centre.  It drives content strategy (identify knowledge gaps).
    """

    __tablename__ = "faqs"

    __table_args__ = (
        Index("ix_faqs_faq_category", "faq_category"),
        Index("ix_faqs_status", "status"),
        Index("ix_faqs_is_active", "is_active"),
        Index("ix_faqs_is_featured", "is_featured"),
        Index("ix_faqs_target_role", "target_role"),
        Index("ix_faqs_category_order", "faq_category", "display_order"),
        Index(
            "ix_faqs_keywords_gin",
            "search_keywords",
            postgresql_using="gin",
        ),
        CheckConstraint("display_order >= 0", name="ck_faqs_display_order_non_negative"),
        CheckConstraint("helpful_count >= 0", name="ck_faqs_helpful_count_non_negative"),
        CheckConstraint(
            "not_helpful_count >= 0", name="ck_faqs_not_helpful_count_non_negative"
        ),
        CheckConstraint("view_count >= 0", name="ck_faqs_view_count_non_negative"),
    )

    # ── Classification ────────────────────────────────────────────────────────

    faq_category: Mapped[FAQCategory] = mapped_column(
        SAEnum(FAQCategory, name="faq_category", native_enum=False),
        nullable=False,
        comment="Help Centre section this FAQ belongs to",
    )

    # ── Content ───────────────────────────────────────────────────────────────

    question: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
        comment="The FAQ question in plain text (English default)",
    )

    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment=(
            "Full answer text. Supports Markdown for rich formatting. "
            "Rendered by the app's Markdown parser."
        ),
    )

    short_answer: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment=(
            "Condensed one-liner answer for tooltip or snackbar contexts "
            "where the full answer would not fit."
        ),
    )

    # ── Multilingual ──────────────────────────────────────────────────────────

    translations: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Language-keyed translations. "
            'Structure: {"hi": {"question": "...", "answer": "...", "short_answer": "..."}}'
        ),
    )

    # ── Targeting ─────────────────────────────────────────────────────────────

    target_role: Mapped[UserRole | None] = mapped_column(
        SAEnum(UserRole, name="user_role", native_enum=False),
        nullable=True,
        comment=(
            "Restrict visibility to a specific user role. "
            "NULL = visible to all authenticated users."
        ),
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Manual sort rank within the category (lower = shown first)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False hides the FAQ immediately without deleting it",
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="True pins this FAQ to the top of its category section",
    )

    # ── Search ────────────────────────────────────────────────────────────────

    search_keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),
        nullable=True,
        comment=(
            "Additional terms that map to this FAQ in the help search "
            "(e.g. ['refund', 'money back', 'cancellation']).  "
            "GIN-indexed for fast contains-any queries."
        ),
    )

    # ── CMS Lifecycle ─────────────────────────────────────────────────────────

    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", native_enum=False),
        nullable=False,
        default=ContentStatus.DRAFT,
        comment="CMS publication state",
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when the FAQ was first published",
    )

    # ── Analytics (denormalized) ──────────────────────────────────────────────

    helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Cumulative 'Yes, this was helpful' votes",
    )

    not_helpful_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Cumulative 'No, this was not helpful' votes",
    )

    view_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Approximate number of times this FAQ was opened by a user",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def helpfulness_ratio(self) -> float:
        """
        Ratio of helpful votes to total votes (0.0–1.0).
        Returns 1.0 when there are no votes yet (optimistic default).
        """
        total = self.helpful_count + self.not_helpful_count
        if not total:
            return 1.0
        return self.helpful_count / total

    def __repr__(self) -> str:
        return (
            f"<FAQ id={self.id} category={self.faq_category} "
            f"status={self.status} question={self.question[:50]!r}>"
        )
