from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Flight(Base):
    """Sortie or flight record representing an operational mission for an aircraft."""

    __tablename__ = "flights"
    __table_args__ = (
        Index("ix_flights_aircraft_id_date", "aircraft_id", "date"),
        CheckConstraint(
            "duration_hours > 0",
            name="ck_flights_duration_positive",
        ),
        CheckConstraint(
            "cycles >= 0",
            name="ck_flights_cycles_non_negative",
        ),
        CheckConstraint(
            "load_factor IS NULL OR load_factor >= 0",
            name="ck_flights_load_factor_non_negative",
        ),
    )

    flight_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'FL-00001'
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    cycles: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ambient_temp_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    altitude_band: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    load_factor: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    readings: Mapped[list["SensorReading"]] = relationship(
        "SensorReading", back_populates="flight", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Flight(id={self.flight_id}, aircraft={self.aircraft_id}, date={self.date})>"


class SensorReading(Base):
    """Post-flight aggregate sensor summary for a monitored component parameter."""

    __tablename__ = "sensor_readings"
    __table_args__ = (
        Index("ix_sensor_readings_component_id_flight_id", "component_id", "flight_id"),
        Index("ix_sensor_readings_flight_id", "flight_id"),
        CheckConstraint(
            "quality_flag IN ('valid', 'dropout', 'stuck', 'drift', 'spike', 'missing')",
            name="ck_sensor_readings_quality_flag_valid",
        ),
    )

    reading_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    flight_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("flights.flight_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    parameter: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'vibration', 'pressure', 'temp'
    mean: Mapped[float] = mapped_column(Float, nullable=False)
    max: Mapped[float] = mapped_column(Float, nullable=False)
    min: Mapped[float] = mapped_column(Float, nullable=False)
    std: Mapped[float] = mapped_column(Float, nullable=False)
    quality_flag: Mapped[str] = mapped_column(String(20), default="valid", nullable=False)

    flight: Mapped["Flight"] = relationship("Flight", back_populates="readings")

    def __repr__(self) -> str:
        return f"<SensorReading(id={self.reading_id}, comp={self.component_id}, param={self.parameter})>"


class FaultEvent(Base):
    """Recorded fault, exceedance, or Built-In-Test (BIT) message."""

    __tablename__ = "fault_events"
    __table_args__ = (
        Index("ix_fault_events_aircraft_timestamp", "aircraft_id", "timestamp"),
        Index("ix_fault_events_component_timestamp", "component_id", "timestamp"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_fault_events_severity_valid",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'EVT-00001'
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fault_code: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="BIT", nullable=False)

    def __repr__(self) -> str:
        return f"<FaultEvent(id={self.event_id}, code={self.fault_code}, sev={self.severity})>"
