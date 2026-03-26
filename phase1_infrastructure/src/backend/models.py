"""
Database Models & Schema
=========================
Defines the TimescaleDB hypertable schema for storing processed
emission sensor readings.  Uses SQLAlchemy 2.0 declarative style.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Float,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EmissionReading(Base):
    """
    Core hypertable: one row per 15-second sensor reading per facility.
    """
    __tablename__ = "emission_readings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    facility_id: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    co2_ppm: Mapped[float] = mapped_column(Float, nullable=False)
    ch4_ppm: Mapped[float] = mapped_column(Float, nullable=False)
    nox_ppb: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_rate: Mapped[float] = mapped_column(Float, nullable=False)
    energy_kwh: Mapped[float] = mapped_column(Float, nullable=False)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("idx_facility_time", "facility_id", "timestamp_utc"),
    )

    def __repr__(self):
        return (
            f"<EmissionReading fac={self.facility_id} "
            f"ts={self.timestamp_utc} co2={self.co2_ppm}>"
        )


class FacilityProfile(Base):
    """Registry of monitored industrial facilities."""
    __tablename__ = "facility_profiles"

    facility_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    facility_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<Facility {self.facility_id} type={self.facility_type}>"
