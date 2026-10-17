"""Digital Twin service providing queries, historical replay, and what-if delegation (§6)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.availability.scenarios import (
    ScenarioEngine,
    build_simulation_config_from_db,
)
from app.core.errors import NotFoundError
from app.models.fleet import Aircraft, Component, ComponentType, System
from app.models.maintenance import MaintenanceEvent, WorkOrder
from app.models.platform import Advisory, Prediction, TwinSnapshot
from app.models.sensors import SensorReading
from app.schemas.twin import (
    DriverComponentOut,
    TwinAircraftNodeOut,
    TwinComponentDetailOut,
    TwinComponentNodeOut,
    TwinFleetOut,
    TwinFleetSummaryAircraftOut,
    TwinMaintenanceEvent,
    TwinSystemNodeOut,
    TwinTrajectoryPoint,
    TwinWhatIfIn,
)
from app.twin.snapshots import build_twin_hierarchy
from app.twin.state_model import (
    DEFAULT_THRESHOLDS,
    TwinHealthState,
    TwinThresholdsConfig,
    determine_health_state,
)

logger = logging.getLogger(__name__)


async def _resolve_latest_date(session: AsyncSession) -> date:
    """Find the most recent telemetry/prediction date in the database."""
    pred_stmt = select(func.max(Prediction.as_of_date))
    pred_res = await session.execute(pred_stmt)
    latest_pred_date = pred_res.scalar()
    if latest_pred_date:
        return latest_pred_date

    snap_stmt = select(func.max(TwinSnapshot.as_of_date))
    snap_res = await session.execute(snap_stmt)
    latest_snap_date = snap_res.scalar()
    if latest_snap_date:
        return latest_snap_date

    return date.today()


async def get_fleet_twin(
    session: AsyncSession,
    as_of: date | None = None,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> TwinFleetOut:
    """Retrieve the fleet-wide digital twin hierarchy and state distribution.

    Supports historical replay when `as_of` date is provided.
    """
    target_date = as_of or await _resolve_latest_date(session)

    # 1. Check if snapshots already exist for target date
    snap_query = select(TwinSnapshot).where(
        TwinSnapshot.as_of_date == target_date,
        TwinSnapshot.node_type == "aircraft",
    )
    snap_res = await session.execute(snap_query)
    aircraft_snaps = snap_res.scalars().all()

    total_ac_res = await session.execute(select(func.count(Aircraft.aircraft_id)))
    total_ac_count = total_ac_res.scalar_one()

    if aircraft_snaps and len(aircraft_snaps) >= total_ac_count and total_ac_count > 0:
        # Build fleet response directly from snapshots
        ac_ids = [s.node_id for s in aircraft_snaps]
        ac_query = select(Aircraft).where(Aircraft.aircraft_id.in_(ac_ids))
        ac_res = await session.execute(ac_query)
        ac_map = {ac.aircraft_id: ac for ac in ac_res.scalars().all()}

        dist = {s.value: 0 for s in TwinHealthState}
        summary_aircraft: list[TwinFleetSummaryAircraftOut] = []
        total_hi = 0.0

        for s in aircraft_snaps:
            dist[s.state] = dist.get(s.state, 0) + 1
            total_hi += s.health_index
            ac = ac_map.get(s.node_id)
            tail = ac.tail_code if ac else s.node_id
            type_code = ac.type_code if ac else "Generic"

            summary_aircraft.append(
                TwinFleetSummaryAircraftOut(
                    aircraft_id=s.node_id,
                    tail_code=tail,
                    type_code=type_code,
                    health_index=round(s.health_index, 1),
                    state=s.state,
                    risk=s.risk,
                    rul_p50=s.rul_p50,
                    driver_component=None,
                )
            )

        mean_hi = total_hi / len(aircraft_snaps) if aircraft_snaps else 100.0

        # Sort aircraft by worst state and lowest HI
        summary_aircraft.sort(key=lambda a: a.health_index)
        driver_id = summary_aircraft[0].aircraft_id if summary_aircraft else None

        return TwinFleetOut(
            node_id="FLEET",
            as_of_date=target_date.isoformat(),
            health_index=round(mean_hi, 1),
            total_aircraft=len(summary_aircraft),
            state_distribution=dist,
            driver_aircraft_id=driver_id,
            aircraft=summary_aircraft,
        )

    # 2. Dynamic roll-up if snapshots not pre-generated for this date
    fleet_item = await build_twin_hierarchy(
        session=session,
        as_of_date=target_date,
        config=config,
    )

    summary_aircraft = []
    for ac in fleet_item.aircraft:
        driver_out = (
            DriverComponentOut(**ac.driver_component.to_dict()) if ac.driver_component else None
        )
        summary_aircraft.append(
            TwinFleetSummaryAircraftOut(
                aircraft_id=ac.aircraft_id,
                tail_code=ac.tail_code,
                type_code=ac.type_code,
                health_index=ac.health_index,
                state=ac.state,
                risk=ac.risk,
                rul_p50=ac.rul_p50,
                driver_component=driver_out,
            )
        )

    return TwinFleetOut(
        node_id="FLEET",
        as_of_date=target_date.isoformat(),
        health_index=fleet_item.health_index,
        total_aircraft=fleet_item.total_aircraft,
        state_distribution=fleet_item.state_distribution,
        driver_aircraft_id=fleet_item.driver_aircraft_id,
        aircraft=summary_aircraft,
    )


async def get_aircraft_twin(
    session: AsyncSession,
    aircraft_id: str,
    as_of: date | None = None,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> TwinAircraftNodeOut:
    """Retrieve full hierarchical Digital Twin model for a single aircraft.

    Includes systems, component states, worst-component driver,
    maintenance history timeline, and degradation trajectory.
    Supports historical replay when `as_of` date is provided.
    """
    # 1. Resolve aircraft
    ac_stmt = select(Aircraft).where(
        (Aircraft.aircraft_id == aircraft_id) | (Aircraft.tail_code == aircraft_id)
    )
    ac_res = await session.execute(ac_stmt)
    aircraft = ac_res.scalars().first()
    if not aircraft:
        raise NotFoundError(f"Aircraft '{aircraft_id}' not found")

    target_date = as_of or await _resolve_latest_date(session)
    is_replay = as_of is not None

    # 2. Build full hierarchy roll-up for this aircraft
    fleet_item = await build_twin_hierarchy(
        session=session,
        as_of_date=target_date,
        aircraft_id=aircraft.aircraft_id,
        config=config,
    )

    if not fleet_item.aircraft:
        raise NotFoundError(f"No component hierarchy found for aircraft '{aircraft.aircraft_id}'")

    ac_item = fleet_item.aircraft[0]

    # Convert systems to schemas
    system_nodes: list[TwinSystemNodeOut] = []
    for s in ac_item.systems:
        comp_nodes = [
            TwinComponentNodeOut(
                component_id=c.component_id,
                component_name=c.component_name,
                part_number=c.part_number,
                serial_number=c.serial_number,
                system_id=c.system_id,
                system_name=c.system_name,
                aircraft_id=c.aircraft_id,
                criticality=c.criticality,
                health_index=c.health_index,
                state=c.state,
                risk=c.risk,
                rul_p50=c.rul_p50,
            )
            for c in s.components
        ]

        sys_driver = (
            DriverComponentOut(**s.driver_component.to_dict()) if s.driver_component else None
        )

        system_nodes.append(
            TwinSystemNodeOut(
                system_id=s.system_id,
                system_name=s.system_name,
                health_index=s.health_index,
                state=s.state,
                risk=s.risk,
                rul_p50=s.rul_p50,
                driver_component=sys_driver,
                components=comp_nodes,
            )
        )

    ac_driver = (
        DriverComponentOut(**ac_item.driver_component.to_dict())
        if ac_item.driver_component
        else None
    )

    # 3. Fetch Maintenance History Timeline
    maint_stmt = (
        select(MaintenanceEvent)
        .where(MaintenanceEvent.aircraft_id == aircraft.aircraft_id)
        .where(MaintenanceEvent.start <= datetime.combine(target_date, datetime.max.time()))
        .order_by(MaintenanceEvent.start.desc())
        .limit(10)
    )
    maint_res = await session.execute(maint_stmt)
    maint_events = maint_res.scalars().all()
    history = [
        TwinMaintenanceEvent(
            event_id=me.event_id,
            event_type=me.type,
            date=me.start.date().isoformat(),
            description=f"{me.action.capitalize()} on {me.component_id or 'aircraft'} ({me.labor_hours:.1f} hrs)",
            status="completed" if me.end else "in_progress",
        )
        for me in maint_events
    ]

    # 4. Degradation Trajectory (Past progression + future projection)
    trajectory: list[TwinTrajectoryPoint] = []
    # Historical trajectory from Predictions / Snapshots
    driver_comp_id = ac_driver.component_id if ac_driver else None
    if driver_comp_id:
        past_preds_stmt = (
            select(Prediction)
            .where(Prediction.component_id == driver_comp_id)
            .where(Prediction.as_of_date <= target_date)
            .order_by(Prediction.as_of_date.asc())
        )
        past_preds_res = await session.execute(past_preds_stmt)
        past_preds = past_preds_res.scalars().all()

        for p in past_preds:
            rul_hi = (p.rul_p50 / 60.0 * 100.0) if p.rul_p50 is not None else 85.0
            r_pen = (p.risk_14d * 40.0) if p.risk_14d is not None else 0.0
            hi_val = max(0.0, min(100.0, rul_hi - r_pen))
            trajectory.append(
                TwinTrajectoryPoint(
                    date=p.as_of_date.isoformat(),
                    health_index=round(hi_val, 1),
                    risk=round(p.risk_14d, 4) if p.risk_14d is not None else None,
                    rul=round(p.rul_p50, 1) if p.rul_p50 is not None else None,
                    is_forecast=False,
                )
            )

    # Ensure current target_date is in trajectory
    if not any(pt.date == target_date.isoformat() for pt in trajectory):
        trajectory.append(
            TwinTrajectoryPoint(
                date=target_date.isoformat(),
                health_index=ac_item.health_index,
                risk=ac_item.risk,
                rul=ac_item.rul_p50,
                is_forecast=False,
            )
        )

    # Future Projected Trajectory (based on RUL)
    cur_rul = ac_item.rul_p50 if ac_item.rul_p50 is not None else 45.0
    cur_hi = ac_item.health_index
    daily_drop = (cur_hi / max(5.0, cur_rul)) if cur_rul > 0 else 2.0

    for day_offset in [5, 10, 15, 20, 30]:
        f_date = target_date + timedelta(days=day_offset)
        proj_hi = max(0.0, cur_hi - daily_drop * day_offset)
        proj_rul = max(0.0, cur_rul - day_offset)
        proj_risk = min(0.99, (ac_item.risk or 0.1) + 0.02 * day_offset)
        trajectory.append(
            TwinTrajectoryPoint(
                date=f_date.isoformat(),
                health_index=round(proj_hi, 1),
                risk=round(proj_risk, 4),
                rul=round(proj_rul, 1),
                is_forecast=True,
            )
        )

    return TwinAircraftNodeOut(
        aircraft_id=aircraft.aircraft_id,
        tail_code=aircraft.tail_code,
        type_code=aircraft.type_code,
        health_index=ac_item.health_index,
        state=ac_item.state,
        risk=ac_item.risk,
        rul_p50=ac_item.rul_p50,
        as_of_date=target_date.isoformat(),
        is_replay=is_replay,
        driver_component=ac_driver,
        systems=system_nodes,
        maintenance_history=history,
        predicted_trajectory=trajectory,
    )


async def get_component_twin(
    session: AsyncSession,
    component_id: str,
    as_of: date | None = None,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> TwinComponentDetailOut:
    """Retrieve detailed digital twin state for a specific component.

    Includes current/replay health state, operating hours, active advisory,
    recent sensor metrics, maintenance history, and degradation trajectory.
    """
    comp_stmt = (
        select(
            Component,
            ComponentType.name.label("component_name"),
            ComponentType.part_number,
            ComponentType.criticality,
            System.system_id,
            System.name.label("system_name"),
        )
        .join(ComponentType, Component.component_type_id == ComponentType.component_type_id)
        .join(System, ComponentType.system_id == System.system_id)
        .where(Component.component_id == component_id)
    )
    comp_res = await session.execute(comp_stmt)
    row = comp_res.first()
    if not row:
        raise NotFoundError(f"Component '{component_id}' not found")

    comp, comp_name, part_num, crit, sys_id, sys_name = row
    target_date = as_of or await _resolve_latest_date(session)
    is_replay = as_of is not None

    # Fetch latest prediction on or before target_date
    pred_stmt = (
        select(Prediction)
        .where(Prediction.component_id == component_id)
        .where(Prediction.as_of_date <= target_date)
        .order_by(Prediction.as_of_date.desc(), Prediction.created_at.desc())
    )
    pred_res = await session.execute(pred_stmt)
    pred = pred_res.scalars().first()

    risk = pred.risk_14d if pred else None
    rul = pred.rul_p50 if pred else None

    # Check for active maintenance
    wo_stmt = (
        select(WorkOrder)
        .where(WorkOrder.component_id == component_id)
        .where(WorkOrder.status.in_(["open", "in_progress", "awaiting_parts"]))
        .where(WorkOrder.opened <= datetime.combine(target_date, datetime.max.time()))
    )
    wo_res = await session.execute(wo_stmt)
    is_maint = wo_res.scalars().first() is not None

    # Active Advisory
    adv_stmt = (
        select(Advisory)
        .where(Advisory.component_id == component_id)
        .where(Advisory.as_of_date <= target_date)
        .order_by(Advisory.as_of_date.desc(), Advisory.created_at.desc())
    )
    adv_res = await session.execute(adv_stmt)
    adv = adv_res.scalars().first()

    # Health Index & State
    if comp.status in ["unserviceable", "failed", "scrapped"]:
        hi = 0.0
    elif (
        adv
        and adv.explanation
        and isinstance(adv.explanation, dict)
        and "health_index" in adv.explanation
    ):
        hi = float(adv.explanation["health_index"])
    elif pred:
        rul_hi = (pred.rul_p50 / 60.0 * 100.0) if pred.rul_p50 is not None else 85.0
        risk_penalty = (pred.risk_14d * 40.0) if pred.risk_14d is not None else 0.0
        hi = max(0.0, min(100.0, rul_hi - risk_penalty))
    else:
        hi = 92.0

    state = determine_health_state(
        health_index=hi,
        risk=risk,
        is_under_maintenance=is_maint,
        is_failed=(comp.status == "failed"),
        config=config,
    )
    adv_dict = (
        {
            "advisory_id": adv.advisory_id,
            "priority": adv.priority,
            "action": adv.action,
            "status": adv.status,
            "spare_status": adv.spare_status,
            "expected_downtime_days": adv.expected_downtime_days,
            "explanation": adv.explanation,
        }
        if adv
        else None
    )

    # Recent Sensor Metrics
    sensor_stmt = (
        select(
            SensorReading.parameter,
            func.avg(SensorReading.mean),
            func.max(SensorReading.max),
            func.min(SensorReading.min),
        )
        .where(SensorReading.component_id == component_id)
        .group_by(SensorReading.parameter)
    )
    sensor_res = await session.execute(sensor_stmt)
    sensor_metrics = {
        row[0]: {
            "avg_mean": round(float(row[1]), 2),
            "max_value": round(float(row[2]), 2),
            "min_value": round(float(row[3]), 2),
        }
        for row in sensor_res.all()
    }

    # Maintenance History
    maint_stmt = (
        select(MaintenanceEvent)
        .where(MaintenanceEvent.component_id == component_id)
        .where(MaintenanceEvent.start <= datetime.combine(target_date, datetime.max.time()))
        .order_by(MaintenanceEvent.start.desc())
        .limit(5)
    )
    maint_res = await session.execute(maint_stmt)
    history = [
        TwinMaintenanceEvent(
            event_id=me.event_id,
            event_type=me.type,
            date=me.start.date().isoformat(),
            description=f"{me.action.capitalize()} action ({me.labor_hours:.1f} hrs)",
            status="completed" if me.end else "in_progress",
        )
        for me in maint_res.scalars().all()
    ]

    # Degradation Trajectory
    trajectory: list[TwinTrajectoryPoint] = []
    past_preds_stmt = (
        select(Prediction)
        .where(Prediction.component_id == component_id)
        .where(Prediction.as_of_date <= target_date)
        .order_by(Prediction.as_of_date.asc())
    )
    past_preds_res = await session.execute(past_preds_stmt)
    for p in past_preds_res.scalars().all():
        rul_h = (p.rul_p50 / 60.0 * 100.0) if p.rul_p50 is not None else 85.0
        r_p = (p.risk_14d * 40.0) if p.risk_14d is not None else 0.0
        h_val = max(0.0, min(100.0, rul_h - r_p))
        trajectory.append(
            TwinTrajectoryPoint(
                date=p.as_of_date.isoformat(),
                health_index=round(h_val, 1),
                risk=round(p.risk_14d, 4) if p.risk_14d is not None else None,
                rul=round(p.rul_p50, 1) if p.rul_p50 is not None else None,
                is_forecast=False,
            )
        )

    if not any(pt.date == target_date.isoformat() for pt in trajectory):
        trajectory.append(
            TwinTrajectoryPoint(
                date=target_date.isoformat(),
                health_index=round(hi, 1),
                risk=round(risk, 4) if risk is not None else None,
                rul=round(rul, 1) if rul is not None else None,
                is_forecast=False,
            )
        )

    # Forward projection
    cur_rul = rul if rul is not None else 45.0
    daily_drop = (hi / max(5.0, cur_rul)) if cur_rul > 0 else 2.0
    for day_offset in [5, 10, 15, 20, 30]:
        f_date = target_date + timedelta(days=day_offset)
        proj_hi = max(0.0, hi - daily_drop * day_offset)
        proj_rul = max(0.0, cur_rul - day_offset)
        proj_risk = min(0.99, (risk or 0.1) + 0.02 * day_offset)
        trajectory.append(
            TwinTrajectoryPoint(
                date=f_date.isoformat(),
                health_index=round(proj_hi, 1),
                risk=round(proj_risk, 4),
                rul=round(proj_rul, 1),
                is_forecast=True,
            )
        )

    return TwinComponentDetailOut(
        component_id=comp.component_id,
        component_name=comp_name,
        part_number=part_num,
        serial_number=comp.serial_no,
        system_id=sys_id,
        system_name=sys_name,
        aircraft_id=comp.aircraft_id or "",
        criticality=crit,
        health_index=round(hi, 1),
        state=state.value,
        risk=round(risk, 4) if risk is not None else None,
        rul_p50=round(rul, 1) if rul is not None else None,
        as_of_date=target_date.isoformat(),
        is_replay=is_replay,
        hours_since_new=comp.hours_since_new,
        operating_hours=comp.hours_since_new - comp.hours_at_install,
        active_advisory=adv_dict,
        recent_sensor_metrics=sensor_metrics,
        maintenance_history=history,
        predicted_trajectory=trajectory,
    )


async def execute_twin_whatif(
    session: AsyncSession,
    whatif_in: TwinWhatIfIn,
    username: str,
) -> dict[str, Any]:
    """Execute digital twin what-if scenario by delegating to ScenarioEngine (§6, §7)."""
    base_config = await build_simulation_config_from_db(
        session=session,
        horizon_days=whatif_in.horizon_days,
        runs=whatif_in.runs,
        seed=whatif_in.seed,
    )

    result = ScenarioEngine.run_scenario(
        scenario_type=whatif_in.type,
        params=whatif_in.params,
        base_config=base_config,
    )

    # Persist scenario run
    from app.availability.scenarios import save_scenario_run

    await save_scenario_run(session=session, scenario_result=result, created_by=username)

    return result
