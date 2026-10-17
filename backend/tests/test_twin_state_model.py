"""Unit tests for digital twin health state model, configurable thresholds, and transitions (§6)."""

from app.twin.state_model import (
    STATE_SEVERITY,
    TwinHealthState,
    TwinThresholdsConfig,
    determine_health_state,
    get_worst_state,
    validate_state_transition,
)


def test_determine_health_state_boundaries():
    """Verify health state classifications across HI boundaries under default thresholds."""
    # Healthy: HI >= 80
    assert determine_health_state(health_index=100.0) == TwinHealthState.HEALTHY
    assert determine_health_state(health_index=80.0) == TwinHealthState.HEALTHY

    # Watch: 60 <= HI < 80
    assert determine_health_state(health_index=79.9) == TwinHealthState.WATCH
    assert determine_health_state(health_index=60.0) == TwinHealthState.WATCH

    # Degraded: 40 <= HI < 60
    assert determine_health_state(health_index=59.9) == TwinHealthState.DEGRADED
    assert determine_health_state(health_index=40.0) == TwinHealthState.DEGRADED

    # Critical: HI < 40 or risk > 0.70
    assert determine_health_state(health_index=39.9) == TwinHealthState.CRITICAL
    assert determine_health_state(health_index=15.0) == TwinHealthState.CRITICAL

    # Critical triggered by high risk even if HI is moderate
    assert determine_health_state(health_index=75.0, risk=0.85) == TwinHealthState.CRITICAL
    assert determine_health_state(health_index=50.0, risk=0.75) == TwinHealthState.CRITICAL

    # Low risk does not trigger critical if HI is healthy/watch
    assert determine_health_state(health_index=85.0, risk=0.10) == TwinHealthState.HEALTHY
    assert determine_health_state(health_index=65.0, risk=0.30) == TwinHealthState.WATCH


def test_determine_health_state_failed_and_maintenance():
    """Verify Failed and Under Maintenance overrides."""
    # Failed flag or HI <= 0
    assert determine_health_state(health_index=0.0) == TwinHealthState.FAILED
    assert determine_health_state(health_index=-5.0) == TwinHealthState.FAILED
    assert determine_health_state(health_index=85.0, is_failed=True) == TwinHealthState.FAILED

    # Under Maintenance
    assert (
        determine_health_state(health_index=85.0, is_under_maintenance=True)
        == TwinHealthState.UNDER_MAINTENANCE
    )
    assert (
        determine_health_state(health_index=35.0, is_under_maintenance=True)
        == TwinHealthState.UNDER_MAINTENANCE
    )


def test_configurable_thresholds_override():
    """Verify that custom thresholds modify state boundaries correctly."""
    custom_cfg = TwinThresholdsConfig(
        healthy_hi_min=90.0,
        watch_hi_min=75.0,
        degraded_hi_min=50.0,
        critical_risk_threshold=0.60,
    )

    # HI 85 was Healthy under default (80), now Watch under custom (90)
    assert determine_health_state(health_index=85.0, config=custom_cfg) == TwinHealthState.WATCH

    # HI 70 was Watch under default (60), now Degraded under custom (75)
    assert determine_health_state(health_index=70.0, config=custom_cfg) == TwinHealthState.DEGRADED

    # Risk 0.65 was not Critical under default (0.70), now Critical under custom (0.60)
    assert (
        determine_health_state(health_index=80.0, risk=0.65, config=custom_cfg)
        == TwinHealthState.CRITICAL
    )


def test_state_severity_ordering():
    """Verify severity ordering and get_worst_state."""
    assert (
        STATE_SEVERITY[TwinHealthState.HEALTHY]
        < STATE_SEVERITY[TwinHealthState.WATCH]
        < STATE_SEVERITY[TwinHealthState.DEGRADED]
        < STATE_SEVERITY[TwinHealthState.UNDER_MAINTENANCE]
        < STATE_SEVERITY[TwinHealthState.CRITICAL]
        < STATE_SEVERITY[TwinHealthState.FAILED]
    )

    assert (
        get_worst_state([TwinHealthState.HEALTHY, TwinHealthState.WATCH]) == TwinHealthState.WATCH
    )
    assert (
        get_worst_state([TwinHealthState.HEALTHY, TwinHealthState.DEGRADED])
        == TwinHealthState.DEGRADED
    )
    assert (
        get_worst_state(
            [
                TwinHealthState.HEALTHY,
                TwinHealthState.WATCH,
                TwinHealthState.CRITICAL,
            ]
        )
        == TwinHealthState.CRITICAL
    )
    assert (
        get_worst_state(
            [
                TwinHealthState.DEGRADED,
                TwinHealthState.FAILED,
                TwinHealthState.CRITICAL,
            ]
        )
        == TwinHealthState.FAILED
    )
    assert get_worst_state([]) == TwinHealthState.HEALTHY


def test_state_transition_validation():
    """Verify valid vs invalid digital twin health state transitions."""
    # Valid normal degradation progression
    assert validate_state_transition(TwinHealthState.HEALTHY, TwinHealthState.WATCH)
    assert validate_state_transition(TwinHealthState.WATCH, TwinHealthState.DEGRADED)
    assert validate_state_transition(TwinHealthState.DEGRADED, TwinHealthState.CRITICAL)
    assert validate_state_transition(TwinHealthState.CRITICAL, TwinHealthState.FAILED)

    # Valid maintenance workflows
    assert validate_state_transition(TwinHealthState.CRITICAL, TwinHealthState.UNDER_MAINTENANCE)
    assert validate_state_transition(TwinHealthState.FAILED, TwinHealthState.UNDER_MAINTENANCE)
    assert validate_state_transition(TwinHealthState.UNDER_MAINTENANCE, TwinHealthState.HEALTHY)
    assert validate_state_transition(TwinHealthState.UNDER_MAINTENANCE, TwinHealthState.WATCH)

    # Invalid transitions: e.g. Failed directly to Healthy without Under maintenance
    assert not validate_state_transition(TwinHealthState.FAILED, TwinHealthState.HEALTHY)
    assert not validate_state_transition(TwinHealthState.FAILED, TwinHealthState.WATCH)
    assert not validate_state_transition(TwinHealthState.FAILED, TwinHealthState.DEGRADED)

    # Invalid strings
    assert not validate_state_transition("UnknownState", TwinHealthState.HEALTHY)
