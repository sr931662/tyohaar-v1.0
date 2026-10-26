"""character sets for customisable lines + managed balloon colour palette

* package_items / package_services get `character_set` (DIGITS | LETTERS |
  ALPHANUMERIC). Every existing customisable line keeps behaving as before
  because the default is DIGITS.
* `balloon_colors` replaces the hard-coded balloon palette so admins can manage
  it. Seeded with the 13 colours the app already offered, in the same order,
  so nothing changes for customers on day one.

balloon_color_mode needs no change: the column is VARCHAR(6) holding the enum
member name and 'TRIPLE' / 'QUAD' fit.

Enum columns store the Python member *name*, so the values here are upper-case.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-10-26 00:00:00.000000
"""
from __future__ import annotations

import uuid
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None

SEED = [
    ("Red", "#E63946"),
    ("Gold", "#D4AF37"),
    ("Rose Gold", "#E8B4B8"),
    ("Pink", "#F48FB1"),
    ("Sky Blue", "#87CEEB"),
    ("Navy Blue", "#1E3A5F"),
    ("White", "#FFFFFF"),
    ("Black", "#1C1C1C"),
    ("Silver", "#C0C0C0"),
    ("Purple", "#8E44AD"),
    ("Green", "#2ECC71"),
    ("Orange", "#F39C12"),
    ("Yellow", "#F1C40F"),
]


def upgrade() -> None:
    for table in ("package_items", "package_services"):
        op.add_column(
            table,
            sa.Column("character_set", sa.String(12), nullable=False, server_default="DIGITS"),
        )

    colors = op.create_table(
        "balloon_colors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(60), nullable=False),
        sa.Column("hex_code", sa.String(7), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("hex_code", name="uq_balloon_colors_hex_code"),
    )
    op.create_index("uq_balloon_colors_name_lower", "balloon_colors", [sa.text("lower(name)")], unique=True)
    op.bulk_insert(
        colors,
        [
            {"id": uuid.uuid4(), "name": name, "hex_code": hex_code, "sort_order": i, "is_active": True}
            for i, (name, hex_code) in enumerate(SEED)
        ],
    )


def downgrade() -> None:
    op.drop_index("uq_balloon_colors_name_lower", table_name="balloon_colors")
    op.drop_table("balloon_colors")
    for table in ("package_services", "package_items"):
        op.drop_column(table, "character_set")
