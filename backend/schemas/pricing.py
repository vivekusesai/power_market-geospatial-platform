"""Pricing schema definitions."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PricingNodeBase(BaseModel):
    """Base pricing node fields."""
    node_id: str = Field(..., max_length=50)
    node_name: str = Field(..., max_length=255)
    node_type: str = Field(..., max_length=50)
    iso_region: str = Field(..., max_length=20)
    zone: Optional[str] = Field(None, max_length=50)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class PricingNodeCreate(PricingNodeBase):
    """Schema for creating a pricing node."""
    pass


class PricingNodeResponse(PricingNodeBase):
    """Schema for pricing node response."""
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PricingRecordBase(BaseModel):
    """Base pricing record fields."""
    node_id: Optional[str] = Field(None, max_length=50)
    asset_id: Optional[str] = Field(None, max_length=50)
    timestamp: datetime
    lmp_total: float
    lmp_energy: Optional[float] = None
    lmp_congestion: Optional[float] = None
    lmp_loss: Optional[float] = None
    iso_region: str = Field(..., max_length=20)
    market_type: str = Field("DAM", max_length=20)


class PricingRecordCreate(PricingRecordBase):
    """Schema for creating a pricing record."""
    pass


class PricingRecordResponse(PricingRecordBase):
    """Schema for pricing record response."""
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class PricingTimeSeries(BaseModel):
    """Time series of pricing data for a node."""
    node_id: str
    node_name: str
    iso_region: str
    data: List[Dict[str, Any]]  # List of {timestamp, lmp_total, lmp_energy, lmp_congestion, lmp_loss}


class PricingHeatmapPoint(BaseModel):
    """Point for LMP heatmap visualization."""
    node_id: str
    latitude: float
    longitude: float
    lmp_total: float
    lmp_energy: Optional[float] = None
    lmp_congestion: Optional[float] = None
    lmp_loss: Optional[float] = None
    timestamp: datetime


class PricingHeatmapResponse(BaseModel):
    """Response for LMP heatmap data."""
    timestamp: datetime
    iso_region: str
    market_type: str
    min_lmp: float
    max_lmp: float
    avg_lmp: float
    points: List[PricingHeatmapPoint]


class PricingStats(BaseModel):
    """Pricing statistics summary."""
    iso_region: str
    timestamp: datetime
    min_lmp: float
    max_lmp: float
    avg_lmp: float
    std_lmp: float
    congestion_count: int  # Number of nodes with significant congestion
