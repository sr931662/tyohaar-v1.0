"""package item enhancements: max_quantity + package_item_images table

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("package_items", sa.Column("max_quantity", sa.Integer(), nullable=True))

    op.create_table(
        "package_item_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["item_id"], ["package_items.id"],
            name="fk_package_item_images_item_id_package_items",
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_package_item_images_item_id", "package_item_images", ["item_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_package_item_images_item_id", table_name="package_item_images")
    op.drop_table("package_item_images")
    op.drop_column("package_items", "max_quantity")
