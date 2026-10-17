from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import Component, ComponentType
from app.models.maintenance import Agency, MaintenanceEvent, ScheduledTask, WorkOrder
from app.models.platform import Advisory
from app.models.spares import Inventory
from app.schemas.common import PaginatedResponse
from app.schemas.maintenance import (
    AgencyOut,
    MaintenanceEventOut,
    ScheduledTaskOut,
    WorkOrderCreateIn,
    WorkOrderOut,
)


async def list_work_orders(
    session: AsyncSession,
    status: str | None = None,
    agency_id: str | None = None,
    aircraft_id: str | None = None,
    priority: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[WorkOrderOut]:
    """List maintenance work orders with filtering and pagination."""
    stmt = select(WorkOrder)

    if status:
        stmt = stmt.where(WorkOrder.status == status)
    if agency_id:
        stmt = stmt.where(WorkOrder.agency_id == agency_id)
    if aircraft_id:
        stmt = stmt.where(WorkOrder.aircraft_id == aircraft_id)
    if priority:
        stmt = stmt.where(WorkOrder.priority == priority)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(WorkOrder.opened.desc()).offset(offset).limit(page_size)
    res = await session.execute(stmt)
    items = [WorkOrderOut.model_validate(wo) for wo in res.scalars().all()]

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def list_maintenance_events(
    session: AsyncSession,
    aircraft_id: str | None = None,
    component_id: str | None = None,
    type_: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[MaintenanceEventOut]:
    """List maintenance events with filtering and pagination."""
    stmt = select(MaintenanceEvent)

    if aircraft_id:
        stmt = stmt.where(MaintenanceEvent.aircraft_id == aircraft_id)
    if component_id:
        stmt = stmt.where(MaintenanceEvent.component_id == component_id)
    if type_:
        stmt = stmt.where(MaintenanceEvent.type == type_)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(MaintenanceEvent.start.desc()).offset(offset).limit(page_size)
    res = await session.execute(stmt)
    items = [MaintenanceEventOut.model_validate(me) for me in res.scalars().all()]

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def list_agencies(session: AsyncSession) -> list[AgencyOut]:
    """List all internal and external maintenance agencies / workshops."""
    stmt = select(Agency).order_by(Agency.agency_id)
    res = await session.execute(stmt)
    return [AgencyOut.model_validate(a) for a in res.scalars().all()]


async def list_scheduled_tasks(
    session: AsyncSession, aircraft_id: str | None = None
) -> list[ScheduledTaskOut]:
    """List scheduled compliance inspection tasks."""
    stmt = select(ScheduledTask)
    if aircraft_id:
        stmt = stmt.where(ScheduledTask.aircraft_id == aircraft_id)
    stmt = stmt.order_by(ScheduledTask.task_id)
    res = await session.execute(stmt)
    return [ScheduledTaskOut.model_validate(st) for st in res.scalars().all()]


async def create_work_order(
    session: AsyncSession,
    payload: WorkOrderCreateIn,
) -> WorkOrderOut:
    """Create a new maintenance work order, optionally linking and advancing an advisory."""
    now = datetime.utcnow()
    prefix = f"WO-{now.strftime('%Y%m%d')}"
    max_res = await session.execute(
        select(WorkOrder.wo_id)
        .where(WorkOrder.wo_id.like(f"{prefix}-%"))
        .order_by(WorkOrder.wo_id.desc())
        .limit(1)
    )
    last_wo = max_res.scalar_one_or_none()
    seq = 1
    if last_wo and last_wo.startswith(f"{prefix}-"):
        try:
            seq = int(last_wo.split("-")[-1]) + 1
        except ValueError:
            seq = 1

    while True:
        candidate = f"{prefix}-{seq:04d}"
        exists = await session.execute(select(WorkOrder.wo_id).where(WorkOrder.wo_id == candidate))
        if not exists.scalar_one_or_none():
            wo_id = candidate
            break
        seq += 1

    # Verify agency exists
    agency_res = await session.execute(select(Agency).where(Agency.agency_id == payload.agency_id))
    agency = agency_res.scalar_one_or_none()
    agency_id = agency.agency_id if agency else payload.agency_id

    planned_start = payload.planned_start or now
    promised_done = payload.promised_done or (planned_start + timedelta(days=2.5))

    wo = WorkOrder(
        wo_id=wo_id,
        aircraft_id=payload.aircraft_id,
        component_id=payload.component_id,
        advisory_id=payload.advisory_id,
        agency_id=agency_id,
        opened=now,
        planned_start=planned_start,
        promised_done=promised_done,
        status="open",
        priority=payload.priority,
        delay_reason=payload.delay_reason
        or ("Bundled with scheduled phase inspection" if payload.bundle_inspection else None),
    )
    session.add(wo)

    # Transition associated advisory to "scheduled"
    if payload.advisory_id:
        adv_res = await session.execute(
            select(Advisory).where(Advisory.advisory_id == payload.advisory_id)
        )
        adv = adv_res.scalar_one_or_none()
        if adv and adv.status in ("proposed", "accepted"):
            adv.status = "scheduled"

    # Reserve spare if component has associated part
    if payload.component_id:
        comp_res = await session.execute(
            select(ComponentType.part_number)
            .join(Component, Component.component_type_id == ComponentType.component_type_id)
            .where(Component.component_id == payload.component_id)
        )
        pn = comp_res.scalar_one_or_none()
        if pn:
            inv_res = await session.execute(
                select(Inventory)
                .where(Inventory.part_number == pn)
                .order_by(Inventory.on_hand.desc())
                .limit(1)
            )
            inv = inv_res.scalar_one_or_none()
            if inv and inv.on_hand > inv.reserved:
                inv.reserved += 1

    await session.commit()
    await session.refresh(wo)
    return WorkOrderOut.model_validate(wo)
