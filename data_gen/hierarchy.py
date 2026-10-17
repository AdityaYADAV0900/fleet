"""Hierarchy definitions for systems, component types, spares, agencies, and initial fleet."""

import random
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class SystemDef:
    system_id: str
    name: str


@dataclass(frozen=True)
class SensorDef:
    parameter: str
    baseline: float
    unit: str
    direction: str  # 'increase' or 'decrease' or 'drift'
    delta_at_failure: float
    noise_sigma: float
    temp_coef: float = 0.0
    load_coef: float = 0.0


@dataclass(frozen=True)
class ComponentTypeDef:
    component_type_id: str
    system_id: str
    name: str
    criticality: int
    design_life_hours: float
    mtbf_hours: float
    part_number: str
    is_repairable: bool
    description: str
    unit_cost: float
    lead_time_days: int
    reorder_level: int
    sensors: tuple[SensorDef, ...]


# 7 Systems
SYSTEMS: list[SystemDef] = [
    SystemDef(system_id="SYS-PROP", name="Propulsion System"),
    SystemDef(system_id="SYS-HYD", name="Hydraulics System"),
    SystemDef(system_id="SYS-ELEC", name="Electrical Power System"),
    SystemDef(system_id="SYS-LG", name="Landing Gear System"),
    SystemDef(system_id="SYS-AVION", name="Avionics & Flight Control"),
    SystemDef(system_id="SYS-FUEL", name="Fuel Distribution System"),
    SystemDef(system_id="SYS-ECS", name="Environmental Control System (ECS)"),
]

