"""Tests for Phase 2 synthetic fleet data generation: reproducibility, FK integrity, and invariants."""

import math
from datetime import date

import pytest

from data_gen.config import FleetConfig, SimulationConfig, TimelineConfig
from data_gen.generator import FleetSimulator


@pytest.fixture(scope="module")
def small_sim_config() -> SimulationConfig:
    """Fast simulation configuration for testing."""
    cfg = SimulationConfig(
        seed=42,
        fleet=FleetConfig(size=10),
        timeline=TimelineConfig(
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),  # 6 months
            live_demo_window_days=30,
        ),
    )
    return cfg


def test_seed_reproducibility():
    """Verify that running simulator with the exact same seed produces identical outputs."""
    cfg1 = SimulationConfig(
        seed=123,
        fleet=FleetConfig(size=5),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31)),
    )
    cfg2 = SimulationConfig(
        seed=123,
        fleet=FleetConfig(size=5),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 3, 31)),
    )

    sim1 = FleetSimulator(cfg1)
    data1 = sim1.generate()

    sim2 = FleetSimulator(cfg2)
    data2 = sim2.generate()

    # Identical counts
    assert len(data1.flights) == len(data2.flights)
    assert len(data1.sensor_readings) == len(data2.sensor_readings)
    assert len(data1.fault_events) == len(data2.fault_events)
    assert len(data1.work_orders) == len(data2.work_orders)
    assert len(data1.aircraft_daily_status) == len(data2.aircraft_daily_status)
    assert len(data1.simulation_truth) == len(data2.simulation_truth)

    # Identical sample values
    assert data1.flights[0]["flight_id"] == data2.flights[0]["flight_id"]
    assert data1.flights[0]["duration_hours"] == data2.flights[0]["duration_hours"]
    assert data1.sensor_readings[0]["mean"] == data2.sensor_readings[0]["mean"]
    assert data1.simulation_truth[0]["true_health"] == data2.simulation_truth[0]["true_health"]


def test_foreign_key_integrity(small_sim_config: SimulationConfig):
    """Verify relational integrity across all generated entity references."""
    sim = FleetSimulator(small_sim_config)
    dataset = sim.generate()

    system_ids = {s["system_id"] for s in dataset.systems}
    comp_type_ids = {ct["component_type_id"] for ct in dataset.component_types}
    spare_part_nos = {p["part_number"] for p in dataset.spare_parts}
    agency_ids = {a["agency_id"] for a in dataset.agencies}
    aircraft_ids = {ac["aircraft_id"] for ac in dataset.aircraft}
    component_ids = {c["component_id"] for c in dataset.components}
    flight_ids = {f["flight_id"] for f in dataset.flights}
    wo_ids = {w["wo_id"] for w in dataset.work_orders}

    # 1. Component Types -> Systems
    for ct in dataset.component_types:
        assert ct["system_id"] in system_ids

    # 2. Components -> Aircraft & Component Types
    for c in dataset.components:
        if c["aircraft_id"]:
            assert c["aircraft_id"] in aircraft_ids
        assert c["component_type_id"] in comp_type_ids

    # 3. Scheduled Tasks -> Aircraft
    for st in dataset.scheduled_tasks:
        assert st["aircraft_id"] in aircraft_ids

    # 4. Inventory & Transactions -> Spare Parts
    for inv in dataset.inventory:
        assert inv["part_number"] in spare_part_nos
    for txn in dataset.inventory_transactions:
        assert txn["part_number"] in spare_part_nos
        if txn["work_order_id"]:
            assert txn["work_order_id"] in wo_ids

    # 5. Flights -> Aircraft
    for fl in dataset.flights:
        assert fl["aircraft_id"] in aircraft_ids

    # 6. Sensor Readings -> Flights & Components
    for sr in dataset.sensor_readings:
        assert sr["flight_id"] in flight_ids
        assert sr["component_id"] in component_ids

    # 7. Fault Events -> Aircraft & Components
    for fe in dataset.fault_events:
        assert fe["aircraft_id"] in aircraft_ids
        assert fe["component_id"] in component_ids

    # 8. Work Orders -> Aircraft, Components & Agencies
    for wo in dataset.work_orders:
        assert wo["aircraft_id"] in aircraft_ids
        assert wo["agency_id"] in agency_ids
        if wo["component_id"]:
            assert wo["component_id"] in component_ids

    # 9. Maintenance Events -> Aircraft, Components & Work Orders
    for me in dataset.maintenance_events:
        assert me["aircraft_id"] in aircraft_ids
        if me["component_id"]:
            assert me["component_id"] in component_ids
        if me["work_order_id"]:
            assert me["work_order_id"] in wo_ids

    # 10. Aircraft Daily Status -> Aircraft
    for ads in dataset.aircraft_daily_status:
        assert ads["aircraft_id"] in aircraft_ids

    # 11. Simulation Truth -> Components
    for st in dataset.simulation_truth:
        assert st["component_id"] in component_ids


