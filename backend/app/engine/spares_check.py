"""Spare parts requirement, stock availability, and lead time vs RUL evaluation.

Connects maintenance advisory demand to inventory levels across operating bases.
Evaluates whether supply lead times exceed the component's remaining useful life.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import ComponentType
from app.models.spares import Inventory, SparePart


@dataclass(frozen=True)
class SpareCheckResult:
    """Outcome of spare part stock and lead time verification."""

    part_number: str
    part_description: str
    on_hand: int
    reserved: int
    available: int
    on_order: int
    lead_time_days: int
    rul_days: float
    has_shortfall_risk: bool
    status_label: str  # 'Available', 'Tight', 'Shortfall Risk'
    summary_text: str  # e.g., "Pump P/N HYD-114, 1 in stock (reserved: 0), available"


async def check_component_spares(
    session: AsyncSession,
    component_type_id: str,
    base_id: str | None = None,
    rul_days: float = 60.0,
) -> SpareCheckResult:
    """Query spare part inventory and compare stock and lead time against remaining life.

    If base_id is specified, queries the local base inventory with fallback to total fleet stock.
    """
    # 1. Fetch component type & part number
    ct_query = select(ComponentType).where(ComponentType.component_type_id == component_type_id)
    ct_res = await session.execute(ct_query)
    ct = ct_res.scalars().first()

    part_number = ct.part_number if ct else "UNKNOWN"

    # 2. Fetch spare part catalog definition
    sp_query = select(SparePart).where(SparePart.part_number == part_number)
    sp_res = await session.execute(sp_query)
    sp = sp_res.scalars().first()

    description = sp.description if sp else (ct.name if ct else "Generic Replacement Part")
    lead_time = sp.lead_time_days if sp else 30

    # 3. Fetch inventory levels
    inv_query = select(Inventory).where(Inventory.part_number == part_number)
    if base_id:
        inv_query = inv_query.where(Inventory.location_id == base_id)

    inv_res = await session.execute(inv_query)
    inv_items = inv_res.scalars().all()

    if not inv_items and base_id:
        # Fallback to total fleet inventory
        inv_all_query = select(Inventory).where(Inventory.part_number == part_number)
        inv_all_res = await session.execute(inv_all_query)
        inv_items = inv_all_res.scalars().all()

    on_hand = sum(item.on_hand for item in inv_items)
    reserved = sum(item.reserved for item in inv_items)
    on_order = sum(item.on_order for item in inv_items)
    available = max(0, on_hand - reserved)

    # 4. Assess shortfall risk
    # Shortfall condition:
    # A) 0 available parts
    # B) 1 part available, but lead time exceeds remaining useful life, creating fleet supply vulnerability
    if available == 0:
        shortfall = True
        status_label = "Shortfall Risk"
        summary = (
            f"Part P/N {part_number}, 0 available (reserved: {reserved}), "
            f"lead time {lead_time} days exceeds RUL {rul_days:.0f} days"
        )
    elif available == 1 and (lead_time > rul_days or rul_days <= 14.0):
        shortfall = True
        status_label = "Tight"
        summary = (
            f"Part P/N {part_number}, 1 in stock (reserved: {reserved}), "
            f"available; lead time {lead_time} days"
        )
    else:
        shortfall = False
        status_label = "Available"
        summary = f"Part P/N {part_number}, {available} in stock (reserved: {reserved}), available"

    return SpareCheckResult(
        part_number=part_number,
        part_description=description,
        on_hand=on_hand,
        reserved=reserved,
        available=available,
        on_order=on_order,
        lead_time_days=lead_time,
        rul_days=rul_days,
        has_shortfall_risk=shortfall,
        status_label=status_label,
        summary_text=summary,
    )


def evaluate_spare_urgency(
    available: int,
    lead_time_days: int,
    rul_days: float,
) -> tuple[float, str]:
    """Pure heuristic evaluation of spare shortfall penalty [0.0, 1.0] and status label."""
    if available == 0:
        penalty = 1.0 if lead_time_days > rul_days else 0.8
        return penalty, "Shortfall Risk"
    elif available == 1:
        if lead_time_days > rul_days:
            return 0.6, "Tight"
        return 0.3, "Tight"
    else:
        return 0.0, "Available"
