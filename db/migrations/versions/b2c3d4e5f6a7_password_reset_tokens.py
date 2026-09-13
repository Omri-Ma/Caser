"""password reset tokens

Revision ID: b2c3d4e5f6a7
Revises: 35968b0ff2b2
Create Date: 2026-09-13 00:00:00.000000

Adds PasswordResetTokens (CLAUDE.md's Data model) — backs the real
self-service forgot-password flow, replacing the office_manager-driven
manual reset that's being removed in this same slice. Tenant-less on
purpose: a forgotten password is an Identities-level problem, not a
per-firm one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "35968b0ff2b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identity_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["identity_id"], ["identities.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_identity_id", "password_reset_tokens", ["identity_id"], unique=False)
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_identity_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
