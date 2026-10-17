"""Spares and inventory management API router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.platform import User
from app.schemas.common import PaginatedResponse
from app.schemas.spares import InventoryOut, InventoryTransactionOut, SparePartOut
from app.services import spares_service

router = APIRouter(prefix="/inventory", tags=["Spares & Inventory"])


@router.get(
    "", response_model=PaginatedResponse[InventoryOut], summary="List inventory stock levels"
)
async def list_inventory(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    part_number: str | None = Query(None, description="Filter by part number"),
    location_id: str | None = Query(None, description="Filter by storage location"),
    low_stock: bool = Query(False, description="Filter to parts below reorder level"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[InventoryOut]:
    """Retrieve multi-location stock levels, on-hand, reserved, and incoming supply orders."""
    return await spares_service.list_inventory(
        session,
        part_number=part_number,
        location_id=location_id,
        low_stock_only=low_stock,
        page=page,
        page_size=page_size,
    )


@router.get("/parts", response_model=list[SparePartOut], summary="List spare parts catalog")
async def list_spare_parts(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[SparePartOut]:
    """Retrieve catalog of LRUs, assemblies, lead times, and standard unit costs."""
    return await spares_service.list_spare_parts(session)


@router.get(
    "/transactions",
    response_model=PaginatedResponse[InventoryTransactionOut],
    summary="List inventory transactions",
)
async def list_transactions(
    _: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    part_number: str | None = Query(None, description="Filter by part number"),
    type: str | None = Query(
        None, description="Filter by type (issue, receipt, repair-return, adjustment)"
    ),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
) -> PaginatedResponse[InventoryTransactionOut]:
    """List historical stock movements (issues for work orders, supplier receipts)."""
    return await spares_service.list_inventory_transactions(
        session, part_number=part_number, type_=type, page=page, page_size=page_size
    )
