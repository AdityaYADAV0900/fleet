"""performance indexes

Revision ID: 0002_performance_indexes
Revises: 0001_initial_schema
Create Date: 2026-10-04 13:36:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_performance_indexes"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_components_aircraft_id",
        "components",
        ["aircraft_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_components_component_type_id",
        "components",
        ["component_type_id"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_aircraft_daily_status_date",
        "aircraft_daily_status",
        ["date"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_advisories_as_of_date",
        "advisories",
        ["as_of_date"],
        unique=False,
        if_not_exists=True,
    )
    op.create_index(
        "ix_work_orders_advisory_id",
        "work_orders",
        ["advisory_id"],
        unique=False,
        if_not_exists=True,
    )


def downgrade() -> None:
    op.drop_index("ix_work_orders_advisory_id", table_name="work_orders", if_exists=True)
    op.drop_index("ix_advisories_as_of_date", table_name="advisories", if_exists=True)
    op.drop_index(
        "ix_aircraft_daily_status_date", table_name="aircraft_daily_status", if_exists=True
    )
    op.drop_index("ix_components_component_type_id", table_name="components", if_exists=True)
    op.drop_index("ix_components_aircraft_id", table_name="components", if_exists=True)
