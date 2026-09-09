"""documents archive and metadata columns

Revision ID: a1b2c3d4e5f6
Revises: 4373dd888437
Create Date: 2026-09-09 00:00:00.000000

Drops Documents.visible_to (superseded entirely by CaseAssignments +
folder_type, per CLAUDE.md's Data model — it never had a defined purpose
once CaseAssignments existed) and adds the columns the Documents feature
actually needs: archived_at (two-stage trash), file_size (storage-quota
enforcement), original_filename + content_type (display, same-filename
detection, correct download headers), created_at (listing/sort order).

Written as a real incremental migration rather than the project's earlier
"drop the DB and regenerate from scratch" pattern — that pattern only ever
held because no real data existed yet; real demo/case data now does.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "4373dd888437"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("documents", "visible_to")
    op.add_column("documents", sa.Column("original_filename", sa.String(length=255), nullable=False, server_default=""))
    op.add_column("documents", sa.Column("content_type", sa.String(length=100), nullable=False, server_default=""))
    op.add_column("documents", sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0"))
    op.add_column("documents", sa.Column("archived_at", sa.DateTime(), nullable=True))
    op.add_column("documents", sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False))
    # Drop the server_defaults now that existing rows (if any) are backfilled
    # — new inserts always supply these explicitly via the ORM, so the
    # column shouldn't silently default to "" going forward.
    op.alter_column("documents", "original_filename", server_default=None)
    op.alter_column("documents", "content_type", server_default=None)
    op.alter_column("documents", "file_size", server_default=None)


def downgrade() -> None:
    op.drop_column("documents", "created_at")
    op.drop_column("documents", "archived_at")
    op.drop_column("documents", "file_size")
    op.drop_column("documents", "content_type")
    op.drop_column("documents", "original_filename")
    op.add_column("documents", sa.Column("visible_to", sa.String(length=255), nullable=True))
