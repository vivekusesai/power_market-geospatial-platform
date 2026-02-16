"""
Generate sample seed data for the power market geospatial platform.

This script creates realistic sample data including:
- Generator assets across multiple ISOs
- Outages (planned, forced, maintenance)
- Pricing nodes and LMP records
- Zone boundaries

Run: python scripts/seed_data.py
"""
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path

from geoalchemy2.functions import ST_SetSRID, ST_MakePoint
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.config import get_settings
from backend.models.asset import Asset, FuelType
from backend.models.outage import Outage, OutageStatus, OutageType
from backend.models.pricing import PricingNode, PricingRecord
from backend.models.zone import Zone, ZoneType

settings = get_settings()

# ISO region definitions with approximate boundaries
ISO_REGIONS = {
    "PJM": {
        "center": (40.0, -77.0),
        "bounds": {"min_lat": 36.5, "max_lat": 42.5, "min_lon": -82.0, "max_lon": -74.0},
        "color": "#1f77b4",
        "zones": ["AEP", "APS", "ATSI", "BGE", "COMED", "DAY", "DEOK", "DOM", "DPL", "DUQ", "EKPC", "JC", "METED", "PECO", "PENELEC", "PPL", "PSEG", "RECO"],
    },
    "MISO": {
        "center": (42.0, -90.0),
        "bounds": {"min_lat": 30.0, "max_lat": 48.0, "min_lon": -98.0, "max_lon": -82.0},
        "color": "#ff7f0e",
        "zones": ["AMIL", "AMMO", "CLEC", "CONS", "DECO", "EES", "EMBA", "GRE", "IPL", "LGEE", "MEC", "MHEB", "NIPS", "NSP", "OTP", "SMP", "UPPC", "WEC", "WPS"],
    },
    "SPP": {
        "center": (36.0, -98.0),
        "bounds": {"min_lat": 30.0, "max_lat": 42.0, "min_lon": -104.0, "max_lon": -92.0},
        "color": "#2ca02c",
        "zones": ["AEPW", "GRDA", "KCPL", "LES", "MIDW", "NPPD", "OKGE", "OPPD", "SPS", "SUNC", "WFEC"],
    },
    "ERCOT": {
        "center": (31.0, -99.0),
        "bounds": {"min_lat": 26.0, "max_lat": 36.5, "min_lon": -106.5, "max_lon": -93.5},
        "color": "#d62728",
        "zones": ["COAST", "EAST", "FWEST", "NORTH", "NCENT", "SCENT", "SOUTH", "WEST"],
    },
    "NYISO": {
        "center": (43.0, -75.5),
        "bounds": {"min_lat": 40.5, "max_lat": 45.0, "min_lon": -79.8, "max_lon": -71.8},
        "color": "#9467bd",
        "zones": ["CAPITL", "CENTRL", "DUNWOD", "GENESE", "HUD VL", "LONGIL", "MHK VL", "MILLWD", "N.Y.C.", "NORTH", "WEST"],
    },
    "ISONE": {
        "center": (42.5, -71.5),
        "bounds": {"min_lat": 41.0, "max_lat": 47.5, "min_lon": -73.5, "max_lon": -66.9},
        "color": "#8c564b",
        "zones": ["CT", "ME", "NEMASSBOST", "NH", "RI", "SEMASS", "VT", "WCMASS"],
    },
}

FUEL_TYPES = [
    (FuelType.NATURAL_GAS, 0.40, 500),  # (type, probability, avg_capacity)
    (FuelType.COAL, 0.15, 600),
    (FuelType.NUCLEAR, 0.08, 1000),
    (FuelType.WIND, 0.15, 150),
    (FuelType.SOLAR, 0.12, 100),
    (FuelType.HYDRO, 0.05, 200),
    (FuelType.OIL, 0.02, 100),
    (FuelType.BATTERY, 0.02, 50),
    (FuelType.OTHER, 0.01, 100),
]

