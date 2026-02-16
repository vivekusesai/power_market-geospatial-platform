"""Outage model definition."""
import enum
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.asset import Asset


class OutageType(str, enum.Enum):
    """Types of generator outages."""
    PLANNED = "planned"
    FORCED = "forced"
    MAINTENANCE = "maintenance"
    DERATE = "derate"


class OutageStatus(str, enum.Enum):
    """Current status of outage."""
    ACTIVE = "active"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Outage(Base):
    """Generator outage record."""

    __tablename__ = "outages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outage_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    asset_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("assets.asset_id", ondelete="CASCADE"), nullable=False
    )
    outage_type: Mapped[OutageType] = mapped_column(
        Enum(OutageType, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True
    )
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[OutageStatus] = mapped_column(
        Enum(OutageStatus, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OutageStatus.ACTIVE,
        index=True
    )
    cause_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    cause_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    capacity_reduction_mw: Mapped[Optional[float]] = mapped_column(nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="outages")

    # Indexes for time range queries
    __table_args__ = (
        Index("idx_outages_time_range", "start_time", "end_time"),
        Index("idx_outages_asset_time", "asset_id", "start_time"),
        Index("idx_outages_status_time", "status", "start_time"),
    )

    def __repr__(self) -> str:
        return f"<Outage(id={self.id}, outage_id={self.outage_id}, type={self.outage_type})>"
