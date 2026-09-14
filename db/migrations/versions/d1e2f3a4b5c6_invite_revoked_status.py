"""invite revoked status

Revision ID: d1e2f3a4b5c6
Revises: c9d0e1f2a3b4
Create Date: 2026-09-14 00:00:00.000000

Adds InviteStatus.REVOKED (CLAUDE.md's MembershipInvites note on
office_manager cancelling a pending invite before it's ever answered).
Kept distinct from DECLINED: declined means the invitee responded no,
revoked means the office_manager withdrew it before any response - two
different actors and two different facts worth telling apart in the
Members screen's history, not one status doing double duty.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "membership_invites",
        "status",
        existing_type=sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="invitestatus"),
        type_=sa.Enum("PENDING", "ACCEPTED", "DECLINED", "REVOKED", name="invitestatus"),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "membership_invites",
        "status",
        existing_type=sa.Enum("PENDING", "ACCEPTED", "DECLINED", "REVOKED", name="invitestatus"),
        type_=sa.Enum("PENDING", "ACCEPTED", "DECLINED", name="invitestatus"),
        existing_nullable=False,
    )
