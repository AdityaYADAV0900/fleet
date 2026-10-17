"""Comprehensive tests for role-based access control (RBAC), 401/403 errors, and input validation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


async def get_token_for_user(client: AsyncClient, username: str) -> str:
    """Helper to authenticate a seeded demo user and retrieve the bearer token."""
    res = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": f"{username}123"},
    )
    assert res.status_code == 200, f"Failed to login {username}: {res.text}"
    return res.json()["access_token"]


@pytest.mark.asyncio
async def test_unauthenticated_endpoints_return_401() -> None:
    """Verify that requests without an Authorization header or with invalid token receive 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        protected_endpoints = [
            ("GET", "/api/v1/fleet/summary"),
            ("GET", "/api/v1/aircraft"),
            ("GET", "/api/v1/advisories"),
            ("GET", "/api/v1/work-orders"),
            ("GET", "/api/v1/inventory"),
            ("GET", "/api/v1/alerts"),
            ("GET", "/api/v1/kpis"),
            ("GET", "/api/v1/twin/fleet"),
            ("POST", "/api/v1/work-orders"),
            ("POST", "/api/v1/scenarios/run"),
            ("POST", "/api/v1/engine/run"),
            ("POST", "/api/v1/ingest/sensor-readings"),
        ]

        for method, endpoint in protected_endpoints:
            # 1. No auth header
            res_no_auth = await client.request(method, endpoint)
            assert res_no_auth.status_code == 401, (
                f"Expected 401 for {method} {endpoint}, got {res_no_auth.status_code}"
            )
            assert res_no_auth.json()["error"]["code"] == "AUTHENTICATION_FAILED"

            # 2. Invalid bearer token
            res_bad_token = await client.request(
                method, endpoint, headers={"Authorization": "Bearer bad.token.here"}
            )
            assert res_bad_token.status_code == 401
            assert res_bad_token.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_technician_role_forbidden_on_write_endpoints() -> None:
    """Verify that technician role (read-only) receives 403 Forbidden on write routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tech_token = await get_token_for_user(client, "technician")
        headers = {"Authorization": f"Bearer {tech_token}"}

        # 1. PATCH /advisories/{id}
        res_patch_adv = await client.patch(
            "/api/v1/advisories/adv_dummy",
            headers=headers,
            json={"status": "accepted"},
        )
        assert res_patch_adv.status_code == 403
        assert res_patch_adv.json()["error"]["code"] == "FORBIDDEN"

        # 2. POST /work-orders
        res_post_wo = await client.post(
            "/api/v1/work-orders",
            headers=headers,
            json={
                "advisory_id": "adv_dummy",
                "agency_id": "ag_dummy",
                "planned_start": "2026-01-01",
            },
        )
        assert res_post_wo.status_code == 403
        assert res_post_wo.json()["error"]["code"] == "FORBIDDEN"

        # 3. POST /scenarios/run
        res_scenario = await client.post(
            "/api/v1/scenarios/run",
            headers=headers,
            json={"type": "schedule_maintenance", "params": {}},
        )
        assert res_scenario.status_code == 403
        assert res_scenario.json()["error"]["code"] == "FORBIDDEN"

        # 4. GET /scenarios
        res_get_scenarios = await client.get("/api/v1/scenarios", headers=headers)
        assert res_get_scenarios.status_code == 403
        assert res_get_scenarios.json()["error"]["code"] == "FORBIDDEN"

        # 5. POST /ingest/sensor-readings
        res_ingest = await client.post(
            "/api/v1/ingest/sensor-readings",
            headers=headers,
            json={"readings": []},
        )
        assert res_ingest.status_code == 403
        assert res_ingest.json()["error"]["code"] == "FORBIDDEN"

        # 6. POST /engine/run
        res_engine = await client.post(
            "/api/v1/engine/run",
            headers=headers,
            json={"as_of_date": "2025-10-01"},
        )
        assert res_engine.status_code == 403
        assert res_engine.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_planner_and_commander_roles_permitted() -> None:
    """Verify that planner and commander roles have write access and read access."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Planner
        planner_token = await get_token_for_user(client, "planner")
        planner_headers = {"Authorization": f"Bearer {planner_token}"}

        # GET /scenarios should succeed (200) for planner
        res_scenarios = await client.get("/api/v1/scenarios", headers=planner_headers)
        assert res_scenarios.status_code == 200

        # Commander
        cmdr_token = await get_token_for_user(client, "commander")
        cmdr_headers = {"Authorization": f"Bearer {cmdr_token}"}

        res_cmdr_scenarios = await client.get("/api/v1/scenarios", headers=cmdr_headers)
        assert res_cmdr_scenarios.status_code == 200


@pytest.mark.asyncio
async def test_input_validation_errors() -> None:
    """Verify that malformed requests return 422 Unprocessable Content."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        planner_token = await get_token_for_user(client, "planner")
        headers = {"Authorization": f"Bearer {planner_token}"}

        # 1. Invalid query param (min_risk > 1.0)
        res_risk = await client.get(
            "/api/v1/predictions?min_risk=2.5",
            headers=headers,
        )
        assert res_risk.status_code == 422

        # 2. Invalid date format
        res_date = await client.get(
            "/api/v1/fleet/summary?as_of=not-a-date",
            headers=headers,
        )
        assert res_date.status_code == 422

        # 3. Malformed JSON payload
        res_body = await client.post(
            "/api/v1/scenarios/run",
            headers=headers,
            json={"type": 12345},  # type must be string
        )
        assert res_body.status_code == 422
