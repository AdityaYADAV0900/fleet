"""Tests for spares, inventory levels, and material transactions endpoints."""

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


@pytest.mark.asyncio
async def test_list_inventory(technician_auth: dict[str, str]):
    """Verify inventory stock query with low_stock alert calculation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/inventory?location_id=BASE-MAIN", headers=technician_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 20  # 20 parts at BASE-MAIN
        assert "on_hand" in data["items"][0]
        assert "is_low_stock" in data["items"][0]


@pytest.mark.asyncio
async def test_list_spare_parts(technician_auth: dict[str, str]):
    """Verify listing spare parts catalog."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/inventory/parts", headers=technician_auth)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 20
        part_nos = {p["part_number"] for p in data}
        assert "HYD-114" in part_nos
        assert "PROP-101" in part_nos


@pytest.mark.asyncio
async def test_list_inventory_transactions(technician_auth: dict[str, str]):
    """Verify listing material movement transactions."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/inventory/transactions?type=issue&page_size=10", headers=technician_auth
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["items"]) == 10
        for item in data["items"]:
            assert item["type"] == "issue"
