"""Common schema definitions."""
from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """Geographic bounding box for spatial queries."""
    min_lon: float = Field(..., ge=-180, le=180, description="Minimum longitude (west)")
    min_lat: float = Field(..., ge=-90, le=90, description="Minimum latitude (south)")
    max_lon: float = Field(..., ge=-180, le=180, description="Maximum longitude (east)")
    max_lat: float = Field(..., ge=-90, le=90, description="Maximum latitude (north)")

    @classmethod
    def from_string(cls, bbox_str: str) -> "BoundingBox":
        """Parse bbox from comma-separated string: 'min_lon,min_lat,max_lon,max_lat'"""
        parts = [float(x.strip()) for x in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("Bounding box must have exactly 4 values")
        return cls(min_lon=parts[0], min_lat=parts[1], max_lon=parts[2], max_lat=parts[3])


class TimeRange(BaseModel):
    """Time range for temporal queries."""
    start: datetime
    end: datetime


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int


class GeoJSONFeatureCollection(BaseModel):
    """GeoJSON FeatureCollection structure."""
    type: str = "FeatureCollection"
    features: List[dict]


class MapConfig(BaseModel):
    """Map configuration response."""
    center_lat: float
    center_lon: float
    zoom: int
    iso_regions: List[str]
