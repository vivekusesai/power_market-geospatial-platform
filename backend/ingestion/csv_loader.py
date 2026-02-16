"""CSV data ingestion utilities."""
import csv
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.asset import Asset, FuelType
from backend.models.outage import Outage, OutageStatus, OutageType
from backend.models.pricing import PricingNode, PricingRecord
from backend.schemas.asset import AssetCreate
from backend.schemas.outage import OutageCreate
from backend.schemas.pricing import PricingNodeCreate, PricingRecordCreate


class CSVLoader:
    """Load data from CSV files."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_assets(
        self,
        file_path: Path,
        iso_region: str,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Load assets from CSV file.

        Expected columns (or mapped equivalents):
        - asset_id, asset_name, fuel_type, capacity_mw, latitude, longitude, zone, owner
        """
        df = pd.read_csv(file_path)

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # Normalize fuel types
        fuel_type_map = {
            "coal": FuelType.COAL,
            "natural gas": FuelType.NATURAL_GAS,
            "gas": FuelType.NATURAL_GAS,
            "ng": FuelType.NATURAL_GAS,
            "nuclear": FuelType.NUCLEAR,
            "hydro": FuelType.HYDRO,
            "hydroelectric": FuelType.HYDRO,
            "wind": FuelType.WIND,
            "solar": FuelType.SOLAR,
            "oil": FuelType.OIL,
            "petroleum": FuelType.OIL,
            "biomass": FuelType.BIOMASS,
            "geothermal": FuelType.GEOTHERMAL,
            "battery": FuelType.BATTERY,
            "storage": FuelType.BATTERY,
        }

        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

        assets = []
        for _, row in df.iterrows():
            fuel_str = str(row.get("fuel_type", "other")).lower().strip()
            fuel_type = fuel_type_map.get(fuel_str, FuelType.OTHER)

            asset = Asset(
                asset_id=str(row["asset_id"]),
                asset_name=str(row["asset_name"]),
                fuel_type=fuel_type,
                capacity_mw=float(row["capacity_mw"]),
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                iso_region=iso_region,
                zone=str(row.get("zone", "")) or None,
                owner=str(row.get("owner", "")) or None,
                geom=ST_SetSRID(
                    ST_MakePoint(float(row["longitude"]), float(row["latitude"])),
                    4326,
                ),
            )
            assets.append(asset)

        self.db.add_all(assets)
        await self.db.flush()
        return len(assets)

    async def load_outages(
        self,
        file_path: Path,
        column_mapping: Optional[Dict[str, str]] = None,
        date_format: str = "%Y-%m-%d %H:%M:%S",
    ) -> int:
        """
        Load outages from CSV file.

        Expected columns:
        - outage_id, asset_id, outage_type, start_time, end_time, status, cause_code, capacity_reduction_mw
        """
        df = pd.read_csv(file_path)

        if column_mapping:
            df = df.rename(columns=column_mapping)

        outage_type_map = {
            "planned": OutageType.PLANNED,
            "forced": OutageType.FORCED,
            "maintenance": OutageType.MAINTENANCE,
            "derate": OutageType.DERATE,
        }

        status_map = {
            "active": OutageStatus.ACTIVE,
            "scheduled": OutageStatus.SCHEDULED,
            "completed": OutageStatus.COMPLETED,
            "cancelled": OutageStatus.CANCELLED,
        }

        outages = []
        for _, row in df.iterrows():
            outage_type_str = str(row.get("outage_type", "forced")).lower().strip()
            status_str = str(row.get("status", "active")).lower().strip()

            start_time = pd.to_datetime(row["start_time"])
            end_time = pd.to_datetime(row.get("end_time")) if pd.notna(row.get("end_time")) else None

            outage = Outage(
                outage_id=str(row["outage_id"]),
                asset_id=str(row["asset_id"]),
                outage_type=outage_type_map.get(outage_type_str, OutageType.FORCED),
                start_time=start_time,
                end_time=end_time,
                status=status_map.get(status_str, OutageStatus.ACTIVE),
                cause_code=str(row.get("cause_code", "")) or None,
                cause_description=str(row.get("cause_description", "")) or None,
                capacity_reduction_mw=float(row["capacity_reduction_mw"]) if pd.notna(row.get("capacity_reduction_mw")) else None,
            )
            outages.append(outage)

        self.db.add_all(outages)
        await self.db.flush()
        return len(outages)

    async def load_pricing_nodes(
        self,
        file_path: Path,
        iso_region: str,
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Load pricing nodes from CSV file.

        Expected columns:
        - node_id, node_name, node_type, latitude, longitude, zone
        """
        df = pd.read_csv(file_path)

        if column_mapping:
            df = df.rename(columns=column_mapping)

        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

        nodes = []
        for _, row in df.iterrows():
            lat = float(row["latitude"]) if pd.notna(row.get("latitude")) else None
            lon = float(row["longitude"]) if pd.notna(row.get("longitude")) else None

            node = PricingNode(
                node_id=str(row["node_id"]),
                node_name=str(row["node_name"]),
                node_type=str(row.get("node_type", "generator")),
                iso_region=iso_region,
                zone=str(row.get("zone", "")) or None,
                latitude=lat,
                longitude=lon,
                geom=ST_SetSRID(ST_MakePoint(lon, lat), 4326) if lat and lon else None,
            )
            nodes.append(node)

        self.db.add_all(nodes)
        await self.db.flush()
        return len(nodes)

    async def load_pricing_records(
        self,
        file_path: Path,
        iso_region: str,
        market_type: str = "DAM",
        column_mapping: Optional[Dict[str, str]] = None,
        chunk_size: int = 10000,
    ) -> int:
        """
        Load pricing records from CSV file (supports large files via chunking).

        Expected columns:
        - node_id or asset_id, timestamp, lmp_total, lmp_energy, lmp_congestion, lmp_loss
        """
        total_count = 0

        for chunk in pd.read_csv(file_path, chunksize=chunk_size):
            if column_mapping:
                chunk = chunk.rename(columns=column_mapping)

            records = []
            for _, row in chunk.iterrows():
                record = PricingRecord(
                    node_id=str(row.get("node_id")) if pd.notna(row.get("node_id")) else None,
                    asset_id=str(row.get("asset_id")) if pd.notna(row.get("asset_id")) else None,
                    timestamp=pd.to_datetime(row["timestamp"]),
                    lmp_total=float(row["lmp_total"]),
                    lmp_energy=float(row["lmp_energy"]) if pd.notna(row.get("lmp_energy")) else None,
                    lmp_congestion=float(row["lmp_congestion"]) if pd.notna(row.get("lmp_congestion")) else None,
                    lmp_loss=float(row["lmp_loss"]) if pd.notna(row.get("lmp_loss")) else None,
                    iso_region=iso_region,
                    market_type=market_type,
                )
                records.append(record)

            self.db.add_all(records)
            await self.db.flush()
            total_count += len(records)

        return total_count