# 20 Component Types with realistic physics sensor specs
COMPONENT_TYPES: list[ComponentTypeDef] = [
    # 1. Propulsion
    ComponentTypeDef(
        component_type_id="CT-PROP-01",
        system_id="SYS-PROP",
        name="Main Engine Compressor",
        criticality=5,
        design_life_hours=6000.0,
        mtbf_hours=2600.0,
        part_number="PROP-101",
        is_repairable=True,
        description="Rotary multi-stage axial air compressor",
        unit_cost=85000.0,
        lead_time_days=45,
        reorder_level=2,
        sensors=(
            SensorDef(
                "vib_ips",
                baseline=0.18,
                unit="in/s",
                direction="increase",
                delta_at_failure=1.1,
                noise_sigma=0.03,
                load_coef=0.05,
            ),
            SensorDef(
                "eff_ratio",
                baseline=0.96,
                unit="ratio",
                direction="decrease",
                delta_at_failure=-0.22,
                noise_sigma=0.015,
                temp_coef=-0.002,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-PROP-02",
        system_id="SYS-PROP",
        name="High Pressure Turbine",
        criticality=5,
        design_life_hours=5000.0,
        mtbf_hours=2200.0,
        part_number="PROP-102",
        is_repairable=True,
        description="High pressure turbine disc and blisk module",
        unit_cost=120000.0,
        lead_time_days=60,
        reorder_level=2,
        sensors=(
            SensorDef(
                "egt_c",
                baseline=640.0,
                unit="deg_C",
                direction="increase",
                delta_at_failure=140.0,
                noise_sigma=8.0,
                temp_coef=1.2,
                load_coef=35.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-PROP-03",
        system_id="SYS-PROP",
        name="Engine Oil Scavenge Pump",
        criticality=4,
        design_life_hours=8000.0,
        mtbf_hours=3500.0,
        part_number="PROP-103",
        is_repairable=True,
        description="Positive displacement scavenge oil pump",
        unit_cost=18500.0,
        lead_time_days=30,
        reorder_level=3,
        sensors=(
            SensorDef(
                "oil_pressure_psi",
                baseline=55.0,
                unit="psi",
                direction="decrease",
                delta_at_failure=-22.0,
                noise_sigma=1.8,
                temp_coef=-0.2,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-PROP-04",
        system_id="SYS-PROP",
        name="Digital Fuel Control Unit",
        criticality=4,
        design_life_hours=7000.0,
        mtbf_hours=3200.0,
        part_number="PROP-104",
        is_repairable=True,
        description="Full authority digital hydromechanical fuel metering unit",
        unit_cost=42000.0,
        lead_time_days=40,
        reorder_level=2,
        sensors=(
            SensorDef(
                "metering_valve_pct",
                baseline=52.0,
                unit="pct",
                direction="drift",
                delta_at_failure=18.0,
                noise_sigma=2.0,
            ),
        ),
    ),
    # 2. Hydraulics
    ComponentTypeDef(
        component_type_id="CT-HYD-01",
        system_id="SYS-HYD",
        name="Primary Hydraulic Pump",
        criticality=5,
        design_life_hours=4500.0,
        mtbf_hours=1800.0,
        part_number="HYD-114",
        is_repairable=True,
        description="3000 PSI axial piston engine-driven hydraulic pump",
        unit_cost=34000.0,
        lead_time_days=45,
        reorder_level=1,  # Tight spares for hero scenario!
        sensors=(
            SensorDef(
                "outlet_pressure_psi",
                baseline=3000.0,
                unit="psi",
                direction="decrease",
                delta_at_failure=-620.0,
                noise_sigma=35.0,
                temp_coef=-1.5,
            ),
            SensorDef(
                "fluid_temp_c",
                baseline=54.0,
                unit="deg_C",
                direction="increase",
                delta_at_failure=42.0,
                noise_sigma=2.5,
                temp_coef=0.8,
                load_coef=6.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-HYD-02",
        system_id="SYS-HYD",
        name="Flight Control Servoactuator",
        criticality=5,
        design_life_hours=6000.0,
        mtbf_hours=2800.0,
        part_number="HYD-115",
        is_repairable=True,
        description="Dual tandem electro-hydraulic flight control actuator",
        unit_cost=29000.0,
        lead_time_days=35,
        reorder_level=2,
        sensors=(
            SensorDef(
                "response_lag_ms",
                baseline=45.0,
                unit="ms",
                direction="increase",
                delta_at_failure=120.0,
                noise_sigma=4.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-HYD-03",
        system_id="SYS-HYD",
        name="Return Line Reservoir Filter",
        criticality=3,
        design_life_hours=3000.0,
        mtbf_hours=1500.0,
        part_number="HYD-116",
        is_repairable=False,
        description="Micro-glass hydraulic return manifold filter element",
        unit_cost=1200.0,
        lead_time_days=15,
        reorder_level=6,
        sensors=(
            SensorDef(
                "diff_pressure_psi",
                baseline=8.5,
                unit="psi",
                direction="increase",
                delta_at_failure=28.0,
                noise_sigma=1.2,
            ),
        ),
    ),
    # 3. Electrical
    ComponentTypeDef(
        component_type_id="CT-ELEC-01",
        system_id="SYS-ELEC",
        name="Main Integrated Drive Generator",
        criticality=5,
        design_life_hours=5000.0,
        mtbf_hours=2400.0,
        part_number="ELEC-201",
        is_repairable=True,
        description="40 kVA 115V AC 400Hz integrated drive generator",
        unit_cost=52000.0,
        lead_time_days=40,
        reorder_level=2,
        sensors=(
            SensorDef(
                "bus_voltage_v",
                baseline=115.0,
                unit="V",
                direction="decrease",
                delta_at_failure=-14.0,
                noise_sigma=1.2,
            ),
            SensorDef(
                "winding_temp_c",
                baseline=78.0,
                unit="deg_C",
                direction="increase",
                delta_at_failure=55.0,
                noise_sigma=3.0,
                temp_coef=0.7,
                load_coef=8.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-ELEC-02",
        system_id="SYS-ELEC",
        name="Emergency Backup Battery",
        criticality=4,
        design_life_hours=3000.0,
        mtbf_hours=1600.0,
        part_number="ELEC-202",
        is_repairable=False,
        description="24V 45Ah sealed lead-acid emergency flight battery",
        unit_cost=6500.0,
        lead_time_days=20,
        reorder_level=4,
        sensors=(
            SensorDef(
                "charge_capacity_ah",
                baseline=46.0,
                unit="Ah",
                direction="decrease",
                delta_at_failure=-22.0,
                noise_sigma=1.5,
                temp_coef=-0.15,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-ELEC-03",
        system_id="SYS-ELEC",
        name="Primary Power Bus Controller",
        criticality=4,
        design_life_hours=8000.0,
        mtbf_hours=4000.0,
        part_number="ELEC-203",
        is_repairable=True,
        description="Solid state solid power distribution controller",
        unit_cost=24000.0,
        lead_time_days=30,
        reorder_level=2,
        sensors=(
            SensorDef(
                "ripple_voltage_mv",
                baseline=120.0,
                unit="mV",
                direction="increase",
                delta_at_failure=520.0,
                noise_sigma=18.0,
            ),
        ),
    ),
    # 4. Landing Gear
    ComponentTypeDef(
        component_type_id="CT-LG-01",
        system_id="SYS-LG",
        name="Multi-Disc Brake Assembly",
        criticality=4,
        design_life_hours=3500.0,
        mtbf_hours=1400.0,
        part_number="LG-301",
        is_repairable=True,
        description="Carbon composite multi-disc main gear brake unit",
        unit_cost=19500.0,
        lead_time_days=25,
        reorder_level=3,
        sensors=(
            SensorDef(
                "brake_temp_c",
                baseline=145.0,
                unit="deg_C",
                direction="increase",
                delta_at_failure=210.0,
                noise_sigma=12.0,
                load_coef=25.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-LG-02",
        system_id="SYS-LG",
        name="Main Oleo Shock Strut",
        criticality=5,
        design_life_hours=9000.0,
        mtbf_hours=4500.0,
        part_number="LG-302",
        is_repairable=True,
        description="Nitrogen-oil pneumatic-hydraulic shock absorber strut",
        unit_cost=65000.0,
        lead_time_days=50,
        reorder_level=1,
        sensors=(
            SensorDef(
                "extension_rate_mps",
                baseline=0.85,
                unit="m/s",
                direction="decrease",
                delta_at_failure=-0.45,
                noise_sigma=0.04,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-LG-03",
        system_id="SYS-LG",
        name="Main Landing Gear Tyre Set",
        criticality=3,
        design_life_hours=1500.0,
        mtbf_hours=750.0,
        part_number="LG-303",
        is_repairable=False,
        description="Reinforced tubeless aircraft tire assembly 32x8.8",
        unit_cost=2800.0,
        lead_time_days=15,
        reorder_level=8,
        sensors=(
            SensorDef(
                "tread_depth_mm",
                baseline=14.0,
                unit="mm",
                direction="decrease",
                delta_at_failure=-12.2,
                noise_sigma=0.3,
            ),
        ),
    ),
    # 5. Avionics
    ComponentTypeDef(
        component_type_id="CT-AVION-01",
        system_id="SYS-AVION",
        name="Flight Management Core Computer",
        criticality=5,
        design_life_hours=10000.0,
        mtbf_hours=5000.0,
        part_number="AV-401",
        is_repairable=True,
        description="Triple redundant avionics processing unit (FMC)",
        unit_cost=95000.0,
        lead_time_days=60,
        reorder_level=1,
        sensors=(
            SensorDef(
                "bus_latency_ms",
                baseline=12.0,
                unit="ms",
                direction="increase",
                delta_at_failure=68.0,
                noise_sigma=2.2,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-AVION-02",
        system_id="SYS-AVION",
        name="Primary Multi-Function Display",
        criticality=3,
        design_life_hours=8000.0,
        mtbf_hours=4000.0,
        part_number="AV-402",
        is_repairable=True,
        description="High-resolution active-matrix LCD pilot flight display",
        unit_cost=22000.0,
        lead_time_days=30,
        reorder_level=2,
        sensors=(
            SensorDef(
                "luminance_cdm2",
                baseline=460.0,
                unit="cd/m2",
                direction="decrease",
                delta_at_failure=-270.0,
                noise_sigma=14.0,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-AVION-03",
        system_id="SYS-AVION",
        name="Air Data Sensor Suite",
        criticality=4,
        design_life_hours=6000.0,
        mtbf_hours=3000.0,
        part_number="AV-403",
        is_repairable=True,
        description="Smart pitot-static probe and air data transducer",
        unit_cost=31000.0,
        lead_time_days=35,
        reorder_level=2,
        sensors=(
            SensorDef(
                "pitot_delta_pa",
                baseline=15.0,
                unit="Pa",
                direction="increase",
                delta_at_failure=95.0,
                noise_sigma=4.5,
            ),
        ),
    ),
    # 6. Fuel
    ComponentTypeDef(
        component_type_id="CT-FUEL-01",
        system_id="SYS-FUEL",
        name="High Pressure Fuel Boost Pump",
        criticality=4,
        design_life_hours=5500.0,
        mtbf_hours=2600.0,
        part_number="FUEL-501",
        is_repairable=True,
        description="Submerged centrifugal AC motor fuel boost pump",
        unit_cost=16500.0,
        lead_time_days=28,
        reorder_level=3,
        sensors=(
            SensorDef(
                "boost_pressure_psi",
                baseline=42.0,
                unit="psi",
                direction="decrease",
                delta_at_failure=-21.0,
                noise_sigma=1.4,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-FUEL-02",
        system_id="SYS-FUEL",
        name="Capacitance Fuel Quantity Transmitter",
        criticality=3,
        design_life_hours=7000.0,
        mtbf_hours=3500.0,
        part_number="FUEL-502",
        is_repairable=False,
        description="Fuel tank multi-probe capacitance quantity sensor",
        unit_cost=4800.0,
        lead_time_days=20,
        reorder_level=4,
        sensors=(
            SensorDef(
                "signal_variance_mv",
                baseline=5.2,
                unit="mV",
                direction="increase",
                delta_at_failure=54.0,
                noise_sigma=1.1,
            ),
        ),
    ),
    # 7. Environmental (ECS)
    ComponentTypeDef(
        component_type_id="CT-ECS-01",
        system_id="SYS-ECS",
        name="Air Cycle Cooling Pack",
        criticality=4,
        design_life_hours=5000.0,
        mtbf_hours=2200.0,
        part_number="ECS-601",
        is_repairable=True,
        description="Bootstrap air cycle machine and primary heat exchanger",
        unit_cost=46000.0,
        lead_time_days=40,
        reorder_level=2,
        sensors=(
            SensorDef(
                "pack_outlet_temp_c",
                baseline=8.5,
                unit="deg_C",
                direction="increase",
                delta_at_failure=24.0,
                noise_sigma=1.6,
                temp_coef=0.25,
            ),
        ),
    ),
    ComponentTypeDef(
        component_type_id="CT-ECS-02",
        system_id="SYS-ECS",
        name="Cabin Pressure Regulating Controller",
        criticality=4,
        design_life_hours=6500.0,
        mtbf_hours=3200.0,
        part_number="ECS-602",
        is_repairable=True,
        description="Dual electro-pneumatic cabin outflow thrust valve controller",
        unit_cost=27500.0,
        lead_time_days=30,
        reorder_level=2,
        sensors=(
            SensorDef(
                "cabin_diff_psi",
                baseline=7.8,
                unit="psi",
                direction="decrease",
                delta_at_failure=-2.4,
                noise_sigma=0.2,
            ),
        ),
    ),
]

# Lookup map
COMPONENT_TYPE_MAP: dict[str, ComponentTypeDef] = {
    ct.component_type_id: ct for ct in COMPONENT_TYPES
}

# 3 Maintenance Agencies
AGENCIES = [
    {
        "agency_id": "AG-LINE-01",
        "name": "Line Maintenance Squadron Alpha",
        "level": "line",
        "bays": 4,
        "capacity_hours_per_day": 32.0,
        "avg_turnaround_days": 1.5,
    },
    {
        "agency_id": "AG-BASE-01",
        "name": "Base Intermediate Maintenance Facility",
        "level": "base",
        "bays": 2,
        "capacity_hours_per_day": 16.0,
        "avg_turnaround_days": 5.0,
    },
    {
        "agency_id": "AG-DEPOT-01",
        "name": "Central Specialized Overhaul Depot",
        "level": "depot",
        "bays": 2,
        "capacity_hours_per_day": 16.0,
        "avg_turnaround_days": 14.0,
    },
]


def build_aircraft_records(
    size: int,
    tail_prefix: str,
    type_code: str,
    comm_start: date,
    bases: list[str],
    rng: random.Random,
) -> list[dict]:
    """Generate the initial fleet aircraft records."""
    records = []
    for i in range(1, size + 1):
        tail_code = f"{tail_prefix}{i:03d}"
        days_offset = rng.randint(0, 365)
        commissioned = comm_start + timedelta(days=days_offset)
        # Prior flight hours prior to simulation start (2020 to 2023)
        prior_hours = round(rng.uniform(600.0, 1800.0), 1)
        prior_cycles = int(prior_hours * rng.uniform(0.6, 0.9))
        base_id = bases[(i - 1) % len(bases)]
        records.append(
            {
                "aircraft_id": tail_code,
                "tail_code": tail_code,
                "type_code": type_code,
                "commissioned_date": commissioned,
                "total_flight_hours": prior_hours,
                "total_cycles": prior_cycles,
                "base_id": base_id,
            }
        )
    return records


def build_initial_components(
    aircraft_list: list[dict],
    rng: random.Random,
) -> tuple[list[dict], dict[str, float]]:
    """Build the initial 20 components installed on each aircraft and their initial health.

    Returns:
        (components_records, initial_health_by_component_id)
    """
    records = []
    health_map = {}
    comp_counter = 1

    for ac in aircraft_list:
        ac_id = ac["aircraft_id"]
        comm_date = ac["commissioned_date"]
        ac_hours = ac["total_flight_hours"]

        for ct in COMPONENT_TYPES:
            comp_id = f"CMP-{comp_counter:05d}"
            serial_no = f"SN-{ct.part_number}-{comp_counter:05d}"
            comp_counter += 1

            # Component install hours
            hours_at_install = 0.0
            hours_since_new = round(ac_hours * rng.uniform(0.7, 1.0), 1)
            # Health reflects initial hours
            init_health = max(
                0.65, min(1.0, 1.0 - (hours_since_new / ct.mtbf_hours) * 0.45 + rng.gauss(0, 0.03))
            )

            records.append(
                {
                    "component_id": comp_id,
                    "aircraft_id": ac_id,
                    "component_type_id": ct.component_type_id,
                    "serial_no": serial_no,
                    "installed_date": comm_date,
                    "hours_at_install": hours_at_install,
                    "hours_since_new": hours_since_new,
                    "status": "installed",
                }
            )
            health_map[comp_id] = round(init_health, 4)

    return records, health_map


def build_spare_parts_catalog() -> list[dict]:
    """Catalog of spare parts mapping 1:1 to component types."""
    records = []
    for ct in COMPONENT_TYPES:
        records.append(
            {
                "part_number": ct.part_number,
                "description": ct.description,
                "criticality": ct.criticality,
                "unit_cost": ct.unit_cost,
                "lead_time_days": ct.lead_time_days,
                "reorder_level": ct.reorder_level,
            }
        )
    return records


def build_scheduled_tasks(aircraft_list: list[dict]) -> list[dict]:
    """Generate recurring inspection task requirements for each aircraft."""
    tasks = []
    task_idx = 1
    for ac in aircraft_list:
        ac_id = ac["aircraft_id"]
        hours = ac["total_flight_hours"]

        # A-Check (100h)
        last_a = (hours // 100.0) * 100.0
        tasks.append(
            {
                "task_id": f"ST-{task_idx:05d}",
                "aircraft_id": ac_id,
                "task_name": "A-Check / 100-Hour Routine Inspection",
                "interval_hours": 100.0,
                "last_done_hours": last_a,
                "due_hours": last_a + 100.0,
                "due_date": None,
            }
        )
        task_idx += 1

        # B-Check (300h)
        last_b = (hours // 300.0) * 300.0
        tasks.append(
            {
                "task_id": f"ST-{task_idx:05d}",
                "aircraft_id": ac_id,
                "task_name": "B-Check / 300-Hour Intermediate Servicing",
                "interval_hours": 300.0,
                "last_done_hours": last_b,
                "due_hours": last_b + 300.0,
                "due_date": None,
            }
        )
        task_idx += 1

        # C-Check (1200h)
        last_c = (hours // 1200.0) * 1200.0
        tasks.append(
            {
                "task_id": f"ST-{task_idx:05d}",
                "aircraft_id": ac_id,
                "task_name": "C-Check / 1200-Hour Major Depot Inspection",
                "interval_hours": 1200.0,
                "last_done_hours": last_c,
                "due_hours": last_c + 1200.0,
                "due_date": None,
            }
        )
        task_idx += 1

    return tasks
