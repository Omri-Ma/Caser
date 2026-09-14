"""membership invites

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-14 00:00:00.000000

Adds MembershipInvites (CLAUDE.md's Data model) — an office manager
adding a lawyer/client to their firm becomes a real request instead of an
instant Membership row. Keyed by email, not identity_id: the invited
person may not have an Identity yet at all.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "membership_invites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("role", sa.Enum("SUPER_ADMIN", "OFFICE_MANAGER", "LAWYER", "CLIENT", name="userrole"), nullable=False),
        sa.Column("invited_by", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="invitestatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("responded_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["invited_by"], ["memberships.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_membership_invites_tenant_id", "membership_invites", ["tenant_id"], unique=False)
    op.create_index("ix_membership_invites_email", "membership_invites", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_membership_invites_email", table_name="membership_invites")
    op.drop_index("ix_membership_invites_tenant_id", table_name="membership_invites")
    op.drop_table("membership_invites")
