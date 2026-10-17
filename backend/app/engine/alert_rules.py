"""Platform alert generation rules.

Evaluates operational state and model inferences to fire action-oriented alerts:
  1. risk_threshold: High or critical failure probability detected
  2. spare_shortfall: Required spare lead time exceeds RUL with zero/tight inventory
  3. overdue: Scheduled inspections or maintenance intervals exceeded
  4. backlog: Maintenance queue or open work orders exceeding base workshop capacity
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.advisory import AdvisoryCandidate, GeneratedAdvisory
from app.models.fleet import Aircraft
from app.models.maintenance import ScheduledTask, WorkOrder


@dataclass(frozen=True)
class GeneratedAlert:
    """Structure for an alert to be persisted in the alerts table."""

    type: str  # 'risk_threshold', 'spare_shortfall', 'overdue', 'backlog'
    severity: str  # 'low', 'medium', 'high', 'critical'
    aircraft_id: str | None
    component_id: str | None
    advisory_id: str | None
    message: str


def evaluate_risk_alerts(
    candidates: Sequence[AdvisoryCandidate],
    advisories: Sequence[GeneratedAdvisory],
) -> list[GeneratedAlert]:
    """Generate risk threshold alerts for high or critical probability components."""
    alerts: list[GeneratedAlert] = []
    adv_by_comp = {adv.component_id: adv for adv in advisories}

    for c in candidates:
        adv = adv_by_comp.get(c.component_id)
        adv_id = adv.advisory_id if adv else None

        if c.risk_14d >= 0.70 or c.health_state == "Critical":
            alerts.append(
                GeneratedAlert(
                    type="risk_threshold",
                    severity="critical",
                    aircraft_id=c.aircraft_id,
                    component_id=c.component_id,
                    advisory_id=adv_id,
                    message=(
                        f"CRITICAL RISK: {c.tail_code} {c.component_name} shows 14-day failure risk "
                        f"of {c.risk_14d:.2f} (RUL ~{c.rul_p50:.0f} days). Action: {adv.action if adv else 'Inspect'}."
                    ),
                )
            )
        elif c.risk_14d >= 0.45 or c.health_state == "Degraded":
            alerts.append(
                GeneratedAlert(
                    type="risk_threshold",
                    severity="high",
                    aircraft_id=c.aircraft_id,
                    component_id=c.component_id,
                    advisory_id=adv_id,
                    message=(
                        f"HIGH RISK: {c.tail_code} {c.component_name} degrading (HI {c.health_index:.0f}/100, "
                        f"risk {c.risk_14d:.2f}). Priority {adv.priority if adv else 'P2'}."
                    ),
                )
            )

    return alerts


def evaluate_spare_shortfall_alerts(
    candidates: Sequence[AdvisoryCandidate],
    advisories: Sequence[GeneratedAdvisory],
) -> list[GeneratedAlert]:
    """Generate spare shortfall alerts when lead time exceeds RUL under tight stock."""
    alerts: list[GeneratedAlert] = []
    adv_by_comp = {adv.component_id: adv for adv in advisories}

    for c in candidates:
        if not c.spares.has_shortfall_risk or c.risk_14d < 0.20:
            continue

        adv = adv_by_comp.get(c.component_id)
        adv_id = adv.advisory_id if adv else None

        severity = "critical" if (c.spares.available == 0 and c.risk_14d >= 0.45) else "high"
        alerts.append(
            GeneratedAlert(
                type="spare_shortfall",
                severity=severity,
                aircraft_id=c.aircraft_id,
                component_id=c.component_id,
                advisory_id=adv_id,
                message=(
                    f"SPARES SHORTFALL RISK: {c.spares.part_number} for {c.tail_code}. Available: "
                    f"{c.spares.available} unit(s). Lead time ({c.spares.lead_time_days} days) "
                    f"exceeds component RUL (~{c.rul_p50:.0f} days)."
                ),
            )
        )

    return alerts


async def evaluate_overdue_alerts(
    session: AsyncSession,
    as_of_date: date,
) -> list[GeneratedAlert]:
    """Identify overdue periodic inspections and flight hour service intervals."""
    alerts: list[GeneratedAlert] = []

    # Join scheduled tasks with current aircraft flight hours
    query = (
        select(ScheduledTask, Aircraft.total_flight_hours, Aircraft.tail_code)
        .join(Aircraft, ScheduledTask.aircraft_id == Aircraft.aircraft_id)
        .where(
            (ScheduledTask.due_date.is_not(None) & (ScheduledTask.due_date < as_of_date))
            | (ScheduledTask.due_hours <= Aircraft.total_flight_hours)
        )
    )
    res = await session.execute(query)
    rows = res.all()

    for task, total_hours, tail_code in rows:
        is_date_overdue = task.due_date is not None and task.due_date < as_of_date
        overdue_days = (as_of_date - task.due_date).days if is_date_overdue and task.due_date else 0
        hours_over = round(total_hours - task.due_hours, 1)

        severity = "high" if overdue_days > 14 or hours_over > 50 else "medium"

        alerts.append(
            GeneratedAlert(
                type="overdue",
                severity=severity,
                aircraft_id=task.aircraft_id,
                component_id=None,
                advisory_id=None,
                message=(
                    f"OVERDUE INSPECTION: {task.task_name} on {tail_code} is past due "
                    f"({overdue_days} days overdue, {hours_over} hrs beyond limit)."
                ),
            )
        )

    return alerts


async def evaluate_backlog_alerts(
    session: AsyncSession,
    advisories: Sequence[GeneratedAdvisory],
) -> list[GeneratedAlert]:
    """Assess whether active maintenance work orders and open advisories exceed agency capacity."""
    alerts: list[GeneratedAlert] = []

    # Count open/in-progress work orders
    wo_count_query = select(func.count(WorkOrder.wo_id)).where(
        WorkOrder.status.in_(["opened", "in_progress", "waiting_spares", "scheduled"])
    )
    wo_res = await session.execute(wo_count_query)
    open_wo_count = wo_res.scalar() or 0

    # Count open P1/P2 advisories
    high_prio_adv_count = sum(1 for a in advisories if a.priority in ("P1", "P2"))

    if open_wo_count >= 15 or high_prio_adv_count >= 8:
        alerts.append(
            GeneratedAlert(
                type="backlog",
                severity="high" if open_wo_count >= 25 else "medium",
                aircraft_id=None,
                component_id=None,
                advisory_id=None,
                message=(
                    f"MAINTENANCE BACKLOG ALERT: {open_wo_count} active work orders and "
                    f"{high_prio_adv_count} high-priority advisories queued across workshop bays."
                ),
            )
        )

    return alerts
