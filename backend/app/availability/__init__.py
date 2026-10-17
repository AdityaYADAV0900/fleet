"""Fleet availability, reliability metrics, and Monte Carlo scenario simulation."""

from app.availability.kpis import (
    calculate_backlog,
    calculate_downtime_by_cause,
    calculate_failure_rate,
    calculate_fleet_availability,
    calculate_inherent_availability,
    calculate_mtbf,
    calculate_mttr,
    calculate_operational_availability,
    calculate_readiness_proxy,
    calculate_serviceability,
    calculate_spare_fill_rate,
    calculate_turnaround,
    fetch_fleet_kpis,
    fetch_fleet_summary,
)
from app.availability.scenarios import (
    ScenarioEngine,
    build_simulation_config_from_db,
    list_scenario_runs,
    save_scenario_run,
)
from app.availability.simulator import (
    AircraftSimState,
    FleetSimulator,
    ScheduledMaintenanceTask,
    SimulationConfig,
    SimulationResult,
    SpareSimConfig,
    create_default_simulation_config,
)

__all__ = [
    # KPIs
    "calculate_fleet_availability",
    "calculate_inherent_availability",
    "calculate_operational_availability",
    "calculate_serviceability",
    "calculate_downtime_by_cause",
    "calculate_mtbf",
    "calculate_mttr",
    "calculate_turnaround",
    "calculate_failure_rate",
    "calculate_backlog",
    "calculate_readiness_proxy",
    "calculate_spare_fill_rate",
    "fetch_fleet_kpis",
    "fetch_fleet_summary",
    # Simulator
    "FleetSimulator",
    "AircraftSimState",
    "SpareSimConfig",
    "ScheduledMaintenanceTask",
    "SimulationConfig",
    "SimulationResult",
    "create_default_simulation_config",
    # Scenarios
    "ScenarioEngine",
    "build_simulation_config_from_db",
    "save_scenario_run",
    "list_scenario_runs",
]
