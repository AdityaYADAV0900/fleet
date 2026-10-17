"""Sensors, telemetry trends, fault codes, and ingestion API router."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.platform import User
from app.schemas.sensors import (
    AnomalyScoreOut,
    FaultEventOut,
    IngestResultOut,
    IngestSensorReadingsRequest,
    SensorReadingOut,
)
from app.services import sensors_service

router = APIRouter(tags=["Sensors & Telemetry"])


@router.get(
    "/components/{id}/sensors",
    response_model=list[SensorReadingOut],
    summary="Get component sensor trends",
)
async def get_component_sensors(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    parameter: Annotated[str | None, Query(description="Telemetry parameter name")] = None,
    from_date: Annotated[date | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    to_date: Annotated[date | None, Query(description="End date (YYYY-MM-DD)")] = None,
    limit: Annotated[int, Query(ge=1, le=5000, description="Max readings to return")] = 500,
) -> list[SensorReadingOut]:
    """Retrieve historical post-flight sensor readings for a monitored component instance."""
    return await sensors_service.get_component_sensor_readings(
        session,
        component_id=id,
        parameter=parameter,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


@router.get(
    "/components/{id}/anomalies",
    response_model=list[AnomalyScoreOut],
    summary="Get component anomaly score timeline",
)
async def get_component_anomalies(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    from_date: Annotated[date | None, Query(description="Start date (YYYY-MM-DD)")] = None,
    to_date: Annotated[date | None, Query(description="End date (YYYY-MM-DD)")] = None,
    limit: Annotated[int, Query(ge=1, le=5000, description="Max readings to return")] = 500,
) -> list[AnomalyScoreOut]:
    """Retrieve anomaly score timeline and detection flags for a monitored component instance."""
    return await sensors_service.get_component_anomalies(
        session,
        component_id=id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
    )


@router.post(
    "/ingest/sensor-readings",
    response_model=IngestResultOut,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest batch sensor readings",
)
async def ingest_sensor_readings(
    payload: IngestSensorReadingsRequest,
    # Technician role is strictly read-only; requires planner or commander!
    _: Annotated[User, Depends(require_roles("planner", "commander"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> IngestResultOut:
    """Ingest a batch of post-flight sensor summaries with schema validation and per-row error reporting."""
    return await sensors_service.ingest_sensor_readings(session, items=payload.readings)


@router.get("/fault-events", response_model=list[FaultEventOut], summary="List fault events")
async def list_fault_events(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    aircraft_id: str | None = Query(None, description="Filter by aircraft ID"),
    component_id: str | None = Query(None, description="Filter by component ID"),
    severity: str | None = Query(
        None, description="Filter by severity (low, medium, high, critical)"
    ),
    limit: int = Query(100, ge=1, le=1000, description="Max events to return"),
) -> list[FaultEventOut]:
    """List built-in-test (BIT) messages and operational fault events."""
    return await sensors_service.list_fault_events(
        session,
        aircraft_id=aircraft_id,
        component_id=component_id,
        severity=severity,
        limit=limit,
    )
