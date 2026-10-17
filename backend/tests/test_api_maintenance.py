"""Tests for maintenance, work orders, agencies, and scheduled tasks endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, update

from app.core.database import get_session_factory
from app.main import app
from app.models.maintenance import WorkOrder
from app.models.platform import Advisory
from app.models.spares import Inventory


@pytest.fixture
async def planner_auth() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "planner", "password": "planner123"},
        )
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_work_orders(planner_auth: dict[str, str]):
    """Verify listing work orders with status filter and pagination."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/work-orders?page=1&page_size=20", headers=planner_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 20
        assert data["total"] >= 1000
        assert "agency_id" in data["items"][0]
        assert "status" in data["items"][0]


@pytest.mark.asyncio
async def test_list_maintenance_events(planner_auth: dict[str, str]):
    """Verify listing physical maintenance events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/maintenance/events?type=unscheduled&page_size=10", headers=planner_auth
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 10
        for item in data["items"]:
            assert item["type"] == "unscheduled"


@pytest.mark.asyncio
async def test_list_agencies(planner_auth: dict[str, str]):
    """Verify retrieving maintenance workshop agencies."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/agencies", headers=planner_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 3
        agency_ids = {a["agency_id"] for a in data}
        assert "AG-LINE-01" in agency_ids
        assert "AG-BASE-01" in agency_ids
        assert "AG-DEPOT-01" in agency_ids


@pytest.mark.asyncio
async def test_list_scheduled_tasks(planner_auth: dict[str, str]):
    """Verify listing scheduled phase inspection tasks across aircraft."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/scheduled-tasks?aircraft_id=AC-017", headers=planner_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 3  # A-check, B-check, C-check


@pytest.mark.asyncio
async def test_create_work_order(planner_auth: dict[str, str]):
    """Verify creating a work order from an advisory with slot reservation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch an open advisory
        adv_res = await client.get(
            "/api/v1/advisories?status=proposed&page_size=1", headers=planner_auth
        )
        assert adv_res.status_code == 200
        advisories = adv_res.json()["items"]
        if not advisories:
            # If all proposed are taken, just test with None advisory_id
            adv_id = None
            aircraft_id = "AC-017"
            comp_id = "CMP-00325"
        else:
            adv_id = advisories[0]["advisory_id"]
            aircraft_id = advisories[0]["aircraft_id"]
            comp_id = advisories[0]["component_id"]

        wo_payload = {
            "advisory_id": adv_id,
            "aircraft_id": aircraft_id,
            "component_id": comp_id,
            "agency_id": "AG-BASE-01",
            "title": "Scheduled Proactive Pump Replacement",
            "description": "Integration test created proactive replacement order",
            "type": "predictive",
            "priority": "P2",
            "scheduled_start": "2025-11-26T08:00:00",
            "scheduled_end": "2025-11-28T12:00:00",
            "bay_id": "BAY-BASE-01",
            "spare_part_id": "HYD-114",
            "spare_quantity": 1,
        }

        try:
            res = await client.post("/api/v1/work-orders", json=wo_payload, headers=planner_auth)
            assert res.status_code == 201
            wo = res.json()
            assert wo["wo_id"].startswith("WO-")
            assert wo["aircraft_id"] == aircraft_id
            assert wo["status"] == "open"
            assert wo["agency_id"] == "AG-BASE-01"
        finally:
            if adv_id:
                factory = get_session_factory()
                async with factory() as s:
                    await s.execute(delete(WorkOrder).where(WorkOrder.advisory_id == adv_id))
                    await s.execute(
                        update(Advisory)
                        .where(Advisory.advisory_id == adv_id)
                        .values(status="proposed")
                    )
                    await s.execute(
                        update(Inventory)
                        .where(
                            Inventory.part_number == "HYD-114", Inventory.location_id == "BASE-MAIN"
                        )
                        .values(reserved=0)
                    )
                    await s.commit()
