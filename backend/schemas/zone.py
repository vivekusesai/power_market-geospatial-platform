"""Zone schema definitions."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.zone import ZoneType


class ZoneBase(BaseModel):
    """Base zone fields."""
    zone_id: str = Field(..., max_length=50)
    zone_name: str = Field(..., max_length=255)
    zone_type: ZoneType
    iso_region: str = Field(..., max_length=20)
    parent_zone_id: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = None
    fill_color: Optional[str] = Field(None, max_length=20)
    stroke_color: Optional[str] = Field(None, max_length=20)
    fill_opacity: Optional[float] = Field(0.3, ge=0, le=1)


class ZoneCreate(ZoneBase):
    """Schema for creating a zone."""
    geojson: Optional[Dict[str, Any]] = None  # GeoJSON geometry


class ZoneResponse(ZoneBase):
    """Schema for zone response."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ZoneFeatureProperties(BaseModel):
    """Properties for GeoJSON zone feature."""
    zone_id: str
    zone_name: str
    zone_type: str
    iso_region: str
    fill_color: Optional[str] = None
    stroke_color: Optional[str] = None
    fill_opacity: Optional[float] = 0.3


class ZoneFeature(BaseModel):
    """GeoJSON Feature for a zone."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: ZoneFeatureProperties


class ZoneGeoJSON(BaseModel):
    """GeoJSON FeatureCollection for zones."""
    type: str = "FeatureCollection"
    features: List[ZoneFeature]


class ZoneListResponse(BaseModel):
    """List of zones grouped by type."""
    iso_boundaries: List[ZoneResponse]
    load_zones: List[ZoneResponse]
    transmission_zones: List[ZoneResponse]
    settlement_zones: List[ZoneResponse]
