"""Pydantic schemas for Fleet Availability KPIs and Monte Carlo Scenarios."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DowntimeByCauseOut(BaseModel):
    """Breakdown of aircraft-days lost by downtime cause."""

    scheduled_days: int = Field(description="Days lost to scheduled inspections and overhauls")
    unscheduled_days: int = Field(description="Days lost to corrective/unscheduled repairs")
    supply_wait_days: int = Field(description="Days grounded awaiting spare parts delivery")
    agency_wait_days: int = Field(
        description="Days queued awaiting workshop/agency bay availability"
    )
    total_downtime_days: int = Field(description="Total cumulative aircraft downtime days")
    scheduled_pct: float = Field(description="Percentage of downtime due to scheduled maintenance")
    unscheduled_pct: float = Field(description="Percentage of downtime due to unscheduled repairs")
    supply_wait_pct: float = Field(description="Percentage of downtime due to supply chain waiting")
    agency_wait_pct: float = Field(description="Percentage of downtime due to workshop bay queues")


class BacklogOut(BaseModel):
    """Maintenance work orders backlog and outstanding labor."""

    open_orders: int = Field(description="Total count of open or in-progress work orders")
    outstanding_man_hours: float = Field(description="Estimated outstanding labor hours required")


class ComponentTypeKpiOut(BaseModel):
    """Reliability metrics grouped by component type."""

    component_type_id: str
    name: str
    failures: int
    mtbf_spec: float
    calculated_mtbf: float
    mttr_hours: float


class KpiResponse(BaseModel):
    """Comprehensive fleet maintenance and availability KPI response."""

    fleet_availability_pct: float = Field(
        description="Observed fleet availability percentage across the period"
    )
    inherent_availability_pct: float = Field(
        description="Inherent availability Ai = MTBF / (MTBF + MTTR)"
    )
    operational_availability_pct: float = Field(
        description="Operational availability Ao = MTBM / (MTBM + MDT)"
    )
    serviceability_pct: float = Field(
        description="Current snapshot fraction of fleet in Available state"
    )
    downtime_by_cause: DowntimeByCauseOut
    mtbf_hours: float = Field(description="Mean Time Between Failures in flight hours")
    mttr_hours: float = Field(description="Mean Time To Repair in active maintenance hours")
    turnaround_days: float = Field(description="Mean work-order turnaround time in days")
    failure_rate_per_1000_hours: float = Field(
        description="Number of unscheduled failures per 1,000 flight hours"
    )
    backlog: BacklogOut
    readiness_proxy_pct: float = Field(
        description="Decision-support readiness proxy: % available with no open P1/P2 advisory"
    )
    spare_fill_rate_pct: float = Field(
        description="Percentage of spare requests fulfilled without stock-out delay"
    )
    total_aircraft: int
    total_flight_hours: float
    by_component_type: list[ComponentTypeKpiOut] = Field(default_factory=list)


class FleetSummaryOut(BaseModel):
    """Top-level dashboard summary card metrics (§10)."""

    as_of: str
    total_aircraft: int
    serviceable_count: int
    availability_pct: float
    by_state: dict[str, int]
    open_p1: int
    open_p2: int
    backlog: dict[str, Any]
    parts_at_risk: int


class AvailabilityTrendPoint(BaseModel):
    """Single data point in the historical and forecast availability trend."""

    date: str
    avail: float = Field(
        description="Availability percentage (historical actual or forecast median)"
    )
    p10: float | None = Field(default=None, description="P10 lower quantile for forecast")
    p90: float | None = Field(default=None, description="P90 upper quantile for forecast")
    is_forecast: bool = False


class AvailabilityTrendOut(BaseModel):
    """Historical daily availability trend concatenated with forward simulation projection."""

    points: list[AvailabilityTrendPoint]


class ScenarioRunIn(BaseModel):
    """Request payload to execute a what-if Monte Carlo availability scenario."""

    type: str = Field(
        description="Scenario type: schedule_maintenance, spare_unavailable, early_vs_run_to_failure, extra_capacity"
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Scenario-specific parameters (e.g. part_number, lead_time_days, start_day)",
    )
    horizon_days: int = Field(default=30, ge=7, le=180, description="Forward simulation horizon")
    runs: int = Field(default=300, ge=50, le=1000, description="Number of Monte Carlo iterations")
    seed: int = Field(default=42, description="Random seed for reproducible results")


class ScenarioMetricsOut(BaseModel):
    """Availability and loss summary metrics for a scenario leg."""

    availability_p50: float
    availability_p10: float
    availability_p90: float
    aircraft_days_lost: float
    stockout_probability: float = 0.0


class ScenarioDeltaOut(BaseModel):
    """Comparative delta between scenario and baseline."""

    availability_pct_points: float = Field(
        description="Scenario availability minus baseline availability in percentage points"
    )
    aircraft_days_lost: float = Field(
        description="Scenario aircraft-days lost minus baseline aircraft-days lost"
    )


class ScenarioRunOut(BaseModel):
    """Complete response from a what-if scenario run (§10)."""

    id: str
    type: str
    params: dict[str, Any]
    horizon_days: int
    runs: int
    seed: int
    baseline: ScenarioMetricsOut
    scenario: ScenarioMetricsOut
    delta: ScenarioDeltaOut
    by_cause: dict[str, float]
    daily_trend: dict[str, Any] | None = None


class ScenarioHistoryOut(BaseModel):
    """Saved scenario run record from the scenario_runs table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    params: dict[str, Any]
    results: dict[str, Any]
    seed: int
    created_by: str | None = None
    created_at: datetime
