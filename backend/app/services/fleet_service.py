"""Fleet management service for querying aircraft, systems, and component instances."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import NotFoundError
from app.models.fleet import Aircraft, AircraftDailyStatus, Component, ComponentType, System
from app.schemas.common import PaginatedResponse
from app.schemas.fleet import (
    AircraftDetailOut,
    AircraftListOut,
    ComponentOut,
    ComponentTypeOut,
    SystemOut,
)


async def list_aircraft(
    session: AsyncSession,
    state: str | None = None,
    base: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[AircraftListOut]:
    """List fleet aircraft with optional state/base filters and pagination."""
    # Subquery for latest daily status per aircraft
    latest_status_subq = select(
        AircraftDailyStatus.aircraft_id,
        AircraftDailyStatus.status.label("latest_status"),
        func.row_number()
        .over(
            partition_by=AircraftDailyStatus.aircraft_id,
            order_by=AircraftDailyStatus.date.desc(),
        )
        .label("rn"),
    ).subquery()

    query = select(
        Aircraft,
        func.coalesce(latest_status_subq.c.latest_status, "Available").label("current_status"),
    ).outerjoin(
        latest_status_subq,
        (Aircraft.aircraft_id == latest_status_subq.c.aircraft_id) & (latest_status_subq.c.rn == 1),
    )

    if base:
        query = query.where(Aircraft.base_id == base)
    if state:
        query = query.where(latest_status_subq.c.latest_status == state)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_query)
    total = total_res.scalar_one()

    # Pagination
    offset = (page - 1) * page_size
    query = query.order_by(Aircraft.aircraft_id).offset(offset).limit(page_size)
    result = await session.execute(query)

    items = []
    for ac, cur_status in result.all():
        items.append(
            AircraftListOut(
                aircraft_id=ac.aircraft_id,
                tail_code=ac.tail_code,
                type_code=ac.type_code,
                commissioned_date=ac.commissioned_date,
                total_flight_hours=ac.total_flight_hours,
                total_cycles=ac.total_cycles,
                base_id=ac.base_id,
                current_status=cur_status,
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


async def get_aircraft_detail(session: AsyncSession, aircraft_id: str) -> AircraftDetailOut:
    """Retrieve complete aircraft detail including systems and installed components."""
    stmt = (
        select(Aircraft)
        .options(selectinload(Aircraft.components).selectinload(Component.component_type))
        .where(Aircraft.aircraft_id == aircraft_id)
    )
    result = await session.execute(stmt)
    ac = result.scalars().first()

    if not ac:
        raise NotFoundError(f"Aircraft '{aircraft_id}' not found")

    # Get latest status
    status_stmt = (
        select(AircraftDailyStatus.status)
        .where(AircraftDailyStatus.aircraft_id == aircraft_id)
        .order_by(AircraftDailyStatus.date.desc())
        .limit(1)
    )
    status_res = await session.execute(status_stmt)
    latest_status = status_res.scalar_one_or_none() or "Available"

    # Systems list
    systems_stmt = select(System).order_by(System.system_id)
    systems_res = await session.execute(systems_stmt)
    systems = [SystemOut.model_validate(s) for s in systems_res.scalars().all()]

    # Installed components
    installed_components = [
        ComponentOut.model_validate(c) for c in ac.components if c.status == "installed"
    ]

    return AircraftDetailOut(
        aircraft_id=ac.aircraft_id,
        tail_code=ac.tail_code,
        type_code=ac.type_code,
        commissioned_date=ac.commissioned_date,
        total_flight_hours=ac.total_flight_hours,
        total_cycles=ac.total_cycles,
        base_id=ac.base_id,
        current_status=latest_status,
        components_count=len(installed_components),
        systems=systems,
        installed_components=installed_components,
    )


async def list_systems(session: AsyncSession) -> list[SystemOut]:
    """Retrieve all functional systems in the aircraft hierarchy."""
    stmt = select(System).order_by(System.system_id)
    res = await session.execute(stmt)
    return [SystemOut.model_validate(s) for s in res.scalars().all()]


async def list_component_types(
    session: AsyncSession, system_id: str | None = None
) -> list[ComponentTypeOut]:
    """Retrieve component types catalog, optionally filtered by system."""
    stmt = select(ComponentType)
    if system_id:
        stmt = stmt.where(ComponentType.system_id == system_id)
    stmt = stmt.order_by(ComponentType.component_type_id)
    res = await session.execute(stmt)
    return [ComponentTypeOut.model_validate(ct) for ct in res.scalars().all()]


async def list_components(
    session: AsyncSession,
    aircraft_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[ComponentOut]:
    """List components with optional filters."""
    stmt = select(Component)
    if aircraft_id:
        stmt = stmt.where(Component.aircraft_id == aircraft_id)
    if status:
        stmt = stmt.where(Component.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Component.component_id).offset(offset).limit(page_size)
    res = await session.execute(stmt)
    items = [ComponentOut.model_validate(c) for c in res.scalars().all()]

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
