-- Power Market Geospatial Platform - Database Schema
-- Run with: psql -U postgres -d power_market -f scripts/init_db.sql

-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create enum types
DO $$ BEGIN
    CREATE TYPE fueltype AS ENUM (
        'coal', 'natural_gas', 'nuclear', 'hydro', 'wind',
        'solar', 'oil', 'biomass', 'geothermal', 'battery', 'other'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE outagetype AS ENUM (
        'planned', 'forced', 'maintenance', 'derate'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE outagestatus AS ENUM (
        'active', 'scheduled', 'completed', 'cancelled'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
    CREATE TYPE zonetype AS ENUM (
        'iso_boundary', 'load_zone', 'transmission_zone',
        'settlement_zone', 'pricing_zone', 'reserve_zone'
    );
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- Create assets table
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(50) NOT NULL,
    asset_name VARCHAR(255) NOT NULL,
    fuel_type fueltype NOT NULL,
    capacity_mw FLOAT NOT NULL,
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    iso_region VARCHAR(20) NOT NULL,
    zone VARCHAR(50),
    owner VARCHAR(255),
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_assets_asset_id ON assets(asset_id);
CREATE INDEX IF NOT EXISTS idx_assets_fuel_type ON assets(fuel_type);
CREATE INDEX IF NOT EXISTS idx_assets_iso_region ON assets(iso_region);
CREATE INDEX IF NOT EXISTS idx_assets_zone ON assets(zone);
CREATE INDEX IF NOT EXISTS idx_assets_iso_zone ON assets(iso_region, zone);
CREATE INDEX IF NOT EXISTS idx_assets_geom ON assets USING GIST(geom);

-- Create outages table
CREATE TABLE IF NOT EXISTS outages (
    id SERIAL PRIMARY KEY,
    outage_id VARCHAR(50) NOT NULL,
    asset_id VARCHAR(50) NOT NULL REFERENCES assets(asset_id) ON DELETE CASCADE,
    outage_type outagetype NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    status outagestatus NOT NULL,
    cause_code VARCHAR(50),
    cause_description TEXT,
    capacity_reduction_mw FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_outages_outage_id ON outages(outage_id);
CREATE INDEX IF NOT EXISTS idx_outages_asset_id ON outages(asset_id);
CREATE INDEX IF NOT EXISTS idx_outages_outage_type ON outages(outage_type);
CREATE INDEX IF NOT EXISTS idx_outages_status ON outages(status);
CREATE INDEX IF NOT EXISTS idx_outages_time_range ON outages(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_outages_asset_time ON outages(asset_id, start_time);
CREATE INDEX IF NOT EXISTS idx_outages_status_time ON outages(status, start_time);

-- Create pricing_nodes table
CREATE TABLE IF NOT EXISTS pricing_nodes (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(50) NOT NULL,
    node_name VARCHAR(255) NOT NULL,
    node_type VARCHAR(50) NOT NULL,
    iso_region VARCHAR(20) NOT NULL,
    zone VARCHAR(50),
    latitude FLOAT,
    longitude FLOAT,
    geom GEOMETRY(POINT, 4326),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_pricing_nodes_node_id ON pricing_nodes(node_id);
CREATE INDEX IF NOT EXISTS idx_pricing_nodes_iso_region ON pricing_nodes(iso_region);
CREATE INDEX IF NOT EXISTS idx_pricing_nodes_zone ON pricing_nodes(zone);
CREATE INDEX IF NOT EXISTS idx_pricing_nodes_geom ON pricing_nodes USING GIST(geom);

-- Create pricing_records table
CREATE TABLE IF NOT EXISTS pricing_records (
    id SERIAL PRIMARY KEY,
    node_id VARCHAR(50) REFERENCES pricing_nodes(node_id) ON DELETE CASCADE,
    asset_id VARCHAR(50) REFERENCES assets(asset_id) ON DELETE CASCADE,
    timestamp TIMESTAMPTZ NOT NULL,
    lmp_total FLOAT NOT NULL,
    lmp_energy FLOAT,
    lmp_congestion FLOAT,
    lmp_loss FLOAT,
    iso_region VARCHAR(20) NOT NULL,
    market_type VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pricing_node_time ON pricing_records(node_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_pricing_asset_time ON pricing_records(asset_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_pricing_timestamp ON pricing_records(timestamp);
CREATE INDEX IF NOT EXISTS idx_pricing_iso_region ON pricing_records(iso_region);
CREATE INDEX IF NOT EXISTS idx_pricing_timestamp_brin ON pricing_records USING BRIN(timestamp);

-- Create zones table
CREATE TABLE IF NOT EXISTS zones (
    id SERIAL PRIMARY KEY,
    zone_id VARCHAR(50) NOT NULL,
    zone_name VARCHAR(255) NOT NULL,
    zone_type zonetype NOT NULL,
    iso_region VARCHAR(20) NOT NULL,
    parent_zone_id VARCHAR(50),
    description TEXT,
    geom GEOMETRY(MULTIPOLYGON, 4326),
    fill_color VARCHAR(20),
    stroke_color VARCHAR(20),
    fill_opacity FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_zones_zone_id ON zones(zone_id);
CREATE INDEX IF NOT EXISTS idx_zones_zone_type ON zones(zone_type);
CREATE INDEX IF NOT EXISTS idx_zones_iso_region ON zones(iso_region);
CREATE INDEX IF NOT EXISTS idx_zones_iso_type ON zones(iso_region, zone_type);
CREATE INDEX IF NOT EXISTS idx_zones_geom ON zones USING GIST(geom);

-- Mark alembic migration as complete (so alembic doesn't try to run it again)
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);
INSERT INTO alembic_version (version_num) VALUES ('001') ON CONFLICT DO NOTHING;

SELECT 'Database schema created successfully!' AS status;
