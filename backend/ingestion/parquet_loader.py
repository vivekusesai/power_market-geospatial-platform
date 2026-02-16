"""Parquet data ingestion utilities."""
from pathlib import Path
from typing import Dict, Optional

import pandas as pd
import pyarrow.parquet as pq
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.pricing import PricingRecord


class ParquetLoader:
    """Load market data from Parquet files."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load_pricing_records(
        self,
        file_path: Path,
        iso_region: str,
        market_type: str = "DAM",
        column_mapping: Optional[Dict[str, str]] = None,
        batch_size: int = 10000,
    ) -> int:
        """
        Load pricing records from Parquet file.

        Parquet is efficient for large pricing datasets with millions of records.

        Expected columns:
        - node_id or asset_id, timestamp, lmp_total, lmp_energy, lmp_congestion, lmp_loss
        """
        # Read parquet file
        table = pq.read_table(file_path)
        df = table.to_pandas()

        if column_mapping:
            df = df.rename(columns=column_mapping)

        total_count = 0
        batch = []

        for _, row in df.iterrows():
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
            batch.append(record)

            if len(batch) >= batch_size:
                self.db.add_all(batch)
                await self.db.flush()
                total_count += len(batch)
                batch = []

        # Add remaining records
        if batch:
            self.db.add_all(batch)
            await self.db.flush()
            total_count += len(batch)

        return total_count

    async def load_pricing_records_fast(
        self,
        file_path: Path,
        iso_region: str,
        market_type: str = "DAM",
        column_mapping: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Fast bulk load using pandas to_sql (for initial data load).

        This method uses synchronous database operations for maximum speed.
        Use this for initial data loading, not for incremental updates.
        """
        from sqlalchemy import create_engine
        from backend.config import get_settings

        settings = get_settings()

        # Read parquet
        df = pd.read_parquet(file_path)

        if column_mapping:
            df = df.rename(columns=column_mapping)

        # Add metadata columns
        df["iso_region"] = iso_region
        df["market_type"] = market_type

        # Ensure correct column names
        required_cols = ["node_id", "timestamp", "lmp_total", "iso_region", "market_type"]
        for col in required_cols:
            if col not in df.columns:
                if col in ["node_id"]:
                    df[col] = None

        # Use synchronous engine for bulk insert
        sync_engine = create_engine(settings.database_url_sync)

        # Bulk insert
        df.to_sql(
            "pricing_records",
            sync_engine,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )

        sync_engine.dispose()
        return len(df)

    @staticmethod
    def convert_csv_to_parquet(
        csv_path: Path,
        parquet_path: Path,
        compression: str = "snappy",
    ) -> None:
        """Convert a CSV file to Parquet format for faster loading."""
        df = pd.read_csv(csv_path)

        # Optimize data types
        for col in df.columns:
            if df[col].dtype == "object":
                # Try to convert to category if low cardinality
                if df[col].nunique() / len(df) < 0.5:
                    df[col] = df[col].astype("category")

        df.to_parquet(parquet_path, compression=compression, index=False)
