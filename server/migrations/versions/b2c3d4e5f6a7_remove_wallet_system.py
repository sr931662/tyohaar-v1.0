"""remove wallet system

Removes the entire customer wallet (wallets, wallet_transactions,
user_rewards) and vendor payout wallet (vendor_wallets) tables, along
with every foreign key pointing into them from protected domains
(referrals, vendor settlements). Coupons, memberships, and referrals
themselves are untouched — only their wallet linkage is removed:

- referral_rewards.wallet_id / wallet_transaction_id: dropped outright
  (the crediting code path was already a dead stub, never populated).
- vendor_settlements.wallet_id: FK constraint dropped and column made
  nullable, but the column itself is kept (legacy data, no longer an
  FK) since VendorSettlement is not part of the wallet system removal.
- membership_plans.wallet_bonus: left untouched — kept as inert plan
  data per product decision; only the crediting code was removed.

Revision ID: b2c3d4e5f6a7
Revises: c4d5e6f7a8b9
Create Date: 2026-07-10
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Drop FKs pointing into wallet tables from protected domains ────────────
    op.drop_constraint(
        "fk_referral_rewards_wallet_id_wallets",
        "referral_rewards",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_referral_rewards_wallet_transaction_id_wallet_transactions",
        "referral_rewards",
        type_="foreignkey",
    )
    op.drop_column("referral_rewards", "wallet_id")
    op.drop_column("referral_rewards", "wallet_transaction_id")

    op.drop_constraint(
        "fk_vendor_settlements_wallet_id_vendor_wallets",
        "vendor_settlements",
        type_="foreignkey",
    )
    op.alter_column(
        "vendor_settlements",
        "wallet_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # ── Drop wallet tables (children first) ─────────────────────────────────────
    op.drop_table("user_rewards")
    op.drop_table("wallet_transactions")
    op.drop_table("wallets")
    op.drop_table("vendor_wallets")


def downgrade() -> None:
    raise NotImplementedError(
        "Wallet system removal is not reversible via downgrade — "
        "restore from a pre-migration backup if the wallet system must return."
    )
