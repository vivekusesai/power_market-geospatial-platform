"""Outage service for database operations."""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models.asset import Asset
from backend.models.outage import Outage, OutageStatus, OutageType
from backend.schemas.outage import (
    OutageCreate,
    OutageFeature,
    OutageGeoJSON,
    OutageFeatureProperties,
    OutageStats,
)


class OutageService:
    """Service for outage operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        iso_region: Optional[str] = None,
        outage_type: Optional[OutageType] = None,
        status: Optional[OutageStatus] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Outage]:
        """Get outages with optional filters."""
        query = select(Outage).options(joinedload(Outage.asset))

        conditions = []
        if start_time:
            # Outages that overlap with the time range
            conditions.append(
                or_(Outage.end_time.is_(None), Outage.end_time >= start_time)
            )
        if end_time:
            conditions.append(Outage.start_time <= end_time)
        if outage_type:
            conditions.append(Outage.outage_type == outage_type)
        if status:
            conditions.append(Outage.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        if iso_region:
            query = query.join(Asset).where(Asset.iso_region == iso_region)

        query = query.order_by(Outage.start_time.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.unique().scalars().all())

    async def get_active_at_time(
        self,
        at_time: datetime,
        iso_region: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Outage]:
        """Get outages active at a specific point in time."""
        query = (
            select(Outage)
            .options(joinedload(Outage.asset))
            .where(
                and_(
                    Outage.start_time <= at_time,
                    or_(Outage.end_time.is_(None), Outage.end_time >= at_time),
                    Outage.status.in_([OutageStatus.ACTIVE, OutageStatus.SCHEDULED]),
                )
            )
        )

        if iso_region:
            query = query.join(Asset).where(Asset.iso_region == iso_region)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.unique().scalars().all())

    async def get_by_id(self, outage_id: str) -> Optional[Outage]:
        """Get a single outage by ID."""
        query = (
            select(Outage)
            .options(joinedload(Outage.asset))
            .where(Outage.outage_id == outage_id)
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none()

    async def get_by_asset(
        self,
        asset_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Outage]:
        """Get outages for a specific asset."""
        query = select(Outage).where(Outage.asset_id == asset_id)

        if start_time:
            query = query.where(
                or_(Outage.end_time.is_(None), Outage.end_time >= start_time)
            )
        if end_time:
            query = query.where(Outage.start_time <= end_time)

        query = query.order_by(Outage.start_time.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create(self, outage_data: OutageCreate) -> Outage:
        """Create a new outage."""
        outage = Outage(**outage_data.model_dump())
        self.db.add(outage)
        await self.db.flush()
        await self.db.refresh(outage)
        return outage

    async def create_bulk(self, outages_data: List[OutageCreate]) -> int:
        """Bulk create outages."""
        outages = [Outage(**data.model_dump()) for data in outages_data]
        self.db.add_all(outages)
        await self.db.flush()
        return len(outages)

    async def update_status(
        self, outage_id: str, status: OutageStatus, end_time: Optional[datetime] = None
    ) -> Optional[Outage]:
        """Update outage status."""
        outage = await self.get_by_id(outage_id)
        if outage:
            outage.status = status
            if end_time:
                outage.end_time = end_time
            await self.db.flush()
            await self.db.refresh(outage)
        return outage

    async def to_geojson(self, outages: List[Outage]) -> OutageGeoJSON:
        """Convert outages to GeoJSON format."""
        features = []
        for outage in outages:
            if outage.asset:
                feature = OutageFeature(
                    geometry={
                        "type": "Point",
                        "coordinates": [outage.asset.longitude, outage.asset.latitude],
                    },
                    properties=OutageFeatureProperties(
                        outage_id=outage.outage_id,
                        asset_id=outage.asset_id,
                        asset_name=outage.asset.asset_name,
                        outage_type=outage.outage_type.value,
                        status=outage.status.value,
                        start_time=outage.start_time.isoformat(),
                        end_time=outage.end_time.isoformat() if outage.end_time else None,
                        cause_code=outage.cause_code,
                        capacity_reduction_mw=outage.capacity_reduction_mw,
                        fuel_type=outage.asset.fuel_type.value,
                        capacity_mw=outage.asset.capacity_mw,
                    ),
                )
                features.append(feature)

        return OutageGeoJSON(features=features)

    async def get_stats(
        self,
        at_time: Optional[datetime] = None,
        iso_region: Optional[str] = None,
    ) -> OutageStats:
        """Get outage statistics."""
        if at_time is None:
            at_time = datetime.utcnow()

        base_conditions = [
            Outage.start_time <= at_time,
            or_(Outage.end_time.is_(None), Outage.end_time >= at_time),
            Outage.status.in_([OutageStatus.ACTIVE, OutageStatus.SCHEDULED]),
        ]

        # Total outages
        query = select(func.count(Outage.id)).where(and_(*base_conditions))
        if iso_region:
            query = query.join(Asset).where(Asset.iso_region == iso_region)
        result = await self.db.execute(query)
        total = result.scalar_one()

        # By type
        type_query = (
            select(Outage.outage_type, func.count(Outage.id))
            .where(and_(*base_conditions))
            .group_by(Outage.outage_type)
        )
        if iso_region:
            type_query = type_query.join(Asset).where(Asset.iso_region == iso_region)
        result = await self.db.execute(type_query)
        type_counts = {row[0]: row[1] for row in result.all()}

        # Total capacity offline
        cap_query = (
            select(func.coalesce(func.sum(Outage.capacity_reduction_mw), 0))
            .where(and_(*base_conditions))
        )
        if iso_region:
            cap_query = cap_query.join(Asset).where(Asset.iso_region == iso_region)
        result = await self.db.execute(cap_query)
        total_capacity = result.scalar_one() or 0

        return OutageStats(
            total_outages=total,
            forced_outages=type_counts.get(OutageType.FORCED, 0),
            planned_outages=type_counts.get(OutageType.PLANNED, 0),
            maintenance_outages=type_counts.get(OutageType.MAINTENANCE, 0),
            derates=type_counts.get(OutageType.DERATE, 0),
            total_capacity_offline_mw=float(total_capacity),
        )
