"""Digital Twin API router: hierarchy, health-state roll-up, snapshots, replay, and what-if simulation (§6)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.platform import User
from app.schemas.availability import ScenarioRunIn, ScenarioRunOut
from app.schemas.twin import (
    TwinAircraftNodeOut,
    TwinComponentDetailOut,
    TwinFleetOut,
    TwinWhatIfIn,
)
from app.twin import service as twin_service

router = APIRouter(prefix="/twin", tags=["Digital Twin"])


@router.get(
    "/fleet",
    response_model=TwinFleetOut,
    summary="Get fleet-wide digital twin state and roll-up",
)
async def get_fleet_twin(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    as_of: Annotated[
        date | None,
        Query(description="Historical replay date (YYYY-MM-DD)"),
    ] = None,
) -> TwinFleetOut:
    """Retrieve the fleet-wide digital twin hierarchy and state distribution.

    Returns the roll-up across all aircraft, health index distributions,
    and identifies the primary fleet driver airframe.
    Supports historical replay when `as_of` query parameter is provided.
    """
    return await twin_service.get_fleet_twin(session, as_of=as_of)


@router.get(
    "/aircraft/{id}",
    response_model=TwinAircraftNodeOut,
    summary="Get individual aircraft digital twin",
)
async def get_aircraft_twin(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    as_of: Annotated[
        date | None,
        Query(description="Historical replay date (YYYY-MM-DD)"),
    ] = None,
) -> TwinAircraftNodeOut:
    """Retrieve full hierarchical Digital Twin model for an individual aircraft (§6).

    Includes:
    - Criticality-weighted health index roll-up
    - Worst-component driver report (component, system, HI, risk)
    - Constituent functional systems and component health states
    - Maintenance history timeline
    - Degradation trajectory (past history + projected threshold crossings)
    - Historical replay when `as_of` query parameter is provided.
    """
    return await twin_service.get_aircraft_twin(session, aircraft_id=id, as_of=as_of)


@router.get(
    "/component/{id}",
    response_model=TwinComponentDetailOut,
    summary="Get component digital twin detail",
)
async def get_component_twin(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    as_of: Annotated[
        date | None,
        Query(description="Historical replay date (YYYY-MM-DD)"),
    ] = None,
) -> TwinComponentDetailOut:
    """Retrieve detailed digital twin state for a specific component.

    Includes current/replay health state, operating hours, active advisory,
    recent sensor metrics, maintenance history, and degradation trajectory.
    """
    return await twin_service.get_component_twin(session, component_id=id, as_of=as_of)


@router.post(
    "/whatif",
    response_model=ScenarioRunOut,
    status_code=status.HTTP_200_OK,
    summary="Execute digital twin what-if scenario",
)
async def run_twin_whatif(
    body: ScenarioRunIn,
    user: Annotated[User, Depends(require_roles("commander", "planner"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ScenarioRunOut:
    """Execute digital twin what-if scenario by delegating to ScenarioEngine (§6, §7).

    Evaluates baseline vs scenario policies:
    - schedule_maintenance (schedule proactive inspection)
    - spare_unavailable (stock-out and lead-time delays)
    - early_vs_run_to_failure (preventive replacement vs unplanned failure)
    - extra_capacity (workshop bay expansion)

    Returns P10/P50/P90 availability distributions, days lost by cause, and delta.
    Requires Planner or Commander role.
    """
    twin_whatif_input = TwinWhatIfIn(
        type=body.type,
        params=body.params,
        horizon_days=body.horizon_days,
        runs=body.runs,
        seed=body.seed,
    )
    result = await twin_service.execute_twin_whatif(
        session=session,
        whatif_in=twin_whatif_input,
        username=user.username,
    )
    return ScenarioRunOut.model_validate(result)
