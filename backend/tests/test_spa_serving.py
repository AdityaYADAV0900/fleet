"""Unit tests for FastAPI static file serving and SPA fallback routing (Phase 11)."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_spa_root_and_fallback():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Root endpoint serves index.html
        root_res = await client.get("/")
        assert root_res.status_code == 200
        assert "<!doctype html" in root_res.text.lower() or "<html" in root_res.text.lower()

        # Client-side SPA routes fallback to index.html with 200
        dashboard_res = await client.get("/dashboard")
        assert dashboard_res.status_code == 200
        assert (
            "<!doctype html" in dashboard_res.text.lower() or "<html" in dashboard_res.text.lower()
        )

        aircraft_res = await client.get("/aircraft?id=AC-017")
        assert aircraft_res.status_code == 200

        # Unmatched API routes must return 404 JSON, NOT fallback to SPA HTML
        api_404_res = await client.get("/api/v1/nonexistent_route_test")
        assert api_404_res.status_code == 404
        assert "application/json" in api_404_res.headers.get("content-type", "")

        # Documentation and openapi routes are unaffected
        docs_res = await client.get("/docs")
        assert docs_res.status_code == 200
