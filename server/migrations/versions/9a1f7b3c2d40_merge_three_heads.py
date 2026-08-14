"""merge three divergent heads

Revision ID: 9a1f7b3c2d40
Revises: 202607151128, a4b5c6d7e8f9, f79355e8d645
Create Date: 2026-08-14

The repository had accumulated three independent alembic heads, which makes
`alembic upgrade head` fail with "Multiple head revisions are present".
This is a no-op merge that reunites them so migrations can run again.

It changes no schema. It exists purely to give the graph a single head.

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '9a1f7b3c2d40'
down_revision: Union[str, Sequence[str], None] = (
    '202607151128',
    'a4b5c6d7e8f9',
    'f79355e8d645',
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No schema change — merge only."""


def downgrade() -> None:
    """No schema change — merge only."""