OUTAGE_CAUSE_CODES = [
    "BOILER", "TURBINE", "GENERATOR", "TRANSFORMER", "COOLING",
    "FUEL", "ENVIRONMENTAL", "GRID", "WEATHER", "PLANNED",
]

PLANT_NAME_PREFIXES = [
    "North", "South", "East", "West", "Central", "River", "Lake", "Valley",
    "Mountain", "Prairie", "Coastal", "Desert", "Forest", "Metro",
]

PLANT_NAME_SUFFIXES = [
    "Energy Center", "Power Station", "Generating Station", "Plant",
    "Generation Facility", "Power Plant", "Energy Facility",
]

OWNER_NAMES = [
    "NextEra Energy", "Duke Energy", "Southern Company", "Dominion Energy",
    "Exelon Corporation", "American Electric Power", "Xcel Energy",
    "WEC Energy Group", "Entergy Corporation", "FirstEnergy",
    "Vistra Corp", "NRG Energy", "Public Service Enterprise",
    "Edison International", "Ameren Corporation", "Evergy",
]


def random_point_in_bounds(bounds):
    """Generate a random point within geographic bounds."""
    lat = random.uniform(bounds["min_lat"], bounds["max_lat"])
    lon = random.uniform(bounds["min_lon"], bounds["max_lon"])
    return lat, lon


def generate_plant_name():
    """Generate a realistic power plant name."""
    prefix = random.choice(PLANT_NAME_PREFIXES)
    suffix = random.choice(PLANT_NAME_SUFFIXES)
    number = random.choice(["", " I", " II", " III", " 1", " 2", " 3", ""])
    return f"{prefix} {suffix}{number}"


def select_fuel_type():
    """Select a fuel type based on probability distribution."""
    r = random.random()
    cumulative = 0
    for fuel, prob, _ in FUEL_TYPES:
        cumulative += prob
        if r <= cumulative:
            return fuel
    return FuelType.OTHER


def get_capacity_for_fuel(fuel_type):
    """Get a realistic capacity for the fuel type."""
    for fuel, _, avg_cap in FUEL_TYPES:
        if fuel == fuel_type:
            # Random capacity around the average
            return max(10, random.gauss(avg_cap, avg_cap * 0.5))
    return 100


def create_polygon_wkt(bounds):
    """Create a WKT MultiPolygon for the given bounds."""
    min_lon, max_lon = bounds["min_lon"], bounds["max_lon"]
    min_lat, max_lat = bounds["min_lat"], bounds["max_lat"]
    return f"SRID=4326;MULTIPOLYGON((({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat})))"


def generate_assets(session, num_per_iso=200):
    """Generate sample generator assets."""
    print(f"Generating {num_per_iso} assets per ISO...")
    assets = []
    asset_id_counter = 1

    for iso, config in ISO_REGIONS.items():
        for i in range(num_per_iso):
            fuel_type = select_fuel_type()
            lat, lon = random_point_in_bounds(config["bounds"])
            zone = random.choice(config["zones"])
            capacity = get_capacity_for_fuel(fuel_type)

            asset = Asset(
                asset_id=f"{iso}_{asset_id_counter:05d}",
                asset_name=generate_plant_name(),
                fuel_type=fuel_type,
                capacity_mw=round(capacity, 1),
                latitude=lat,
                longitude=lon,
                iso_region=iso,
                zone=zone,
                owner=random.choice(OWNER_NAMES),
                geom=f"SRID=4326;POINT({lon} {lat})",
            )
            assets.append(asset)
            asset_id_counter += 1

    session.add_all(assets)
    session.commit()
    print(f"Created {len(assets)} assets")
    return assets


