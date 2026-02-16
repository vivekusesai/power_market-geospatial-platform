"""Asset schema definitions."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.asset import FuelType


class AssetBase(BaseModel):
    """Base asset fields."""
    asset_id: str = Field(..., max_length=50)
    asset_name: str = Field(..., max_length=255)
    fuel_type: FuelType
    capacity_mw: float = Field(..., gt=0)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    iso_region: str = Field(..., max_length=20)
    zone: Optional[str] = Field(None, max_length=50)
    owner: Optional[str] = Field(None, max_length=255)


class AssetCreate(AssetBase):
    """Schema for creating an asset."""
    pass


class AssetResponse(AssetBase):
    """Schema for asset response."""
    id: int
    created_at: datetime
    updated_at: datetime
    current_status: Optional[str] = None  # Computed from active outages

    model_config = {"from_attributes": True}


class AssetWithOutage(AssetResponse):
    """Asset with current outage information."""
    outage_type: Optional[str] = None
    outage_status: Optional[str] = None
    outage_start: Optional[datetime] = None
    outage_end: Optional[datetime] = None
    cause_code: Optional[str] = None
    capacity_reduction_mw: Optional[float] = None


class AssetFeatureProperties(BaseModel):
    """Properties for GeoJSON asset feature."""
    asset_id: str
    asset_name: str
    fuel_type: str
    capacity_mw: float
    iso_region: str
    zone: Optional[str] = None
    owner: Optional[str] = None
    status: str = "available"
    outage_type: Optional[str] = None


class AssetFeature(BaseModel):
    """GeoJSON Feature for an asset."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: AssetFeatureProperties


class AssetGeoJSON(BaseModel):
    """GeoJSON FeatureCollection for assets."""
    type: str = "FeatureCollection"
    features: List[AssetFeature]
