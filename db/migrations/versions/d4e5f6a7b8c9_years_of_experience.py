"""identities years_of_experience

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-14 00:00:00.000000

Adds Identities.years_of_experience (CLAUDE.md's Data model) — self-
reported, same as bio; sort key for the public homepage's team section.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("identities", sa.Column("years_of_experience", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("identities", "years_of_experience")