def generate_outages(session, assets, num_active=50, num_history=200):
    """Generate sample outages."""
    print(f"Generating {num_active} active and {num_history} historical outages...")
    outages = []
    outage_id_counter = 1
    now = datetime.utcnow()

    # Select random assets for outages
    outage_assets = random.sample(assets, min(num_active + num_history, len(assets)))

    for i, asset in enumerate(outage_assets[:num_active]):
        # Active outages
        outage_type = random.choice(list(OutageType))
        start_offset = random.randint(0, 72)  # Started 0-72 hours ago
        duration = random.randint(24, 168)  # 1-7 days

        outage = Outage(
            outage_id=f"OUT_{outage_id_counter:06d}",
            asset_id=asset.asset_id,
            outage_type=outage_type,
            start_time=now - timedelta(hours=start_offset),
            end_time=now + timedelta(hours=duration - start_offset) if outage_type == OutageType.PLANNED else None,
            status=OutageStatus.ACTIVE,
            cause_code=random.choice(OUTAGE_CAUSE_CODES),
            capacity_reduction_mw=asset.capacity_mw if outage_type != OutageType.DERATE else asset.capacity_mw * random.uniform(0.2, 0.5),
        )
        outages.append(outage)
        outage_id_counter += 1

    for asset in outage_assets[num_active:num_active + num_history]:
        # Historical outages
        outage_type = random.choice(list(OutageType))
        days_ago = random.randint(1, 90)
        duration = random.randint(6, 72)

        outage = Outage(
            outage_id=f"OUT_{outage_id_counter:06d}",
            asset_id=asset.asset_id,
            outage_type=outage_type,
            start_time=now - timedelta(days=days_ago, hours=random.randint(0, 23)),
            end_time=now - timedelta(days=days_ago) + timedelta(hours=duration),
            status=OutageStatus.COMPLETED,
            cause_code=random.choice(OUTAGE_CAUSE_CODES),
            capacity_reduction_mw=asset.capacity_mw if outage_type != OutageType.DERATE else asset.capacity_mw * random.uniform(0.2, 0.5),
        )
        outages.append(outage)
        outage_id_counter += 1

    session.add_all(outages)
    session.commit()
    print(f"Created {len(outages)} outages")
    return outages


def generate_pricing_nodes(session, assets):
    """Generate pricing nodes from assets."""
    print("Generating pricing nodes...")
    nodes = []

    for asset in assets:
        node = PricingNode(
            node_id=f"PN_{asset.asset_id}",
            node_name=f"{asset.asset_name} Node",
            node_type="generator",
            iso_region=asset.iso_region,
            zone=asset.zone,
            latitude=asset.latitude,
            longitude=asset.longitude,
            geom=f"SRID=4326;POINT({asset.longitude} {asset.latitude})",
        )
        nodes.append(node)

    # Add some hub nodes
    for iso, config in ISO_REGIONS.items():
        lat, lon = config["center"]
        hub = PricingNode(
            node_id=f"HUB_{iso}",
            node_name=f"{iso} Hub",
            node_type="hub",
            iso_region=iso,
            latitude=lat,
            longitude=lon,
            geom=f"SRID=4326;POINT({lon} {lat})",
        )
        nodes.append(hub)

    session.add_all(nodes)
    session.commit()
    print(f"Created {len(nodes)} pricing nodes")
    return nodes


def generate_pricing_records(session, nodes, hours=24):
    """Generate sample LMP pricing records."""
    print(f"Generating {hours} hours of pricing data for {len(nodes)} nodes...")
    records = []
    now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    for hour in range(hours):
        timestamp = now - timedelta(hours=hours - hour - 1)

        # Base price varies by hour (load curve)
        hour_of_day = timestamp.hour
        if 6 <= hour_of_day < 10:
            base_price = random.uniform(35, 55)  # Morning ramp
        elif 10 <= hour_of_day < 15:
            base_price = random.uniform(40, 60)  # Midday
        elif 15 <= hour_of_day < 21:
            base_price = random.uniform(50, 80)  # Peak
        else:
            base_price = random.uniform(20, 35)  # Off-peak

        for node in nodes:
            # Add some randomness per node
            lmp_energy = base_price + random.gauss(0, 5)
            lmp_congestion = random.gauss(0, 3) if random.random() > 0.7 else 0
            lmp_loss = random.uniform(-2, 2)
            lmp_total = lmp_energy + lmp_congestion + lmp_loss

            record = PricingRecord(
                node_id=node.node_id,
                timestamp=timestamp,
                lmp_total=round(lmp_total, 2),
                lmp_energy=round(lmp_energy, 2),
                lmp_congestion=round(lmp_congestion, 2),
                lmp_loss=round(lmp_loss, 2),
                iso_region=node.iso_region,
                market_type="DAM",
            )
            records.append(record)

        # Batch insert every hour
        if len(records) >= 5000:
            session.add_all(records)
            session.commit()
            records = []

    if records:
        session.add_all(records)
        session.commit()

    print(f"Created pricing records for {hours} hours")


