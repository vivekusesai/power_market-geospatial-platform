"""Outage API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.outage import OutageStatus, OutageType
from backend.schemas.outage import OutageGeoJSON, OutageResponse, OutageStats
from backend.services.outage_service import OutageService

router = APIRouter(prefix="/outages", tags=["outages"])


@router.get("", response_model=OutageGeoJSON)
async def get_outages(
    start: Optional[datetime] = Query(
        None, description="Start time filter (ISO format)"
    ),
    end: Optional[datetime] = Query(None, description="End time filter (ISO format)"),
    iso_region: Optional[str] = Query(None, description="Filter by ISO region"),
    outage_type: Optional[OutageType] = Query(None, description="Filter by outage type"),
    status: Optional[OutageStatus] = Query(None, description="Filter by status"),
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """
    Get outages as GeoJSON.

    Returns outages that overlap with the specified time range.
    Each outage includes location from the associated asset.
    """
    service = OutageService(db)
    outages = await service.get_all(
        start_time=start,
        end_time=end,
        iso_region=iso_region,
        outage_type=outage_type,
        status=status,
        limit=limit,
    )
    return await service.to_geojson(outages)


@router.get("/active")
async def get_active_outages(
    at_time: Optional[datetime] = Query(
        None, description="Point in time (defaults to now)"
    ),
    iso_region: Optional[str] = Query(None),
    limit: int = Query(1000, le=5000),
    db: AsyncSession = Depends(get_db),
):
    """Get outages active at a specific point in time."""
    service = OutageService(db)
    if at_time is None:
        at_time = datetime.utcnow()

    outages = await service.get_active_at_time(
        at_time=at_time,
        iso_region=iso_region,
        limit=limit,
    )
    return await service.to_geojson(outages)


@router.get("/stats", response_model=OutageStats)
async def get_outage_stats(
    at_time: Optional[datetime] = Query(None),
    iso_region: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get outage statistics summary."""
    service = OutageService(db)
    return await service.get_stats(at_time=at_time, iso_region=iso_region)


@router.get("/timeline")
async def get_outage_timeline(
    start: datetime = Query(..., description="Start time"),
    end: datetime = Query(..., description="End time"),
    iso_region: Optional[str] = Query(None),
    interval_hours: int = Query(1, ge=1, le=24, description="Aggregation interval"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get outage counts over time for timeline visualization.

    Returns hourly (or custom interval) counts of active outages.
    """
    service = OutageService(db)
    from datetime import timedelta

    timeline = []
    current = start
    while current <= end:
        stats = await service.get_stats(at_time=current, iso_region=iso_region)
        timeline.append({
            "timestamp": current.isoformat(),
            "total_outages": stats.total_outages,
            "forced_outages": stats.forced_outages,
            "planned_outages": stats.planned_outages,
            "capacity_offline_mw": stats.total_capacity_offline_mw,
        })
        current += timedelta(hours=interval_hours)

    return {"timeline": timeline, "interval_hours": interval_hours}


@router.get("/{outage_id}", response_model=OutageResponse)
async def get_outage(
    outage_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a single outage by ID."""
    service = OutageService(db)
    outage = await service.get_by_id(outage_id)
    if not outage:
        raise HTTPException(status_code=404, detail="Outage not found")
    return OutageResponse.model_validate(outage)


@router.get("/asset/{asset_id}")
async def get_outages_for_asset(
    asset_id: str,
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(100),
    db: AsyncSession = Depends(get_db),
):
    """Get outage history for a specific asset."""
    service = OutageService(db)
    outages = await service.get_by_asset(
        asset_id=asset_id,
        start_time=start,
        end_time=end,
        limit=limit,
    )
    return {"outages": [OutageResponse.model_validate(o) for o in outages]}
