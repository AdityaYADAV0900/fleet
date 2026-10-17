import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "ok"
        assert data["database"] in ("connected", "disconnected")
        assert data["synthetic_data"] is True
        assert data["status"] in ("healthy", "degraded")


@pytest.mark.asyncio
async def test_health_alias_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["backend"] == "ok"
        assert data["database"] in ("connected", "disconnected")
