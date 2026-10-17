"""Digital Twin package (§6).

Contains health state models, hierarchical roll-up engine,
snapshots persistence, and digital twin service.
"""

from app.twin.rollup import (
    AircraftTwinItem,
    ComponentTwinItem,
    DriverComponentInfo,
    FleetTwinItem,
    SystemTwinItem,
    roll_up_aircraft,
    roll_up_fleet,
    roll_up_system,
    select_worst_component,
)
from app.twin.service import (
    execute_twin_whatif,
    get_aircraft_twin,
    get_component_twin,
    get_fleet_twin,
)
from app.twin.snapshots import build_twin_hierarchy, write_twin_snapshots
from app.twin.state_model import (
    DEFAULT_THRESHOLDS,
    STATE_SEVERITY,
    TwinHealthState,
    TwinThresholdsConfig,
    determine_health_state,
    get_worst_state,
    validate_state_transition,
)

__all__ = [
    "TwinHealthState",
    "TwinThresholdsConfig",
    "DEFAULT_THRESHOLDS",
    "STATE_SEVERITY",
    "determine_health_state",
    "validate_state_transition",
    "get_worst_state",
    "DriverComponentInfo",
    "ComponentTwinItem",
    "SystemTwinItem",
    "AircraftTwinItem",
    "FleetTwinItem",
    "select_worst_component",
    "roll_up_system",
    "roll_up_aircraft",
    "roll_up_fleet",
    "build_twin_hierarchy",
    "write_twin_snapshots",
    "get_fleet_twin",
    "get_aircraft_twin",
    "get_component_twin",
    "execute_twin_whatif",
]
