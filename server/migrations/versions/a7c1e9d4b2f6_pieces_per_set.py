"""set size for lines sold in sets

A line like "200 / sets / 999" meant one set of 200 balloons for 999, but
quantity is the billed count, so it was charged 200 x 999. The set size now has
its own column and quantity counts sets.

Revision ID: a7c1e9d4b2f6
Revises: e1a2b3c4d5f6
Create Date: 2026-11-26
"""

from alembic import op
import sqlalchemy as sa


revision = "a7c1e9d4b2f6"
down_revision = "e1a2b3c4d5f6"
branch_labels = None
depends_on = None


_PACKAGE_TABLES = ("package_items", "package_services")
_TABLES = _PACKAGE_TABLES + ("booking_items", "booking_service_items")


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("pieces_per_set", sa.Integer(), nullable=True))

    # Until now the only place to write a set's size was quantity. Move it
    # across, leaving one set at the same price. A max_quantity was counted in
    # the same pieces, so it becomes the whole number of sets it covers.
    # Booking rows are records of what was ordered and are left as they are.
    for table in _PACKAGE_TABLES:
        op.execute(
            f"""
            UPDATE {table}
               SET pieces_per_set = quantity,
                   max_quantity = CASE
                       WHEN max_quantity IS NULL THEN NULL
                       ELSE GREATEST(1, max_quantity / quantity)
                   END,
                   quantity = 1
             WHERE lower(trim(unit)) IN ('set', 'sets')
               AND quantity > 1
            """
        )


def downgrade() -> None:
    for table in _PACKAGE_TABLES:
        op.execute(
            f"""
            UPDATE {table}
               SET max_quantity = max_quantity * pieces_per_set,
                   quantity = quantity * pieces_per_set
             WHERE pieces_per_set IS NOT NULL
            """
        )
    for table in _TABLES:
        op.drop_column(table, "pieces_per_set")
