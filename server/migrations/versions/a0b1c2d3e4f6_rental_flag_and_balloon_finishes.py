"""rental/keep snapshot on booking items + managed balloon finishes

* booking_items.is_returnable — snapshot of PackageItem.is_returnable, so an
  invoice says RENTAL / KEEP from what was true at booking time. Existing rows
  are backfilled from the package item they came from (false when that item no
  longer exists).
* bookings.balloon_finish — the finish the customer chose.
* balloon_finishes — admin-managed list, seeded with the three finishes the
  customer flow offers.

Revision ID: a0b1c2d3e4f6
Revises: f8a9b0c1d2e3
Create Date: 2026-10-27 00:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a0b1c2d3e4f6"
down_revision: Union[str, None] = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None

FINISHES = ["Standard matte", "Pastel", "Chrome / metallic"]


def upgrade() -> None:
    op.add_column("booking_items", sa.Column("is_returnable", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute(
        """
        UPDATE booking_items bi
           SET is_returnable = pi.is_returnable
          FROM package_items pi
         WHERE bi.package_item_id = pi.id
        """
    )
    op.add_column("bookings", sa.Column("balloon_finish", sa.String(60), nullable=True))

    finishes = op.create_table(
        "balloon_finishes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_balloon_finishes_name_lower", "balloon_finishes", [sa.text("lower(name)")], unique=True)
    op.bulk_insert(
        finishes,
        [{"id": uuid.uuid4(), "name": n, "sort_order": i, "is_active": True} for i, n in enumerate(FINISHES)],
    )


def downgrade() -> None:
    op.drop_index("uq_balloon_finishes_name_lower", table_name="balloon_finishes")
    op.drop_table("balloon_finishes")
    op.drop_column("bookings", "balloon_finish")
    op.drop_column("booking_items", "is_returnable")
