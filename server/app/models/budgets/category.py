"""
ExpenseCategory — hierarchical taxonomy for budget expense items.

Supports two kinds of categories:
- System categories (is_system=True): platform-defined, mapped 1:1 to the
  BudgetCategory enum.  These cannot be deleted and carry a stable `slug`
  that the service layer uses for JSONB breakdown keys.
- Custom categories (is_system=False): created by customers for personal
  expense tracking that falls outside the platform taxonomy.

The tree is arbitrarily deep (parent_id self-reference) but in practice the
UI enforces a maximum depth of two levels (root → leaf) for usability.
Root categories have parent_id = NULL.

Deleting a parent category sets child parent_id values to NULL (SET NULL),
keeping orphaned children as root-level categories rather than cascading
a delete of user-entered expense data.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import BudgetCategory
from app.models.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.budgets.expense import Expense


class ExpenseCategory(UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, Base):
    """
    Hierarchical category for budget expense line items.

    System categories are seeded at deploy time and correspond 1:1 to
    `BudgetCategory` enum values.  They cannot be renamed or deleted via
    the admin UI.

    Custom categories are created by customers and can be freely edited or
    removed as long as no active expenses reference them (service layer guard).

    Tree structure:
        Decoration (root, system)
        └─ Floral Arrangements  (leaf, custom)
        └─ Stage & Lighting     (leaf, custom)
        Catering (root, system)
        ...

    The `slug` is URL-safe and stable; system slugs match BudgetCategory
    values exactly (e.g. "decoration", "catering").  Custom slugs are
    generated from the name and suffixed with a short UUID fragment to
    avoid collisions.

    `color_hex` follows the 6-digit hex format (#RRGGBB).
    `icon_url` points to a CDN-hosted SVG or PNG icon.
    `translations` stores display strings for supported languages:
        {"hi": {"name": "सजावट"}, "ta": {"name": "அலங்காரம்"}}
    """

    __tablename__ = "expense_categories"

    __table_args__ = (
        UniqueConstraint("slug", name="uq_expense_categories_slug"),
        Index("ix_expense_categories_parent_id", "parent_id"),
        Index("ix_expense_categories_is_system", "is_system"),
        Index("ix_expense_categories_is_active", "is_active"),
        Index("ix_expense_categories_display_order", "display_order"),
        Index("ix_expense_categories_system_category", "system_category"),
        CheckConstraint("display_order >= 0", name="ck_expense_categories_display_order_non_negative"),
        CheckConstraint(
            "NOT (is_system = true AND deleted_at IS NOT NULL)",
            name="ck_expense_categories_system_not_deleted",
        ),
    )

    # ── Hierarchy ─────────────────────────────────────────────────────────────

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("expense_categories.id", ondelete="SET NULL"),
        nullable=True,
        comment=(
            "Parent category UUID. NULL for root categories. "
            "SET NULL on parent delete keeps children as orphaned root entries."
        ),
    )

    # ── Identity ──────────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="Display name of the category (e.g. 'Decoration', 'Floral Arrangements')",
    )

    slug: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
        comment=(
            "URL-safe unique identifier. System slugs match BudgetCategory values. "
            "Custom slugs are auto-generated and may include a UUID suffix."
        ),
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of what expenses belong in this category",
    )

    # ── Platform Mapping ──────────────────────────────────────────────────────

    system_category: Mapped[BudgetCategory | None] = mapped_column(
        SAEnum(BudgetCategory, name="budget_category", native_enum=False),
        nullable=True,
        comment=(
            "Maps this row to a BudgetCategory enum value for system-defined categories. "
            "NULL for custom user-created categories."
        ),
    )

    is_system: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment=(
            "True = seeded by the platform; cannot be renamed or deleted by admins. "
            "False = created by a customer or admin for custom tracking."
        ),
    )

    # ── Display ───────────────────────────────────────────────────────────────

    icon_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        comment="CDN URL of a category icon (SVG or PNG, ~48×48px)",
    )

    color_hex: Mapped[str | None] = mapped_column(
        String(7),
        nullable=True,
        comment="6-digit hex color code (e.g. #FF5733) used for UI chips and charts",
    )

    display_order: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0,
        comment="Sort rank within the parent level (lower = displayed first)",
    )

    # ── Visibility ────────────────────────────────────────────────────────────

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="False hides the category from selection UIs without deleting it",
    )

    # ── Multilingual ──────────────────────────────────────────────────────────

    translations: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Language-keyed display strings for internationalisation. "
            'Structure: {"hi": {"name": "सजावट"}, "ta": {"name": "அலங்காரம்"}}'
        ),
    )

    # ── Usage Counter (denormalized) ──────────────────────────────────────────

    expense_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment=(
            "Denormalized count of active Expense records referencing this category. "
            "Maintained by the service layer; used to block deletion of referenced categories."
        ),
    )

    # ── Relationships ─────────────────────────────────────────────────────────

    parent: Mapped[ExpenseCategory | None] = relationship(
        "ExpenseCategory",
        foreign_keys="[ExpenseCategory.parent_id]",
        remote_side="[ExpenseCategory.id]",
        back_populates="children",
        lazy="noload",
    )

    children: Mapped[list[ExpenseCategory]] = relationship(
        "ExpenseCategory",
        foreign_keys="[ExpenseCategory.parent_id]",
        back_populates="parent",
        lazy="noload",
        cascade="save-update, merge",
    )

    expenses: Mapped[list[Expense]] = relationship(
        "Expense",
        back_populates="category",
        lazy="noload",
        cascade="save-update, merge",
    )

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def is_root(self) -> bool:
        """True when this is a top-level category with no parent."""
        return self.parent_id is None

    @property
    def is_deletable(self) -> bool:
        """System categories and categories with active expenses cannot be deleted."""
        return not self.is_system and self.expense_count == 0

    def __repr__(self) -> str:
        return (
            f"<ExpenseCategory id={self.id} slug={self.slug!r} "
            f"is_system={self.is_system} parent_id={self.parent_id}>"
        )
