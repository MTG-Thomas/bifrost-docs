"""Add user_favorites table for personal bookmarks

Revision ID: 040
Revises: 039
Create Date: 2026-04-06 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "040"
down_revision: str | None = "039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create user_favorites table for quick access bookmarks
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column(
            "entity_type",
            sa.String(length=50),
            nullable=False,
            comment="Entity type: password, configuration, document, location, custom_asset",
        ),
        sa.Column("entity_id", sa.UUID(), nullable=False),
        sa.Column(
            "display_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
            comment="Sort order for display",
        ),
        sa.Column(
            "custom_label",
            sa.String(length=255),
            nullable=True,
            comment="Optional custom display label",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_favorites_user_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_user_favorites_organization_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "organization_id",
            "entity_type",
            "entity_id",
            name="uq_user_favorites_user_org_entity",
        ),
    )

    # Create index for faster lookups by user_id
    op.create_index(
        "ix_user_favorites_user_id",
        "user_favorites",
        ["user_id"],
    )

    # Create index for lookups by user + org
    op.create_index(
        "ix_user_favorites_user_org",
        "user_favorites",
        ["user_id", "organization_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_favorites_user_org", table_name="user_favorites")
    op.drop_index("ix_user_favorites_user_id", table_name="user_favorites")
    op.drop_table("user_favorites")