def generate_zones(session):
    """Generate zone boundaries."""
    print("Generating zone boundaries...")
    zones = []

    for iso, config in ISO_REGIONS.items():
        # ISO boundary
        boundary = Zone(
            zone_id=f"{iso}_BOUNDARY",
            zone_name=f"{iso} ISO/RTO",
            zone_type=ZoneType.ISO_BOUNDARY,
            iso_region=iso,
            fill_color=config["color"],
            stroke_color=config["color"],
            fill_opacity=0.15,
            geom=create_polygon_wkt(config["bounds"]),
        )
        zones.append(boundary)

        # Load zones (subdivide the ISO area)
        for i, zone_name in enumerate(config["zones"][:5]):  # Limit to 5 zones per ISO
            lat_step = (config["bounds"]["max_lat"] - config["bounds"]["min_lat"]) / 3
            lon_step = (config["bounds"]["max_lon"] - config["bounds"]["min_lon"]) / 3

            row = i // 3
            col = i % 3

            zone_bounds = {
                "min_lat": config["bounds"]["min_lat"] + row * lat_step,
                "max_lat": config["bounds"]["min_lat"] + (row + 1) * lat_step,
                "min_lon": config["bounds"]["min_lon"] + col * lon_step,
                "max_lon": config["bounds"]["min_lon"] + (col + 1) * lon_step,
            }

            load_zone = Zone(
                zone_id=f"{iso}_{zone_name}",
                zone_name=zone_name,
                zone_type=ZoneType.LOAD_ZONE,
                iso_region=iso,
                parent_zone_id=f"{iso}_BOUNDARY",
                fill_color=config["color"],
                stroke_color=config["color"],
                fill_opacity=0.25,
                geom=create_polygon_wkt(zone_bounds),
            )
            zones.append(load_zone)

    session.add_all(zones)
    session.commit()
    print(f"Created {len(zones)} zones")
    return zones


def main():
    """Main seed data generation function."""
    print("=" * 50)
    print("Power Market Geospatial Platform - Seed Data Generator")
    print("=" * 50)

    # Create sync engine
    engine = create_engine(settings.database_url_sync)

    # Ensure PostGIS is enabled
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    with Session(engine) as session:
        # Clear existing data
        print("\nClearing existing data...")
        session.execute(text("TRUNCATE pricing_records, pricing_nodes, outages, assets, zones CASCADE"))
        session.commit()

        # Generate data
        print("\n--- Generating Sample Data ---\n")

        zones = generate_zones(session)
        assets = generate_assets(session, num_per_iso=200)
        outages = generate_outages(session, assets, num_active=50, num_history=200)
        nodes = generate_pricing_nodes(session, assets)
        generate_pricing_records(session, nodes, hours=24)

        print("\n" + "=" * 50)
        print("Seed data generation complete!")
        print("=" * 50)

        # Summary
        print(f"\nSummary:")
        print(f"  - Zones: {len(zones)}")
        print(f"  - Assets: {len(assets)}")
        print(f"  - Outages: {len(outages)}")
        print(f"  - Pricing Nodes: {len(nodes)}")
        print(f"  - Pricing Records: ~{len(nodes) * 24}")


if __name__ == "__main__":
    main()
