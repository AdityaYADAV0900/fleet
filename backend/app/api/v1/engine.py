"""Predictive maintenance engine, predictions, advisories, and alerts API router."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.platform import User
from app.schemas.common import PaginatedResponse
from app.schemas.engine import (
    AdvisoryOut,
    AdvisoryUpdateIn,
    AlertAckIn,
    AlertOut,
    EngineRunIn,
    EngineRunSummaryOut,
    PredictionOut,
)
from app.services import engine_service

router = APIRouter(tags=["Predictive Maintenance Engine"])


# 1. Predictions
@router.get(
    "/predictions",
    response_model=PaginatedResponse[PredictionOut],
    summary="List scored model predictions",
)
async def list_predictions(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    aircraft_id: Annotated[
        str | None, Query(description="Filter by aircraft ID or tail code")
    ] = None,
    system: Annotated[str | None, Query(description="Filter by functional system name")] = None,
    min_risk: Annotated[
        float | None, Query(ge=0.0, le=1.0, description="Minimum 14-day failure risk")
    ] = None,
    as_of_date: Annotated[date | None, Query(description="Cutoff date for predictions")] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
) -> PaginatedResponse[PredictionOut]:
    """Retrieve scored model predictions: 14-day risk, 30-day risk, and RUL quantiles (P10/P50/P90)."""
    return await engine_service.list_predictions(
        session=session,
        aircraft_id=aircraft_id,
        system_name=system,
        min_risk=min_risk,
        as_of_date=as_of_date,
        page=page,
        page_size=page_size,
    )


# 2. Advisories
@router.get(
    "/advisories",
    response_model=PaginatedResponse[AdvisoryOut],
    summary="List maintenance advisories risk queue",
)
async def list_advisories(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    priority: Annotated[
        str | None, Query(description="Filter by priority (P1, P2, P3, P4)")
    ] = None,
    status: Annotated[
        str | None,
        Query(
            description="Filter by workflow status (proposed, accepted, scheduled, completed, dismissed)"
        ),
    ] = None,
    spare_status: Annotated[
        str | None, Query(description="Filter by spare availability status")
    ] = None,
    aircraft_id: Annotated[
        str | None, Query(description="Filter by aircraft ID or tail code")
    ] = None,
    as_of_date: Annotated[
        date | None, Query(description="Filter by as_of_date (YYYY-MM-DD)")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
) -> PaginatedResponse[AdvisoryOut]:
    """Retrieve decision-support Maintenance Advisories synthesized from ML inference and rules."""
    return await engine_service.list_advisories(
        session=session,
        priority=priority,
        status=status,
        spare_status=spare_status,
        aircraft_id=aircraft_id,
        as_of_date=as_of_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/advisories/{id}",
    response_model=AdvisoryOut,
    summary="Get maintenance advisory detail",
)
async def get_advisory(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdvisoryOut:
    """Retrieve complete Maintenance Advisory detail with plain-language explanation and factor attribution."""
    return await engine_service.get_advisory_by_id(session=session, advisory_id=id)


@router.patch(
    "/advisories/{id}",
    response_model=AdvisoryOut,
    summary="Update advisory workflow status",
)
async def update_advisory(
    id: str,
    update: AdvisoryUpdateIn,
    _: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AdvisoryOut:
    """Transition an advisory to accepted, scheduled, completed, or dismissed.

    Requires Planner or Commander role. Dismissal strictly requires a valid reason for audit logging.
    """
    return await engine_service.update_advisory_status(
        session=session,
        advisory_id=id,
        update=update,
    )


# 3. Alerts
@router.get(
    "/alerts",
    response_model=PaginatedResponse[AlertOut],
    summary="List active platform alerts",
)
async def list_alerts(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    severity: Annotated[
        str | None, Query(description="Filter by severity: low, medium, high, critical")
    ] = None,
    acknowledged: Annotated[bool | None, Query(description="Filter by acknowledged status")] = None,
    type: Annotated[
        str | None,
        Query(
            description="Filter by alert type: risk_threshold, spare_shortfall, overdue, backlog"
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 50,
) -> PaginatedResponse[AlertOut]:
    """Retrieve operational alerts for dashboard notification banner and planner monitoring."""
    return await engine_service.list_alerts(
        session=session,
        severity=severity,
        acknowledged=acknowledged,
        type_=type,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/alerts/{id}/ack",
    response_model=AlertOut,
    summary="Acknowledge alert",
)
async def acknowledge_alert(
    id: int,
    ack: AlertAckIn,
    _: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AlertOut:
    """Acknowledge or clear an operational alert banner. Requires Planner or Commander role."""
    return await engine_service.acknowledge_alert(
        session=session,
        alert_id=id,
        acknowledged=ack.acknowledged,
    )


# 4. Engine Run Orchestration
@router.post(
    "/engine/run",
    response_model=EngineRunSummaryOut,
    status_code=status.HTTP_200_OK,
    summary="Trigger predictive maintenance batch scoring",
)
async def trigger_engine_run(
    params: EngineRunIn,
    _: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EngineRunSummaryOut:
    """Trigger batch scoring job for specified as_of_date.

    Loads telemetry, executes models, evaluates HI, checks spares, and writes predictions,
    advisories, and alerts to the database. Requires Planner or Commander role.
    """
    summary = await engine_service.execute_engine_run(session=session, params=params)
    return EngineRunSummaryOut(
        as_of_date=summary.as_of_date,
        duration_seconds=summary.duration_seconds,
        components_scored=summary.components_scored,
        predictions_recorded=summary.predictions_recorded,
        anomaly_scores_recorded=summary.anomaly_scores_recorded,
        advisories_generated=summary.advisories_generated,
        alerts_generated=summary.alerts_generated,
        p1_count=summary.p1_count,
        p2_count=summary.p2_count,
        high_risk_components=summary.high_risk_components,
    )
