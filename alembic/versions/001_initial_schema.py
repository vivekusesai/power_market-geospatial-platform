"""Initial schema with all tables

Revision ID: 001
Revises:
Create Date: 2024-01-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import geoalchemy2

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable PostGIS extension
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # Create fuel_type enum
    op.execute("""
        CREATE TYPE fueltype AS ENUM (
            'coal', 'natural_gas', 'nuclear', 'hydro', 'wind',
            'solar', 'oil', 'biomass', 'geothermal', 'battery', 'other'
        )
    """)

    # Create outage_type enum
    op.execute("""
        CREATE TYPE outagetype AS ENUM (
            'planned', 'forced', 'maintenance', 'derate'
        )
    """)

    # Create outage_status enum
    op.execute("""
        CREATE TYPE outagestatus AS ENUM (
            'active', 'scheduled', 'completed', 'cancelled'
        )
    """)

    # Create zone_type enum
    op.execute("""
        CREATE TYPE zonetype AS ENUM (
            'iso_boundary', 'load_zone', 'transmission_zone',
            'settlement_zone', 'pricing_zone', 'reserve_zone'
        )
    """)

    # Create assets table
    op.create_table(
        "assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("asset_id", sa.String(50), nullable=False),
        sa.Column("asset_name", sa.String(255), nullable=False),
        sa.Column("fuel_type", sa.Enum("coal", "natural_gas", "nuclear", "hydro", "wind", "solar", "oil", "biomass", "geothermal", "battery", "other", name="fueltype"), nullable=False),
        sa.Column("capacity_mw", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("iso_region", sa.String(20), nullable=False),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_assets_asset_id", "assets", ["asset_id"], unique=True)
    op.create_index("idx_assets_fuel_type", "assets", ["fuel_type"])
    op.create_index("idx_assets_iso_region", "assets", ["iso_region"])
    op.create_index("idx_assets_zone", "assets", ["zone"])
    op.create_index("idx_assets_iso_zone", "assets", ["iso_region", "zone"])
    op.create_index("idx_assets_geom", "assets", ["geom"], postgresql_using="gist")

    # Create outages table
    op.create_table(
        "outages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("outage_id", sa.String(50), nullable=False),
        sa.Column("asset_id", sa.String(50), nullable=False),
        sa.Column("outage_type", sa.Enum("planned", "forced", "maintenance", "derate", name="outagetype"), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("active", "scheduled", "completed", "cancelled", name="outagestatus"), nullable=False),
        sa.Column("cause_code", sa.String(50), nullable=True),
        sa.Column("cause_description", sa.Text(), nullable=True),
        sa.Column("capacity_reduction_mw", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.asset_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_outages_outage_id", "outages", ["outage_id"], unique=True)
    op.create_index("idx_outages_asset_id", "outages", ["asset_id"])
    op.create_index("idx_outages_outage_type", "outages", ["outage_type"])
    op.create_index("idx_outages_status", "outages", ["status"])
    op.create_index("idx_outages_time_range", "outages", ["start_time", "end_time"])
    op.create_index("idx_outages_asset_time", "outages", ["asset_id", "start_time"])
    op.create_index("idx_outages_status_time", "outages", ["status", "start_time"])

    # Create pricing_nodes table
    op.create_table(
        "pricing_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(50), nullable=False),
        sa.Column("node_name", sa.String(255), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("iso_region", sa.String(20), nullable=False),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="POINT", srid=4326), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pricing_nodes_node_id", "pricing_nodes", ["node_id"], unique=True)
    op.create_index("idx_pricing_nodes_iso_region", "pricing_nodes", ["iso_region"])
    op.create_index("idx_pricing_nodes_zone", "pricing_nodes", ["zone"])
    op.create_index("idx_pricing_nodes_geom", "pricing_nodes", ["geom"], postgresql_using="gist")

    # Create pricing_records table
    op.create_table(
        "pricing_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("node_id", sa.String(50), nullable=True),
        sa.Column("asset_id", sa.String(50), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lmp_total", sa.Float(), nullable=False),
        sa.Column("lmp_energy", sa.Float(), nullable=True),
        sa.Column("lmp_congestion", sa.Float(), nullable=True),
        sa.Column("lmp_loss", sa.Float(), nullable=True),
        sa.Column("iso_region", sa.String(20), nullable=False),
        sa.Column("market_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["node_id"], ["pricing_nodes.node_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.asset_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_pricing_node_time", "pricing_records", ["node_id", "timestamp"])
    op.create_index("idx_pricing_asset_time", "pricing_records", ["asset_id", "timestamp"])
    op.create_index("idx_pricing_timestamp", "pricing_records", ["timestamp"])
    op.create_index("idx_pricing_iso_region", "pricing_records", ["iso_region"])
    op.execute("CREATE INDEX idx_pricing_timestamp_brin ON pricing_records USING BRIN (timestamp)")

    # Create zones table
    op.create_table(
        "zones",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("zone_id", sa.String(50), nullable=False),
        sa.Column("zone_name", sa.String(255), nullable=False),
        sa.Column("zone_type", sa.Enum("iso_boundary", "load_zone", "transmission_zone", "settlement_zone", "pricing_zone", "reserve_zone", name="zonetype"), nullable=False),
        sa.Column("iso_region", sa.String(20), nullable=False),
        sa.Column("parent_zone_id", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("geom", geoalchemy2.types.Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("fill_color", sa.String(20), nullable=True),
        sa.Column("stroke_color", sa.String(20), nullable=True),
        sa.Column("fill_opacity", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_zones_zone_id", "zones", ["zone_id"], unique=True)
    op.create_index("idx_zones_zone_type", "zones", ["zone_type"])
    op.create_index("idx_zones_iso_region", "zones", ["iso_region"])
    op.create_index("idx_zones_iso_type", "zones", ["iso_region", "zone_type"])
    op.create_index("idx_zones_geom", "zones", ["geom"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_table("zones")
    op.drop_table("pricing_records")
    op.drop_table("pricing_nodes")
    op.drop_table("outages")
    op.drop_table("assets")

    op.execute("DROP TYPE IF EXISTS zonetype")
    op.execute("DROP TYPE IF EXISTS outagestatus")
    op.execute("DROP TYPE IF EXISTS outagetype")
    op.execute("DROP TYPE IF EXISTS fueltype")
