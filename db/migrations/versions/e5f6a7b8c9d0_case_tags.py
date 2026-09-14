"""case tags

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-14 00:00:00.000000

Adds CaseTags (CLAUDE.md's Data model) — many-to-many practice-area tagging
on a case, since a case can genuinely carry more than one tag.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PRACTICE_AREAS = (
    "TRAFFIC",
    "CRIMINAL",
    "FAMILY",
    "CIVIL",
    "LABOR",
    "REAL_ESTATE",
    "CORPORATE",
    "IMMIGRATION",
)


def upgrade() -> None:
    op.create_table(
        "case_tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("practice_area", sa.Enum(*PRACTICE_AREAS, name="practicearea"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "practice_area", name="uq_case_tags_case_practice_area"),
    )
    op.create_index("ix_case_tags_tenant_id", "case_tags", ["tenant_id"], unique=False)
    op.create_index("ix_case_tags_case_id", "case_tags", ["case_id"], unique=False)
    op.create_index("ix_case_tags_practice_area", "case_tags", ["practice_area"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_case_tags_practice_area", table_name="case_tags")
    op.drop_index("ix_case_tags_case_id", table_name="case_tags")
    op.drop_index("ix_case_tags_tenant_id", table_name="case_tags")
    op.drop_table("case_tags")
    sa.Enum(name="practicearea").drop(op.get_bind(), checkfirst=True)
