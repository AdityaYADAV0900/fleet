"""Digital Twin health state model, configurable thresholds, and state transitions (§6).

Defines the six primary digital twin health states:
- Healthy: HI >= 80
- Watch: 60 <= HI < 80
- Degraded: 40 <= HI < 60
- Critical: HI < 40 or risk > 0.70
- Failed: HI == 0 or explicit failure/unserviceable flag
- Under maintenance: undergoing active inspection, servicing, or repair work order

Provides configurable thresholds, severity ranking for hierarchical roll-up,
and state transition validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class TwinHealthState(StrEnum):
    """Primary health states for components, systems, and aircraft in the digital twin."""

    HEALTHY = "Healthy"
    WATCH = "Watch"
    DEGRADED = "Degraded"
    CRITICAL = "Critical"
    FAILED = "Failed"
    UNDER_MAINTENANCE = "Under maintenance"


# Severity rank for roll-up comparison (higher is more severe/restrictive)
STATE_SEVERITY: dict[TwinHealthState, int] = {
    TwinHealthState.HEALTHY: 1,
    TwinHealthState.WATCH: 2,
    TwinHealthState.DEGRADED: 3,
    TwinHealthState.UNDER_MAINTENANCE: 4,
    TwinHealthState.CRITICAL: 5,
    TwinHealthState.FAILED: 6,
}


@dataclass(frozen=True)
class TwinThresholdsConfig:
    """Configurable thresholds for digital twin health state classification (§6)."""

    healthy_hi_min: float = 80.0
    watch_hi_min: float = 60.0
    degraded_hi_min: float = 40.0
    critical_risk_threshold: float = 0.70
    failed_hi_threshold: float = 0.0


DEFAULT_THRESHOLDS = TwinThresholdsConfig()


def determine_health_state(
    health_index: float,
    risk: float | None = None,
    is_under_maintenance: bool = False,
    is_failed: bool = False,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> TwinHealthState:
    """Classify health index, risk, and operational status into a TwinHealthState.

    Rules (§6):
    1. If explicitly failed or HI <= failed_hi_threshold -> Failed
    2. If under active maintenance work order -> Under maintenance
    3. If HI < degraded_hi_min (40) OR risk > critical_risk_threshold (0.70) -> Critical
    4. If HI < watch_hi_min (60) -> Degraded
    5. If HI < healthy_hi_min (80) -> Watch
    6. Else -> Healthy
    """
    if is_failed or health_index <= config.failed_hi_threshold:
        return TwinHealthState.FAILED

    if is_under_maintenance:
        return TwinHealthState.UNDER_MAINTENANCE

    if health_index < config.degraded_hi_min or (
        risk is not None and risk > config.critical_risk_threshold
    ):
        return TwinHealthState.CRITICAL

    if health_index < config.watch_hi_min:
        return TwinHealthState.DEGRADED

    if health_index < config.healthy_hi_min:
        return TwinHealthState.WATCH

    return TwinHealthState.HEALTHY


# Valid allowed operational state transitions
# Key: from_state, Value: allowed set of to_states
VALID_TRANSITIONS: dict[TwinHealthState, set[TwinHealthState]] = {
    TwinHealthState.HEALTHY: {
        TwinHealthState.HEALTHY,
        TwinHealthState.WATCH,
        TwinHealthState.DEGRADED,  # Rapid drop
        TwinHealthState.CRITICAL,  # Sudden failure risk spike
        TwinHealthState.FAILED,  # Sudden mechanical failure
        TwinHealthState.UNDER_MAINTENANCE,  # Scheduled routine maintenance
    },
    TwinHealthState.WATCH: {
        TwinHealthState.HEALTHY,  # Slight calibration adjustment
        TwinHealthState.WATCH,
        TwinHealthState.DEGRADED,  # Continued progression
        TwinHealthState.CRITICAL,
        TwinHealthState.FAILED,
        TwinHealthState.UNDER_MAINTENANCE,
    },
    TwinHealthState.DEGRADED: {
        TwinHealthState.WATCH,  # Minor tuning / calibration
        TwinHealthState.DEGRADED,
        TwinHealthState.CRITICAL,  # Continued degradation
        TwinHealthState.FAILED,
        TwinHealthState.UNDER_MAINTENANCE,  # Proactive replacement
    },
    TwinHealthState.CRITICAL: {
        TwinHealthState.CRITICAL,
        TwinHealthState.FAILED,
        TwinHealthState.UNDER_MAINTENANCE,  # Grounded for replacement
        TwinHealthState.DEGRADED,  # Rare de-escalation if re-evaluated
    },
    TwinHealthState.FAILED: {
        TwinHealthState.FAILED,
        TwinHealthState.UNDER_MAINTENANCE,  # Work order opened to rectify failure
    },
    TwinHealthState.UNDER_MAINTENANCE: {
        TwinHealthState.UNDER_MAINTENANCE,
        TwinHealthState.HEALTHY,  # New / overhauled part installed
        TwinHealthState.WATCH,  # Repaired part installed with partial life
        TwinHealthState.DEGRADED,  # If work order was incomplete or interim
    },
}


def validate_state_transition(
    from_state: TwinHealthState | str,
    to_state: TwinHealthState | str,
) -> bool:
    """Check whether a transition between two digital twin health states is valid."""
    try:
        from_enum = TwinHealthState(from_state)
        to_enum = TwinHealthState(to_state)
    except ValueError:
        return False

    return to_enum in VALID_TRANSITIONS.get(from_enum, set())


def get_worst_state(states: list[TwinHealthState | str]) -> TwinHealthState:
    """Return the most severe health state from a list of states."""
    if not states:
        return TwinHealthState.HEALTHY

    valid_states: list[TwinHealthState] = []
    for s in states:
        try:
            valid_states.append(TwinHealthState(s))
        except ValueError:
            continue

    if not valid_states:
        return TwinHealthState.HEALTHY

    return max(valid_states, key=lambda s: STATE_SEVERITY[s])
