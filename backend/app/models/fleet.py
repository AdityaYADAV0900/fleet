from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class System(Base):
    """Aircraft system hierarchy level (e.g., Propulsion, Hydraulics, Electrical)."""

    __tablename__ = "systems"

    system_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)

    component_types: Mapped[list["ComponentType"]] = relationship(
        "ComponentType", back_populates="system", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<System(id={self.system_id}, name={self.name})>"


class ComponentType(Base):
    """Specification and engineering attributes of a component type."""

    __tablename__ = "component_types"
    __table_args__ = (
        CheckConstraint(
            "criticality >= 1 AND criticality <= 5",
            name="ck_component_types_criticality_range",
        ),
        CheckConstraint(
            "design_life_hours > 0",
            name="ck_component_types_design_life_positive",
        ),
        CheckConstraint(
            "mtbf_hours > 0",
            name="ck_component_types_mtbf_positive",
        ),
    )

    component_type_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    system_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("systems.system_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 (lowest) to 5 (critical)
    design_life_hours: Mapped[float] = mapped_column(Float, nullable=False)
    mtbf_hours: Mapped[float] = mapped_column(Float, nullable=False)
    part_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_repairable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    system: Mapped["System"] = relationship("System", back_populates="component_types")
    components: Mapped[list["Component"]] = relationship("Component", back_populates="component_type")

    def __repr__(self) -> str:
        return f"<ComponentType(id={self.component_type_id}, name={self.name}, criticality={self.criticality})>"


class Aircraft(Base):
    """Individual aircraft entity in the fleet."""

    __tablename__ = "aircraft"
    __table_args__ = (
        CheckConstraint(
            "total_flight_hours >= 0",
            name="ck_aircraft_flight_hours_non_negative",
        ),
        CheckConstraint(
            "total_cycles >= 0",
            name="ck_aircraft_cycles_non_negative",
        ),
    )

    aircraft_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'AC-001'
    tail_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # e.g., 'AC-017'
    type_code: Mapped[str] = mapped_column(String(50), nullable=False)  # Generic type e.g., 'Generic-Twin-Engine-Transport'
    commissioned_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_flight_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    base_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    components: Mapped[list["Component"]] = relationship("Component", back_populates="aircraft")
    daily_statuses: Mapped[list["AircraftDailyStatus"]] = relationship(
        "AircraftDailyStatus", back_populates="aircraft", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Aircraft(id={self.aircraft_id}, tail_code={self.tail_code})>"


class Component(Base):
    """Specific serialized component instance installed on an aircraft or held in reserve."""

    __tablename__ = "components"
    __table_args__ = (
        Index("ix_components_aircraft_id", "aircraft_id"),
        Index("ix_components_component_type_id", "component_type_id"),
        CheckConstraint(
            "hours_at_install >= 0",
            name="ck_components_hours_at_install_non_negative",
        ),
        CheckConstraint(
            "hours_since_new >= 0",
            name="ck_components_hours_since_new_non_negative",
        ),
        CheckConstraint(
            "status IN ('installed', 'in_stock', 'under_repair', 'scrapped')",
            name="ck_components_status_valid",
        ),
    )

    component_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'CMP-001'
    aircraft_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="SET NULL"), nullable=True
    )
    component_type_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("component_types.component_type_id", ondelete="RESTRICT"), nullable=False
    )
    serial_no: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    installed_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    hours_at_install: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    hours_since_new: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="installed", nullable=False)

    aircraft: Mapped[Optional["Aircraft"]] = relationship("Aircraft", back_populates="components")
    component_type: Mapped["ComponentType"] = relationship("ComponentType", back_populates="components")

    def __repr__(self) -> str:
        return f"<Component(id={self.component_id}, serial={self.serial_no}, status={self.status})>"


class AircraftDailyStatus(Base):
    """Daily availability status for each aircraft across time."""

    __tablename__ = "aircraft_daily_status"
    __table_args__ = (
        UniqueConstraint("aircraft_id", "date", name="uq_aircraft_daily_status_aircraft_date"),
        Index("ix_aircraft_daily_status_aircraft_date", "aircraft_id", "date"),
        Index("ix_aircraft_daily_status_date", "date"),
        CheckConstraint(
            "status IN ('Available', 'Scheduled Maintenance', 'Unscheduled Repair', 'Awaiting Spares', 'Awaiting Workshop')",
            name="ck_aircraft_daily_status_enum",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    aircraft: Mapped["Aircraft"] = relationship("Aircraft", back_populates="daily_statuses")

    def __repr__(self) -> str:
        return f"<AircraftDailyStatus(aircraft={self.aircraft_id}, date={self.date}, status={self.status})>"
