from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fleet import (
    Aircraft,
    AircraftDailyStatus,
    Component,
    ComponentType,
    System,
)
from app.models.maintenance import (
    MaintenanceEvent,
)
from app.models.platform import (
    Advisory,
    Prediction,
    SimulationTruth,
    User,
)
from app.models.spares import (
    Inventory,
    SparePart,
)


@pytest.mark.asyncio
async def test_foreign_key_violation(async_session: AsyncSession) -> None:
    """Inserting a component referencing a non-existent component_type must fail FK integrity."""
    invalid_comp = Component(
        component_id="CMP-TEST-FK-01",
        component_type_id="NON_EXISTENT_TYPE",
        serial_no="SN-FK-01",
        status="installed",
    )
    async_session.add(invalid_comp)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_component_type_criticality_check(async_session: AsyncSession) -> None:
    """Criticality must be between 1 and 5 inclusive."""
    system = System(system_id="SYS-TEST-01", name="Test System")
    async_session.add(system)
    await async_session.flush()

    invalid_ct = ComponentType(
        component_type_id="CT-INVALID-01",
        system_id="SYS-TEST-01",
        name="Invalid CT",
        criticality=6,  # Invalid: > 5
        design_life_hours=1000.0,
        mtbf_hours=500.0,
        part_number="PN-01",
    )
    async_session.add(invalid_ct)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_inventory_non_negative_check(async_session: AsyncSession) -> None:
    """Inventory on_hand cannot be negative."""
    part = SparePart(
        part_number="PART-TEST-01",
        description="Test Spare",
        criticality=3,
        unit_cost=150.0,
        lead_time_days=14,
        reorder_level=5,
    )
    async_session.add(part)
    await async_session.flush()

    invalid_inv = Inventory(
        part_number="PART-TEST-01",
        location_id="BASE-MAIN",
        on_hand=-1,  # Invalid: < 0
        reserved=0,
        on_order=0,
    )
    async_session.add(invalid_inv)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_aircraft_daily_status_enum_check(async_session: AsyncSession) -> None:
    """aircraft_daily_status must adhere to allowed status enum values."""
    ac = Aircraft(
        aircraft_id="AC-TEST-01",
        tail_code="AC-T01",
        type_code="Generic-Transport",
        commissioned_date=date(2023, 1, 1),
    )
    async_session.add(ac)
    await async_session.flush()

    invalid_status = AircraftDailyStatus(
        aircraft_id="AC-TEST-01",
        date=date(2023, 1, 2),
        status="InvalidStatus",  # Not in allowed list
    )
    async_session.add(invalid_status)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_aircraft_daily_status_unique_constraint(async_session: AsyncSession) -> None:
    """Duplicate (aircraft_id, date) in aircraft_daily_status must raise IntegrityError."""
    ac = Aircraft(
        aircraft_id="AC-TEST-02",
        tail_code="AC-T02",
        type_code="Generic-Transport",
        commissioned_date=date(2023, 1, 1),
    )
    async_session.add(ac)
    await async_session.flush()

    stat1 = AircraftDailyStatus(
        aircraft_id="AC-TEST-02",
        date=date(2023, 1, 5),
        status="Available",
    )
    stat2 = AircraftDailyStatus(
        aircraft_id="AC-TEST-02",
        date=date(2023, 1, 5),
        status="Scheduled Maintenance",
    )
    async_session.add(stat1)
    await async_session.flush()

    async_session.add(stat2)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_maintenance_events_end_date_check(async_session: AsyncSession) -> None:
    """maintenance_events.end must be >= maintenance_events.start if specified."""
    ac = Aircraft(
        aircraft_id="AC-TEST-03",
        tail_code="AC-T03",
        type_code="Generic-Transport",
        commissioned_date=date(2023, 1, 1),
    )
    async_session.add(ac)
    await async_session.flush()

    now = datetime.now(UTC)
    earlier = now - timedelta(hours=5)

    invalid_event = MaintenanceEvent(
        event_id="ME-TEST-01",
        aircraft_id="AC-TEST-03",
        type="scheduled",
        start=now,
        end=earlier,  # Invalid: end < start
        action="inspect",
    )
    async_session.add(invalid_event)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_user_role_check(async_session: AsyncSession) -> None:
    """users.role must be one of 'commander', 'planner', 'technician'."""
    invalid_user = User(
        username="hacker",
        password_hash="secret_hash",
        role="superuser",  # Invalid role
    )
    async_session.add(invalid_user)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_advisory_priority_and_status_checks(async_session: AsyncSession) -> None:
    """advisories priority must be P1-P4 and status in valid set."""
    sys_obj = System(system_id="SYS-TEST-02", name="Hydraulics")
    ct = ComponentType(
        component_type_id="CT-TEST-02",
        system_id="SYS-TEST-02",
        name="Pump",
        criticality=4,
        design_life_hours=2000.0,
        mtbf_hours=1000.0,
        part_number="PN-02",
    )
    comp = Component(
        component_id="CMP-TEST-ADV-01",
        component_type_id="CT-TEST-02",
        serial_no="SN-ADV-01",
        status="installed",
    )
    async_session.add_all([sys_obj, ct, comp])
    await async_session.flush()

    invalid_advisory = Advisory(
        advisory_id="ADV-TEST-01",
        component_id="CMP-TEST-ADV-01",
        as_of_date=date(2025, 6, 1),
        priority="P9",  # Invalid priority
        action="replace immediately",
        status="proposed",
    )
    async_session.add(invalid_advisory)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_predictions_range_check(async_session: AsyncSession) -> None:
    """predictions risk must be in [0, 1]."""
    sys_obj = System(system_id="SYS-TEST-03", name="Avionics")
    ct = ComponentType(
        component_type_id="CT-TEST-03",
        system_id="SYS-TEST-03",
        name="Computer",
        criticality=5,
        design_life_hours=5000.0,
        mtbf_hours=3000.0,
        part_number="PN-03",
    )
    comp = Component(
        component_id="CMP-TEST-PRED-01",
        component_type_id="CT-TEST-03",
        serial_no="SN-PRED-01",
        status="installed",
    )
    async_session.add_all([sys_obj, ct, comp])
    await async_session.flush()

    invalid_pred = Prediction(
        component_id="CMP-TEST-PRED-01",
        as_of_date=date(2025, 6, 1),
        risk_14d=1.5,  # Invalid: > 1.0
        risk_30d=0.8,
        rul_p10=10.0,
        rul_p50=20.0,
        rul_p90=30.0,
        model_version="v1.0.0",
    )
    async_session.add(invalid_pred)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_predictions_unique_constraint(async_session: AsyncSession) -> None:
    """(component_id, as_of_date, model_version) must be unique in predictions."""
    sys_obj = System(system_id="SYS-TEST-03B", name="Avionics B")
    ct = ComponentType(
        component_type_id="CT-TEST-03B",
        system_id="SYS-TEST-03B",
        name="Computer B",
        criticality=5,
        design_life_hours=5000.0,
        mtbf_hours=3000.0,
        part_number="PN-03B",
    )
    comp = Component(
        component_id="CMP-TEST-PRED-02",
        component_type_id="CT-TEST-03B",
        serial_no="SN-PRED-02",
        status="installed",
    )
    async_session.add_all([sys_obj, ct, comp])
    await async_session.flush()

    valid_pred_1 = Prediction(
        component_id="CMP-TEST-PRED-02",
        as_of_date=date(2025, 6, 1),
        risk_14d=0.4,
        risk_30d=0.7,
        rul_p10=10.0,
        rul_p50=20.0,
        rul_p90=30.0,
        model_version="v1.0.0",
    )
    valid_pred_2 = Prediction(
        component_id="CMP-TEST-PRED-02",
        as_of_date=date(2025, 6, 1),
        risk_14d=0.45,
        risk_30d=0.75,
        rul_p10=9.0,
        rul_p50=18.0,
        rul_p90=28.0,
        model_version="v1.0.0",
    )
    async_session.add(valid_pred_1)
    await async_session.flush()

    async_session.add(valid_pred_2)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()


@pytest.mark.asyncio
async def test_simulation_truth_health_range_check(async_session: AsyncSession) -> None:
    """simulation_truth true_health must be between 0.0 and 1.0."""
    sys_obj = System(system_id="SYS-TEST-04", name="Fuel")
    ct = ComponentType(
        component_type_id="CT-TEST-04",
        system_id="SYS-TEST-04",
        name="Fuel Pump",
        criticality=4,
        design_life_hours=4000.0,
        mtbf_hours=2000.0,
        part_number="PN-04",
    )
    comp = Component(
        component_id="CMP-TEST-TRUTH-01",
        component_type_id="CT-TEST-04",
        serial_no="SN-TRUTH-01",
        status="installed",
    )
    async_session.add_all([sys_obj, ct, comp])
    await async_session.flush()

    invalid_truth = SimulationTruth(
        component_id="CMP-TEST-TRUTH-01",
        date=date(2025, 6, 1),
        true_health=1.2,  # Invalid: > 1.0
        is_failed=False,
    )
    async_session.add(invalid_truth)
    with pytest.raises(IntegrityError):
        await async_session.flush()
    await async_session.rollback()
