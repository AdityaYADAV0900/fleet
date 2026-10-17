"""Digital Twin hierarchical roll-up engine (§6).

Implements hierarchical roll-up:
Component -> System -> Aircraft -> Fleet

Formulas & Rules:
- System Health Index: Criticality-weighted mean of its components:
  HI_sys = sum(HI_c * crit_c) / sum(crit_c)
- System State: Worst health state among its components.
- System Driver: Component causing the worst state (highest severity, lowest HI, highest risk).
- Aircraft Health Index: Criticality-weighted mean across all components:
  HI_ac = sum(HI_c * crit_c) / sum(crit_c)
- Aircraft State: Worst health state among its critical components (criticality >= 3).
- Aircraft Driver: Critical component that drives the aircraft's degraded/critical state.
- Fleet Health Index: Mean of aircraft health indices.
- Fleet Distribution: Tally of aircraft by state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.twin.state_model import (
    STATE_SEVERITY,
    TwinHealthState,
    get_worst_state,
)


@dataclass
class DriverComponentInfo:
    """Details of the worst-performing component driving higher-level state."""

    component_id: str
    component_name: str
    system_name: str
    criticality: int
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_name": self.component_name,
            "system_name": self.system_name,
            "criticality": self.criticality,
            "health_index": round(self.health_index, 1),
            "state": self.state,
            "risk": round(self.risk, 4) if self.risk is not None else None,
            "rul_p50": round(self.rul_p50, 1) if self.rul_p50 is not None else None,
        }


@dataclass
class ComponentTwinItem:
    """Component level twin state."""

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

    def to_driver_info(self) -> DriverComponentInfo:
        return DriverComponentInfo(
            component_id=self.component_id,
            component_name=self.component_name,
            system_name=self.system_name,
            criticality=self.criticality,
            health_index=self.health_index,
            state=self.state,
            risk=self.risk,
            rul_p50=self.rul_p50,
        )


@dataclass
class SystemTwinItem:
    """System level twin roll-up state."""

    system_id: str
    system_name: str
    aircraft_id: str
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    driver_component: DriverComponentInfo | None = None
    components: list[ComponentTwinItem] = field(default_factory=list)


@dataclass
class AircraftTwinItem:
    """Aircraft level twin roll-up state."""

    aircraft_id: str
    tail_code: str
    type_code: str
    health_index: float
    state: str
    risk: float | None = None
    rul_p50: float | None = None
    driver_component: DriverComponentInfo | None = None
    systems: list[SystemTwinItem] = field(default_factory=list)


@dataclass
class FleetTwinItem:
    """Fleet level twin roll-up state."""

    node_id: str
    health_index: float
    total_aircraft: int
    state_distribution: dict[str, int]
    driver_aircraft_id: str | None = None
    aircraft: list[AircraftTwinItem] = field(default_factory=list)


def select_worst_component(components: list[ComponentTwinItem]) -> ComponentTwinItem | None:
    """Identify the worst-performing component in a set based on state severity, HI, and risk."""
    if not components:
        return None

    def sort_key(c: ComponentTwinItem) -> tuple[int, float, float, float]:
        # Sort key to find worst:
        # 1. State severity (descending)
        # 2. Health index (ascending - lower is worse)
        # 3. Risk (descending - higher is worse)
        # 4. RUL (ascending - lower is worse)
        try:
            state_enum = TwinHealthState(c.state)
            sev = STATE_SEVERITY.get(state_enum, 1)
        except ValueError:
            sev = 1

        risk_val = c.risk if c.risk is not None else 0.0
        rul_val = c.rul_p50 if c.rul_p50 is not None else 999.0
        # For max() we want worse to be greater:
        return (sev, -c.health_index, risk_val, -rul_val)

    return max(components, key=sort_key)


def roll_up_system(
    system_id: str,
    system_name: str,
    aircraft_id: str,
    components: list[ComponentTwinItem],
) -> SystemTwinItem:
    """Calculate criticality-weighted roll-up for a system from its components."""
    if not components:
        return SystemTwinItem(
            system_id=system_id,
            system_name=system_name,
            aircraft_id=aircraft_id,
            health_index=100.0,
            state=TwinHealthState.HEALTHY.value,
            risk=0.0,
            rul_p50=None,
            driver_component=None,
            components=[],
        )

    # Criticality-weighted Health Index
    total_weight = sum(max(1, c.criticality) for c in components)
    weighted_hi_sum = sum(c.health_index * max(1, c.criticality) for c in components)
    system_hi = weighted_hi_sum / total_weight if total_weight > 0 else 100.0

    # System state is worst state among components
    worst_state = get_worst_state([c.state for c in components])

    # Max risk and Min RUL
    risks = [c.risk for c in components if c.risk is not None]
    max_risk = max(risks) if risks else None

    ruls = [c.rul_p50 for c in components if c.rul_p50 is not None]
    min_rul = min(ruls) if ruls else None

    # Driver component
    worst_comp = select_worst_component(components)
    driver_info = worst_comp.to_driver_info() if worst_comp else None

    return SystemTwinItem(
        system_id=system_id,
        system_name=system_name,
        aircraft_id=aircraft_id,
        health_index=round(system_hi, 1),
        state=worst_state.value,
        risk=round(max_risk, 4) if max_risk is not None else None,
        rul_p50=round(min_rul, 1) if min_rul is not None else None,
        driver_component=driver_info,
        components=components,
    )


def roll_up_aircraft(
    aircraft_id: str,
    tail_code: str,
    type_code: str,
    systems: list[SystemTwinItem],
    is_aircraft_under_maintenance: bool = False,
    is_aircraft_failed: bool = False,
) -> AircraftTwinItem:
    """Calculate criticality-weighted roll-up for an aircraft from its systems/components."""
    all_components: list[ComponentTwinItem] = []
    for sys in systems:
        all_components.extend(sys.components)

    if not all_components:
        return AircraftTwinItem(
            aircraft_id=aircraft_id,
            tail_code=tail_code,
            type_code=type_code,
            health_index=100.0,
            state=TwinHealthState.HEALTHY.value,
            risk=0.0,
            rul_p50=None,
            driver_component=None,
            systems=systems,
        )

    # Criticality-weighted Health Index across all aircraft components
    total_weight = sum(max(1, c.criticality) for c in all_components)
    weighted_hi_sum = sum(c.health_index * max(1, c.criticality) for c in all_components)
    ac_hi = weighted_hi_sum / total_weight if total_weight > 0 else 100.0

    # Critical components (criticality >= 3, or all components if none >= 3)
    critical_components = [c for c in all_components if c.criticality >= 3]
    eval_components = critical_components if critical_components else all_components

    # Worst state and driver component among critical components
    worst_comp = select_worst_component(eval_components)
    driver_info = worst_comp.to_driver_info() if worst_comp else None

    if is_aircraft_failed:
        ac_state = TwinHealthState.FAILED.value
    elif is_aircraft_under_maintenance:
        ac_state = TwinHealthState.UNDER_MAINTENANCE.value
    else:
        worst_critical_state = get_worst_state([c.state for c in eval_components])
        ac_state = worst_critical_state.value

    # Max risk and Min RUL among components
    risks = [c.risk for c in all_components if c.risk is not None]
    max_risk = max(risks) if risks else None

    ruls = [c.rul_p50 for c in all_components if c.rul_p50 is not None]
    min_rul = min(ruls) if ruls else None

    return AircraftTwinItem(
        aircraft_id=aircraft_id,
        tail_code=tail_code,
        type_code=type_code,
        health_index=round(ac_hi, 1),
        state=ac_state,
        risk=round(max_risk, 4) if max_risk is not None else None,
        rul_p50=round(min_rul, 1) if min_rul is not None else None,
        driver_component=driver_info,
        systems=systems,
    )


def roll_up_fleet(aircraft_list: list[AircraftTwinItem]) -> FleetTwinItem:
    """Calculate aggregate roll-up for the entire fleet."""
    if not aircraft_list:
        return FleetTwinItem(
            node_id="FLEET",
            health_index=100.0,
            total_aircraft=0,
            state_distribution={s.value: 0 for s in TwinHealthState},
            driver_aircraft_id=None,
            aircraft=[],
        )

    mean_hi = sum(ac.health_index for ac in aircraft_list) / len(aircraft_list)

    dist = {s.value: 0 for s in TwinHealthState}
    for ac in aircraft_list:
        dist[ac.state] = dist.get(ac.state, 0) + 1

    # Find driver aircraft (lowest HI, worst state)
    driver_ac = min(
        aircraft_list,
        key=lambda ac: (
            -STATE_SEVERITY.get(TwinHealthState(ac.state), 1),
            ac.health_index,
        ),
    )

    return FleetTwinItem(
        node_id="FLEET",
        health_index=round(mean_hi, 1),
        total_aircraft=len(aircraft_list),
        state_distribution=dist,
        driver_aircraft_id=driver_ac.aircraft_id if driver_ac else None,
        aircraft=aircraft_list,
    )
