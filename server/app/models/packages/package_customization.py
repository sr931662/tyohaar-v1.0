"""
PackageCustomization — configurable option templates for a package.

Defines WHAT choices are available (theme colors, cake flavor, etc.).
Customer's actual selections for a booking are stored in the Bookings domain.
"""

from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.packages.package import Package


class CustomizationOptionType(str, enum.Enum):
    """
    Data type of the customization input field.
    NOTE: Move to app/models/enums.py in the next enums update.
    """
    TEXT = "text"                    # Free-text input (e.g., name on cake)
    SINGLE_SELECT = "single_select"  # Pick one from a list (e.g., cake flavor)
    MULTI_SELECT = "multi_select"    # Pick many from a list (e.g., balloon colors)
    COLOR = "color"                  # Color picker (hex code)
    NUMBER = "number"                # Numeric input (e.g., extra guests)
    DATE = "date"                    # Date picker
    IMAGE_UPLOAD = "image_upload"    # Customer uploads a photo (e.g., for a banner)


class PackageCustomization(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """
    A single configurable option template for a package.

    Examples for a Birthday Package:
    - name: 'Cake Flavor', type: SINGLE_SELECT,
      options: ['Chocolate', 'Vanilla', 'Strawberry', 'Butterscotch']
    - name: 'Balloon Colors', type: MULTI_SELECT,
      options: ['Red', 'Blue', 'Gold', 'White', 'Pink']
    - name: 'Banner Message', type: TEXT
    - name: 'Honoree Photo', type: IMAGE_UPLOAD

    `options` JSONB stores available choices for SELECT types (list of strings),
    or validation rules for TEXT/NUMBER types (dict: {max_length: 50}).
    """

    __tablename__ = "package_customizations"

    __table_args__ = (
        Index("ix_package_customizations_package_id", "package_id"),
        Index("ix_package_customizations_order", "package_id", "display_order"),
    )

    # ── Ownership ─────────────────────────────────────────────────────────────

    package_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Configuration ─────────────────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Customer-facing label (e.g. 'Cake Flavor', 'Banner Message')",
    )

    option_type: Mapped[CustomizationOptionType] = mapped_column(
        SAEnum(CustomizationOptionType, name="customization_option_type", native_enum=False),
        nullable=False,
    )

    options: Mapped[list[Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment=(
            "Available choices for SELECT types (list of strings). "
            "Validation rules for TEXT/NUMBER types (dict e.g. {max_length: 50})."
        ),
    )

    placeholder_text: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="Hint text shown inside the input field",
    )

    help_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Extended help text shown below the input field",
    )

    # ── Validation ────────────────────────────────────────────────────────────

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Required customizations must be completed before booking is confirmed",
    )

    # ── Display ───────────────────────────────────────────────────────────────

    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Relationships ─────────────────────────────────────────────────────────

    package: Mapped[Package] = relationship(
        "Package",
        back_populates="customizations",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PackageCustomization id={self.id} name={self.name!r} "
            f"type={self.option_type}>"
        )
