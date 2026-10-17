"""Maintenance, work orders, and agency API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_roles
from app.core.database import get_db
from app.models.platform import User
from app.schemas.common import PaginatedResponse
from app.schemas.maintenance import (
    AgencyOut,
    MaintenanceEventOut,
    ScheduledTaskOut,
    WorkOrderCreateIn,
    WorkOrderOut,
)
from app.services import maintenance_service

router = APIRouter(tags=["Maintenance & Work Orders"])


@router.get(
    "/work-orders", response_model=PaginatedResponse[WorkOrderOut], summary="List work orders"
)
async def list_work_orders(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    status: str | None = Query(None, description="Filter by status"),
    agency: str | None = Query(None, description="Filter by agency ID"),
    aircraft: str | None = Query(None, description="Filter by aircraft ID"),
    priority: str | None = Query(None, description="Filter by priority (P1, P2, P3, P4)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[WorkOrderOut]:
    """Retrieve maintenance work orders and turnaround delay reasons."""
    return await maintenance_service.list_work_orders(
        session,
        status=status,
        agency_id=agency,
        aircraft_id=aircraft,
        priority=priority,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/work-orders",
    response_model=WorkOrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create maintenance work order",
)
async def create_work_order(
    payload: WorkOrderCreateIn,
    _: Annotated[User, Depends(require_roles("planner", "commander"))],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WorkOrderOut:
    """Schedule and create a maintenance work order assigned to a workshop agency bay."""
    return await maintenance_service.create_work_order(session, payload=payload)


@router.get(
    "/maintenance/events",
    response_model=PaginatedResponse[MaintenanceEventOut],
    summary="List maintenance events",
)
async def list_maintenance_events(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    aircraft_id: str | None = Query(None, description="Filter by aircraft ID"),
    component_id: str | None = Query(None, description="Filter by component ID"),
    type: str | None = Query(
        None, description="Filter by type (scheduled, unscheduled, inspection)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[MaintenanceEventOut]:
    """List physical maintenance actions (replacements, repairs, inspections)."""
    return await maintenance_service.list_maintenance_events(
        session,
        aircraft_id=aircraft_id,
        component_id=component_id,
        type_=type,
        page=page,
        page_size=page_size,
    )


@router.get("/agencies", response_model=list[AgencyOut], summary="List maintenance agencies")
async def list_agencies(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgencyOut]:
    """Retrieve internal squadrons, base workshops, and specialized depot agencies."""
    return await maintenance_service.list_agencies(session)


@router.get(
    "/scheduled-tasks",
    response_model=list[ScheduledTaskOut],
    summary="List scheduled compliance tasks",
)
async def list_scheduled_tasks(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    aircraft_id: str | None = Query(None, description="Filter by aircraft ID"),
) -> list[ScheduledTaskOut]:
    """Retrieve recurring phase inspection and compliance tasks across the fleet."""
    return await maintenance_service.list_scheduled_tasks(session, aircraft_id=aircraft_id)
