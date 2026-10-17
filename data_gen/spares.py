"""Spares and inventory management simulating stock levels, reorders, and lead-time delays."""

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from data_gen.config import InventoryConfig
from data_gen.hierarchy import COMPONENT_TYPES


@dataclass
class PendingOrder:
    part_number: str
    location_id: str
    quantity: int
    arrival_date: date


class SparesManager:
    """Simulates multi-location inventory, consumption, lead times, and replenishment."""

    def __init__(self, config: InventoryConfig, rng: random.Random):
        self.config = config
        self.rng = rng
        # inventory[(part_number, location_id)] = {"on_hand": int, "reserved": int, "on_order": int, "expected_receipt": Optional[date]}
        self.stock: dict[tuple[str, str], dict] = {}
        self.transactions: list[dict] = []
        self.pending_orders: list[PendingOrder] = []

    def initialize_inventory(self, force_overrides: dict[str, int] | None = None) -> list[dict]:
        """Initialize stock levels across locations according to reorder levels and safety stock."""
        records = []
        overrides = force_overrides or {}

        for ct in COMPONENT_TYPES:
            part_no = ct.part_number
            for loc in self.config.locations:
                # Main base carries operational spares; depot carries safety buffer
                if loc == "BASE-MAIN":
                    if part_no in overrides:
                        on_hand = overrides[part_no]
                    else:
                        base_stock = int(ct.reorder_level * self.config.safety_stock_mult)
                        on_hand = max(1, base_stock)
                else:
                    on_hand = max(1, ct.reorder_level)

                self.stock[(part_no, loc)] = {
                    "on_hand": on_hand,
                    "reserved": 0,
                    "on_order": 0,
                    "expected_receipt_date": None,
                }

                records.append(
                    {
                        "part_number": part_no,
                        "location_id": loc,
                        "on_hand": on_hand,
                        "reserved": 0,
                        "on_order": 0,
                        "expected_receipt_date": None,
                    }
                )
        return records

    def process_daily_deliveries(self, current_date: date) -> None:
        """Deliver arriving orders and increment stock levels."""
        still_pending = []
        for order in self.pending_orders:
            if current_date >= order.arrival_date:
                key = (order.part_number, order.location_id)
                if key in self.stock:
                    self.stock[key]["on_hand"] += order.quantity
                    self.stock[key]["on_order"] = max(
                        0, self.stock[key]["on_order"] - order.quantity
                    )
                    if self.stock[key]["on_order"] == 0:
                        self.stock[key]["expected_receipt_date"] = None

                # Log receipt transaction
                txn_time = datetime(
                    current_date.year, current_date.month, current_date.day, 8, 0, tzinfo=UTC
                )
                self.transactions.append(
                    {
                        "part_number": order.part_number,
                        "date": txn_time,
                        "qty": order.quantity,
                        "type": "receipt",
                        "work_order_id": None,
                    }
                )
            else:
                still_pending.append(order)
        self.pending_orders = still_pending

    def request_spare(
        self,
        part_number: str,
        current_date: date,
        work_order_id: str,
        location_id: str = "BASE-MAIN",
    ) -> tuple[bool, int]:
        """Attempt to issue a spare part for maintenance.

        Returns:
            (is_immediately_available, spare_wait_days)
        """
        key = (part_number, location_id)
        if key not in self.stock:
            # Fallback
            key = (part_number, "BASE-MAIN")
            if key not in self.stock:
                return True, 0

        item = self.stock[key]
        if item["on_hand"] > 0:
            # Immediate issue
            item["on_hand"] -= 1
            txn_time = datetime(
                current_date.year, current_date.month, current_date.day, 10, 0, tzinfo=UTC
            )
            self.transactions.append(
                {
                    "part_number": part_number,
                    "date": txn_time,
                    "qty": -1,
                    "type": "issue",
                    "work_order_id": work_order_id,
                }
            )

            # Check if reorder triggered
            ct = next((c for c in COMPONENT_TYPES if c.part_number == part_number), None)
            reorder_lvl = ct.reorder_level if ct else 2
            lead_time = ct.lead_time_days if ct else 30

            if item["on_hand"] <= reorder_lvl and item["on_order"] == 0:
                reorder_qty = max(2, reorder_lvl * 2)
                item["on_order"] += reorder_qty
                # Lead time with slight jitter
                lead_days = max(5, int(lead_time + self.rng.gauss(0, max(2, lead_time * 0.15))))
                arrival = current_date + timedelta(days=lead_days)
                item["expected_receipt_date"] = arrival
                self.pending_orders.append(
                    PendingOrder(
                        part_number=part_number,
                        location_id=location_id,
                        quantity=reorder_qty,
                        arrival_date=arrival,
                    )
                )

            return True, 0

        else:
            # Stock-out! Critical supply wait
            ct = next((c for c in COMPONENT_TYPES if c.part_number == part_number), None)
            lead_time = ct.lead_time_days if ct else 30
            # If already on order, wait until that order or place rush order
            if item["expected_receipt_date"] and item["expected_receipt_date"] > current_date:
                wait_days = max(1, (item["expected_receipt_date"] - current_date).days)
            else:
                rush_lead = max(7, int(lead_time * 0.75 + self.rng.gauss(0, 3)))
                wait_days = rush_lead
                item["on_order"] += 2
                arrival = current_date + timedelta(days=rush_lead)
                item["expected_receipt_date"] = arrival
                self.pending_orders.append(
                    PendingOrder(
                        part_number=part_number,
                        location_id=location_id,
                        quantity=2,
                        arrival_date=arrival,
                    )
                )

            return False, wait_days
