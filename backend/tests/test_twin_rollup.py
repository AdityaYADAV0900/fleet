"""Unit tests for digital twin hierarchical roll-up engine (§6)."""

from app.twin.rollup import (
    AircraftTwinItem,
    ComponentTwinItem,
    roll_up_aircraft,
    roll_up_fleet,
    roll_up_system,
    select_worst_component,
)
from app.twin.state_model import TwinHealthState


def test_system_roll_up_criticality_weighted_hi():
    """Verify system health index is weighted by component criticality."""
    # System with 3 components:
    # Comp 1: HI=90, Crit=5 (Weight=5) -> 450
    # Comp 2: HI=60, Crit=3 (Weight=3) -> 180
    # Comp 3: HI=50, Crit=2 (Weight=2) -> 100
    # Total Weight = 10, Total Weighted HI = 730 -> Expected System HI = 73.0
    c1 = ComponentTwinItem(
        component_id="CMP-1",
        component_name="Pump",
        part_number="P-1",
        serial_number="SN-1",
        system_id="SYS-HYD",
        system_name="Hydraulics",
        aircraft_id="AC-001",
        criticality=5,
        health_index=90.0,
        state=TwinHealthState.HEALTHY.value,
        risk=0.05,
        rul_p50=50.0,
    )
    c2 = ComponentTwinItem(
        component_id="CMP-2",
        component_name="Valve",
        part_number="P-2",
        serial_number="SN-2",
        system_id="SYS-HYD",
        system_name="Hydraulics",
        aircraft_id="AC-001",
        criticality=3,
        health_index=60.0,
        state=TwinHealthState.WATCH.value,
        risk=0.25,
        rul_p50=30.0,
    )
    c3 = ComponentTwinItem(
        component_id="CMP-3",
        component_name="Sensor",
        part_number="P-3",
        serial_number="SN-3",
        system_id="SYS-HYD",
        system_name="Hydraulics",
        aircraft_id="AC-001",
        criticality=2,
        health_index=50.0,
        state=TwinHealthState.DEGRADED.value,
        risk=0.45,
        rul_p50=15.0,
    )

    sys_res = roll_up_system(
        system_id="SYS-HYD",
        system_name="Hydraulics",
        aircraft_id="AC-001",
        components=[c1, c2, c3],
    )

    assert sys_res.health_index == 73.0
    # Worst state is Degraded from CMP-3
    assert sys_res.state == TwinHealthState.DEGRADED.value
    assert sys_res.risk == 0.45
    assert sys_res.rul_p50 == 15.0
    assert sys_res.driver_component is not None
    assert sys_res.driver_component.component_id == "CMP-3"


def test_select_worst_component_tie_breaking():
    """Verify worst-component driver selection uses state severity, then HI, then risk."""
    # Both in Degraded state, but CMP-B has lower HI
    c_a = ComponentTwinItem(
        component_id="CMP-A",
        component_name="Actuator A",
        part_number="P-A",
        serial_number="SN-A",
        system_id="SYS-FLT",
        system_name="Flight Controls",
        aircraft_id="AC-001",
        criticality=4,
        health_index=55.0,
        state=TwinHealthState.DEGRADED.value,
        risk=0.30,
        rul_p50=25.0,
    )
    c_b = ComponentTwinItem(
        component_id="CMP-B",
        component_name="Actuator B",
        part_number="P-B",
        serial_number="SN-B",
        system_id="SYS-FLT",
        system_name="Flight Controls",
        aircraft_id="AC-001",
        criticality=4,
        health_index=42.0,
        state=TwinHealthState.DEGRADED.value,
        risk=0.55,
        rul_p50=12.0,
    )

    worst = select_worst_component([c_a, c_b])
    assert worst is not None
    assert worst.component_id == "CMP-B"


