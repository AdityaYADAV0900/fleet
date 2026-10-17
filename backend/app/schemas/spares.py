"""Spares and inventory management schemas."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime

from pydantic import BaseModel, Field


class SparePartOut(BaseModel):
    part_number: str
    description: str
    criticality: int
    unit_cost: float
    lead_time_days: int
    reorder_level: int

    class Config:
        from_attributes = True


class InventoryOut(BaseModel):
    inventory_id: int
    part_number: str
    location_id: str
    on_hand: int
    reserved: int
    on_order: int
    expected_receipt_date: dt_date | None = None
    is_low_stock: bool = Field(
        default=False, description="True if on_hand is at or below reorder level"
    )

    class Config:
        from_attributes = True


class InventoryTransactionOut(BaseModel):
    txn_id: int
    part_number: str
    date: datetime
    qty: int
    type: str
    work_order_id: str | None = None

    class Config:
        from_attributes = True
