"""Tests for fleet, aircraft, systems, and component API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def auth_headers() -> dict[str, str]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "commander", "password": "commander123"},
        )
        token = res.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_aircraft_requires_auth():
    """Verify aircraft endpoints reject unauthenticated requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/aircraft")
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_list_aircraft_success(auth_headers: dict[str, str]):
    """Verify listing aircraft returns paginated airframe models with availability status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/aircraft", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 40
        assert len(data["items"]) == 40
        assert "current_status" in data["items"][0]
        assert "tail_code" in data["items"][0]


@pytest.mark.asyncio
async def test_list_aircraft_filters(auth_headers: dict[str, str]):
    """Verify filtering by base ID and availability state."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/aircraft?base=BASE-NORTH", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        for item in data["items"]:
            assert item["base_id"] == "BASE-NORTH"


@pytest.mark.asyncio
async def test_get_aircraft_detail(auth_headers: dict[str, str]):
    """Verify retrieving detailed aircraft record including systems and installed components."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/aircraft/AC-017", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["aircraft_id"] == "AC-017"
        assert len(data["systems"]) == 7
        assert data["components_count"] >= 20
        assert len(data["installed_components"]) >= 20


@pytest.mark.asyncio
async def test_get_aircraft_not_found(auth_headers: dict[str, str]):
    """Verify 404 for non-existent aircraft ID with standard error format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/aircraft/AC-999", headers=auth_headers)
        assert res.status_code == 404
        data = res.json()
        assert data["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_systems(auth_headers: dict[str, str]):
    """Verify listing all 7 functional aircraft systems."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/systems", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 7
        system_ids = {s["system_id"] for s in data}
        assert "SYS-PROP" in system_ids
        assert "SYS-HYD" in system_ids


@pytest.mark.asyncio
async def test_list_component_types(auth_headers: dict[str, str]):
    """Verify listing all 20 component types with specifications."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/component-types", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 20


@pytest.mark.asyncio
async def test_list_components(auth_headers: dict[str, str]):
    """Verify component instance listing with pagination."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/components?page=1&page_size=20", headers=auth_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 20
        assert data["total"] >= 800
