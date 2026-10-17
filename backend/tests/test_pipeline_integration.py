"""End-to-end integration test: data -> score -> advisory -> work order -> scenario."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.database import get_session_factory
from app.main import app
from app.models.fleet import Component
from app.models.maintenance import WorkOrder
from app.models.platform import Advisory


@pytest.fixture
async def isolated_pipeline_advisory() -> None:
    """Ensure AC-017 starts and ends with an isolated advisory state for the integration test."""
    target_date = date(2025, 11, 25)
    comp_subq = select(Component.component_id).where(Component.aircraft_id == "AC-017")
    session_factory = get_session_factory()

    # Clean existing mutated advisories and line work orders for AC-017 on target date
    async with session_factory() as session:
        await session.execute(
            delete(Advisory).where(
                Advisory.as_of_date == target_date,
                Advisory.component_id.in_(comp_subq),
            )
        )
        await session.execute(
            delete(WorkOrder).where(
                WorkOrder.aircraft_id == "AC-017",
                WorkOrder.agency_id == "AG-LINE-01",
            )
        )
        await session.commit()

    yield

    # Clean up test-created work orders and advisories
    async with session_factory() as session:
        await session.execute(
            delete(WorkOrder).where(
                WorkOrder.aircraft_id == "AC-017",
                WorkOrder.agency_id == "AG-LINE-01",
            )
        )
        await session.execute(
            delete(Advisory).where(
                Advisory.as_of_date == target_date,
                Advisory.component_id.in_(comp_subq),
            )
        )
        await session.commit()


@pytest.fixture
async def planner_auth() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "planner", "password": "planner123"},
        )
        assert res.status_code == 200
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_pipeline_integration(
    planner_auth: dict[str, str], isolated_pipeline_advisory: None
) -> None:
    """Verify end-to-end chain:

    1. Trigger engine scoring for hero aircraft AC-017 as of 2025-11-25.
    2. Retrieve generated Maintenance Advisory for the primary hydraulic pump.
    3. Accept and schedule the advisory via PATCH.
    4. Create an unscheduled work order tied to the advisory.
    5. Run what-if scenario comparison comparing proactive maintenance vs run-to-failure.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Run Engine Scoring Job
        score_res = await client.post(
            "/api/v1/engine/run",
            json={"as_of_date": "2025-11-25", "aircraft_id": "AC-017"},
            headers=planner_auth,
        )
        assert score_res.status_code == 200
        score_data = score_res.json()
        assert score_data["components_scored"] >= 20

        # Step 2: Retrieve Maintenance Advisory for AC-017
        adv_res = await client.get(
            "/api/v1/advisories?aircraft_id=AC-017&as_of_date=2025-11-25",
            headers=planner_auth,
        )
        assert adv_res.status_code == 200
        advisories = adv_res.json()["items"]
        assert len(advisories) > 0, "Expected at least one advisory for AC-017 on 2025-11-25"

        hyd_adv = next(
            (a for a in advisories if "Hydraulic" in (a.get("component_name") or "")),
            advisories[0],
        )
        adv_id = hyd_adv["advisory_id"]
        assert hyd_adv["status"] in ("proposed", "accepted", "scheduled")
        assert hyd_adv["priority"] in ("P1", "P2", "P3", "P4")

        current_status = hyd_adv["status"]
        if current_status == "proposed":
            # Step 3: Transition Advisory to Accepted
            accept_res = await client.patch(
                f"/api/v1/advisories/{adv_id}",
                json={"status": "accepted"},
                headers=planner_auth,
            )
            assert accept_res.status_code == 200
            assert accept_res.json()["status"] == "accepted"

            # Transition Advisory to Scheduled
            sched_adv_res = await client.patch(
                f"/api/v1/advisories/{adv_id}",
                json={"status": "scheduled"},
                headers=planner_auth,
            )
            assert sched_adv_res.status_code == 200
            assert sched_adv_res.json()["status"] == "scheduled"
        elif current_status == "accepted":
            sched_adv_res = await client.patch(
                f"/api/v1/advisories/{adv_id}",
                json={"status": "scheduled"},
                headers=planner_auth,
            )
            assert sched_adv_res.status_code == 200
            assert sched_adv_res.json()["status"] == "scheduled"

        # Step 4: Create Work Order
        wo_res = await client.post(
            "/api/v1/work-orders",
            json={
                "aircraft_id": "AC-017",
                "component_id": hyd_adv.get("component_id"),
                "advisory_id": adv_id,
                "agency_id": "AG-LINE-01",
                "priority": hyd_adv.get("priority", "P2"),
            },
            headers=planner_auth,
        )
        assert wo_res.status_code in (200, 201)
        wo_data = wo_res.json()
        assert wo_data["aircraft_id"] == "AC-017"
        assert wo_data["status"] == "open"

        # Step 5: Execute What-If Availability Scenario Comparison
        scenario_res = await client.post(
            "/api/v1/scenarios/run",
            json={
                "type": "early_vs_run_to_failure",
                "params": {
                    "aircraft_id": "AC-017",
                    "early_replace_day": 3,
                    "planned_duration_days": 1,
                },
                "horizon_days": 30,
                "runs": 50,
                "seed": 42,
            },
            headers=planner_auth,
        )
        assert scenario_res.status_code == 200
        scenario_data = scenario_res.json()
        assert "baseline" in scenario_data
        assert "scenario" in scenario_data
        assert "delta" in scenario_data
        assert "availability_pct_points" in scenario_data["delta"]
