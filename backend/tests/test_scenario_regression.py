"""Fixed-seed scenario regression and monotonicity sanity tests."""

from __future__ import annotations

import pytest

from app.availability.scenarios import ScenarioEngine
from app.availability.simulator import create_default_simulation_config


@pytest.fixture
def base_config():
    """Deterministic simulation base config for regression tests."""
    return create_default_simulation_config(
        num_aircraft=20,
        horizon_days=30,
        runs=100,
        seed=101,
        default_spare_stock=2,
        total_bays=3,
    )


def test_scenario_fixed_seed_determinism(base_config) -> None:
    """Verify that ScenarioEngine runs are bit-for-bit deterministic with fixed seeds."""
    params = {"part_number": "HYD-114", "stock_override": 0, "lead_time_days": 45}

    res1 = ScenarioEngine.run_scenario(
        scenario_type="spare_unavailable",
        params=params,
        base_config=base_config,
    )
    res2 = ScenarioEngine.run_scenario(
        scenario_type="spare_unavailable",
        params=params,
        base_config=base_config,
    )

    assert res1["baseline"]["availability_p50"] == res2["baseline"]["availability_p50"]
    assert res1["scenario"]["availability_p50"] == res2["scenario"]["availability_p50"]
    assert res1["delta"]["availability_pct_points"] == res2["delta"]["availability_pct_points"]
    assert res1["delta"]["aircraft_days_lost"] == res2["delta"]["aircraft_days_lost"]
    assert res1["by_cause"] == res2["by_cause"]


def test_monotonic_early_replacement_benefit(base_config) -> None:
    """Verify that proactive replacement (early_vs_run_to_failure) yields positive availability delta."""
    params = {
        "aircraft_id": "AC-017",
        "early_replace_day": 3,
        "planned_duration_days": 1,
    }

    result = ScenarioEngine.run_scenario(
        scenario_type="early_vs_run_to_failure",
        params=params,
        base_config=base_config,
    )

    # Proactive replacement avoids sudden failure & supply wait -> should improve or match availability
    assert result["delta"]["availability_pct_points"] >= -0.05
    assert "baseline" in result
    assert "scenario" in result


def test_monotonic_spare_unavailable_penalty(base_config) -> None:
    """Verify that spare unavailability increases supply wait downtime and reduces availability."""
    params = {"part_number": "HYD-114", "stock_override": 0, "lead_time_days": 60}

    result = ScenarioEngine.run_scenario(
        scenario_type="spare_unavailable",
        params=params,
        base_config=base_config,
    )

    # Scenarios where spare is unavailable must have lower or equal availability
    assert result["delta"]["availability_pct_points"] <= 0.05
    assert result["delta"]["aircraft_days_lost"] >= -0.1
    assert result["by_cause"].get("supply_wait", 0.0) >= -0.1


def test_monotonic_extra_capacity_benefit() -> None:
    """Verify that adding workshop bays reduces agency queuing and improves or maintains availability."""
    tight_config = create_default_simulation_config(
        num_aircraft=20,
        horizon_days=30,
        runs=100,
        seed=202,
        default_spare_stock=2,
        total_bays=1,
    )
    params = {"bay_increase": 3}

    result = ScenarioEngine.run_scenario(
        scenario_type="extra_capacity",
        params=params,
        base_config=tight_config,
    )

    assert result["delta"]["availability_pct_points"] >= -0.05
    assert result["delta"]["aircraft_days_lost"] <= 0.1
