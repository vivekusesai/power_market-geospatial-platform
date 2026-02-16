"""Asset (generator) model definition."""
import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import Enum, Float, Index, Integer, String, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.outage import Outage
    from backend.models.pricing import PricingRecord


class FuelType(str, enum.Enum):
    """Generator fuel types."""
    COAL = "coal"
    NATURAL_GAS = "natural_gas"
    NUCLEAR = "nuclear"
    HYDRO = "hydro"
    WIND = "wind"
    SOLAR = "solar"
    OIL = "oil"
    BIOMASS = "biomass"
    GEOTHERMAL = "geothermal"
    BATTERY = "battery"
    OTHER = "other"


class Asset(Base):
    """Power generation asset (generator unit)."""

    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    asset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    fuel_type: Mapped[FuelType] = mapped_column(
        Enum(FuelType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    capacity_mw: Mapped[float] = mapped_column(Float, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    iso_region: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    owner: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # PostGIS geometry column for spatial queries
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    outages: Mapped[List["Outage"]] = relationship("Outage", back_populates="asset")
    pricing_records: Mapped[List["PricingRecord"]] = relationship(
        "PricingRecord", back_populates="asset"
    )

    # Spatial index
    __table_args__ = (
        Index("idx_assets_geom", "geom", postgresql_using="gist"),
        Index("idx_assets_iso_zone", "iso_region", "zone"),
    )

    def __repr__(self) -> str:
        return f"<Asset(id={self.id}, asset_id={self.asset_id}, name={self.asset_name})>"
