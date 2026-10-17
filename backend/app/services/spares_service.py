"""Spares, inventory tracking, and warehouse material movements service."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.spares import Inventory, InventoryTransaction, SparePart
from app.schemas.common import PaginatedResponse
from app.schemas.spares import InventoryOut, InventoryTransactionOut, SparePartOut


async def list_inventory(
    session: AsyncSession,
    part_number: str | None = None,
    location_id: str | None = None,
    low_stock_only: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[InventoryOut]:
    """List inventory levels across locations with reorder threshold alerts and pagination."""
    query = select(Inventory, SparePart.reorder_level).join(
        SparePart, Inventory.part_number == SparePart.part_number
    )

    if part_number:
        query = query.where(Inventory.part_number == part_number)
    if location_id:
        query = query.where(Inventory.location_id == location_id)
    if low_stock_only:
        query = query.where(Inventory.on_hand <= SparePart.reorder_level)

    count_stmt = select(func.count()).select_from(query.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    query = (
        query.order_by(Inventory.part_number, Inventory.location_id).offset(offset).limit(page_size)
    )
    res = await session.execute(query)

    items = []
    for inv, reorder_lvl in res.all():
        is_low = inv.on_hand <= reorder_lvl
        items.append(
            InventoryOut(
                inventory_id=inv.inventory_id,
                part_number=inv.part_number,
                location_id=inv.location_id,
                on_hand=inv.on_hand,
                reserved=inv.reserved,
                on_order=inv.on_order,
                expected_receipt_date=inv.expected_receipt_date,
                is_low_stock=is_low,
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


async def list_spare_parts(session: AsyncSession) -> list[SparePartOut]:
    """List entire catalog of spare parts and components."""
    stmt = select(SparePart).order_by(SparePart.part_number)
    res = await session.execute(stmt)
    return [SparePartOut.model_validate(p) for p in res.scalars().all()]


async def list_inventory_transactions(
    session: AsyncSession,
    part_number: str | None = None,
    type_: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedResponse[InventoryTransactionOut]:
    """List material transaction records (issues, receipts, returns)."""
    stmt = select(InventoryTransaction)

    if part_number:
        stmt = stmt.where(InventoryTransaction.part_number == part_number)
    if type_:
        stmt = stmt.where(InventoryTransaction.type == type_)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_res = await session.execute(count_stmt)
    total = total_res.scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(InventoryTransaction.date.desc()).offset(offset).limit(page_size)
    res = await session.execute(stmt)
    items = [InventoryTransactionOut.model_validate(t) for t in res.scalars().all()]

    pages = (total + page_size - 1) // page_size if total > 0 else 1
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )
