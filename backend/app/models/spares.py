from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SparePart(Base):
    """Catalog of spare parts, line-replaceable units (LRUs), and consumables."""

    __tablename__ = "spare_parts"
    __table_args__ = (
        CheckConstraint(
            "criticality >= 1 AND criticality <= 5",
            name="ck_spare_parts_criticality_range",
        ),
        CheckConstraint(
            "unit_cost >= 0",
            name="ck_spare_parts_unit_cost_non_negative",
        ),
        CheckConstraint(
            "lead_time_days >= 0",
            name="ck_spare_parts_lead_time_non_negative",
        ),
        CheckConstraint(
            "reorder_level >= 0",
            name="ck_spare_parts_reorder_level_non_negative",
        ),
    )

    part_number: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'HYD-114'
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 5
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    reorder_level: Mapped[int] = mapped_column(Integer, nullable=False)

    inventory_items: Mapped[list["Inventory"]] = relationship(
        "Inventory", back_populates="spare_part", cascade="all, delete-orphan"
    )
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction", back_populates="spare_part"
    )

    def __repr__(self) -> str:
        return f"<SparePart(part_no={self.part_number}, crit={self.criticality}, lead={self.lead_time_days}d)>"


class Inventory(Base):
    """Stock levels, reservations, and on-order quantities by storage location."""

    __tablename__ = "inventory"
    __table_args__ = (
        UniqueConstraint("part_number", "location_id", name="uq_inventory_part_location"),
        Index("ix_inventory_part_number_location_id", "part_number", "location_id"),
        CheckConstraint(
            "on_hand >= 0",
            name="ck_inventory_on_hand_non_negative",
        ),
        CheckConstraint(
            "reserved >= 0",
            name="ck_inventory_reserved_non_negative",
        ),
        CheckConstraint(
            "on_order >= 0",
            name="ck_inventory_on_order_non_negative",
        ),
    )

    inventory_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    part_number: Mapped[str] = mapped_column(
        String(50), ForeignKey("spare_parts.part_number", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'BASE-MAIN', 'DEPOT-01'
    on_hand: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    on_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    expected_receipt_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    spare_part: Mapped["SparePart"] = relationship("SparePart", back_populates="inventory_items")

    def __repr__(self) -> str:
        return (
            f"<Inventory(part={self.part_number}, loc={self.location_id}, "
            f"on_hand={self.on_hand}, reserved={self.reserved})>"
        )


class InventoryTransaction(Base):
    """Material movements (issues, receipts, repairs) affecting stock levels."""

    __tablename__ = "inventory_transactions"
    __table_args__ = (
        Index("ix_inventory_transactions_part_date", "part_number", "date"),
        CheckConstraint(
            "type IN ('issue', 'receipt', 'repair-return', 'adjustment')",
            name="ck_inventory_transactions_type_valid",
        ),
    )

    txn_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    part_number: Mapped[str] = mapped_column(
        String(50), ForeignKey("spare_parts.part_number", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # issue, receipt, repair-return, adjustment
    work_order_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("work_orders.wo_id", ondelete="SET NULL"), nullable=True
    )

    spare_part: Mapped["SparePart"] = relationship("SparePart", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<InventoryTransaction(id={self.txn_id}, part={self.part_number}, qty={self.qty}, type={self.type})>"
