"""Integration tests for Digital Twin API endpoints, replay, snapshots, and what-if simulation (§6)."""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_session_factory
from app.main import app
from app.twin.snapshots import write_twin_snapshots


@pytest.fixture
async def technician_auth() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "technician", "password": "technician123"},
        )
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


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
async def test_get_fleet_twin(technician_auth: dict[str, str]):
    """Verify GET /api/v1/twin/fleet returns fleet hierarchy and state distribution."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/twin/fleet", headers=technician_auth)
        assert res.status_code == 200
        data = res.json()

        assert data["node_id"] == "FLEET"
        assert 0.0 <= data["health_index"] <= 100.0
        assert data["total_aircraft"] >= 10
        assert "Healthy" in data["state_distribution"]
        assert "Watch" in data["state_distribution"]
        assert "Degraded" in data["state_distribution"]
        assert len(data["aircraft"]) == data["total_aircraft"]


@pytest.mark.asyncio
async def test_get_aircraft_twin_and_replay_ac017(planner_auth: dict[str, str]):
    """Verify GET /api/v1/twin/aircraft/{id} with historical replay for AC-017 (§6).

    Replay on 2025-11-25: AC-017 must return Degraded state with Primary Hydraulic Pump
    (CMP-00325) identified as the worst-component driver.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Query AC-017 as of 2025-11-25
        res = await client.get(
            "/api/v1/twin/aircraft/AC-017?as_of=2025-11-25",
            headers=planner_auth,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["aircraft_id"] == "AC-017"
        assert data["tail_code"] == "AC-017"
        assert data["is_replay"] is True
        assert data["as_of_date"] == "2025-11-25"
        assert data["state"] == "Degraded"

        # Verify worst-component driver reported
        driver = data["driver_component"]
        assert driver is not None, "Driver component must be reported"
        assert "Hydraulic Pump" in driver["component_name"]
        assert driver["system_name"] == "Hydraulics System"
        assert driver["state"] == "Degraded"
        assert driver["health_index"] < 60.0
        assert driver["risk"] >= 0.50

        # Verify constituent systems exist
        assert len(data["systems"]) >= 5
        hyd_sys = next((s for s in data["systems"] if "Hydraulic" in s["system_name"]), None)
        assert hyd_sys is not None
        assert hyd_sys["state"] == "Degraded"
        assert len(hyd_sys["components"]) >= 1

        # Verify trajectory exists
        assert len(data["predicted_trajectory"]) > 0
        forecast_pts = [p for p in data["predicted_trajectory"] if p["is_forecast"]]
        assert len(forecast_pts) > 0


@pytest.mark.asyncio
async def test_get_component_twin(technician_auth: dict[str, str]):
    """Verify GET /api/v1/twin/component/{id} returns component state and history."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # CMP-00325 is AC-017's Primary Hydraulic Pump
        res = await client.get(
            "/api/v1/twin/component/CMP-00325?as_of=2025-11-25",
            headers=technician_auth,
        )
        assert res.status_code == 200
        data = res.json()

        assert data["component_id"] == "CMP-00325"
        assert "Hydraulic Pump" in data["component_name"]
        assert data["aircraft_id"] == "AC-017"
        assert data["criticality"] == 5
        assert data["state"] == "Degraded"
        assert data["is_replay"] is True
        assert data["operating_hours"] >= 0.0
        assert len(data["predicted_trajectory"]) > 0


@pytest.mark.asyncio
async def test_post_twin_whatif_scenario_delegation(
    planner_auth: dict[str, str],
    technician_auth: dict[str, str],
):
    """Verify POST /api/v1/twin/whatif delegates to the Monte Carlo scenario engine."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "type": "schedule_maintenance",
            "params": {"aircraft_id": "AC-017", "start_day": 3, "duration_days": 4},
            "horizon_days": 14,
            "runs": 50,
            "seed": 42,
        }

        # 1. Technician should be forbidden (requires Planner or Commander)
        res_tech = await client.post(
            "/api/v1/twin/whatif",
            json=payload,
            headers=technician_auth,
        )
        assert res_tech.status_code == 403

        # 2. Planner should succeed
        res_plan = await client.post(
            "/api/v1/twin/whatif",
            json=payload,
            headers=planner_auth,
        )
        assert res_plan.status_code == 200
        data = res_plan.json()

        assert "baseline" in data
        assert "scenario" in data
        assert "delta" in data
        assert "availability_pct_points" in data["delta"]
        assert "aircraft_days_lost" in data["delta"]
        assert data["horizon_days"] == 14


@pytest.mark.asyncio
async def test_snapshot_writer_persists_twin_snapshots():
    """Verify write_twin_snapshots populates twin_snapshots table for fleet, aircraft, systems, and components."""
    factory = get_session_factory()
    target_date = date(2025, 11, 25)

    async with factory() as session:
        # Write snapshots for target date
        count = await write_twin_snapshots(
            session=session,
            as_of_date=target_date,
            aircraft_id="AC-017",
        )
        assert count > 0, "Must write twin snapshots for AC-017"

    # Query twin endpoint which will read from existing snapshots
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "planner", "password": "planner123"},
        )
        headers = {"Authorization": f"Bearer {res.json()['access_token']}"}

        res_snap = await client.get(
            f"/api/v1/twin/aircraft/AC-017?as_of={target_date.isoformat()}",
            headers=headers,
        )
        assert res_snap.status_code == 200
        snap_data = res_snap.json()
        assert snap_data["aircraft_id"] == "AC-017"
        assert snap_data["state"] == "Degraded"
