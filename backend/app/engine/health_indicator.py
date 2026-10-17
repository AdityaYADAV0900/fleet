"""Health Indicator (HI) computation and hierarchical state roll-up.

Calculates a 0-100 continuous health indicator for components, rolling up
to system and aircraft levels weighted by criticality.
Maps continuous HI and model risk to discrete health states:
  Healthy (HI >= 80) -> Watch (60-80) -> Degraded (40-60) -> Critical (<40 or risk > 0.7)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

HEALTH_STATE_HEALTHY = "Healthy"
HEALTH_STATE_WATCH = "Watch"
HEALTH_STATE_DEGRADED = "Degraded"
HEALTH_STATE_CRITICAL = "Critical"
HEALTH_STATE_FAILED = "Failed"
HEALTH_STATE_UNDER_MAINTENANCE = "Under maintenance"

STATE_SEVERITY_ORDER = {
    HEALTH_STATE_HEALTHY: 1,
    HEALTH_STATE_WATCH: 2,
    HEALTH_STATE_DEGRADED: 3,
    HEALTH_STATE_CRITICAL: 4,
    HEALTH_STATE_FAILED: 5,
    HEALTH_STATE_UNDER_MAINTENANCE: 6,
}


@dataclass(frozen=True)
class ComponentHealthResult:
    """Computed health indicator and state for a single component."""

    component_id: str
    health_index: float  # 0.0 to 100.0
    state: str  # Healthy, Watch, Degraded, Critical, Failed, Under maintenance
    driving_factor: str  # e.g. "sensor_flutter", "anomaly_drift", "nominal"
    drop_from_nominal: float  # e.g. 100 - HI


@dataclass(frozen=True)
class RollupHealthResult:
    """Aggregated health score and state for a system or aircraft."""

    node_id: str
    node_type: str  # 'system' or 'aircraft'
    health_index: float
    state: str
    driving_component_id: str | None
    driving_component_state: str | None


def compute_component_hi(
    max_abs_z: float = 0.0,
    max_roll_mean_20: float = 0.0,
    anomaly_score: float = 0.0,
    fault_count_14d: int = 0,
    risk_14d: float = 0.0,
    is_failed: bool = False,
    under_maintenance: bool = False,
) -> ComponentHealthResult:
    """Compute component Health Index (HI) on a 0-100 scale from physical features.

    When sensors are near baseline (z ~ 0, anomaly ~ 0), HI is ~95-100.
    As sensor deviations or anomaly scores grow, HI smoothly drops.
    """
    if is_failed:
        return ComponentHealthResult(
            component_id="",
            health_index=0.0,
            state=HEALTH_STATE_FAILED,
            driving_factor="component_failure",
            drop_from_nominal=100.0,
        )

    if under_maintenance:
        return ComponentHealthResult(
            component_id="",
            health_index=50.0,
            state=HEALTH_STATE_UNDER_MAINTENANCE,
            driving_factor="scheduled_or_corrective_work",
            drop_from_nominal=50.0,
        )

    # Base penalty from sensor deviations (sigma units)
    # 0 sigma -> 0 penalty; 1 sigma -> ~10 penalty; 2.5 sigma -> ~35 penalty; 4+ sigma -> ~65 penalty
    z_penalty = min(70.0, max(0.0, (max(max_abs_z, max_roll_mean_20) - 0.5) * 16.0))

    # Penalty from unsupervised anomaly score (0 to 1)
    anomaly_penalty = min(40.0, anomaly_score * 40.0)

    # Penalty from recent fault events
    fault_penalty = min(20.0, float(fault_count_14d) * 8.0)

    total_penalty = z_penalty * 0.55 + anomaly_penalty * 0.35 + fault_penalty * 0.10

    # If risk is elevated, reinforce degradation according to §5.1 state boundaries:
    # Critical: HI < 40; Degraded: HI 40-59; Watch: HI 60-79; Healthy: HI 80-100
    if risk_14d >= 0.70:
        total_penalty = max(total_penalty, 61.0 + (risk_14d - 0.70) * 100.0)
    elif risk_14d >= 0.40:
        total_penalty = max(total_penalty, 41.0 + (risk_14d - 0.40) * 60.0)

    hi = round(max(0.0, min(100.0, 100.0 - total_penalty)), 1)

    # Determine state (§5.1)
    if hi < 40.0 or risk_14d >= 0.70:
        state = HEALTH_STATE_CRITICAL
        driving = "critical_sensor_drift" if z_penalty >= anomaly_penalty else "high_failure_risk"
    elif hi < 60.0 or risk_14d >= 0.45:
        state = HEALTH_STATE_DEGRADED
        driving = "outlet_or_vibration_degradation"
    elif hi < 80.0 or anomaly_score >= 0.50:
        state = HEALTH_STATE_WATCH
        driving = "early_anomaly_detection"
    else:
        state = HEALTH_STATE_HEALTHY
        driving = "nominal_operation"

    return ComponentHealthResult(
        component_id="",
        health_index=hi,
        state=state,
        driving_factor=driving,
        drop_from_nominal=round(100.0 - hi, 1),
    )


def rollup_system_hi(
    system_id: str,
    component_results: Sequence[tuple[ComponentHealthResult, int]],  # (result, criticality)
) -> RollupHealthResult:
    """Roll up component health indices into a system-level HI.

    Uses weighted average by component criticality (1-5). State reflects the
    worst state among critical components.
    """
    if not component_results:
        return RollupHealthResult(
            node_id=system_id,
            node_type="system",
            health_index=100.0,
            state=HEALTH_STATE_HEALTHY,
            driving_component_id=None,
            driving_component_state=None,
        )

    total_weight = sum(crit for _, crit in component_results)
    weighted_hi_sum = sum(res.health_index * crit for res, crit in component_results)
    sys_hi = round(weighted_hi_sum / max(1, total_weight), 1)

    # Find worst component state
    worst_res = component_results[0][0]
    worst_rank = STATE_SEVERITY_ORDER.get(worst_res.state, 1)

    for res, crit in component_results:
        # Prioritize higher criticality or worse state
        rank = STATE_SEVERITY_ORDER.get(res.state, 1)
        if (rank > worst_rank) or (rank == worst_rank and crit >= 4):
            worst_res = res
            worst_rank = rank

    # If system HI is low, state matches worst critical component
    state = (
        worst_res.state
        if worst_rank >= 3
        else (HEALTH_STATE_WATCH if sys_hi < 80.0 else HEALTH_STATE_HEALTHY)
    )

    return RollupHealthResult(
        node_id=system_id,
        node_type="system",
        health_index=sys_hi,
        state=state,
        driving_component_id=worst_res.component_id or None,
        driving_component_state=worst_res.state,
    )


def rollup_aircraft_hi(
    aircraft_id: str,
    system_results: Sequence[RollupHealthResult],
    critical_components: Sequence[ComponentHealthResult] = (),
) -> RollupHealthResult:
    """Roll up aircraft health index and determine overall availability state.

    Per plan.md §6: An aircraft's state is the worst state among its
    critical components, with the driving component shown.
    """
    if not system_results and not critical_components:
        return RollupHealthResult(
            node_id=aircraft_id,
            node_type="aircraft",
            health_index=100.0,
            state=HEALTH_STATE_HEALTHY,
            driving_component_id=None,
            driving_component_state=None,
        )

    # Simple average of functional systems for aircraft overall HI
    avg_hi = (
        round(sum(s.health_index for s in system_results) / len(system_results), 1)
        if system_results
        else 100.0
    )

    # Find worst among critical components
    worst_driver_id = None
    worst_driver_state = HEALTH_STATE_HEALTHY
    worst_rank = 1

    for comp in critical_components:
        r = STATE_SEVERITY_ORDER.get(comp.state, 1)
        if r > worst_rank:
            worst_rank = r
            worst_driver_state = comp.state
            worst_driver_id = comp.component_id

    # If no critical component flagged, check systems
    if worst_rank <= 2:
        for sys in system_results:
            r = STATE_SEVERITY_ORDER.get(sys.state, 1)
            if r > worst_rank:
                worst_rank = r
                worst_driver_state = sys.state
                worst_driver_id = sys.driving_component_id

    final_state = worst_driver_state

    return RollupHealthResult(
        node_id=aircraft_id,
        node_type="aircraft",
        health_index=avg_hi,
        state=final_state,
        driving_component_id=worst_driver_id,
        driving_component_state=worst_driver_state,
    )
