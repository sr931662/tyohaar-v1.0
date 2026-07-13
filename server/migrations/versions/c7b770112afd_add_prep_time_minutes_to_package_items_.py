"""add prep_time_minutes to package_items and booking_items

Revision ID: c7b770112afd
Revises: b8c9d0e1f2a3
Create Date: 2026-07-13 21:13:45.204350

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c7b770112afd'
down_revision: Union[str, None] = 'b8c9d0e1f2a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("package_items", sa.Column("prep_time_minutes", sa.Integer(), nullable=True))
    op.add_column("booking_items", sa.Column("prep_time_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("booking_items", "prep_time_minutes")
    op.drop_column("package_items", "prep_time_minutes")
