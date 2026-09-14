"""membership is_manager

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-09-14 00:00:00.000000

Adds Memberships.is_manager (CLAUDE.md's Memberships note) — an
office_manager-set, lawyer-only flag granting full case visibility plus
narrative-generation authority, orthogonal to `role`: a lawyer with this
flag gets the same case-oversight privileges office_manager has, without
becoming a firm administrator. Added NOT NULL with a server default of
false directly (unlike hourly_rate, which is meaningfully nullable —
"no rate set yet" is a real state; a lawyer either has manager-level
oversight or doesn't, there's no meaningful "unset" third state here),
so every existing row (lawyer or otherwise) defaults to no manager
authority rather than needing a backfill pass.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "memberships",
        sa.Column("is_manager", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("memberships", "is_manager", server_default=None)


def downgrade() -> None:
    op.drop_column("memberships", "is_manager")
