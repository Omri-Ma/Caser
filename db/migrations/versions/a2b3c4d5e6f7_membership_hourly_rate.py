"""membership hourly_rate

Revision ID: a2b3c4d5e6f7
Revises: d1e2f3a4b5c6
Create Date: 2026-09-14 00:00:00.000000

Adds Memberships.hourly_rate (CLAUDE.md's Memberships note) — the
office_manager-set, per-membership billing rate that now feeds
Narratives.total_fee, replacing the old flat platform-wide placeholder
rate. Nullable from the start (not backfilled): a brand-new lawyer
membership simply has no rate set yet until the office manager sets one,
same as an existing lawyer membership predating this column.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("memberships", sa.Column("hourly_rate", sa.Numeric(8, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("memberships", "hourly_rate")