def test_aircraft_roll_up_critical_component_driver():
    """Verify aircraft state is driven by the worst critical component (criticality >= 3)."""
    # Non-critical component (crit 1) is Failed, but critical components (crit >= 3) are Healthy
    c_non_crit = ComponentTwinItem(
        component_id="CMP-BULB",
        component_name="Cabin Reading Light",
        part_number="P-LIGHT",
        serial_number="SN-LIGHT",
        system_id="SYS-ELEC",
        system_name="Electrical",
        aircraft_id="AC-001",
        criticality=1,
        health_index=0.0,
        state=TwinHealthState.FAILED.value,
        risk=0.0,
        rul_p50=0.0,
    )
    c_crit = ComponentTwinItem(
        component_id="CMP-GEN",
        component_name="Main Generator",
        part_number="P-GEN",
        serial_number="SN-GEN",
        system_id="SYS-ELEC",
        system_name="Electrical",
        aircraft_id="AC-001",
        criticality=5,
        health_index=95.0,
        state=TwinHealthState.HEALTHY.value,
        risk=0.02,
        rul_p50=90.0,
    )

    sys_elec = roll_up_system(
        system_id="SYS-ELEC",
        system_name="Electrical",
        aircraft_id="AC-001",
        components=[c_non_crit, c_crit],
    )

    ac_res = roll_up_aircraft(
        aircraft_id="AC-001",
        tail_code="AC-001",
        type_code="Transport",
        systems=[sys_elec],
    )

    # Aircraft state evaluates critical components (criticality >= 3)
    # Since CMP-GEN is Healthy, aircraft is Healthy despite non-critical light bulb failure
    assert ac_res.state == TwinHealthState.HEALTHY.value
    assert ac_res.driver_component is not None
    assert ac_res.driver_component.component_id == "CMP-GEN"


def test_aircraft_roll_up_degraded_critical_driver():
    """Verify aircraft state reflects degraded critical component."""
    c_pump = ComponentTwinItem(
        component_id="CMP-HYD-PUMP",
        component_name="Primary Hydraulic Pump",
        part_number="HYD-114",
        serial_number="SN-PUMP-17",
        system_id="SYS-HYD",
        system_name="Hydraulics",
        aircraft_id="AC-017",
        criticality=5,
        health_index=45.8,
        state=TwinHealthState.DEGRADED.value,
        risk=0.62,
        rul_p50=12.0,
    )
    c_eng = ComponentTwinItem(
        component_id="CMP-ENG",
        component_name="Engine Compressor",
        part_number="ENG-772",
        serial_number="SN-ENG-17",
        system_id="SYS-PROP",
        system_name="Propulsion",
        aircraft_id="AC-017",
        criticality=5,
        health_index=90.0,
        state=TwinHealthState.HEALTHY.value,
        risk=0.08,
        rul_p50=80.0,
    )

    sys_hyd = roll_up_system("SYS-HYD", "Hydraulics", "AC-017", [c_pump])
    sys_prop = roll_up_system("SYS-PROP", "Propulsion", "AC-017", [c_eng])

    ac_res = roll_up_aircraft(
        aircraft_id="AC-017",
        tail_code="AC-017",
        type_code="Transport",
        systems=[sys_hyd, sys_prop],
    )

    assert ac_res.state == TwinHealthState.DEGRADED.value
    assert ac_res.driver_component is not None
    assert ac_res.driver_component.component_id == "CMP-HYD-PUMP"
    assert ac_res.driver_component.component_name == "Primary Hydraulic Pump"
    assert ac_res.risk == 0.62
    assert ac_res.rul_p50 == 12.0


def test_fleet_roll_up():
    """Verify fleet roll-up aggregates mean health index and state tallies."""
    ac1 = AircraftTwinItem(
        aircraft_id="AC-001",
        tail_code="AC-001",
        type_code="Transport",
        health_index=90.0,
        state=TwinHealthState.HEALTHY.value,
    )
    ac2 = AircraftTwinItem(
        aircraft_id="AC-002",
        tail_code="AC-002",
        type_code="Transport",
        health_index=70.0,
        state=TwinHealthState.WATCH.value,
    )
    ac3 = AircraftTwinItem(
        aircraft_id="AC-003",
        tail_code="AC-003",
        type_code="Transport",
        health_index=45.0,
        state=TwinHealthState.DEGRADED.value,
    )

    fleet = roll_up_fleet([ac1, ac2, ac3])

    assert fleet.total_aircraft == 3
    # Mean of 90, 70, 45 = 205 / 3 = 68.3
    assert fleet.health_index == 68.3
    assert fleet.state_distribution[TwinHealthState.HEALTHY.value] == 1
    assert fleet.state_distribution[TwinHealthState.WATCH.value] == 1
    assert fleet.state_distribution[TwinHealthState.DEGRADED.value] == 1
    assert fleet.driver_aircraft_id == "AC-003"