def test_non_negative_stock_invariant(small_sim_config: SimulationConfig):
    """Verify that stock on hand never drops below zero under any demand spike."""
    sim = FleetSimulator(small_sim_config)
    dataset = sim.generate()

    for item in dataset.inventory:
        assert item["on_hand"] >= 0, f"Negative stock detected: {item}"
        assert item["reserved"] >= 0
        assert item["on_order"] >= 0


def test_noise_quality_flags_within_spec(small_sim_config: SimulationConfig):
    """Verify sensor reading quality flags match specified statistical distributions."""
    sim = FleetSimulator(small_sim_config)
    dataset = sim.generate()

    total = len(dataset.sensor_readings)
    assert total > 0

    flag_counts = {}
    for sr in dataset.sensor_readings:
        flag = sr["quality_flag"]
        flag_counts[flag] = flag_counts.get(flag, 0) + 1

    dropout_pct = (flag_counts.get("dropout", 0) / total) * 100
    stuck_pct = (flag_counts.get("stuck", 0) / total) * 100
    drift_pct = (flag_counts.get("drift", 0) / total) * 100
    spike_pct = (flag_counts.get("spike", 0) / total) * 100
    valid_pct = (flag_counts.get("valid", 0) / total) * 100

    # Validate specification limits
    assert 1.5 <= dropout_pct <= 4.0, f"Dropout rate {dropout_pct:.2f}% outside expected 1.5-4.0%"
    assert 0.4 <= stuck_pct <= 2.5
    assert 0.4 <= drift_pct <= 2.5
    assert 0.1 <= spike_pct <= 1.5
    assert valid_pct >= 90.0, f"Valid rate {valid_pct:.2f}% too low"


def test_sensor_correlation_with_latent_health():
    """Verify that sensor readings correlate in the expected physical direction with latent health."""
    cfg = SimulationConfig(
        seed=42,
        fleet=FleetConfig(size=15),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 10, 31)),
    )
    sim = FleetSimulator(cfg)
    dataset = sim.generate()

    # Map (component_id, flight_id) -> reading
    pressure_readings = {}
    for sr in dataset.sensor_readings:
        if sr["parameter"] == "outlet_pressure_psi" and sr["quality_flag"] == "valid":
            pressure_readings[(sr["component_id"], sr["flight_id"])] = sr["mean"]

    flight_dates = {f["flight_id"]: f["date"] for f in dataset.flights}

    # Map (component_id, date) -> true_health
    truth_map = {}
    for st in dataset.simulation_truth:
        truth_map[(st["component_id"], st["date"])] = st["true_health"]

    # Compute correlation
    xs = []
    ys = []
    for (comp_id, fl_id), val in pressure_readings.items():
        fl_date = flight_dates.get(fl_id)
        if (comp_id, fl_date) in truth_map:
            h = truth_map[(comp_id, fl_date)]
            xs.append(val)
            ys.append(h)

    assert len(xs) > 100
    # Pearson correlation
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    r = cov / math.sqrt(var_x * var_y)

    # Positive correlation: as health drops, pressure drops
    assert r > 0.40, f"Expected positive correlation between pressure and health, got {r:.3f}"


def test_hero_scenario_ac017():
    """Verify that AC-017 hydraulic pump degradation arc is properly generated."""
    cfg = SimulationConfig(
        seed=42,
        fleet=FleetConfig(size=40),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 12, 31)),
    )
    sim = FleetSimulator(cfg)
    dataset = sim.generate()

    # Find AC-017 hydraulic pump
    ac017_comps = [
        c
        for c in dataset.components
        if c["aircraft_id"] == "AC-017" and c["component_type_id"] == "CT-HYD-01"
    ]
    assert len(ac017_comps) >= 1
    target_comp_id = ac017_comps[0]["component_id"]

    # Check truth trajectory
    ac017_truth = [st for st in dataset.simulation_truth if st["component_id"] == target_comp_id]
    assert len(ac017_truth) > 0
    final_health = ac017_truth[-1]["true_health"]
    assert 0.35 <= final_health <= 0.45, f"AC-017 final health {final_health} expected near 0.41"

    # Check tight spares at BASE-MAIN
    hyd114_inv = next(
        (
            i
            for i in dataset.inventory
            if i["part_number"] == "HYD-114" and i["location_id"] == "BASE-MAIN"
        ),
        None,
    )
    assert hyd114_inv is not None
    assert hyd114_inv["on_hand"] <= 1, "Expected tight spares (<=1) for hero aircraft HYD-114"
