"""Maintenance, work order, and workshop agency schemas."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime

from pydantic import BaseModel


class AgencyOut(BaseModel):
    agency_id: str
    name: str
    level: str
    bays: int
    capacity_hours_per_day: float
    avg_turnaround_days: float

    class Config:
        from_attributes = True


class ScheduledTaskOut(BaseModel):
    task_id: str
    aircraft_id: str
    task_name: str
    interval_hours: float
    last_done_hours: float
    due_hours: float
    due_date: dt_date | None = None

    class Config:
        from_attributes = True


class WorkOrderOut(BaseModel):
    wo_id: str
    aircraft_id: str
    component_id: str | None = None
    advisory_id: str | None = None
    agency_id: str
    opened: datetime
    planned_start: datetime | None = None
    actual_start: datetime | None = None
    promised_done: datetime | None = None
    actual_done: datetime | None = None
    status: str
    priority: str
    delay_reason: str | None = None

    class Config:
        from_attributes = True


class WorkOrderCreateIn(BaseModel):
    aircraft_id: str
    component_id: str | None = None
    advisory_id: str | None = None
    agency_id: str
    priority: str = "P2"
    planned_start: datetime | None = None
    promised_done: datetime | None = None
    bundle_inspection: bool = False
    delay_reason: str | None = None


class MaintenanceEventOut(BaseModel):
    event_id: str
    aircraft_id: str
    component_id: str | None = None
    type: str
    start: datetime
    end: datetime | None = None
    action: str
    labor_hours: float
    work_order_id: str | None = None
    root_cause: str | None = None

    class Config:
        from_attributes = True
