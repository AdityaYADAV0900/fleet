"""Pydantic schemas for Digital Twin hierarchy, roll-up, replay, and what-if simulation (§6)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DriverComponentOut(BaseModel):
    """Details of the worst-performing component driving higher-level state."""

    model_config = ConfigDict(from_attributes=True)

    component_id: str
    component_name: str
    system_name: str
    criticality: int
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None


class TwinTrajectoryPoint(BaseModel):
    """Historical or projected degradation trajectory point."""

    date: str
    health_index: float
    risk: float | None = None
    rul: float | None = None
    is_forecast: bool = False


class TwinMaintenanceEvent(BaseModel):
    """Record of maintenance event or inspection compliance for a twin node."""

    event_id: str | int
    event_type: str
    date: str
    description: str
    status: str


class TwinComponentNodeOut(BaseModel):
    """Component-level twin node in hierarchy."""

    model_config = ConfigDict(from_attributes=True)

    component_id: str
    component_name: str
    part_number: str
    serial_number: str
    system_id: str
    system_name: str
    aircraft_id: str
    criticality: int
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None


class TwinSystemNodeOut(BaseModel):
    """System-level twin roll-up node with constituent components."""

    model_config = ConfigDict(from_attributes=True)

    system_id: str
    system_name: str
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    driver_component: DriverComponentOut | None = None
    components: list[TwinComponentNodeOut] = Field(default_factory=list)


class TwinAircraftNodeOut(BaseModel):
    """Aircraft-level digital twin node with roll-up, trajectory, and replay support."""

    model_config = ConfigDict(from_attributes=True)

    aircraft_id: str
    tail_code: str
    type_code: str
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    as_of_date: str
    is_replay: bool = False
    driver_component: DriverComponentOut | None = None
    systems: list[TwinSystemNodeOut] = Field(default_factory=list)
    maintenance_history: list[TwinMaintenanceEvent] = Field(default_factory=list)
    predicted_trajectory: list[TwinTrajectoryPoint] = Field(default_factory=list)


class TwinFleetSummaryAircraftOut(BaseModel):
    """Summary of an aircraft inside the fleet twin view."""

    model_config = ConfigDict(from_attributes=True)

    aircraft_id: str
    tail_code: str
    type_code: str
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    driver_component: DriverComponentOut | None = None


class TwinFleetOut(BaseModel):
    """Fleet-wide digital twin state and health distribution."""

    model_config = ConfigDict(from_attributes=True)

    node_id: str = "FLEET"
    as_of_date: str
    health_index: float
    total_aircraft: int
    state_distribution: dict[str, int]
    driver_aircraft_id: str | None = None
    aircraft: list[TwinFleetSummaryAircraftOut] = Field(default_factory=list)


class TwinComponentDetailOut(BaseModel):
    """Detailed component digital twin with degradation history and sensor summaries."""

    model_config = ConfigDict(from_attributes=True)

    component_id: str
    component_name: str
    part_number: str
    serial_number: str
    system_id: str
    system_name: str
    aircraft_id: str
    criticality: int
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    as_of_date: str
    is_replay: bool = False
    hours_since_new: float = 0.0
    operating_hours: float = 0.0
    active_advisory: dict[str, Any] | None = None
    recent_sensor_metrics: dict[str, Any] = Field(default_factory=dict)
    maintenance_history: list[TwinMaintenanceEvent] = Field(default_factory=list)
    predicted_trajectory: list[TwinTrajectoryPoint] = Field(default_factory=list)


class TwinWhatIfIn(BaseModel):
    """Request payload for digital twin what-if scenario delegation (§6, §7)."""

    type: str = Field(
        ...,
        description="Scenario type: schedule_maintenance, spare_unavailable, early_vs_run_to_failure, extra_capacity",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Scenario-specific parameters (e.g., aircraft_id, part_number, lead_time_days)",
    )
    horizon_days: int = Field(30, ge=7, le=90, description="Simulation horizon in days")
    runs: int = Field(300, ge=10, le=1000, description="Monte Carlo iterations")
    seed: int = Field(42, description="Pseudorandom seed for reproducible simulation")
