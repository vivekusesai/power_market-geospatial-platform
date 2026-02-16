"""Pricing (LMP) model definitions."""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.asset import Asset


class PricingNode(Base):
    """Pricing node (pnode) for LMP data."""

    __tablename__ = "pricing_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    node_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    node_name: Mapped[str] = mapped_column(String(255), nullable=False)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # hub, zone, generator, load
    iso_region: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    zone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # PostGIS geometry column
    geom: Mapped[Optional[str]] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    pricing_records: Mapped[List["PricingRecord"]] = relationship(
        "PricingRecord", back_populates="node", foreign_keys="PricingRecord.node_id"
    )

    __table_args__ = (
        Index("idx_pricing_nodes_geom", "geom", postgresql_using="gist"),
    )

    def __repr__(self) -> str:
        return f"<PricingNode(id={self.id}, node_id={self.node_id})>"


class PricingRecord(Base):
    """LMP pricing record for a specific timestamp."""

    __tablename__ = "pricing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Can be associated with either a pricing node or directly with an asset
    node_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("pricing_nodes.node_id", ondelete="CASCADE"), nullable=True
    )
    asset_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # LMP components
    lmp_total: Mapped[float] = mapped_column(Float, nullable=False)
    lmp_energy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lmp_congestion: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lmp_loss: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Metadata
    iso_region: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    market_type: Mapped[str] = mapped_column(String(20), nullable=False, default="DAM")  # DAM, RTM

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    node: Mapped[Optional["PricingNode"]] = relationship(
        "PricingNode", back_populates="pricing_records"
    )
    asset: Mapped[Optional["Asset"]] = relationship("Asset", back_populates="pricing_records")

    # Indexes for time series queries (BRIN for large time series)
    __table_args__ = (
        Index("idx_pricing_node_time", "node_id", "timestamp"),
        Index("idx_pricing_asset_time", "asset_id", "timestamp"),
        Index("idx_pricing_timestamp", "timestamp"),
        Index("idx_pricing_timestamp_brin", "timestamp", postgresql_using="brin"),
    )

    def __repr__(self) -> str:
        return f"<PricingRecord(id={self.id}, node={self.node_id}, time={self.timestamp})>"
