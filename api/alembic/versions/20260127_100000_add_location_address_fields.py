"""Add address fields to locations table

Adds address-related columns to the locations table for IT Glue migration:
- address_1, address_2: Street address lines
- city, region, postal_code, country: Standard address components
- phone: Contact phone number

Revision ID: 20260127_100000
Revises: 20260126_001000
Create Date: 2026-01-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260127_100000"
down_revision: str | None = "20260126_001000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# New address columns to add to locations table
ADDRESS_COLUMNS = [
    ("address_1", sa.String(255)),
    ("address_2", sa.String(255)),
    ("city", sa.String(100)),
    ("region", sa.String(100)),
    ("postal_code", sa.String(20)),
    ("country", sa.String(100)),
    ("phone", sa.String(50)),
]


def upgrade() -> None:
    for column_name, column_type in ADDRESS_COLUMNS:
        op.add_column(
            "locations",
            sa.Column(column_name, column_type, nullable=True),
        )


def downgrade() -> None:
    for column_name, _ in reversed(ADDRESS_COLUMNS):
        op.drop_column("locations", column_name)
