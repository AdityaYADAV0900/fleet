"""Unit and simulation sanity tests for the Monte Carlo availability simulator."""

import time

from app.availability.scenarios import ScenarioEngine
from app.availability.simulator import (
    FleetSimulator,
    create_default_simulation_config,
)


def test_seeded_simulation_reproducibility():
    """Verify that running with an identical seed produces bit-for-bit identical results."""
    config1 = create_default_simulation_config(num_aircraft=20, horizon_days=30, runs=100, seed=777)
    config2 = create_default_simulation_config(num_aircraft=20, horizon_days=30, runs=100, seed=777)

    sim1 = FleetSimulator(config1)
    sim2 = FleetSimulator(config2)

    res1 = sim1.run()
    res2 = sim2.run()

    assert res1.availability_p50 == res2.availability_p50
    assert res1.availability_p10 == res2.availability_p10
    assert res1.availability_p90 == res2.availability_p90
    assert res1.aircraft_days_lost == res2.aircraft_days_lost
    assert res1.aircraft_days_lost_by_cause == res2.aircraft_days_lost_by_cause
    assert res1.stockout_probability == res2.stockout_probability
    assert len(res1.daily_trend) == len(res2.daily_trend)
    for p1, p2 in zip(res1.daily_trend, res2.daily_trend, strict=True):
        assert p1["p50"] == p2["p50"]
        assert p1["p10"] == p2["p10"]
        assert p1["p90"] == p2["p90"]


def test_sanity_removing_spares_never_raises_availability():
    """Sanity test: eliminating spare parts inventory must never raise availability

    (or must increase/maintain aircraft-days lost awaiting spares).
    """
    # 1. Config with ample spares on hand
    config_abundant = create_default_simulation_config(
        num_aircraft=20, horizon_days=30, runs=150, seed=42, default_spare_stock=10
    )
    # 2. Config with 0 spares on hand
    config_zero_spares = create_default_simulation_config(
        num_aircraft=20, horizon_days=30, runs=150, seed=42, default_spare_stock=0
    )

    res_abundant = FleetSimulator(config_abundant).run()
    res_zero_spares = FleetSimulator(config_zero_spares).run()

    # Availability with 0 spares should be <= availability with abundant spares
    assert res_zero_spares.availability_p50 <= res_abundant.availability_p50
    # Supply wait downtime should be >= with zero spares
    assert (
        res_zero_spares.aircraft_days_lost_by_cause["supply_wait"]
        >= res_abundant.aircraft_days_lost_by_cause["supply_wait"]
    )
    # Stock-out probability must be higher or equal
    assert res_zero_spares.stockout_probability >= res_abundant.stockout_probability


def test_sanity_adding_capacity_never_lowers_availability():
    """Sanity test: expanding workshop bay capacity must never lower availability

    (or must decrease/maintain agency wait queuing).
    """
    # 1. Config with constrained bay capacity (e.g., 1 bay)
    config_tight = create_default_simulation_config(
        num_aircraft=20, horizon_days=30, runs=150, seed=42, total_bays=1
    )
    # 2. Config with expanded bay capacity (e.g., 6 bays)
    config_expanded = create_default_simulation_config(
        num_aircraft=20, horizon_days=30, runs=150, seed=42, total_bays=6
    )

    res_tight = FleetSimulator(config_tight).run()
    res_expanded = FleetSimulator(config_expanded).run()

    # Availability with more bays should be >= availability with 1 bay
    assert res_expanded.availability_p50 >= res_tight.availability_p50
    # Queue wait downtime should be <= with more bays
    assert (
        res_expanded.aircraft_days_lost_by_cause["agency_wait"]
        <= res_tight.aircraft_days_lost_by_cause["agency_wait"]
    )


def test_simulation_execution_performance_benchmark():
    """Acceptance criterion: a 30-day, 300-run scenario must run in about 10 seconds or less."""
    config = create_default_simulation_config(num_aircraft=20, horizon_days=30, runs=300, seed=42)
    sim = FleetSimulator(config)

    t0 = time.perf_counter()
    res = sim.run()
    elapsed = time.perf_counter() - t0

    assert elapsed < 10.0, f"Simulation took {elapsed:.2f}s, exceeding 10s budget!"
    assert res.total_aircraft == 20
    assert res.horizon_days == 30
    assert res.runs == 300
    assert 0.0 <= res.availability_p50 <= 1.0


def test_all_four_scenario_types_produce_valid_comparisons():
    """Verify that all four required scenario types execute and return comparative outputs with deltas."""
    base_config = create_default_simulation_config(
        num_aircraft=20, horizon_days=30, runs=50, seed=42
    )

    # 1. Schedule maintenance
    res_sched = ScenarioEngine.run_scenario(
        scenario_type="schedule_maintenance",
        params={"aircraft_id": "AC-017", "start_day": 4, "duration_days": 2},
        base_config=base_config,
    )
    assert res_sched["type"] == "schedule_maintenance"
    assert "delta" in res_sched
    assert "availability_pct_points" in res_sched["delta"]
    assert "by_cause" in res_sched

    # 2. Spare unavailable
    res_spare = ScenarioEngine.run_scenario(
        scenario_type="spare_unavailable",
        params={"part_number": "HYD-114", "stock_override": 0, "lead_time_days": 45},
        base_config=base_config,
    )
    assert res_spare["type"] == "spare_unavailable"
    # Setting spare unavailable should increase supply wait or lower availability
    assert res_spare["delta"]["availability_pct_points"] <= 0.05

    # 3. Early vs run to failure
    res_early = ScenarioEngine.run_scenario(
        scenario_type="early_vs_run_to_failure",
        params={"aircraft_id": "AC-017", "early_replace_day": 3, "planned_duration_days": 1},
        base_config=base_config,
    )
    assert res_early["type"] == "early_vs_run_to_failure"
    assert "baseline" in res_early
    assert "scenario" in res_early

    # 4. Extra capacity
    res_cap = ScenarioEngine.run_scenario(
        scenario_type="extra_capacity",
        params={"bay_increase": 2},
        base_config=base_config,
    )
    assert res_cap["type"] == "extra_capacity"
    assert res_cap["delta"]["availability_pct_points"] >= -0.05
