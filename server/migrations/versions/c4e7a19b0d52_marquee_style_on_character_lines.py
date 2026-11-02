"""marquee_style on customisable package lines — LED vs balloon presentation

A character line (marquee letters / numbers) can now be shown to the customer
as lit LED pieces or as balloon letters in the colours they chose. Presentation
only: billing and character sets are untouched. Every existing line keeps
behaving as before because the default is LED.

Enum columns store the Python member *name*, so the default is upper-case.

Revision ID: c4e7a19b0d52
Revises: b182698914aa
Create Date: 2026-11-02 00:00:00.000000
"""
from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e7a19b0d52"
down_revision: Union[str, None] = "b182698914aa"
branch_labels = None
depends_on = None

TABLES = ("package_items", "package_services")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column("marquee_style", sa.String(7), nullable=False, server_default="LED"),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, "marquee_style")
