"""common package items: vendor-owned reusable items + package_item_links

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("package_items", "package_id", nullable=True)

    op.add_column(
        "package_items",
        sa.Column("vendor_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "package_items",
        sa.Column("is_common", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_foreign_key(
        "fk_package_items_vendor_id_vendors",
        "package_items", "vendors",
        ["vendor_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_package_items_vendor_id", "package_items", ["vendor_id"])

    op.create_check_constraint(
        "ck_package_items_common_xor_package",
        "package_items",
        "(is_common AND package_id IS NULL) OR (NOT is_common AND package_id IS NOT NULL)",
    )

    op.create_table(
        "package_item_links",
        sa.Column("package_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("package_item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("package_id", "package_item_id"),
        sa.ForeignKeyConstraint(
            ["package_id"], ["packages.id"],
            name="fk_package_item_links_package_id_packages",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["package_item_id"], ["package_items.id"],
            name="fk_package_item_links_package_item_id_package_items",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_package_item_links_package_item_id", "package_item_links", ["package_item_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_package_item_links_package_item_id", table_name="package_item_links")
    op.drop_table("package_item_links")
    op.drop_constraint("ck_package_items_common_xor_package", "package_items", type_="check")
    op.drop_index("ix_package_items_vendor_id", table_name="package_items")
    op.drop_constraint("fk_package_items_vendor_id_vendors", "package_items", type_="foreignkey")
    op.drop_column("package_items", "is_common")
    op.drop_column("package_items", "vendor_id")
    op.alter_column("package_items", "package_id", nullable=False)
