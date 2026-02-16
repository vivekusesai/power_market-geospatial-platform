"""Pricing service for database operations."""
from datetime import datetime
from typing import List, Optional

from geoalchemy2.functions import ST_MakeEnvelope, ST_Within
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.pricing import PricingNode, PricingRecord
from backend.schemas.common import BoundingBox
from backend.schemas.pricing import (
    PricingNodeCreate,
    PricingRecordCreate,
    PricingHeatmapPoint,
    PricingHeatmapResponse,
    PricingTimeSeries,
    PricingStats,
)


class PricingService:
    """Service for pricing operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # Pricing Node operations
    async def get_all_nodes(
        self,
        iso_region: Optional[str] = None,
        node_type: Optional[str] = None,
        limit: int = 5000,
    ) -> List[PricingNode]:
        """Get all pricing nodes."""
        query = select(PricingNode)

        if iso_region:
            query = query.where(PricingNode.iso_region == iso_region)
        if node_type:
            query = query.where(PricingNode.node_type == node_type)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_nodes_by_bbox(
        self,
        bbox: BoundingBox,
        iso_region: Optional[str] = None,
        limit: int = 5000,
    ) -> List[PricingNode]:
        """Get pricing nodes within a bounding box."""
        envelope = ST_MakeEnvelope(
            bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326
        )

        query = select(PricingNode).where(ST_Within(PricingNode.geom, envelope))

        if iso_region:
            query = query.where(PricingNode.iso_region == iso_region)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_node_by_id(self, node_id: str) -> Optional[PricingNode]:
        """Get a pricing node by ID."""
        query = select(PricingNode).where(PricingNode.node_id == node_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create_node(self, node_data: PricingNodeCreate) -> PricingNode:
        """Create a pricing node."""
        from geoalchemy2.functions import ST_SetSRID, ST_MakePoint

        node = PricingNode(**node_data.model_dump())
        if node_data.latitude and node_data.longitude:
            node.geom = ST_SetSRID(
                ST_MakePoint(node_data.longitude, node_data.latitude), 4326
            )
        self.db.add(node)
        await self.db.flush()
        await self.db.refresh(node)
        return node

    # Pricing Record operations
    async def get_pricing_for_node(
        self,
        node_id: str,
        start_time: datetime,
        end_time: datetime,
        market_type: str = "DAM",
        limit: int = 10000,
    ) -> List[PricingRecord]:
        """Get pricing records for a specific node."""
        query = (
            select(PricingRecord)
            .where(
                and_(
                    PricingRecord.node_id == node_id,
                    PricingRecord.timestamp >= start_time,
                    PricingRecord.timestamp <= end_time,
                    PricingRecord.market_type == market_type,
                )
            )
            .order_by(PricingRecord.timestamp)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_pricing_time_series(
        self,
        node_id: str,
        start_time: datetime,
        end_time: datetime,
        market_type: str = "DAM",
    ) -> Optional[PricingTimeSeries]:
        """Get pricing time series for a node."""
        node = await self.get_node_by_id(node_id)
        if not node:
            return None

        records = await self.get_pricing_for_node(
            node_id, start_time, end_time, market_type
        )

        data = [
            {
                "timestamp": r.timestamp.isoformat(),
                "lmp_total": r.lmp_total,
                "lmp_energy": r.lmp_energy,
                "lmp_congestion": r.lmp_congestion,
                "lmp_loss": r.lmp_loss,
            }
            for r in records
        ]

        return PricingTimeSeries(
            node_id=node.node_id,
            node_name=node.node_name,
            iso_region=node.iso_region,
            data=data,
        )

    async def get_heatmap_data(
        self,
        timestamp: datetime,
        iso_region: Optional[str] = None,
        market_type: str = "DAM",
        bbox: Optional[BoundingBox] = None,
        component: str = "total",  # total, energy, congestion, loss
    ) -> PricingHeatmapResponse:
        """Get LMP heatmap data for a specific timestamp."""
        # Get the closest timestamp's data
        query = (
            select(PricingRecord, PricingNode)
            .join(PricingNode, PricingRecord.node_id == PricingNode.node_id)
            .where(
                and_(
                    PricingRecord.timestamp == timestamp,
                    PricingRecord.market_type == market_type,
                )
            )
        )

        if iso_region:
            query = query.where(PricingRecord.iso_region == iso_region)

        if bbox:
            envelope = ST_MakeEnvelope(
                bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326
            )
            query = query.where(ST_Within(PricingNode.geom, envelope))

        result = await self.db.execute(query)
        rows = result.all()

        points = []
        lmp_values = []

        for record, node in rows:
            if node.latitude and node.longitude:
                point = PricingHeatmapPoint(
                    node_id=node.node_id,
                    latitude=node.latitude,
                    longitude=node.longitude,
                    lmp_total=record.lmp_total,
                    lmp_energy=record.lmp_energy,
                    lmp_congestion=record.lmp_congestion,
                    lmp_loss=record.lmp_loss,
                    timestamp=record.timestamp,
                )
                points.append(point)
                lmp_values.append(record.lmp_total)

        min_lmp = min(lmp_values) if lmp_values else 0
        max_lmp = max(lmp_values) if lmp_values else 0
        avg_lmp = sum(lmp_values) / len(lmp_values) if lmp_values else 0

        return PricingHeatmapResponse(
            timestamp=timestamp,
            iso_region=iso_region or "ALL",
            market_type=market_type,
            min_lmp=min_lmp,
            max_lmp=max_lmp,
            avg_lmp=avg_lmp,
            points=points,
        )

    async def get_available_timestamps(
        self,
        iso_region: Optional[str] = None,
        market_type: str = "DAM",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[datetime]:
        """Get available pricing timestamps."""
        query = (
            select(PricingRecord.timestamp)
            .distinct()
            .where(PricingRecord.market_type == market_type)
        )

        if iso_region:
            query = query.where(PricingRecord.iso_region == iso_region)
        if start_time:
            query = query.where(PricingRecord.timestamp >= start_time)
        if end_time:
            query = query.where(PricingRecord.timestamp <= end_time)

        query = query.order_by(PricingRecord.timestamp).limit(limit)
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def create_record(self, record_data: PricingRecordCreate) -> PricingRecord:
        """Create a pricing record."""
        record = PricingRecord(**record_data.model_dump())
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def create_records_bulk(self, records_data: List[PricingRecordCreate]) -> int:
        """Bulk create pricing records."""
        records = [PricingRecord(**data.model_dump()) for data in records_data]
        self.db.add_all(records)
        await self.db.flush()
        return len(records)

    async def get_stats(
        self,
        timestamp: datetime,
        iso_region: Optional[str] = None,
        market_type: str = "DAM",
    ) -> PricingStats:
        """Get pricing statistics for a timestamp."""
        query = (
            select(
                func.min(PricingRecord.lmp_total),
                func.max(PricingRecord.lmp_total),
                func.avg(PricingRecord.lmp_total),
                func.stddev(PricingRecord.lmp_total),
                func.count(
                    func.nullif(
                        func.abs(PricingRecord.lmp_congestion) > 5, False
                    )
                ),
            )
            .where(
                and_(
                    PricingRecord.timestamp == timestamp,
                    PricingRecord.market_type == market_type,
                )
            )
        )

        if iso_region:
            query = query.where(PricingRecord.iso_region == iso_region)

        result = await self.db.execute(query)
        row = result.one()

        return PricingStats(
            iso_region=iso_region or "ALL",
            timestamp=timestamp,
            min_lmp=row[0] or 0,
            max_lmp=row[1] or 0,
            avg_lmp=row[2] or 0,
            std_lmp=row[3] or 0,
            congestion_count=row[4] or 0,
        )
