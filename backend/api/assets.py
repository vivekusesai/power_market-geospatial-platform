"""Asset API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.asset import FuelType
from backend.schemas.asset import AssetGeoJSON, AssetResponse, AssetWithOutage
from backend.schemas.common import BoundingBox
from backend.services.asset_service import AssetService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetGeoJSON)
async def get_assets(
    bbox: Optional[str] = Query(
        None,
        description="Bounding box as 'min_lon,min_lat,max_lon,max_lat'",
        example="-100,30,-80,45",
    ),
    iso_region: Optional[str] = Query(None, description="Filter by ISO region"),
    fuel_type: Optional[FuelType] = Query(None, description="Filter by fuel type"),
    at_time: Optional[datetime] = Query(
        None, description="Get status at specific time (ISO format)"
    ),
    limit: int = Query(5000, le=10000, description="Maximum assets to return"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get assets as GeoJSON with current outage status.

    Returns generator assets with their current operational status based on
    active outages at the specified time (defaults to now).
    """
    service = AssetService(db)

    bbox_obj = None
    if bbox:
        try:
            bbox_obj = BoundingBox.from_string(bbox)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    assets = await service.get_with_current_outages(
        bbox=bbox_obj,
        iso_region=iso_region,
        at_time=at_time,
        limit=limit,
    )

    return await service.to_geojson(assets)


@router.get("/list")
async def list_assets(
    iso_region: Optional[str] = Query(None),
    fuel_type: Optional[FuelType] = Query(None),
    zone: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of assets (non-geospatial)."""
    service = AssetService(db)
    assets = await service.get_all(
        iso_region=iso_region,
        fuel_type=fuel_type,
        zone=zone,
        limit=limit,
        offset=offset,
    )
    total = await service.get_count(iso_region=iso_region)

    return {
        "items": [AssetResponse.model_validate(a) for a in assets],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/regions")
async def get_iso_regions(db: AsyncSession = Depends(get_db)):
    """Get list of available ISO regions."""
    service = AssetService(db)
    regions = await service.get_iso_regions()
    return {"regions": regions}


@router.get("/fuel-types")
async def get_fuel_type_distribution(
    iso_region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get asset count and capacity by fuel type."""
    service = AssetService(db)
    distribution = await service.get_fuel_type_distribution(iso_region=iso_region)
    return {"distribution": distribution}


@router.get("/{asset_id}")
async def get_asset(
    asset_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single asset by ID."""
    service = AssetService(db)
    asset = await service.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetResponse.model_validate(asset)


@router.get("/{asset_id}/details")
async def get_asset_details(
    asset_id: str,
    at_time: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed asset info including current outage status."""
    service = AssetService(db)
    asset = await service.get_by_id(asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Get current outage info
    assets_with_outages = await service.get_with_current_outages(
        iso_region=asset.iso_region,
        at_time=at_time,
        limit=10000,
    )

    # Find this specific asset
    for a in assets_with_outages:
        if a["asset_id"] == asset_id:
            return AssetWithOutage(**a, id=asset.id, created_at=asset.created_at, updated_at=asset.updated_at)

    return AssetResponse.model_validate(asset)
