"""Predictive maintenance engine service: predictions, advisories, alerts, and batch job orchestration."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError, ValidationError
from app.engine.advisory import validate_advisory_transition
from app.engine.scoring_job import EngineRunSummary, run_scoring_job
from app.models.fleet import Aircraft, Component, ComponentType, System
from app.models.platform import Advisory, Alert, Prediction
from app.schemas.common import PaginatedResponse
from app.schemas.engine import (
    AdvisoryOut,
    AdvisoryUpdateIn,
    AlertOut,
    EngineRunIn,
    PredictionOut,
)


async def list_predictions(
    session: AsyncSession,
    aircraft_id: str | None = None,
    system_name: str | None = None,
    min_risk: float | None = None,
    as_of_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[PredictionOut]:
    """Retrieve scored model predictions with aircraft and system metadata."""
    query = (
        select(
            Prediction,
            Component.aircraft_id,
            Aircraft.tail_code,
            System.name.label("system_name"),
            ComponentType.name.label("component_name"),
        )
        .join(Component, Prediction.component_id == Component.component_id)
        .join(Aircraft, Component.aircraft_id == Aircraft.aircraft_id)
        .join(ComponentType, Component.component_type_id == ComponentType.component_type_id)
        .join(System, ComponentType.system_id == System.system_id)
    )

    if aircraft_id:
        query = query.where(
            (Component.aircraft_id == aircraft_id) | (Aircraft.tail_code == aircraft_id)
        )
    if system_name:
        query = query.where(System.name.ilike(f"%{system_name}%"))
    if min_risk is not None:
        query = query.where(Prediction.risk_14d >= min_risk)
    if as_of_date is not None:
        query = query.where(Prediction.as_of_date == as_of_date)

    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(Prediction.risk_14d.desc(), Prediction.as_of_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await session.execute(query)

    items: list[PredictionOut] = []
    for pred, ac_id, tail_code, sys_name, comp_name in res.all():
        items.append(
            PredictionOut(
                prediction_id=pred.prediction_id,
                component_id=pred.component_id,
                aircraft_id=ac_id,
                tail_code=tail_code,
                system_name=sys_name,
                component_name=comp_name,
                as_of_date=pred.as_of_date,
                risk_14d=pred.risk_14d,
                risk_30d=pred.risk_30d,
                rul_p10=pred.rul_p10,
                rul_p50=pred.rul_p50,
                rul_p90=pred.rul_p90,
                model_version=pred.model_version,
                created_at=pred.created_at,
            )
        )

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def list_advisories(
    session: AsyncSession,
    priority: str | None = None,
    status: str | None = None,
    spare_status: str | None = None,
    aircraft_id: str | None = None,
    as_of_date: date | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[AdvisoryOut]:
    """Retrieve decision-support Maintenance Advisories for the planner risk queue."""
    query = (
        select(
            Advisory,
            Component.aircraft_id,
            Aircraft.tail_code,
            System.name.label("system_name"),
            ComponentType.name.label("component_name"),
        )
        .join(Component, Advisory.component_id == Component.component_id)
        .join(Aircraft, Component.aircraft_id == Aircraft.aircraft_id)
        .join(ComponentType, Component.component_type_id == ComponentType.component_type_id)
        .join(System, ComponentType.system_id == System.system_id)
    )

    if priority:
        query = query.where(Advisory.priority == priority)
    if status:
        query = query.where(Advisory.status == status)
    if spare_status:
        query = query.where(Advisory.spare_status.ilike(f"%{spare_status}%"))
    if aircraft_id:
        query = query.where(
            (Component.aircraft_id == aircraft_id) | (Aircraft.tail_code == aircraft_id)
        )
    if as_of_date is not None:
        query = query.where(Advisory.as_of_date == as_of_date)

    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(Advisory.priority.asc(), Advisory.as_of_date.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await session.execute(query)

    items: list[AdvisoryOut] = []
    for adv, ac_id, tail_code, sys_name, comp_name in res.all():
        items.append(
            AdvisoryOut(
                advisory_id=adv.advisory_id,
                component_id=adv.component_id,
                aircraft_id=ac_id,
                tail_code=tail_code,
                system_name=sys_name,
                component_name=comp_name,
                as_of_date=adv.as_of_date,
                priority=adv.priority,
                action=adv.action,
                status=adv.status,
                dismiss_reason=adv.dismiss_reason,
                explanation=adv.explanation,
                spare_status=adv.spare_status,
                expected_downtime_days=adv.expected_downtime_days,
                created_at=adv.created_at,
            )
        )

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def get_advisory_by_id(
    session: AsyncSession,
    advisory_id: str,
) -> AdvisoryOut:
    """Retrieve individual advisory detail by advisory_id."""
    query = (
        select(
            Advisory,
            Component.aircraft_id,
            Aircraft.tail_code,
            System.name.label("system_name"),
            ComponentType.name.label("component_name"),
        )
        .join(Component, Advisory.component_id == Component.component_id)
        .join(Aircraft, Component.aircraft_id == Aircraft.aircraft_id)
        .join(ComponentType, Component.component_type_id == ComponentType.component_type_id)
        .join(System, ComponentType.system_id == System.system_id)
        .where(Advisory.advisory_id == advisory_id)
    )
    res = await session.execute(query)
    row = res.first()
    if not row:
        raise NotFoundError(f"Advisory '{advisory_id}' not found")

    adv, ac_id, tail_code, sys_name, comp_name = row
    return AdvisoryOut(
        advisory_id=adv.advisory_id,
        component_id=adv.component_id,
        aircraft_id=ac_id,
        tail_code=tail_code,
        system_name=sys_name,
        component_name=comp_name,
        as_of_date=adv.as_of_date,
        priority=adv.priority,
        action=adv.action,
        status=adv.status,
        dismiss_reason=adv.dismiss_reason,
        explanation=adv.explanation,
        spare_status=adv.spare_status,
        expected_downtime_days=adv.expected_downtime_days,
        created_at=adv.created_at,
    )


async def update_advisory_status(
    session: AsyncSession,
    advisory_id: str,
    update: AdvisoryUpdateIn,
) -> AdvisoryOut:
    """Transition an advisory to a new workflow status with transition validation."""
    query = select(Advisory).where(Advisory.advisory_id == advisory_id)
    res = await session.execute(query)
    adv = res.scalars().first()
    if not adv:
        raise NotFoundError(f"Advisory '{advisory_id}' not found")

    try:
        validate_advisory_transition(
            current_status=adv.status,
            new_status=update.status,
            dismiss_reason=update.reason,
        )
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    adv.status = update.status
    if update.status == "dismissed":
        adv.dismiss_reason = update.reason

    await session.commit()
    await session.refresh(adv)

    return await get_advisory_by_id(session, advisory_id)


async def list_alerts(
    session: AsyncSession,
    severity: str | None = None,
    acknowledged: bool | None = None,
    type_: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[AlertOut]:
    """Retrieve system alerts with filtering and pagination."""
    query = select(Alert)

    if severity:
        query = query.where(Alert.severity == severity)
    if acknowledged is not None:
        query = query.where(Alert.acknowledged == acknowledged)
    if type_:
        query = query.where(Alert.type == type_)

    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(Alert.acknowledged.asc(), Alert.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    res = await session.execute(query)

    items = [AlertOut.model_validate(alert) for alert in res.scalars().all()]
    pages = (total + page_size - 1) // page_size if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def acknowledge_alert(
    session: AsyncSession,
    alert_id: int,
    acknowledged: bool = True,
) -> AlertOut:
    """Acknowledge or clear an alert."""
    query = select(Alert).where(Alert.alert_id == alert_id)
    res = await session.execute(query)
    alert = res.scalars().first()
    if not alert:
        raise NotFoundError(f"Alert ID {alert_id} not found")

    alert.acknowledged = acknowledged
    await session.commit()
    await session.refresh(alert)
    return AlertOut.model_validate(alert)


async def execute_engine_run(
    session: AsyncSession,
    params: EngineRunIn,
) -> EngineRunSummary:
    """Execute predictive maintenance engine scoring run."""
    return await run_scoring_job(
        session=session,
        as_of_date=params.as_of_date,
        target_aircraft_id=params.aircraft_id,
    )
