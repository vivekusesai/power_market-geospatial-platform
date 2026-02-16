"""Zone service for database operations."""
from typing import Any, Dict, List, Optional

from geoalchemy2.functions import ST_AsGeoJSON, ST_GeomFromGeoJSON
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.zone import Zone, ZoneType
from backend.schemas.zone import (
    ZoneCreate,
    ZoneFeature,
    ZoneGeoJSON,
    ZoneFeatureProperties,
)


class ZoneService:
    """Service for zone operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self,
        iso_region: Optional[str] = None,
        zone_type: Optional[ZoneType] = None,
    ) -> List[Zone]:
        """Get all zones."""
        query = select(Zone)

        if iso_region:
            query = query.where(Zone.iso_region == iso_region)
        if zone_type:
            query = query.where(Zone.zone_type == zone_type)

        query = query.order_by(Zone.zone_type, Zone.zone_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, zone_id: str) -> Optional[Zone]:
        """Get a zone by ID."""
        query = select(Zone).where(Zone.zone_id == zone_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_by_type(
        self,
        zone_type: ZoneType,
        iso_region: Optional[str] = None,
    ) -> List[Zone]:
        """Get zones by type."""
        query = select(Zone).where(Zone.zone_type == zone_type)

        if iso_region:
            query = query.where(Zone.iso_region == iso_region)

        query = query.order_by(Zone.zone_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_iso_boundaries(self) -> List[Zone]:
        """Get ISO boundary zones."""
        return await self.get_by_type(ZoneType.ISO_BOUNDARY)

    async def create(self, zone_data: ZoneCreate) -> Zone:
        """Create a new zone."""
        data = zone_data.model_dump(exclude={"geojson"})
        zone = Zone(**data)

        if zone_data.geojson:
            zone.geom = ST_GeomFromGeoJSON(str(zone_data.geojson))

        self.db.add(zone)
        await self.db.flush()
        await self.db.refresh(zone)
        return zone

    async def to_geojson(
        self,
        zones: Optional[List[Zone]] = None,
        iso_region: Optional[str] = None,
        zone_type: Optional[ZoneType] = None,
    ) -> ZoneGeoJSON:
        """Convert zones to GeoJSON format."""
        # Query with geometry as GeoJSON
        query = select(Zone, ST_AsGeoJSON(Zone.geom).label("geojson"))

        if iso_region:
            query = query.where(Zone.iso_region == iso_region)
        if zone_type:
            query = query.where(Zone.zone_type == zone_type)

        query = query.order_by(Zone.zone_type, Zone.zone_name)
        result = await self.db.execute(query)

        features = []
        for row in result.all():
            zone = row[0]
            geojson_str = row[1]

            if geojson_str:
                import json
                geometry = json.loads(geojson_str)

                feature = ZoneFeature(
                    geometry=geometry,
                    properties=ZoneFeatureProperties(
                        zone_id=zone.zone_id,
                        zone_name=zone.zone_name,
                        zone_type=zone.zone_type.value,
                        iso_region=zone.iso_region,
                        fill_color=zone.fill_color,
                        stroke_color=zone.stroke_color,
                        fill_opacity=zone.fill_opacity,
                    ),
                )
                features.append(feature)

        return ZoneGeoJSON(features=features)

    async def get_grouped_by_type(
        self, iso_region: Optional[str] = None
    ) -> Dict[str, List[Zone]]:
        """Get zones grouped by type."""
        zones = await self.get_all(iso_region=iso_region)

        grouped: Dict[str, List[Zone]] = {
            "iso_boundaries": [],
            "load_zones": [],
            "transmission_zones": [],
            "settlement_zones": [],
            "pricing_zones": [],
            "reserve_zones": [],
        }

        type_map = {
            ZoneType.ISO_BOUNDARY: "iso_boundaries",
            ZoneType.LOAD_ZONE: "load_zones",
            ZoneType.TRANSMISSION_ZONE: "transmission_zones",
            ZoneType.SETTLEMENT_ZONE: "settlement_zones",
            ZoneType.PRICING_ZONE: "pricing_zones",
            ZoneType.RESERVE_ZONE: "reserve_zones",
        }

        for zone in zones:
            key = type_map.get(zone.zone_type)
            if key:
                grouped[key].append(zone)

        return grouped
