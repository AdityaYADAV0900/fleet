"""Fleet availability and maintenance KPI calculation engine.

Implements all core KPIs defined in docs/plan.md §1.8 and §7:
- Fleet availability (% aircraft-days available)
- Inherent availability (Ai) and Operational availability (Ao)
- Aircraft serviceability (snapshot fraction available)
- Downtime split by cause (scheduled, unscheduled, supply wait, agency wait)
- Mean Time Between Failures (MTBF)
- Mean Time To Repair (MTTR)
- Maintenance turnaround time
- Failure rate (failures per 1,000 flight hours)
- Maintenance backlog (open orders and man-hours)
- Readiness proxy (% available with no open P1/P2 advisory)
- Spare fill rate (% demands fulfilled without stock-out delay)
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import Aircraft, AircraftDailyStatus, Component, ComponentType
from app.models.maintenance import MaintenanceEvent, WorkOrder
from app.models.platform import Advisory
from app.models.sensors import Flight
from app.models.spares import Inventory, InventoryTransaction

# =====================================================================
# PURE CALCULATION FUNCTIONS (Unit-testable with deterministic fixtures)
# =====================================================================


def calculate_fleet_availability(days_by_state: dict[str, int]) -> float:
    """Calculate fleet availability percentage across a period (§1.8).

    Fleet availability (%) = (sum of aircraft-days in Available state) / (sum of aircraft-days in period) * 100
    """
    available_days = days_by_state.get("Available", 0)
    total_days = sum(days_by_state.values())
    if total_days <= 0:
        return 100.0
    return round((available_days / total_days) * 100.0, 2)


def calculate_inherent_availability(mtbf_hours: float, mttr_hours: float) -> float:
    """Calculate Inherent Availability Ai = MTBF / (MTBF + MTTR).

    Reflects the design-limited availability without supply or administrative delay.
    Returns value as a percentage (0 - 100%).
    """
    total = mtbf_hours + mttr_hours
    if total <= 0:
        return 100.0
    return round((mtbf_hours / total) * 100.0, 2)


def calculate_operational_availability(mtbm_hours: float, mdt_hours: float) -> float:
    """Calculate Operational Availability Ao = MTBM / (MTBM + MDT).

    Reflects actual field availability including supply delay and workshop queues.
    Returns value as a percentage (0 - 100%).
    """
    total = mtbm_hours + mdt_hours
    if total <= 0:
        return 100.0
    return round((mtbm_hours / total) * 100.0, 2)


def calculate_serviceability(available_count: int, total_count: int) -> float:
    """Calculate aircraft serviceability as percentage of fleet currently available."""
    if total_count <= 0:
        return 100.0
    return round((available_count / total_count) * 100.0, 2)


def calculate_downtime_by_cause(days_by_state: dict[str, int]) -> dict[str, Any]:
    """Calculate aircraft-days lost split by cause (§7).

    Causes:
    - scheduled: 'Scheduled Maintenance'
    - unscheduled: 'Unscheduled Repair'
    - supply_wait: 'Awaiting Spares'
    - agency_wait: 'Awaiting Workshop'
    """
    scheduled = days_by_state.get("Scheduled Maintenance", 0)
    unscheduled = days_by_state.get("Unscheduled Repair", 0)
    supply_wait = days_by_state.get("Awaiting Spares", 0)
    agency_wait = days_by_state.get("Awaiting Workshop", 0)
    total_downtime = scheduled + unscheduled + supply_wait + agency_wait

    if total_downtime > 0:
        pcts = {
            "scheduled_pct": round((scheduled / total_downtime) * 100.0, 2),
            "unscheduled_pct": round((unscheduled / total_downtime) * 100.0, 2),
            "supply_wait_pct": round((supply_wait / total_downtime) * 100.0, 2),
            "agency_wait_pct": round((agency_wait / total_downtime) * 100.0, 2),
        }
    else:
        pcts = {
            "scheduled_pct": 0.0,
            "unscheduled_pct": 0.0,
            "supply_wait_pct": 0.0,
            "agency_wait_pct": 0.0,
        }

    return {
        "scheduled_days": scheduled,
        "unscheduled_days": unscheduled,
        "supply_wait_days": supply_wait,
        "agency_wait_days": agency_wait,
        "total_downtime_days": total_downtime,
        **pcts,
    }


def calculate_mtbf(operating_hours: float, failure_count: int) -> float:
    """Mean Time Between Failures = Operating hours / number of failures."""
    if failure_count <= 0:
        return round(operating_hours, 2) if operating_hours > 0 else 0.0
    return round(operating_hours / failure_count, 2)


def calculate_mttr(repair_times_hours: Sequence[float]) -> float:
    """Mean Time To Repair = Mean active repair duration (hours)."""
    if not repair_times_hours:
        return 0.0
    return round(sum(repair_times_hours) / len(repair_times_hours), 2)


def calculate_turnaround(turnaround_days: Sequence[float]) -> float:
    """Mean Turnaround Time = Mean days from work-order open to release."""
    if not turnaround_days:
        return 0.0
    return round(sum(turnaround_days) / len(turnaround_days), 2)


def calculate_failure_rate(failure_count: int, total_flight_hours: float) -> float:
    """Failures per 1,000 flight hours = (failures / total_flight_hours) * 1000."""
    if total_flight_hours <= 0:
        return 0.0
    return round((failure_count / total_flight_hours) * 1000.0, 2)


def calculate_backlog(open_orders_count: int, outstanding_labor_hours: float) -> dict[str, Any]:
    """Maintenance backlog metrics: open work orders and estimated man-hours."""
    return {
        "open_orders": open_orders_count,
        "outstanding_man_hours": round(outstanding_labor_hours, 1),
    }


def calculate_readiness_proxy(
    available_aircraft_ids: set[str],
    at_risk_aircraft_ids: set[str],
    total_aircraft: int,
) -> float:
    """Readiness proxy (§7): fraction of aircraft available with NO open P1/P2 advisory.

    Clearly labeled as decision-support proxy, not operational military readiness.
    """
    if total_aircraft <= 0:
        return 100.0
    ready_count = len(available_aircraft_ids - at_risk_aircraft_ids)
    return round((ready_count / total_aircraft) * 100.0, 2)


def calculate_spare_fill_rate(immediate_issues: int, total_demands: int) -> float:
    """Spare parts fill rate (% requests satisfied immediately from on-hand stock)."""
    if total_demands <= 0:
        return 100.0
    return round((immediate_issues / total_demands) * 100.0, 2)


# =====================================================================
# DATABASE QUERIES & FLEET METRICS AGGREGATION
# =====================================================================


async def fetch_fleet_kpis(
    session: AsyncSession,
    from_date: date | None = None,
    to_date: date | None = None,
    group_by: str | None = None,
) -> dict[str, Any]:
    """Query DB tables and calculate comprehensive fleet KPIs for the specified date range."""
    # 1. Total aircraft count
    total_ac_res = await session.execute(select(func.count(Aircraft.aircraft_id)))
    total_aircraft = total_ac_res.scalar_one() or 0

    # 2. Daily statuses for availability and downtime by cause
    status_stmt = select(
        AircraftDailyStatus.status,
        func.count(AircraftDailyStatus.id).label("cnt"),
    )
    if from_date:
        status_stmt = status_stmt.where(AircraftDailyStatus.date >= from_date)
    if to_date:
        status_stmt = status_stmt.where(AircraftDailyStatus.date <= to_date)
    status_stmt = status_stmt.group_by(AircraftDailyStatus.status)

    status_res = await session.execute(status_stmt)
    days_by_state = {row.status: row.cnt for row in status_res.all()}

    availability_pct = calculate_fleet_availability(days_by_state)
    downtime_split = calculate_downtime_by_cause(days_by_state)

    # 3. Snapshot serviceability (latest daily status per aircraft)
    latest_status_subq = select(
        AircraftDailyStatus.aircraft_id,
        AircraftDailyStatus.status,
        func.row_number()
        .over(
            partition_by=AircraftDailyStatus.aircraft_id,
            order_by=AircraftDailyStatus.date.desc(),
        )
        .label("rn"),
    ).subquery()
    latest_stmt = select(latest_status_subq.c.aircraft_id, latest_status_subq.c.status).where(
        latest_status_subq.c.rn == 1
    )
    latest_res = await session.execute(latest_stmt)
    latest_rows = latest_res.all()
    available_aircraft_ids = {row[0] for row in latest_rows if row[1] == "Available"}
    serviceability_pct = calculate_serviceability(len(available_aircraft_ids), total_aircraft)

    # 4. Total flight hours in period
    flight_stmt = select(func.sum(Flight.duration_hours))
    if from_date:
        flight_stmt = flight_stmt.where(Flight.date >= from_date)
    if to_date:
        flight_stmt = flight_stmt.where(Flight.date <= to_date)
    flight_res = await session.execute(flight_stmt)
    total_flight_hours = float(flight_res.scalar_one() or 0.0)

    # Fallback to aircraft total_flight_hours if flights not logged in period
    if total_flight_hours <= 0:
        ac_hours_res = await session.execute(select(func.sum(Aircraft.total_flight_hours)))
        total_flight_hours = float(ac_hours_res.scalar_one() or 0.0)

    # 5. Maintenance events (failures, repairs, labor hours)
    me_stmt = select(MaintenanceEvent)
    if from_date:
        me_stmt = me_stmt.where(func.date(MaintenanceEvent.start) >= from_date)
    if to_date:
        me_stmt = me_stmt.where(func.date(MaintenanceEvent.start) <= to_date)
    me_res = await session.execute(me_stmt)
    maint_events = me_res.scalars().all()

    unscheduled_events = [e for e in maint_events if e.type == "unscheduled"]
    failure_count = len(unscheduled_events)

    # MTTR: repair durations (labor hours) for unscheduled maintenance
    repair_durations = [e.labor_hours for e in unscheduled_events if e.labor_hours > 0]
    mttr_hours = calculate_mttr(repair_durations)

    # MTBF
    mtbf_hours = calculate_mtbf(total_flight_hours, failure_count)

    # Ai (Inherent)
    ai_pct = calculate_inherent_availability(mtbf_hours, mttr_hours)

    # Ao (Operational): Mean Time Between Maintenance (MTBM) and Mean Downtime (MDT)
    total_maint_count = len(maint_events)
    mtbm_hours = (
        round(total_flight_hours / total_maint_count, 2)
        if total_maint_count > 0 and total_flight_hours > 0
        else mtbf_hours
    )
    total_downtime_hours = downtime_split["total_downtime_days"] * 24.0
    mdt_hours = (
        round(total_downtime_hours / total_maint_count, 2)
        if total_maint_count > 0
        else (mttr_hours if mttr_hours > 0 else 24.0)
    )
    ao_pct = calculate_operational_availability(mtbm_hours, mdt_hours)

    # Failure rate per 1,000 flight hours
    failure_rate = calculate_failure_rate(failure_count, total_flight_hours)

    # 6. Turnaround time from completed work orders
    wo_stmt = select(WorkOrder)
    if from_date:
        wo_stmt = wo_stmt.where(func.date(WorkOrder.opened) >= from_date)
    if to_date:
        wo_stmt = wo_stmt.where(func.date(WorkOrder.opened) <= to_date)
    wo_res = await session.execute(wo_stmt)
    all_work_orders = wo_res.scalars().all()

    turnaround_days_list = []
    for wo in all_work_orders:
        if wo.status == "completed" and wo.actual_done and wo.opened:
            delta_days = (wo.actual_done - wo.opened).total_seconds() / 86400.0
            if delta_days >= 0:
                turnaround_days_list.append(delta_days)
    avg_turnaround_days = calculate_turnaround(turnaround_days_list)

    # 7. Backlog (open / in-progress work orders)
    open_statuses = {"open", "in_progress", "awaiting_spares", "awaiting_agency"}
    open_work_orders = [wo for wo in all_work_orders if wo.status in open_statuses]
    open_count = len(open_work_orders)
    # Estimate 8.0 man-hours per open order if not explicitly linked
    outstanding_man_hours = open_count * 8.0
    backlog_metrics = calculate_backlog(open_count, outstanding_man_hours)

    # 8. Readiness proxy: available aircraft without active P1 or P2 advisories
    adv_stmt = (
        select(Component.aircraft_id)
        .join(Advisory, Component.component_id == Advisory.component_id)
        .where(
            Advisory.status.in_(["proposed", "accepted", "scheduled"]),
            Advisory.priority.in_(["P1", "P2"]),
            Component.aircraft_id.is_not(None),
        )
    )
    adv_res = await session.execute(adv_stmt)
    p1_p2_aircraft_ids = {row[0] for row in adv_res.all() if row[0]}
    readiness_proxy_pct = calculate_readiness_proxy(
        available_aircraft_ids, p1_p2_aircraft_ids, total_aircraft
    )

    # 9. Spares fill rate
    # From transactions: issues with zero delay vs total issue transactions
    txn_stmt = select(InventoryTransaction).where(InventoryTransaction.type == "issue")
    if from_date:
        txn_stmt = txn_stmt.where(func.date(InventoryTransaction.date) >= from_date)
    if to_date:
        txn_stmt = txn_stmt.where(func.date(InventoryTransaction.date) <= to_date)
    txn_res = await session.execute(txn_stmt)
    issue_txns = txn_res.scalars().all()

    # If orders experienced awaiting_spares, consider those delayed
    awaiting_spares_orders = [wo for wo in all_work_orders if wo.status == "awaiting_spares"]
    total_demands = max(len(issue_txns), len(all_work_orders))
    delayed_demands = len(awaiting_spares_orders) + downtime_split["supply_wait_days"]
    immediate_demands = max(0, total_demands - min(total_demands, delayed_demands))
    spare_fill_rate_pct = calculate_spare_fill_rate(immediate_demands, total_demands)

    # Optional group_by component type
    by_component_type: list[dict[str, Any]] = []
    if group_by == "component_type":
        ct_stmt = select(ComponentType).order_by(ComponentType.component_type_id)
        ct_res = await session.execute(ct_stmt)
        for ct in ct_res.scalars().all():
            comp_events = [
                e
                for e in maint_events
                if e.component_id and e.component_id.startswith(ct.component_type_id.split("-")[0])
            ]
            c_fails = len([e for e in comp_events if e.type == "unscheduled"])
            c_repairs = [e.labor_hours for e in comp_events if e.labor_hours > 0]
            by_component_type.append(
                {
                    "component_type_id": ct.component_type_id,
                    "name": ct.name,
                    "failures": c_fails,
                    "mtbf_spec": ct.mtbf_hours,
                    "calculated_mtbf": calculate_mtbf(total_flight_hours, c_fails),
                    "mttr_hours": calculate_mttr(c_repairs),
                }
            )

    return {
        "fleet_availability_pct": availability_pct,
        "inherent_availability_pct": ai_pct,
        "operational_availability_pct": ao_pct,
        "serviceability_pct": serviceability_pct,
        "downtime_by_cause": downtime_split,
        "mtbf_hours": mtbf_hours,
        "mttr_hours": mttr_hours,
        "turnaround_days": avg_turnaround_days,
        "failure_rate_per_1000_hours": failure_rate,
        "backlog": backlog_metrics,
        "readiness_proxy_pct": readiness_proxy_pct,
        "spare_fill_rate_pct": spare_fill_rate_pct,
        "total_aircraft": total_aircraft,
        "total_flight_hours": round(total_flight_hours, 1),
        "by_component_type": by_component_type,
    }


async def fetch_fleet_summary(
    session: AsyncSession,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Fetch high-level dashboard summary metrics as of a specific date (§10)."""
    # 1. Total aircraft
    ac_count_res = await session.execute(select(func.count(Aircraft.aircraft_id)))
    total_aircraft = ac_count_res.scalar_one() or 0

    # 2. Latest status per aircraft as of date
    latest_status_subq = select(
        AircraftDailyStatus.aircraft_id,
        AircraftDailyStatus.status,
        func.row_number()
        .over(
            partition_by=AircraftDailyStatus.aircraft_id,
            order_by=AircraftDailyStatus.date.desc(),
        )
        .label("rn"),
    )
    if as_of:
        latest_status_subq = latest_status_subq.where(AircraftDailyStatus.date <= as_of)
    latest_status_subq = latest_status_subq.subquery()

    stmt = (
        select(latest_status_subq.c.status, func.count())
        .where(latest_status_subq.c.rn == 1)
        .group_by(latest_status_subq.c.status)
    )
    res = await session.execute(stmt)
    by_state = {row[0]: row[1] for row in res.all()}

    # Ensure all states exist in map
    for s in [
        "Available",
        "Scheduled Maintenance",
        "Unscheduled Repair",
        "Awaiting Spares",
        "Awaiting Workshop",
    ]:
        by_state.setdefault(s, 0)

    serviceable_count = by_state.get("Available", 0)
    availability_pct = calculate_serviceability(serviceable_count, total_aircraft)

    # 3. Open P1 and P2 advisories count
    adv_p1_stmt = select(func.count(Advisory.advisory_id)).where(
        Advisory.priority == "P1",
        Advisory.status.in_(["proposed", "accepted", "scheduled"]),
    )
    adv_p2_stmt = select(func.count(Advisory.advisory_id)).where(
        Advisory.priority == "P2",
        Advisory.status.in_(["proposed", "accepted", "scheduled"]),
    )
    if as_of:
        adv_p1_stmt = adv_p1_stmt.where(Advisory.as_of_date <= as_of)
        adv_p2_stmt = adv_p2_stmt.where(Advisory.as_of_date <= as_of)

    p1_res = await session.execute(adv_p1_stmt)
    p2_res = await session.execute(adv_p2_stmt)
    open_p1 = p1_res.scalar_one() or 0
    open_p2 = p2_res.scalar_one() or 0

    # 4. Backlog: open work orders
    wo_stmt = select(func.count(WorkOrder.wo_id)).where(
        WorkOrder.status.in_(["open", "in_progress", "awaiting_spares", "awaiting_agency"])
    )
    if as_of:
        wo_stmt = wo_stmt.where(func.date(WorkOrder.opened) <= as_of)
    wo_res = await session.execute(wo_stmt)
    backlog_count = wo_res.scalar_one() or 0
    backlog = {
        "open_orders": backlog_count,
        "man_hours": round(backlog_count * 8.0, 1),
    }

    # 5. Parts at risk (stock <= reorder_level)
    from app.models.spares import SparePart

    inv_stmt = (
        select(func.count(Inventory.inventory_id))
        .join(SparePart, Inventory.part_number == SparePart.part_number)
        .where(Inventory.on_hand <= SparePart.reorder_level)
    )
    inv_res = await session.execute(inv_stmt)
    parts_at_risk = inv_res.scalar_one() or 0

    return {
        "as_of": as_of.isoformat() if as_of else datetime.utcnow().date().isoformat(),
        "total_aircraft": total_aircraft,
        "serviceable_count": serviceable_count,
        "availability_pct": availability_pct,
        "by_state": by_state,
        "open_p1": open_p1,
        "open_p2": open_p2,
        "backlog": backlog,
        "parts_at_risk": parts_at_risk,
    }
