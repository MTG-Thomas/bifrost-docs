"""add_unique_organization_name

Prevents duplicate organization names at the database level.
The existing ix_organizations_name index is replaced with a unique index.

Revision ID: 20260128_100000
Revises: 20260127_110000
Create Date: 2026-01-28

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260128_100000"
down_revision: str | None = "20260127_110000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the existing non-unique index
    op.drop_index("ix_organizations_name", table_name="organizations")

    # Create unique index to prevent duplicate organization names
    op.create_index(
        "ix_organizations_name",
        "organizations",
        ["name"],
        unique=True,
    )


def downgrade() -> None:
    # Drop unique index
    op.drop_index("ix_organizations_name", table_name="organizations")

    # Recreate non-unique index
    op.create_index(
        "ix_organizations_name",
        "organizations",
        ["name"],
        unique=False,
    )
