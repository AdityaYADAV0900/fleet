"""Fleet availability, KPIs, and Monte Carlo scenario simulation API router."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.availability.kpis import fetch_fleet_kpis, fetch_fleet_summary
from app.availability.scenarios import (
    ScenarioEngine,
    build_simulation_config_from_db,
    list_scenario_runs,
    save_scenario_run,
)
from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.fleet import AircraftDailyStatus
from app.models.platform import User
from app.schemas.availability import (
    AvailabilityTrendOut,
    AvailabilityTrendPoint,
    FleetSummaryOut,
    KpiResponse,
    ScenarioHistoryOut,
    ScenarioRunIn,
    ScenarioRunOut,
)

router = APIRouter(tags=["Fleet Availability & Scenarios"])


# 1. Fleet KPIs
@router.get(
    "/kpis",
    response_model=KpiResponse,
    summary="Get fleet availability and reliability KPIs",
)
async def get_fleet_kpis(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    from_date: Annotated[
        date | None,
        Query(alias="from", description="Start date for KPI aggregation (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(alias="to", description="End date for KPI aggregation (YYYY-MM-DD)"),
    ] = None,
    as_of: Annotated[
        date | None,
        Query(description="As-of cutoff date (YYYY-MM-DD)"),
    ] = None,
    group_by: Annotated[
        str | None,
        Query(description="Optional grouping: 'component_type' or 'none'"),
    ] = None,
) -> KpiResponse:
    """Calculate fleet availability, inherent/operational availability, MTBF, MTTR,

    turnaround, failure rate, backlog, readiness proxy, and spare fill rate (§7).
    """
    effective_to = to_date or as_of
    effective_from = from_date
    if effective_to and not effective_from:
        effective_from = effective_to - timedelta(days=30)

    data = await fetch_fleet_kpis(
        session=session,
        from_date=effective_from,
        to_date=effective_to,
        group_by=group_by,
    )
    return KpiResponse.model_validate(data)


# 2. Fleet Summary Card
@router.get(
    "/fleet/summary",
    response_model=FleetSummaryOut,
    summary="Get high-level dashboard fleet availability summary",
)
async def get_fleet_summary(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    as_of: Annotated[
        date | None,
        Query(description="Snapshot date cutoff (defaults to latest available date)"),
    ] = None,
) -> FleetSummaryOut:
    """Retrieve top-level fleet overview card metrics (§10):

    current availability %, state breakdown, open P1/P2 advisories, backlog, and at-risk spares.
    """
    data = await fetch_fleet_summary(session=session, as_of=as_of)
    return FleetSummaryOut.model_validate(data)


# 3. Fleet Availability Trend (History + Monte Carlo Forecast)
@router.get(
    "/fleet/availability/trend",
    response_model=AvailabilityTrendOut,
    summary="Get historical and forecast fleet availability trend",
)
async def get_fleet_availability_trend(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    from_date: Annotated[
        date | None,
        Query(alias="from", description="Historical start date (YYYY-MM-DD)"),
    ] = None,
    to_date: Annotated[
        date | None,
        Query(alias="to", description="Historical end date (YYYY-MM-DD)"),
    ] = None,
    as_of: Annotated[
        date | None,
        Query(description="As of snapshot date (YYYY-MM-DD)"),
    ] = None,
    horizon: Annotated[
        int,
        Query(ge=7, le=90, description="Forward forecast horizon in days"),
    ] = 30,
) -> AvailabilityTrendOut:
    """Retrieve historical daily availability points concatenated with forward Monte Carlo

    simulation projection including P10, median, and P90 confidence intervals.
    """
    effective_to = to_date or as_of
    effective_from = from_date
    if effective_to and not effective_from:
        effective_from = effective_to - timedelta(days=horizon)

    points: list[AvailabilityTrendPoint] = []

    # 1. Query historical daily availability from AircraftDailyStatus
    hist_stmt = select(
        AircraftDailyStatus.date,
        func.count(AircraftDailyStatus.id).label("total"),
        func.sum(case((AircraftDailyStatus.status == "Available", 1), else_=0)).label("available"),
    )
    if effective_from:
        hist_stmt = hist_stmt.where(AircraftDailyStatus.date >= effective_from)
    if effective_to:
        hist_stmt = hist_stmt.where(AircraftDailyStatus.date <= effective_to)

    hist_stmt = hist_stmt.group_by(AircraftDailyStatus.date).order_by(AircraftDailyStatus.date)
    hist_res = await session.execute(hist_stmt)
    hist_rows = hist_res.all()

    last_date = effective_to or datetime.utcnow().date()
    for row in hist_rows:
        d = row[0]
        last_date = d
        tot = row[1] or 1
        avail_cnt = row[2] or 0
        avail_pct = round((avail_cnt / tot) * 100.0, 2)
        points.append(
            AvailabilityTrendPoint(
                date=d.isoformat(),
                avail=avail_pct,
                p10=None,
                p90=None,
                is_forecast=False,
            )
        )

    # 2. Forward Monte Carlo simulation for forecast points
    sim_config = await build_simulation_config_from_db(
        session=session,
        horizon_days=horizon,
        runs=150,  # Fast run for inline trend visualization
        seed=42,
        as_of=effective_to,
    )
    from app.availability.simulator import FleetSimulator

    simulator = FleetSimulator(sim_config)
    sim_res = simulator.run()

    for item in sim_res.daily_trend:
        f_date = last_date + timedelta(days=item["day"])
        points.append(
            AvailabilityTrendPoint(
                date=f_date.isoformat(),
                avail=round(item["p50"] * 100.0, 2),
                p10=round(item["p10"] * 100.0, 2),
                p90=round(item["p90"] * 100.0, 2),
                is_forecast=True,
            )
        )

    return AvailabilityTrendOut(points=points)


# 4. Run What-If Scenario
@router.post(
    "/scenarios/run",
    response_model=ScenarioRunOut,
    status_code=status.HTTP_200_OK,
    summary="Execute what-if Monte Carlo availability scenario",
)
async def run_scenario(
    body: ScenarioRunIn,
    user: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioRunOut:
    """Execute comparative discrete-event Monte Carlo simulation for a what-if scenario (§7).

    Evaluates baseline vs scenario policies:
    - schedule_maintenance (schedule proactive inspection)
    - spare_unavailable (stock-out and lead-time delays)
    - early_vs_run_to_failure (preventive replacement vs unplanned failure)
    - extra_capacity (workshop bay expansion)

    Returns P10/P50/P90 availability distributions, days lost by cause, and delta.
    Requires Planner or Commander role.
    """
    base_config = await build_simulation_config_from_db(
        session=session,
        horizon_days=body.horizon_days,
        runs=body.runs,
        seed=body.seed,
    )

    result = ScenarioEngine.run_scenario(
        scenario_type=body.type,
        params=body.params,
        base_config=base_config,
    )

    # Save to scenario_runs DB table
    await save_scenario_run(session=session, scenario_result=result, created_by=user.username)

    return ScenarioRunOut.model_validate(result)


# 5. List Saved Scenarios
@router.get(
    "/scenarios",
    response_model=list[ScenarioHistoryOut],
    summary="List saved what-if scenario simulation runs",
)
async def get_saved_scenarios(
    _: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100, description="Max records to return")] = 50,
) -> list[ScenarioHistoryOut]:
    """Retrieve history of previously executed what-if scenario simulations.

    Requires Planner or Commander role.
    """
    records = await list_scenario_runs(session=session, limit=limit)
    return [ScenarioHistoryOut.model_validate(r) for r in records]
