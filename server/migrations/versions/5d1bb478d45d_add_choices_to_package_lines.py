"""Add choices to package items and services

Selectable values a customer picks from on a customisable add-on — the
marquee LED number being the case that prompted it. Stored as a JSONB list of
display strings alongside the existing is_customizable flag, which until now
said that a line was configurable without saying what the options were.

Nullable with no backfill: every existing line has no choices, which is
exactly how they should render.

Revision ID: 5d1bb478d45d
Revises: 9b2e8c4d3f51
Create Date: 2026-09-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "5d1bb478d45d"
down_revision: Union[str, None] = "9b2e8c4d3f51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COMMENT = (
    "Selectable values the customer picks from when is_customizable is set — "
    "e.g. the numbers offered for a marquee LED item. A list of display "
    "strings; null or empty means the line takes no choice."
)

_PROMPT_COMMENT = (
    "Question shown to the customer for a free-text customisation — e.g. "
    "'Which characters do you need?' on a marquee letter set. Used when "
    "choices is empty; with choices set, the customer picks from that list."
)


def upgrade() -> None:
    # booking_service_items gains the notes column booking_items already has,
    # so a customisable service's pick has somewhere to be snapshotted too.
    op.add_column(
        "booking_service_items",
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Customer's pick for a customisable service, snapshotted at booking time.",
        ),
    )
    for table in ("package_items", "package_services"):
        op.add_column(
            table,
            sa.Column(
                "choices",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                comment=_COMMENT,
            ),
        )
        op.add_column(
            table,
            sa.Column(
                "customization_prompt",
                sa.String(length=200),
                nullable=True,
                comment=_PROMPT_COMMENT,
            ),
        )


def downgrade() -> None:
    for table in ("package_items", "package_services"):
        op.drop_column(table, "customization_prompt")
        op.drop_column(table, "choices")
    op.drop_column("booking_service_items", "notes")
