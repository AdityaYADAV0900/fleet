"""API integration and RBAC tests for Fleet Availability and Scenario endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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


@pytest.fixture
async def commander_auth() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "commander", "password": "commander123"},
        )
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_availability_endpoints_auth_required():
    """Verify that unauthenticated requests to availability endpoints are rejected with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/api/v1/kpis")
        assert res1.status_code == 401

        res2 = await client.get("/api/v1/fleet/summary")
        assert res2.status_code == 401

        res3 = await client.get("/api/v1/fleet/availability/trend")
        assert res3.status_code == 401

        res4 = await client.post(
            "/api/v1/scenarios/run",
            json={"type": "extra_capacity", "params": {"bay_increase": 1}},
        )
        assert res4.status_code == 401

        res5 = await client.get("/api/v1/scenarios")
        assert res5.status_code == 401


@pytest.mark.asyncio
async def test_get_fleet_kpis(technician_auth: dict[str, str]):
    """Verify GET /api/v1/kpis returns valid KPI response structure."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/kpis", headers=technician_auth)
        assert res.status_code == 200
        data = res.json()

        assert "fleet_availability_pct" in data
        assert "inherent_availability_pct" in data
        assert "operational_availability_pct" in data
        assert "serviceability_pct" in data
        assert "downtime_by_cause" in data
        assert "mtbf_hours" in data
        assert "mttr_hours" in data
        assert "turnaround_days" in data
        assert "failure_rate_per_1000_hours" in data
        assert "backlog" in data
        assert "readiness_proxy_pct" in data
        assert "spare_fill_rate_pct" in data
        assert data["total_aircraft"] >= 0


@pytest.mark.asyncio
async def test_get_fleet_summary(technician_auth: dict[str, str]):
    """Verify GET /api/v1/fleet/summary returns top-level card metrics."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/fleet/summary", headers=technician_auth)
        assert res.status_code == 200
        data = res.json()

        assert "as_of" in data
        assert "total_aircraft" in data
        assert "serviceable_count" in data
        assert "availability_pct" in data
        assert "by_state" in data
        assert "Available" in data["by_state"]
        assert "open_p1" in data
        assert "open_p2" in data
        assert "backlog" in data
        assert "parts_at_risk" in data


@pytest.mark.asyncio
async def test_get_fleet_availability_trend(technician_auth: dict[str, str]):
    """Verify GET /api/v1/fleet/availability/trend returns historical and forecast points."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/fleet/availability/trend?horizon=14", headers=technician_auth
        )
        assert res.status_code == 200
        data = res.json()

        assert "points" in data
        assert len(data["points"]) > 0

        # Forecast points should have p10, p90, and is_forecast=True
        forecast_points = [p for p in data["points"] if p["is_forecast"]]
        assert len(forecast_points) == 14
        for fp in forecast_points:
            assert fp["p10"] is not None
            assert fp["p90"] is not None
            assert fp["avail"] >= 0.0


@pytest.mark.asyncio
async def test_scenarios_rbac_and_run(
    technician_auth: dict[str, str],
    planner_auth: dict[str, str],
    commander_auth: dict[str, str],
):
    """Verify RBAC on POST /scenarios/run and GET /scenarios, and execution correctness."""
    transport = ASGITransport(app=app)
    payload = {
        "type": "spare_unavailable",
        "params": {"part_number": "HYD-114", "stock_override": 0, "lead_time_days": 30},
        "horizon_days": 20,
        "runs": 50,
        "seed": 42,
    }

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Technician should be forbidden (403)
        res_tech = await client.post("/api/v1/scenarios/run", json=payload, headers=technician_auth)
        assert res_tech.status_code == 403

        # 2. Planner should succeed (200)
        res_planner = await client.post("/api/v1/scenarios/run", json=payload, headers=planner_auth)
        assert res_planner.status_code == 200
        data = res_planner.json()

        assert data["type"] == "spare_unavailable"
        assert "id" in data
        assert "baseline" in data
        assert "scenario" in data
        assert "delta" in data
        assert "by_cause" in data
        assert "availability_pct_points" in data["delta"]

        saved_id = data["id"]

        # 3. GET /scenarios should list the saved run
        res_list = await client.get("/api/v1/scenarios", headers=commander_auth)
        assert res_list.status_code == 200
        items = res_list.json()
        assert any(item["id"] == saved_id for item in items)
