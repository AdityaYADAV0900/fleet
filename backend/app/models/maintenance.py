from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
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


class Agency(Base):
    """Internal workshop or external maintenance agency handling work orders."""

    __tablename__ = "agencies"
    __table_args__ = (
        CheckConstraint(
            "level IN ('line', 'base', 'depot')",
            name="ck_agencies_level_valid",
        ),
        CheckConstraint(
            "bays >= 1",
            name="ck_agencies_bays_positive",
        ),
        CheckConstraint(
            "capacity_hours_per_day > 0",
            name="ck_agencies_capacity_positive",
        ),
        CheckConstraint(
            "avg_turnaround_days > 0",
            name="ck_agencies_turnaround_positive",
        ),
    )

    agency_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'AG-LINE-01'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[str] = mapped_column(String(50), nullable=False)  # 'line', 'base', 'depot'
    bays: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity_hours_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    avg_turnaround_days: Mapped[float] = mapped_column(Float, nullable=False)

    work_orders: Mapped[list["WorkOrder"]] = relationship("WorkOrder", back_populates="agency")

    def __repr__(self) -> str:
        return f"<Agency(id={self.agency_id}, name={self.name}, level={self.level})>"


class ScheduledTask(Base):
    """Recurring scheduled maintenance inspection or compliance task for an aircraft."""

    __tablename__ = "scheduled_tasks"
    __table_args__ = (
        CheckConstraint(
            "interval_hours > 0",
            name="ck_scheduled_tasks_interval_positive",
        ),
        CheckConstraint(
            "last_done_hours >= 0",
            name="ck_scheduled_tasks_last_done_non_negative",
        ),
        CheckConstraint(
            "due_hours >= 0",
            name="ck_scheduled_tasks_due_hours_non_negative",
        ),
    )

    task_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'ST-0001'
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    task_name: Mapped[str] = mapped_column(String(100), nullable=False)
    interval_hours: Mapped[float] = mapped_column(Float, nullable=False)
    last_done_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    due_hours: Mapped[float] = mapped_column(Float, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    def __repr__(self) -> str:
        return f"<ScheduledTask(id={self.task_id}, aircraft={self.aircraft_id}, name={self.task_name})>"


class WorkOrder(Base):
    """Maintenance work order assigned to an agency for an aircraft/component."""

    __tablename__ = "work_orders"
    __table_args__ = (
        Index("ix_work_orders_status_agency_id", "status", "agency_id"),
        Index("ix_work_orders_aircraft_id", "aircraft_id"),
        Index("ix_work_orders_advisory_id", "advisory_id"),
        CheckConstraint(
            "status IN ('open', 'in_progress', 'awaiting_spares', 'awaiting_agency', 'completed', 'cancelled')",
            name="ck_work_orders_status_valid",
        ),
        CheckConstraint(
            "priority IN ('P1', 'P2', 'P3', 'P4')",
            name="ck_work_orders_priority_valid",
        ),
    )

    wo_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'WO-0001'
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="SET NULL"), nullable=True
    )
    advisory_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    agency_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("agencies.agency_id", ondelete="RESTRICT"), nullable=False
    )
    opened: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    planned_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    promised_done: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    actual_done: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)
    priority: Mapped[str] = mapped_column(String(10), default="P2", nullable=False)  # P1 - P4
    delay_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    agency: Mapped["Agency"] = relationship("Agency", back_populates="work_orders")
    events: Mapped[list["MaintenanceEvent"]] = relationship("MaintenanceEvent", back_populates="work_order")

    def __repr__(self) -> str:
        return f"<WorkOrder(id={self.wo_id}, aircraft={self.aircraft_id}, status={self.status}, prio={self.priority})>"


class MaintenanceEvent(Base):
    """Actual physical maintenance action performed (replacement, repair, inspection)."""

    __tablename__ = "maintenance_events"
    __table_args__ = (
        Index("ix_maintenance_events_aircraft_start", "aircraft_id", "start"),
        Index("ix_maintenance_events_component_start", "component_id", "start"),
        CheckConstraint(
            "type IN ('scheduled', 'unscheduled', 'inspection')",
            name="ck_maintenance_events_type_valid",
        ),
        CheckConstraint(
            "action IN ('replace', 'repair', 'inspect', 'defer')",
            name="ck_maintenance_events_action_valid",
        ),
        CheckConstraint(
            "labor_hours >= 0",
            name="ck_maintenance_events_labor_hours_non_negative",
        ),
        CheckConstraint(
            '"end" IS NULL OR "end" >= "start"',
            name="ck_maintenance_events_end_after_start",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'ME-0001'
    aircraft_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=False
    )
    component_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="SET NULL"), nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduled, unscheduled, inspection
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # replace, repair, inspect, defer
    labor_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("work_orders.wo_id", ondelete="SET NULL"), nullable=True
    )
    root_cause: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    work_order: Mapped[Optional["WorkOrder"]] = relationship("WorkOrder", back_populates="events")

    def __repr__(self) -> str:
        return f"<MaintenanceEvent(id={self.event_id}, type={self.type}, action={self.action})>"
