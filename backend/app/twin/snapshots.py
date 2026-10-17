"""Snapshot writer and persistence service for Digital Twin replay (§6).

Persists hierarchical health states to `twin_snapshots` table:
- fleet ('FLEET')
- aircraft (aircraft_id, e.g. 'AC-001')
- system (f"{aircraft_id}:{system_id}")
- component (component_id, e.g. 'CMP-00001')

Called automatically after each predictive maintenance scoring job,
and provides historical state queries for replay across time.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import Aircraft, Component, ComponentType, System
from app.models.maintenance import WorkOrder
from app.models.platform import Advisory, Prediction, TwinSnapshot
from app.twin.rollup import (
    AircraftTwinItem,
    ComponentTwinItem,
    FleetTwinItem,
    SystemTwinItem,
    roll_up_aircraft,
    roll_up_fleet,
    roll_up_system,
)
from app.twin.state_model import (
    DEFAULT_THRESHOLDS,
    TwinHealthState,
    TwinThresholdsConfig,
    determine_health_state,
    get_worst_state,
)

logger = logging.getLogger(__name__)


async def build_twin_hierarchy(
    session: AsyncSession,
    as_of_date: date,
    aircraft_id: str | None = None,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> FleetTwinItem:
    """Query current database state and build full hierarchical Digital Twin roll-up."""
    # 1. Fetch Aircraft
    ac_query = select(Aircraft).order_by(Aircraft.aircraft_id)
    if aircraft_id:
        ac_query = ac_query.where(
            (Aircraft.aircraft_id == aircraft_id) | (Aircraft.tail_code == aircraft_id)
        )
    ac_res = await session.execute(ac_query)
    aircraft_list = ac_res.scalars().all()

    if not aircraft_list:
        return roll_up_fleet([])

    target_ac_ids = [ac.aircraft_id for ac in aircraft_list]

    # 2. Fetch Components with Types and Systems
    comp_query = (
        select(
            Component.component_id,
            Component.serial_no,
            Component.aircraft_id,
            Component.status,
            ComponentType.component_type_id,
            ComponentType.name.label("component_name"),
            ComponentType.part_number,
            ComponentType.criticality,
            System.system_id,
            System.name.label("system_name"),
        )
        .join(ComponentType, Component.component_type_id == ComponentType.component_type_id)
        .join(System, ComponentType.system_id == System.system_id)
        .where(Component.aircraft_id.in_(target_ac_ids))
        .where(Component.status == "installed")
        .order_by(Component.component_id)
    )
    comp_res = await session.execute(comp_query)
    components_raw = comp_res.all()

    comp_ids = [c.component_id for c in components_raw]

    # 3. Fetch latest Predictions on or before as_of_date
    pred_query = (
        select(Prediction)
        .where(Prediction.component_id.in_(comp_ids))
        .where(Prediction.as_of_date <= as_of_date)
        .order_by(Prediction.as_of_date.desc(), Prediction.created_at.desc())
    )
    pred_res = await session.execute(pred_query)
    latest_preds: dict[str, Prediction] = {}
    for p in pred_res.scalars().all():
        if p.component_id not in latest_preds:
            latest_preds[p.component_id] = p

    # 3b. Fetch latest Advisories on or before as_of_date for exact engine HI alignment
    adv_query = (
        select(Advisory)
        .where(Advisory.component_id.in_(comp_ids))
        .where(Advisory.as_of_date <= as_of_date)
        .order_by(Advisory.as_of_date.desc(), Advisory.created_at.desc())
    )
    adv_res = await session.execute(adv_query)
    latest_advs: dict[str, Advisory] = {}
    for a in adv_res.scalars().all():
        if a.component_id not in latest_advs:
            latest_advs[a.component_id] = a

    # 4. Fetch Active Work Orders on as_of_date to flag 'Under maintenance'
    wo_query = (
        select(WorkOrder.aircraft_id, WorkOrder.component_id)
        .where(WorkOrder.aircraft_id.in_(target_ac_ids))
        .where(WorkOrder.status.in_(["open", "in_progress", "awaiting_parts"]))
        .where(WorkOrder.opened <= datetime.combine(as_of_date, datetime.max.time()))
    )
    wo_res = await session.execute(wo_query)
    active_maint_ac: set[str] = set()
    active_maint_comp: set[str] = set()
    for row in wo_res.all():
        if row.aircraft_id:
            active_maint_ac.add(row.aircraft_id)
        if row.component_id:
            active_maint_comp.add(row.component_id)

    # 5. Build Component Twin Items grouped by aircraft and system
    # Structure: ac_id -> sys_id -> list[ComponentTwinItem]
    grouped_comps: dict[str, dict[str, list[ComponentTwinItem]]] = {
        ac.aircraft_id: {} for ac in aircraft_list
    }
    sys_names: dict[str, str] = {}

    for c in components_raw:
        ac_id = c.aircraft_id
        sys_id = c.system_id
        sys_names[sys_id] = c.system_name

        pred = latest_preds.get(c.component_id)
        adv = latest_advs.get(c.component_id)
        risk = pred.risk_14d if pred else None
        rul_p50 = pred.rul_p50 if pred else None

        # Derive Health Index:
        is_maint = c.component_id in active_maint_comp
        is_failed = c.status in ["unserviceable", "failed", "scrapped"]

        if is_failed:
            hi = 0.0
        elif (
            adv
            and adv.explanation
            and isinstance(adv.explanation, dict)
            and "health_index" in adv.explanation
        ):
            hi = float(adv.explanation["health_index"])
        elif pred is not None:
            # Map RUL and Risk to health index (HI in 0-100)
            if pred.rul_p50 is not None:
                rul_hi = min(100.0, max(0.0, (pred.rul_p50 / 60.0) * 100.0))
            else:
                rul_hi = 85.0
            risk_penalty = (pred.risk_14d * 40.0) if pred.risk_14d is not None else 0.0
            hi = max(0.0, min(100.0, rul_hi - risk_penalty))
        else:
            hi = 92.0  # Nominal unflagged part

        state = determine_health_state(
            health_index=hi,
            risk=risk,
            is_under_maintenance=is_maint,
            is_failed=is_failed,
            config=config,
        )

        item = ComponentTwinItem(
            component_id=c.component_id,
            component_name=c.component_name,
            part_number=c.part_number,
            serial_number=c.serial_no,
            system_id=sys_id,
            system_name=c.system_name,
            aircraft_id=ac_id,
            criticality=c.criticality,
            health_index=round(hi, 1),
            state=state.value,
            risk=risk,
            rul_p50=rul_p50,
        )

        if sys_id not in grouped_comps[ac_id]:
            grouped_comps[ac_id][sys_id] = []
        grouped_comps[ac_id][sys_id].append(item)

    # 6. Roll-up systems and aircraft
    aircraft_twin_items: list[AircraftTwinItem] = []
    for ac in aircraft_list:
        sys_twin_items: list[SystemTwinItem] = []
        for sys_id, c_list in grouped_comps[ac.aircraft_id].items():
            s_name = sys_names.get(sys_id, sys_id)
            sys_item = roll_up_system(
                system_id=sys_id,
                system_name=s_name,
                aircraft_id=ac.aircraft_id,
                components=c_list,
            )
            sys_twin_items.append(sys_item)

        is_ac_maint = ac.aircraft_id in active_maint_ac
        ac_item = roll_up_aircraft(
            aircraft_id=ac.aircraft_id,
            tail_code=ac.tail_code,
            type_code=ac.type_code,
            systems=sys_twin_items,
            is_aircraft_under_maintenance=is_ac_maint,
            is_aircraft_failed=False,
        )
        aircraft_twin_items.append(ac_item)

    # 7. Fleet Roll-Up
    return roll_up_fleet(aircraft_twin_items)


async def write_twin_snapshots(
    session: AsyncSession,
    as_of_date: date,
    aircraft_id: str | None = None,
    config: TwinThresholdsConfig = DEFAULT_THRESHOLDS,
) -> int:
    """Build hierarchy roll-up and write snapshots to `twin_snapshots` table (§6).

    Idempotent: removes existing snapshots for the given date and scope before writing.
    Returns the count of snapshots written.
    """
    fleet_twin = await build_twin_hierarchy(
        session=session,
        as_of_date=as_of_date,
        aircraft_id=aircraft_id,
        config=config,
    )

    now_utc = datetime.now(UTC)
    snapshots_to_insert: list[dict[str, Any]] = []

    # 1. Fleet Snapshot (only when writing full fleet)
    if not aircraft_id:
        snapshots_to_insert.append(
            {
                "node_type": "fleet",
                "node_id": "FLEET",
                "as_of_date": as_of_date,
                "health_index": fleet_twin.health_index,
                "state": get_worst_state([ac.state for ac in fleet_twin.aircraft]).value
                if fleet_twin.aircraft
                else TwinHealthState.HEALTHY.value,
                "risk": round(
                    sum(ac.risk or 0.0 for ac in fleet_twin.aircraft) / len(fleet_twin.aircraft), 4
                )
                if fleet_twin.aircraft
                else 0.0,
                "rul_p50": min(
                    (ac.rul_p50 for ac in fleet_twin.aircraft if ac.rul_p50 is not None),
                    default=None,
                ),
                "created_at": now_utc,
            }
        )

    # 2. Aircraft, System, and Component Snapshots
    for ac in fleet_twin.aircraft:
        snapshots_to_insert.append(
            {
                "node_type": "aircraft",
                "node_id": ac.aircraft_id,
                "as_of_date": as_of_date,
                "health_index": ac.health_index,
                "state": ac.state,
                "risk": ac.risk,
                "rul_p50": ac.rul_p50,
                "created_at": now_utc,
            }
        )

        for sys_item in ac.systems:
            snapshots_to_insert.append(
                {
                    "node_type": "system",
                    "node_id": f"{ac.aircraft_id}:{sys_item.system_id}",
                    "as_of_date": as_of_date,
                    "health_index": sys_item.health_index,
                    "state": sys_item.state,
                    "risk": sys_item.risk,
                    "rul_p50": sys_item.rul_p50,
                    "created_at": now_utc,
                }
            )

            for comp in sys_item.components:
                snapshots_to_insert.append(
                    {
                        "node_type": "component",
                        "node_id": comp.component_id,
                        "as_of_date": as_of_date,
                        "health_index": comp.health_index,
                        "state": comp.state,
                        "risk": comp.risk,
                        "rul_p50": comp.rul_p50,
                        "created_at": now_utc,
                    }
                )

    if not snapshots_to_insert:
        return 0

    # Clean existing snapshots for idempotent writes
    node_ids = [s["node_id"] for s in snapshots_to_insert]
    del_stmt = (
        delete(TwinSnapshot)
        .where(TwinSnapshot.as_of_date == as_of_date)
        .where(TwinSnapshot.node_id.in_(node_ids))
    )
    await session.execute(del_stmt)

    # Insert new snapshots
    for s_dict in snapshots_to_insert:
        session.add(TwinSnapshot(**s_dict))

    await session.commit()
    logger.info(
        f"Wrote {len(snapshots_to_insert)} twin snapshots for date={as_of_date} "
        f"(aircraft_filter={aircraft_id or 'ALL'})"
    )
    return len(snapshots_to_insert)
