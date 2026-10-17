"""Tests for authentication, JWT issuance, and user session management."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_login_success():
    """Verify that all three seeded roles can authenticate and receive JWT tokens."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for username in ["commander", "planner", "technician"]:
            pwd = f"{username}123"
            res = await client.post(
                "/api/v1/auth/login",
                json={"username": username, "password": pwd},
            )
            assert res.status_code == 200, f"Login failed for {username}: {res.text}"
            data = res.json()
            assert "access_token" in data
            assert data["role"] == username
            assert data["username"] == username
            assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_password():
    """Verify that invalid password returns 401 with standard error format."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "commander", "password": "wrong_password"},
        )
        assert res.status_code == 401
        data = res.json()
        assert "error" in data
        assert data["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_unknown_user():
    """Verify that non-existent username returns 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/login",
            json={"username": "ghost_user", "password": "any_password"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_get_me_authenticated():
    """Verify /api/v1/auth/me returns identity with valid bearer token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login
        login_res = await client.post(
            "/api/v1/auth/login",
            json={"username": "planner", "password": "planner123"},
        )
        token = login_res.json()["access_token"]

        # 2. Get me
        me_res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == "planner"
        assert me_data["role"] == "planner"


@pytest.mark.asyncio
async def test_get_me_unauthorized():
    """Verify /api/v1/auth/me returns 401 without Bearer header."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/me")
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_get_me_invalid_token():
    """Verify /api/v1/auth/me returns 401 with malformed token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["code"] == "AUTHENTICATION_FAILED"
