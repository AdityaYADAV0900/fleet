"""Tests for sensor trend queries, fault events, and batch ingestion."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def get_token_for_role(role: str) -> str:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": role, "password": f"{role}123"},
        )
        return res.json()["access_token"]


@pytest.mark.asyncio
async def test_get_component_sensors():
    """Verify retrieving telemetry trend readings for a component."""
    token = await get_token_for_role("technician")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get an active component
        comps_res = await client.get(
            "/api/v1/components?aircraft_id=AC-017&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        comp_id = comps_res.json()["items"][0]["component_id"]

        # Fetch sensor readings
        res = await client.get(
            f"/api/v1/components/{comp_id}/sensors?limit=10",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        assert "mean" in data[0]
        assert "quality_flag" in data[0]
        assert "date" in data[0]


@pytest.mark.asyncio
async def test_get_component_sensors_not_found():
    """Verify 404 for unknown component."""
    token = await get_token_for_role("commander")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/components/CMP-INVALID/sensors",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_fault_events():
    """Verify listing operational fault events."""
    token = await get_token_for_role("technician")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/fault-events?limit=25",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data) > 0
        assert "fault_code" in data[0]
        assert "severity" in data[0]


@pytest.mark.asyncio
async def test_ingest_sensor_readings_unauthorized():
    """Verify ingestion endpoint rejects unauthenticated requests with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/ingest/sensor-readings",
            json={"readings": []},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_ingest_sensor_readings_forbidden_for_technician():
    """Verify that technician role is strictly read-only and receives 403 Forbidden on ingestion."""
    token = await get_token_for_role("technician")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "readings": [
                {
                    "flight_id": "FL-000001",
                    "component_id": "CMP-00001",
                    "parameter": "test_param",
                    "mean": 10.0,
                    "max": 12.0,
                    "min": 8.0,
                    "std": 1.0,
                    "quality_flag": "valid",
                }
            ]
        }
        res = await client.post(
            "/api/v1/ingest/sensor-readings",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert res.status_code == 403
        data = res.json()
        assert data["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_ingest_sensor_readings_planner_success():
    """Verify that planner role can ingest valid sensor readings."""
    token = await get_token_for_role("planner")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get valid flight and component IDs
        comps_res = await client.get(
            "/api/v1/components?page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        comp_id = comps_res.json()["items"][0]["component_id"]

        # Valid payload
        payload = {
            "readings": [
                {
                    "flight_id": "FL-000001",
                    "component_id": comp_id,
                    "parameter": "test_pressure_psi",
                    "mean": 2980.5,
                    "max": 3020.0,
                    "min": 2940.0,
                    "std": 15.2,
                    "quality_flag": "valid",
                }
            ]
        }
        res = await client.post(
            "/api/v1/ingest/sensor-readings",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_submitted"] == 1
        assert data["accepted_count"] == 1
        assert data["rejected_count"] == 0
        assert len(data["errors"]) == 0


@pytest.mark.asyncio
async def test_ingest_sensor_readings_per_row_errors():
    """Verify that bad rows are reported individually without rejecting valid rows."""
    token = await get_token_for_role("planner")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Row 0: non-existent flight
        # Row 1: non-existent component
        # Row 2: invalid min > max
        payload = {
            "readings": [
                {
                    "flight_id": "FL-NONEXISTENT",
                    "component_id": "CMP-00001",
                    "parameter": "pressure",
                    "mean": 10.0,
                    "max": 12.0,
                    "min": 8.0,
                    "std": 1.0,
                    "quality_flag": "valid",
                },
                {
                    "flight_id": "FL-000001",
                    "component_id": "CMP-NONEXISTENT",
                    "parameter": "pressure",
                    "mean": 10.0,
                    "max": 12.0,
                    "min": 8.0,
                    "std": 1.0,
                    "quality_flag": "valid",
                },
                {
                    "flight_id": "FL-000001",
                    "component_id": "CMP-00001",
                    "parameter": "pressure",
                    "mean": 10.0,
                    "max": 8.0,
                    "min": 15.0,  # min > max
                    "std": 1.0,
                    "quality_flag": "valid",
                },
            ]
        }
        res = await client.post(
            "/api/v1/ingest/sensor-readings",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        assert res.status_code == 201
        data = res.json()
        assert data["total_submitted"] == 3
        assert data["rejected_count"] == 3
        assert len(data["errors"]) == 3
        assert data["errors"][0]["field"] == "flight_id"
        assert data["errors"][1]["field"] == "component_id"
        assert data["errors"][2]["field"] == "min"


@pytest.mark.asyncio
async def test_get_component_anomalies():
    """Verify retrieving anomaly scores timeline for a component."""
    token = await get_token_for_role("planner")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check AC-017 hydraulic pump or any active component
        comps_res = await client.get(
            "/api/v1/components?aircraft_id=AC-017&page_size=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        comp_id = comps_res.json()["items"][0]["component_id"]

        res = await client.get(
            f"/api/v1/components/{comp_id}/anomalies",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "score" in data[0]
            assert "threshold" in data[0]
            assert "is_anomaly" in data[0]
            assert "date" in data[0]
