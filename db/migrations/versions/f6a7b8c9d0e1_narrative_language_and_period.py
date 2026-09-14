"""narrative language and period

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-14 00:00:00.000000

Adds Narratives.language/period_start/period_end (CLAUDE.md's Data model) —
chosen by the lawyer at generation time, stored per row for the same
fixed-snapshot reason as total_hours/total_fee. Columns are added nullable
first and backfilled (existing rows get language=HE and a period spanning
up to their created_at, the closest honest approximation for data generated
before this feature existed) before being made NOT NULL, since the table
may already hold rows.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "narratives",
        sa.Column("language", sa.Enum("HE", "EN", name="narrativelanguage"), nullable=True),
    )
    op.add_column("narratives", sa.Column("period_start", sa.Date(), nullable=True))
    op.add_column("narratives", sa.Column("period_end", sa.Date(), nullable=True))

    op.execute("UPDATE narratives SET language = 'HE' WHERE language IS NULL")
    op.execute("UPDATE narratives SET period_start = DATE(created_at) WHERE period_start IS NULL")
    op.execute("UPDATE narratives SET period_end = DATE(created_at) WHERE period_end IS NULL")

    op.alter_column(
        "narratives", "language", existing_type=sa.Enum("HE", "EN", name="narrativelanguage"), nullable=False
    )
    op.alter_column("narratives", "period_start", existing_type=sa.Date(), nullable=False)
    op.alter_column("narratives", "period_end", existing_type=sa.Date(), nullable=False)


def downgrade() -> None:
    op.drop_column("narratives", "period_end")
    op.drop_column("narratives", "period_start")
    op.drop_column("narratives", "language")
    sa.Enum(name="narrativelanguage").drop(op.get_bind(), checkfirst=True)
