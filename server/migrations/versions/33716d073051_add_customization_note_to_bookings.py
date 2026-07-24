"""add customization_note to bookings

Revision ID: 33716d073051
Revises: b7c2f4a9d1e8
Create Date: 2026-07-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '33716d073051'
down_revision: Union[str, None] = 'b7c2f4a9d1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'bookings',
        sa.Column(
            'customization_note',
            sa.Text(),
            nullable=True,
            comment="Customer's free-form custom requirements typed in the plan-flow "
                    "Details step, distinct from special_instructions. Visible to both "
                    "the vendor and Tyohaar admin.",
        ),
    )


def downgrade() -> None:
    op.drop_column('bookings', 'customization_note')
