"""add_dcim_tables

Adds full DCIM (Data Center Infrastructure Management) tables:
- racks
- rack_devices  
- circuits
- powered_devices
- cables
- patch_panels
- patch_panel_ports

Revision ID: 20260406_120000
Revises: 20260128_100000
Create Date: 2026-04-06

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "20260406_120000"
down_revision: str | None = "20260128_100000"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create racks table
    op.create_table(
        "racks",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("organization_id", UUID(), nullable=False),
        sa.Column("location_id", UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rack_units", sa.Integer(), nullable=False, server_default="42"),
        sa.Column("width_mm", sa.Integer(), nullable=True),
        sa.Column("depth_mm", sa.Integer(), nullable=True),
        sa.Column("row", sa.String(50), nullable=True),
        sa.Column("position", sa.String(50), nullable=True),
        sa.Column("power_circuits", sa.Text(), nullable=True),  # JSON array
        sa.Column("power_capacity_va", sa.Integer(), nullable=True),
        sa.Column("power_in_use_va", sa.Integer(), server_default="0"),
        sa.Column("weight_capacity_kg", sa.Integer(), nullable=True),
        sa.Column("weight_in_use_kg", sa.Integer(), server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_racks_organization_id", "racks", ["organization_id"])
    op.create_index("ix_racks_location_id", "racks", ["location_id"])

    # Create rack_devices table
    op.create_table(
        "rack_devices",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("rack_id", UUID(), nullable=False),
        sa.Column("configuration_id", UUID(), nullable=False),
        sa.Column("u_position", sa.Integer(), nullable=False),
        sa.Column("u_height", sa.Integer(), server_default="1"),
        sa.Column("mounted_rear", sa.Boolean(), server_default="false"),
        sa.Column("power_circuit_a", sa.String(50), nullable=True),
        sa.Column("power_circuit_b", sa.String(50), nullable=True),
        sa.Column("power_draw_va", sa.Integer(), nullable=True),
        sa.Column("cable_arm_side", sa.String(10), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["rack_id"],
            ["racks.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_id"],
            ["configurations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rack_id", "u_position", name="uq_rack_position"),
        sa.UniqueConstraint("configuration_id", name="uq_config_rack"),
    )
    op.create_index("ix_rack_devices_rack_id", "rack_devices", ["rack_id"])
    op.create_index("ix_rack_devices_config_id", "rack_devices", ["configuration_id"])

    # Create circuits table
    op.create_table(
        "circuits",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("organization_id", UUID(), nullable=False),
        sa.Column("location_id", UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("circuit_type", sa.String(50), server_default="power"),
        sa.Column("phase", sa.String(10), nullable=True),
        sa.Column("voltage_v", sa.Integer(), server_default="120"),
        sa.Column("amperage_a", sa.Integer(), server_default="20"),
        sa.Column("power_in_use_va", sa.Integer(), server_default="0"),
        sa.Column("is_active", sa.Boolean(), server_default="true"),
        sa.Column("is_redundant", sa.Boolean(), server_default="false"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_circuits_organization_id", "circuits", ["organization_id"])
    op.create_index("ix_circuits_location_id", "circuits", ["location_id"])

    # Create powered_devices table
    op.create_table(
        "powered_devices",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("circuit_id", UUID(), nullable=False),
        sa.Column("configuration_id", UUID(), nullable=False),
        sa.Column("psu_number", sa.Integer(), server_default="1"),
        sa.Column("power_draw_va", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["circuit_id"],
            ["circuits.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["configuration_id"],
            ["configurations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("configuration_id", "psu_number", name="uq_device_psu"),
    )
    op.create_index("ix_powered_devices_circuit_id", "powered_devices", ["circuit_id"])
    op.create_index("ix_powered_devices_config_id", "powered_devices", ["configuration_id"])

    # Create cables table
    op.create_table(
        "cables",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("organization_id", UUID(), nullable=False),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("cable_type", sa.String(50), nullable=False),
        sa.Column("length_m", sa.Float(), nullable=True),
        sa.Column("color", sa.String(50), nullable=True),
        sa.Column("end_a_config_id", UUID(), nullable=True),
        sa.Column("end_a_port", sa.String(100), nullable=True),
        sa.Column("end_a_location", sa.String(255), nullable=True),
        sa.Column("end_b_config_id", UUID(), nullable=True),
        sa.Column("end_b_port", sa.String(100), nullable=True),
        sa.Column("end_b_location", sa.String(255), nullable=True),
        sa.Column("strand_id", sa.String(50), nullable=True),
        sa.Column("is_connected", sa.Boolean(), server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["end_a_config_id"],
            ["configurations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["end_b_config_id"],
            ["configurations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cables_organization_id", "cables", ["organization_id"])
    op.create_index("ix_cables_end_a_config_id", "cables", ["end_a_config_id"])
    op.create_index("ix_cables_end_b_config_id", "cables", ["end_b_config_id"])

    # Create patch_panels table
    op.create_table(
        "patch_panels",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("organization_id", UUID(), nullable=False),
        sa.Column("location_id", UUID(), nullable=True),
        sa.Column("rack_id", UUID(), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("panel_type", sa.String(50), server_default="cat6"),
        sa.Column("port_count", sa.Integer(), server_default="24"),
        sa.Column("u_position", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["locations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["rack_id"],
            ["racks.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patch_panels_organization_id", "patch_panels", ["organization_id"])
    op.create_index("ix_patch_panels_location_id", "patch_panels", ["location_id"])
    op.create_index("ix_patch_panels_rack_id", "patch_panels", ["rack_id"])

    # Create patch_panel_ports table
    op.create_table(
        "patch_panel_ports",
        sa.Column("id", UUID(), nullable=False),
        sa.Column("panel_id", UUID(), nullable=False),
        sa.Column("port_number", sa.Integer(), nullable=False),
        sa.Column("port_type", sa.String(50), server_default="rj45"),
        sa.Column("front_cable_id", UUID(), nullable=True),
        sa.Column("rear_cable_id", UUID(), nullable=True),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("vlan_id", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["panel_id"],
            ["patch_panels.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["front_cable_id"],
            ["cables.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["rear_cable_id"],
            ["cables.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("panel_id", "port_number", name="uq_panel_port"),
    )
    op.create_index("ix_patch_panel_ports_panel_id", "patch_panel_ports", ["panel_id"])
    op.create_index("ix_patch_panel_ports_front_cable", "patch_panel_ports", ["front_cable_id"])
    op.create_index("ix_patch_panel_ports_rear_cable", "patch_panel_ports", ["rear_cable_id"])


def downgrade() -> None:
    # Drop in reverse order
    op.drop_table("patch_panel_ports")
    op.drop_table("patch_panels")
    op.drop_table("cables")
    op.drop_table("powered_devices")
    op.drop_table("circuits")
    op.drop_table("rack_devices")
    op.drop_table("racks")
