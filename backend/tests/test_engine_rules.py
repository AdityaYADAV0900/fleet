"""Unit tests for predictive maintenance engine rules and workflows."""

import pytest

from app.engine.advisory import (
    calculate_priority_score,
    determine_recommended_action,
    validate_advisory_transition,
)
from app.engine.health_indicator import (
    HEALTH_STATE_CRITICAL,
    HEALTH_STATE_DEGRADED,
    HEALTH_STATE_FAILED,
    HEALTH_STATE_HEALTHY,
    HEALTH_STATE_UNDER_MAINTENANCE,
    ComponentHealthResult,
    compute_component_hi,
    rollup_aircraft_hi,
    rollup_system_hi,
)
from app.engine.spares_check import evaluate_spare_urgency


def test_health_indicator_nominal():
    """Verify nominal sensor telemetry yields Healthy state and HI near 100."""
    res = compute_component_hi(
        max_abs_z=0.2,
        max_roll_mean_20=0.1,
        anomaly_score=0.05,
        fault_count_14d=0,
        risk_14d=0.01,
    )
    assert res.health_index >= 90.0
    assert res.state == HEALTH_STATE_HEALTHY


def test_health_indicator_degraded():
    """Verify moderate sensor drift drops HI into Degraded state."""
    res = compute_component_hi(
        max_abs_z=2.8,
        max_roll_mean_20=2.0,
        anomaly_score=0.65,
        risk_14d=0.55,
    )
    assert 40.0 <= res.health_index <= 60.0
    assert res.state == HEALTH_STATE_DEGRADED


def test_health_indicator_critical():
    """Verify severe sensor deviation or high risk yields Critical state."""
    res = compute_component_hi(
        max_abs_z=4.5,
        max_roll_mean_20=3.8,
        anomaly_score=0.88,
        risk_14d=0.82,
    )
    assert res.health_index < 40.0
    assert res.state == HEALTH_STATE_CRITICAL


def test_health_indicator_failed_and_maintenance():
    """Verify explicit failed or under-maintenance flags."""
    res_fail = compute_component_hi(is_failed=True)
    assert res_fail.health_index == 0.0
    assert res_fail.state == HEALTH_STATE_FAILED

    res_maint = compute_component_hi(under_maintenance=True)
    assert res_maint.health_index == 50.0
    assert res_maint.state == HEALTH_STATE_UNDER_MAINTENANCE


def test_system_and_aircraft_hi_rollup():
    """Verify hierarchical roll-up from components to system and aircraft."""
    c1 = ComponentHealthResult("C1", 95.0, HEALTH_STATE_HEALTHY, "nominal", 5.0)
    c2 = ComponentHealthResult("C2", 42.0, HEALTH_STATE_DEGRADED, "drift", 58.0)

    # c2 has high criticality 5, c1 has 3
    sys_rollup = rollup_system_hi("SYS-HYD", [(c1, 3), (c2, 5)])
    assert sys_rollup.state == HEALTH_STATE_DEGRADED
    assert sys_rollup.driving_component_id == "C2"

    ac_rollup = rollup_aircraft_hi("AC-017", [sys_rollup], critical_components=[c2])
    assert ac_rollup.state == HEALTH_STATE_DEGRADED
    assert ac_rollup.driving_component_id == "C2"


def test_priority_score_calculation():
    """Verify priority score formula with configurable weights maps to P1-P4."""
    # Critical risk + high criticality + low RUL + spare shortfall -> P1
    p1, score1 = calculate_priority_score(
        risk_14d=0.85,
        criticality=5,
        rul_days=2.0,
        spare_shortfall=True,
    )
    assert p1 == "P1"
    assert score1 >= 0.70

    # High risk with available spare -> P2
    p2, score2 = calculate_priority_score(
        risk_14d=0.55,
        criticality=4,
        rul_days=15.0,
        spare_shortfall=False,
    )
    assert p2 == "P2"
    assert 0.45 <= score2 < 0.70

    # Nominal -> P4
    p4, score4 = calculate_priority_score(
        risk_14d=0.01,
        criticality=2,
        rul_days=60.0,
        spare_shortfall=False,
    )
    assert p4 == "P4"
    assert score4 < 0.25


def test_recommended_action_rules():
    """Verify deterministic recommendation actions based on risk and RUL."""
    assert "ground now" in determine_recommended_action(
        risk_14d=0.80, rul_p50=2.0, health_index=20.0
    )
    assert "replace within 7 days" in determine_recommended_action(
        risk_14d=0.55, rul_p50=10.0, health_index=45.0
    )
    assert "schedule replacement within 14 days" in determine_recommended_action(
        risk_14d=0.30, rul_p50=13.0, health_index=65.0
    )
    assert "inspect at next opportunity" in determine_recommended_action(
        risk_14d=0.12, rul_p50=40.0, health_index=75.0
    )
    assert "continue monitoring" in determine_recommended_action(
        risk_14d=0.02, rul_p50=60.0, health_index=95.0
    )


def test_spare_urgency_heuristic():
    """Verify spare parts urgency penalty and status labels."""
    # 0 stock and lead time 45d > RUL 10d -> Shortfall Risk
    penalty0, label0 = evaluate_spare_urgency(available=0, lead_time_days=45, rul_days=10.0)
    assert penalty0 == 1.0
    assert label0 == "Shortfall Risk"

    # 1 stock and lead time > RUL -> Tight
    penalty1, label1 = evaluate_spare_urgency(available=1, lead_time_days=45, rul_days=12.0)
    assert penalty1 > 0.0
    assert label1 == "Tight"

    # 5 stock -> Available
    penalty5, label5 = evaluate_spare_urgency(available=5, lead_time_days=30, rul_days=40.0)
    assert penalty5 == 0.0
    assert label5 == "Available"


def test_advisory_workflow_transitions():
    """Verify advisory status state machine transitions."""
    # Valid transitions
    validate_advisory_transition("proposed", "accepted")
    validate_advisory_transition("accepted", "scheduled")
    validate_advisory_transition("scheduled", "completed")

    # Dismissal requires reason
    with pytest.raises(ValueError, match="non-empty dismissal reason"):
        validate_advisory_transition("proposed", "dismissed", dismiss_reason="")

    with pytest.raises(ValueError, match="non-empty dismissal reason"):
        validate_advisory_transition("proposed", "dismissed", dismiss_reason=None)

    # Dismissal with valid reason succeeds
    validate_advisory_transition(
        "proposed", "dismissed", dismiss_reason="False alarm; sensor recalibrated"
    )

    # Invalid transitions fail
    with pytest.raises(ValueError, match="Cannot transition advisory"):
        validate_advisory_transition("proposed", "completed")

    with pytest.raises(ValueError, match="Cannot transition advisory"):
        validate_advisory_transition("completed", "proposed")
