"""Outage schema definitions."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from backend.models.outage import OutageStatus, OutageType


class OutageBase(BaseModel):
    """Base outage fields."""
    outage_id: str = Field(..., max_length=50)
    asset_id: str = Field(..., max_length=50)
    outage_type: OutageType
    start_time: datetime
    end_time: Optional[datetime] = None
    status: OutageStatus = OutageStatus.ACTIVE
    cause_code: Optional[str] = Field(None, max_length=50)
    cause_description: Optional[str] = None
    capacity_reduction_mw: Optional[float] = None


class OutageCreate(OutageBase):
    """Schema for creating an outage."""
    pass


class OutageResponse(OutageBase):
    """Schema for outage response."""
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutageWithAsset(OutageResponse):
    """Outage with related asset information."""
    asset_name: str
    fuel_type: str
    capacity_mw: float
    latitude: float
    longitude: float
    iso_region: str
    zone: Optional[str] = None


class OutageFeatureProperties(BaseModel):
    """Properties for GeoJSON outage feature."""
    outage_id: str
    asset_id: str
    asset_name: str
    outage_type: str
    status: str
    start_time: str
    end_time: Optional[str] = None
    cause_code: Optional[str] = None
    capacity_reduction_mw: Optional[float] = None
    fuel_type: str
    capacity_mw: float


class OutageFeature(BaseModel):
    """GeoJSON Feature for an outage."""
    type: str = "Feature"
    geometry: Dict[str, Any]
    properties: OutageFeatureProperties


class OutageGeoJSON(BaseModel):
    """GeoJSON FeatureCollection for outages."""
    type: str = "FeatureCollection"
    features: List[OutageFeature]


class OutageStats(BaseModel):
    """Outage statistics summary."""
    total_outages: int
    forced_outages: int
    planned_outages: int
    maintenance_outages: int
    derates: int
    total_capacity_offline_mw: float
