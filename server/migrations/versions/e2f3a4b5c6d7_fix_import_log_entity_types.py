"""fix cms_import_logs entity_type check constraint + add new entity types

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-07-31 00:00:00.000000

The original constraint used 'services'/'categories' — stale names that
never matched what io_service.py actually inserts ('vendor_services',
'package_categories'), so importing either of those entity types has been
failing at the DB layer since the constraint was created. Fixes that and
adds the new entity types being registered in this same change: themes,
package_items, common_items, package_services, common_services.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e2f3a4b5c6d7'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_CONSTRAINT = (
    "entity_type IN ('vendors','customers','packages','services','categories',"
    "'cities','states','memberships','coupons','faqs','notification_templates','settings')"
)

_NEW_CONSTRAINT = (
    "entity_type IN ('vendors','customers','packages','package_categories','cities','states',"
    "'memberships','coupons','faqs','notification_templates','settings','vendor_services',"
    "'themes','package_items','common_items','package_services','common_services')"
)


def upgrade() -> None:
    op.drop_constraint('ck_import_logs_entity_type', 'cms_import_logs', type_='check')
    op.create_check_constraint('ck_import_logs_entity_type', 'cms_import_logs', _NEW_CONSTRAINT)


def downgrade() -> None:
    op.drop_constraint('ck_import_logs_entity_type', 'cms_import_logs', type_='check')
    op.create_check_constraint('ck_import_logs_entity_type', 'cms_import_logs', _OLD_CONSTRAINT)
