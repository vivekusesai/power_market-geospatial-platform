"""Zone API endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.zone import ZoneType
from backend.schemas.zone import ZoneGeoJSON, ZoneResponse
from backend.services.zone_service import ZoneService

router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=ZoneGeoJSON)
async def get_zones(
    iso_region: Optional[str] = Query(None, description="Filter by ISO region"),
    zone_type: Optional[ZoneType] = Query(None, description="Filter by zone type"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get zones as GeoJSON.

    Returns zone boundaries including ISO footprints, load zones,
    transmission zones, and settlement zones.
    """
    service = ZoneService(db)
    return await service.to_geojson(iso_region=iso_region, zone_type=zone_type)


@router.get("/list")
async def list_zones(
    iso_region: Optional[str] = Query(None),
    zone_type: Optional[ZoneType] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get zones as a simple list (without geometry)."""
    service = ZoneService(db)
    zones = await service.get_all(iso_region=iso_region, zone_type=zone_type)
    return {"zones": [ZoneResponse.model_validate(z) for z in zones]}


@router.get("/grouped")
async def get_zones_grouped(
    iso_region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get zones grouped by type."""
    service = ZoneService(db)
    grouped = await service.get_grouped_by_type(iso_region=iso_region)
    return {
        key: [ZoneResponse.model_validate(z) for z in zones]
        for key, zones in grouped.items()
    }


@router.get("/iso-boundaries", response_model=ZoneGeoJSON)
async def get_iso_boundaries(
    db: AsyncSession = Depends(get_db),
):
    """Get ISO boundary zones as GeoJSON."""
    service = ZoneService(db)
    return await service.to_geojson(zone_type=ZoneType.ISO_BOUNDARY)


@router.get("/load-zones", response_model=ZoneGeoJSON)
async def get_load_zones(
    iso_region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get load zones as GeoJSON."""
    service = ZoneService(db)
    return await service.to_geojson(iso_region=iso_region, zone_type=ZoneType.LOAD_ZONE)


@router.get("/{zone_id}", response_model=ZoneResponse)
async def get_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single zone by ID."""
    service = ZoneService(db)
    zone = await service.get_by_id(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return ZoneResponse.model_validate(zone)


@router.get("/{zone_id}/geojson")
async def get_zone_geojson(
    zone_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single zone as GeoJSON feature."""
    service = ZoneService(db)
    zone = await service.get_by_id(zone_id)
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    geojson = await service.to_geojson()
    for feature in geojson.features:
        if feature.properties.zone_id == zone_id:
            return feature

    raise HTTPException(status_code=404, detail="Zone geometry not found")
