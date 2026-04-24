"""Add sync metadata to configurations and custom assets

Revision ID: 20260424_100000
Revises: 20260406_140000
Create Date: 2026-04-24 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_100000"
down_revision: str | None = "20260406_140000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "configurations",
        sa.Column("sync_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "custom_assets",
        sa.Column("sync_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("custom_assets", "sync_metadata")
    op.drop_column("configurations", "sync_metadata")
