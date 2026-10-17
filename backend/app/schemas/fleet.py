"""Fleet, aircraft, systems, and components schemas."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime

from pydantic import BaseModel, Field


class SystemOut(BaseModel):
    system_id: str
    name: str

    class Config:
        from_attributes = True


class ComponentTypeOut(BaseModel):
    component_type_id: str
    system_id: str
    name: str
    criticality: int
    design_life_hours: float
    mtbf_hours: float
    part_number: str
    is_repairable: bool

    class Config:
        from_attributes = True


class ComponentOut(BaseModel):
    component_id: str
    aircraft_id: str | None = None
    component_type_id: str
    serial_no: str
    installed_date: dt_date | None = None
    hours_at_install: float
    hours_since_new: float
    status: str

    class Config:
        from_attributes = True


class AircraftDailyStatusOut(BaseModel):
    id: int
    aircraft_id: str
    date: dt_date
    status: str
    reason: str | None = None
    recorded_at: datetime

    class Config:
        from_attributes = True


class AircraftListOut(BaseModel):
    aircraft_id: str
    tail_code: str
    type_code: str
    commissioned_date: dt_date
    total_flight_hours: float
    total_cycles: int
    base_id: str | None = None
    current_status: str = Field(default="Available", description="Latest availability state")

    class Config:
        from_attributes = True


class AircraftDetailOut(BaseModel):
    aircraft_id: str
    tail_code: str
    type_code: str
    commissioned_date: dt_date
    total_flight_hours: float
    total_cycles: int
    base_id: str | None = None
    current_status: str
    components_count: int
    systems: list[SystemOut]
    installed_components: list[ComponentOut]

    class Config:
        from_attributes = True
