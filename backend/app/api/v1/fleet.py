"""Fleet, aircraft, and component hierarchy API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.platform import User
from app.schemas.common import PaginatedResponse
from app.schemas.fleet import (
    AircraftDetailOut,
    AircraftListOut,
    ComponentOut,
    ComponentTypeOut,
    SystemOut,
)
from app.services import fleet_service

router = APIRouter(tags=["Fleet & Aircraft"])


@router.get("/aircraft", response_model=PaginatedResponse[AircraftListOut], summary="List aircraft")
async def list_aircraft(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    state: str | None = Query(None, description="Filter by availability status"),
    base: str | None = Query(None, description="Filter by base ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[AircraftListOut]:
    """List fleet airframes with current availability status, flight hours, and cycles."""
    return await fleet_service.list_aircraft(
        session, state=state, base=base, page=page, page_size=page_size
    )


@router.get("/aircraft/{id}", response_model=AircraftDetailOut, summary="Get aircraft detail")
async def get_aircraft(
    id: str,
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AircraftDetailOut:
    """Retrieve individual aircraft details, functional systems, and active installed components."""
    return await fleet_service.get_aircraft_detail(session, aircraft_id=id)


@router.get("/systems", response_model=list[SystemOut], summary="List aircraft systems")
async def list_systems(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SystemOut]:
    """Retrieve catalog of functional aircraft systems."""
    return await fleet_service.list_systems(session)


@router.get(
    "/component-types", response_model=list[ComponentTypeOut], summary="List component types"
)
async def list_component_types(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    system_id: str | None = Query(None, description="Filter by system ID"),
) -> list[ComponentTypeOut]:
    """Retrieve specifications and MTBF limits for component types."""
    return await fleet_service.list_component_types(session, system_id=system_id)


@router.get(
    "/components",
    response_model=PaginatedResponse[ComponentOut],
    summary="List component instances",
)
async def list_components(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    aircraft_id: str | None = Query(None, description="Filter by aircraft ID"),
    status: str | None = Query(None, description="Filter by component status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[ComponentOut]:
    """List tracked serialized component units."""
    return await fleet_service.list_components(
        session, aircraft_id=aircraft_id, status=status, page=page, page_size=page_size
    )
