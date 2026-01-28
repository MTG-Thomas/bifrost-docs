"""Add cascade delete to passwords organization FK

Updates the passwords table foreign key to cascade delete when
the parent organization is deleted.

Revision ID: 20260127_110000
Revises: 20260127_100000
Create Date: 2026-01-27

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260127_110000"
down_revision: str | None = "20260127_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint(
        "passwords_organization_id_fkey",
        "passwords",
        type_="foreignkey",
    )
    # Recreate with CASCADE delete
    op.create_foreign_key(
        "passwords_organization_id_fkey",
        "passwords",
        "organizations",
        ["organization_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop the CASCADE foreign key
    op.drop_constraint(
        "passwords_organization_id_fkey",
        "passwords",
        type_="foreignkey",
    )
    # Recreate without CASCADE
    op.create_foreign_key(
        "passwords_organization_id_fkey",
        "passwords",
        "organizations",
        ["organization_id"],
        ["id"],
    )
