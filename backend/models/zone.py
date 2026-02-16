"""Zone and boundary model definitions."""
import enum
from datetime import datetime
from typing import Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class ZoneType(str, enum.Enum):
    """Types of market zones."""
    ISO_BOUNDARY = "iso_boundary"
    LOAD_ZONE = "load_zone"
    TRANSMISSION_ZONE = "transmission_zone"
    SETTLEMENT_ZONE = "settlement_zone"
    PRICING_ZONE = "pricing_zone"
    RESERVE_ZONE = "reserve_zone"


class Zone(Base):
    """Geographic zone or boundary (ISO, load zone, transmission zone, etc.)."""

    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    zone_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    zone_name: Mapped[str] = mapped_column(String(255), nullable=False)
    zone_type: Mapped[ZoneType] = mapped_column(Enum(ZoneType), nullable=False, index=True)
    iso_region: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    parent_zone_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # PostGIS geometry column for polygon boundaries
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=True,
    )

    # Visual styling
    fill_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    stroke_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    fill_opacity: Mapped[Optional[float]] = mapped_column(nullable=True, default=0.3)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Spatial index
    __table_args__ = (
        Index("idx_zones_geom", "geom", postgresql_using="gist"),
        Index("idx_zones_iso_type", "iso_region", "zone_type"),
    )

    def __repr__(self) -> str:
        return f"<Zone(id={self.id}, zone_id={self.zone_id}, type={self.zone_type})>"
