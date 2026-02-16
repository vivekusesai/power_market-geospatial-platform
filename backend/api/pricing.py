"""Pricing API endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.schemas.common import BoundingBox
from backend.schemas.pricing import (
    PricingHeatmapResponse,
    PricingNodeResponse,
    PricingTimeSeries,
    PricingStats,
)
from backend.services.pricing_service import PricingService

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/nodes")
async def get_pricing_nodes(
    bbox: Optional[str] = Query(
        None, description="Bounding box as 'min_lon,min_lat,max_lon,max_lat'"
    ),
    iso_region: Optional[str] = Query(None),
    node_type: Optional[str] = Query(None, description="hub, zone, generator, load"),
    limit: int = Query(5000, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Get pricing nodes, optionally filtered by bounding box."""
    service = PricingService(db)

    if bbox:
        try:
            bbox_obj = BoundingBox.from_string(bbox)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        nodes = await service.get_nodes_by_bbox(
            bbox=bbox_obj, iso_region=iso_region, limit=limit
        )
    else:
        nodes = await service.get_all_nodes(
            iso_region=iso_region, node_type=node_type, limit=limit
        )

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [n.longitude, n.latitude],
                }
                if n.latitude and n.longitude
                else None,
                "properties": {
                    "node_id": n.node_id,
                    "node_name": n.node_name,
                    "node_type": n.node_type,
                    "iso_region": n.iso_region,
                    "zone": n.zone,
                },
            }
            for n in nodes
        ],
    }


@router.get("/heatmap", response_model=PricingHeatmapResponse)
async def get_lmp_heatmap(
    timestamp: datetime = Query(..., description="Timestamp for LMP data"),
    iso_region: Optional[str] = Query(None),
    market_type: str = Query("DAM", description="DAM or RTM"),
    bbox: Optional[str] = Query(None),
    component: str = Query("total", description="total, energy, congestion, or loss"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get LMP heatmap data for visualization.

    Returns pricing data for all nodes at the specified timestamp,
    suitable for creating heatmap or choropleth visualizations.
    """
    service = PricingService(db)

    bbox_obj = None
    if bbox:
        try:
            bbox_obj = BoundingBox.from_string(bbox)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    return await service.get_heatmap_data(
        timestamp=timestamp,
        iso_region=iso_region,
        market_type=market_type,
        bbox=bbox_obj,
        component=component,
    )


@router.get("/timestamps")
async def get_available_timestamps(
    iso_region: Optional[str] = Query(None),
    market_type: str = Query("DAM"),
    start: Optional[datetime] = Query(None),
    end: Optional[datetime] = Query(None),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get list of available pricing timestamps."""
    service = PricingService(db)
    timestamps = await service.get_available_timestamps(
        iso_region=iso_region,
        market_type=market_type,
        start_time=start,
        end_time=end,
        limit=limit,
    )
    return {"timestamps": [t.isoformat() for t in timestamps]}


@router.get("/stats", response_model=PricingStats)
async def get_pricing_stats(
    timestamp: datetime = Query(...),
    iso_region: Optional[str] = Query(None),
    market_type: str = Query("DAM"),
    db: AsyncSession = Depends(get_db),
):
    """Get pricing statistics for a timestamp."""
    service = PricingService(db)
    return await service.get_stats(
        timestamp=timestamp,
        iso_region=iso_region,
        market_type=market_type,
    )


@router.get("/node/{node_id}", response_model=PricingNodeResponse)
async def get_pricing_node(
    node_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get pricing node details."""
    service = PricingService(db)
    node = await service.get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Pricing node not found")
    return PricingNodeResponse.model_validate(node)


@router.get("/node/{node_id}/timeseries", response_model=PricingTimeSeries)
async def get_node_timeseries(
    node_id: str,
    start: datetime = Query(..., description="Start time"),
    end: datetime = Query(..., description="End time"),
    market_type: str = Query("DAM"),
    db: AsyncSession = Depends(get_db),
):
    """Get LMP time series for a specific node."""
    service = PricingService(db)
    result = await service.get_pricing_time_series(
        node_id=node_id,
        start_time=start,
        end_time=end,
        market_type=market_type,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Pricing node not found")
    return result
