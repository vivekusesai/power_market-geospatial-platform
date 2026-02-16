"""Asset service for database operations."""
from datetime import datetime
from typing import List, Optional

from geoalchemy2.functions import ST_MakeEnvelope, ST_SetSRID, ST_MakePoint, ST_Within
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.asset import Asset, FuelType
from backend.models.outage import Outage, OutageStatus, OutageType
from backend.schemas.asset import AssetCreate, AssetFeature, AssetGeoJSON, AssetFeatureProperties
from backend.schemas.common import BoundingBox


class AssetService:
    """Service for asset operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        iso_region: Optional[str] = None,
        fuel_type: Optional[FuelType] = None,
        zone: Optional[str] = None,
        limit: int = 5000,
        offset: int = 0,
    ) -> List[Asset]:
        """Get all assets with optional filters."""
        query = select(Asset)

        if iso_region:
            query = query.where(Asset.iso_region == iso_region)
        if fuel_type:
            query = query.where(Asset.fuel_type == fuel_type)
        if zone:
            query = query.where(Asset.zone == zone)

        query = query.order_by(Asset.asset_id).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_bbox(
        self,
        bbox: BoundingBox,
        iso_region: Optional[str] = None,
        fuel_type: Optional[FuelType] = None,
        limit: int = 5000,
    ) -> List[Asset]:
        """Get assets within a bounding box."""
        envelope = ST_MakeEnvelope(
            bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326
        )

        query = select(Asset).where(ST_Within(Asset.geom, envelope))

        if iso_region:
            query = query.where(Asset.iso_region == iso_region)
        if fuel_type:
            query = query.where(Asset.fuel_type == fuel_type)

        query = query.limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, asset_id: str) -> Optional[Asset]:
        """Get a single asset by ID."""
        query = select(Asset).where(Asset.asset_id == asset_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(self, asset_data: AssetCreate) -> Asset:
        """Create a new asset."""
        asset = Asset(
            **asset_data.model_dump(),
            geom=ST_SetSRID(
                ST_MakePoint(asset_data.longitude, asset_data.latitude), 4326
            ),
        )
        self.db.add(asset)
        await self.db.flush()
        await self.db.refresh(asset)
        return asset

    async def create_bulk(self, assets_data: List[AssetCreate]) -> int:
        """Bulk create assets."""
        assets = [
            Asset(
                **data.model_dump(),
                geom=ST_SetSRID(ST_MakePoint(data.longitude, data.latitude), 4326),
            )
            for data in assets_data
        ]
        self.db.add_all(assets)
        await self.db.flush()
        return len(assets)

    async def get_with_current_outages(
        self,
        bbox: Optional[BoundingBox] = None,
        iso_region: Optional[str] = None,
        at_time: Optional[datetime] = None,
        limit: int = 5000,
    ) -> List[dict]:
        """Get assets with their current outage status."""
        if at_time is None:
            at_time = datetime.utcnow()

        # Subquery for active outages at the given time
        outage_subq = (
            select(
                Outage.asset_id,
                Outage.outage_type,
                Outage.status,
                Outage.start_time,
                Outage.end_time,
                Outage.cause_code,
                Outage.capacity_reduction_mw,
            )
            .where(
                and_(
                    Outage.status.in_([OutageStatus.ACTIVE, OutageStatus.SCHEDULED]),
                    Outage.start_time <= at_time,
                    or_(Outage.end_time.is_(None), Outage.end_time >= at_time),
                )
            )
            .subquery()
        )

        query = (
            select(Asset, outage_subq)
            .outerjoin(outage_subq, Asset.asset_id == outage_subq.c.asset_id)
        )

        if bbox:
            envelope = ST_MakeEnvelope(
                bbox.min_lon, bbox.min_lat, bbox.max_lon, bbox.max_lat, 4326
            )
            query = query.where(ST_Within(Asset.geom, envelope))

        if iso_region:
            query = query.where(Asset.iso_region == iso_region)

        query = query.limit(limit)
        result = await self.db.execute(query)

        assets_with_outages = []
        for row in result.all():
            asset = row[0]
            asset_dict = {
                "asset_id": asset.asset_id,
                "asset_name": asset.asset_name,
                "fuel_type": asset.fuel_type.value if hasattr(asset.fuel_type, 'value') else asset.fuel_type,
                "capacity_mw": asset.capacity_mw,
                "latitude": asset.latitude,
                "longitude": asset.longitude,
                "iso_region": asset.iso_region,
                "zone": asset.zone,
                "owner": asset.owner,
                "outage_type": row[2].value if row[2] and hasattr(row[2], 'value') else row[2],
                "outage_status": row[3].value if row[3] and hasattr(row[3], 'value') else row[3],
                "outage_start": row[4].isoformat() if row[4] else None,
                "outage_end": row[5].isoformat() if row[5] else None,
                "cause_code": row[6],
                "capacity_reduction_mw": row[7],
            }
            assets_with_outages.append(asset_dict)

        return assets_with_outages

    async def to_geojson(
        self,
        assets: List[dict],
    ) -> AssetGeoJSON:
        """Convert assets to GeoJSON format."""
        features = []
        for asset in assets:
            # Determine status based on outage
            if asset.get("outage_type"):
                if asset["outage_type"] == "forced":
                    status = "forced_outage"
                elif asset["outage_type"] == "planned":
                    status = "planned_maintenance"
                elif asset["outage_type"] == "derate":
                    status = "derated"
                else:
                    status = "maintenance"
            else:
                status = "available"

            feature = AssetFeature(
                geometry={
                    "type": "Point",
                    "coordinates": [asset["longitude"], asset["latitude"]],
                },
                properties=AssetFeatureProperties(
                    asset_id=asset["asset_id"],
                    asset_name=asset["asset_name"],
                    fuel_type=asset["fuel_type"],
                    capacity_mw=asset["capacity_mw"],
                    iso_region=asset["iso_region"],
                    zone=asset.get("zone"),
                    owner=asset.get("owner"),
                    status=status,
                    outage_type=asset.get("outage_type"),
                ),
            )
            features.append(feature)

        return AssetGeoJSON(features=features)

    async def get_count(self, iso_region: Optional[str] = None) -> int:
        """Get total count of assets."""
        query = select(func.count(Asset.id))
        if iso_region:
            query = query.where(Asset.iso_region == iso_region)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def get_iso_regions(self) -> List[str]:
        """Get list of unique ISO regions."""
        query = select(Asset.iso_region).distinct().order_by(Asset.iso_region)
        result = await self.db.execute(query)
        return [row[0] for row in result.all()]

    async def get_fuel_type_distribution(
        self, iso_region: Optional[str] = None
    ) -> dict:
        """Get asset count by fuel type."""
        query = (
            select(Asset.fuel_type, func.count(Asset.id), func.sum(Asset.capacity_mw))
            .group_by(Asset.fuel_type)
        )
        if iso_region:
            query = query.where(Asset.iso_region == iso_region)

        result = await self.db.execute(query)
        return {
            (row[0].value if hasattr(row[0], 'value') else row[0]): {"count": row[1], "capacity_mw": row[2]}
            for row in result.all()
        }
