"""API integration and RBAC tests for predictive maintenance engine endpoints."""

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
async def test_engine_endpoints_require_auth():
    """Verify all engine endpoints reject unauthenticated requests with 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res1 = await client.get("/api/v1/predictions")
        assert res1.status_code == 401

        res2 = await client.get("/api/v1/advisories")
        assert res2.status_code == 401

        res3 = await client.get("/api/v1/alerts")
        assert res3.status_code == 401

        res4 = await client.post("/api/v1/engine/run", json={"as_of_date": "2025-11-25"})
        assert res4.status_code == 401


@pytest.mark.asyncio
async def test_rbac_technician_read_only(technician_auth: dict[str, str]):
    """Technicians can read predictions, advisories, and alerts, but cannot mutate or trigger runs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Read operations should succeed
        res_pred = await client.get("/api/v1/predictions", headers=technician_auth)
        assert res_pred.status_code == 200

        res_adv = await client.get("/api/v1/advisories", headers=technician_auth)
        assert res_adv.status_code == 200

        res_alert = await client.get("/api/v1/alerts", headers=technician_auth)
        assert res_alert.status_code == 200

        # Mutation operations must be 403 Forbidden for technician
        res_patch = await client.patch(
            "/api/v1/advisories/ADV-TEST",
            json={"status": "accepted"},
            headers=technician_auth,
        )
        assert res_patch.status_code == 403

        res_ack = await client.patch(
            "/api/v1/alerts/1/ack",
            json={"acknowledged": True},
            headers=technician_auth,
        )
        assert res_ack.status_code == 403

        res_run = await client.post(
            "/api/v1/engine/run",
            json={"as_of_date": "2025-11-25"},
            headers=technician_auth,
        )
        assert res_run.status_code == 403


@pytest.mark.asyncio
async def test_list_predictions_filtering(planner_auth: dict[str, str]):
    """Verify predictions querying with aircraft and risk filters."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/predictions?aircraft_id=AC-017&page=1&page_size=25",
            headers=planner_auth,
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

        if data["total"] > 0:
            first = data["items"][0]
            assert "component_id" in first
            assert "risk_14d" in first
            assert "rul_p50" in first
            assert first["rul_p10"] <= first["rul_p50"] <= first["rul_p90"]


@pytest.mark.asyncio
async def test_list_advisories_and_detail(planner_auth: dict[str, str]):
    """Verify listing advisories, filtering, and retrieving detailed explanation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/api/v1/advisories?aircraft_id=AC-017",
            headers=planner_auth,
        )
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        if data["total"] == 0:
            await client.post(
                "/api/v1/engine/run",
                json={"as_of_date": "2025-11-25", "aircraft_id": "AC-017", "dry_run": False},
                headers=planner_auth,
            )
            res = await client.get(
                "/api/v1/advisories?aircraft_id=AC-017",
                headers=planner_auth,
            )
            data = res.json()
        assert data["total"] >= 1

        adv = data["items"][0]
        adv_id = adv["advisory_id"]
        assert adv["aircraft_id"] == "AC-017"
        assert adv["priority"] in ["P1", "P2", "P3", "P4"]
        assert "explanation" in adv
        assert adv["explanation"] is not None
        assert "health_index" in adv["explanation"]
        assert (
            "top_factors" in adv["explanation"] or "contributing_parameters" in adv["explanation"]
        )

        # Detail fetch
        res_detail = await client.get(f"/api/v1/advisories/{adv_id}", headers=planner_auth)
        assert res_detail.status_code == 200
        detail = res_detail.json()
        assert detail["advisory_id"] == adv_id
        assert detail["component_id"] == adv["component_id"]
        assert detail["explanation"] is not None
        assert "narrative" in detail["explanation"] or "summary" in detail["explanation"]


@pytest.mark.asyncio
async def test_advisory_not_found(planner_auth: dict[str, str]):
    """Verify 404 response for nonexistent advisory ID."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/advisories/ADV-NONEXISTENT-999", headers=planner_auth)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_advisory_workflow_transitions(commander_auth: dict[str, str]):
    """Verify status transitions: proposed -> accepted -> scheduled -> completed, and dismiss validation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Find a proposed advisory
        res_list = await client.get(
            "/api/v1/advisories?status=proposed&page_size=5", headers=commander_auth
        )
        assert res_list.status_code == 200
        items = res_list.json()["items"]
        if not items:
            await client.post(
                "/api/v1/engine/run",
                json={"as_of_date": "2025-11-25", "aircraft_id": "AC-017", "dry_run": False},
                headers=commander_auth,
            )
            res_list = await client.get(
                "/api/v1/advisories?status=proposed&page_size=5", headers=commander_auth
            )
            items = res_list.json()["items"]
        if not items:
            pytest.skip("No proposed advisories in test DB to exercise transition")

        target_adv = items[0]
        adv_id = target_adv["advisory_id"]

        # 1. Invalid dismissal without reason should return 422
        res_bad_dismiss = await client.patch(
            f"/api/v1/advisories/{adv_id}",
            json={"status": "dismissed"},
            headers=commander_auth,
        )
        assert res_bad_dismiss.status_code == 422

        # 2. Transition proposed -> accepted
        res_accept = await client.patch(
            f"/api/v1/advisories/{adv_id}",
            json={"status": "accepted"},
            headers=commander_auth,
        )
        assert res_accept.status_code == 200
        assert res_accept.json()["status"] == "accepted"

        # 3. Transition accepted -> scheduled
        res_sched = await client.patch(
            f"/api/v1/advisories/{adv_id}",
            json={"status": "scheduled"},
            headers=commander_auth,
        )
        assert res_sched.status_code == 200
        assert res_sched.json()["status"] == "scheduled"

        # 4. Transition scheduled -> completed
        res_comp = await client.patch(
            f"/api/v1/advisories/{adv_id}",
            json={"status": "completed"},
            headers=commander_auth,
        )
        assert res_comp.status_code == 200
        assert res_comp.json()["status"] == "completed"

        # 5. Invalid transition from completed -> accepted should return 422
        res_invalid = await client.patch(
            f"/api/v1/advisories/{adv_id}",
            json={"status": "accepted"},
            headers=commander_auth,
        )
        assert res_invalid.status_code == 422


@pytest.mark.asyncio
async def test_list_alerts_and_acknowledgement(planner_auth: dict[str, str]):
    """Verify alerts listing and acknowledgement workflow."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/alerts?page_size=10", headers=planner_auth)
        assert res.status_code == 200
        data = res.json()
        assert "items" in data
        assert "total" in data

        if data["total"] > 0:
            first_alert = data["items"][0]
            alert_id = first_alert["alert_id"]

            # Acknowledge the alert
            res_ack = await client.patch(
                f"/api/v1/alerts/{alert_id}/ack",
                json={"acknowledged": True},
                headers=planner_auth,
            )
            assert res_ack.status_code == 200
            assert res_ack.json()["acknowledged"] is True


@pytest.mark.asyncio
async def test_engine_run_scoped(planner_auth: dict[str, str]):
    """Verify triggering an engine run for a single aircraft returns summary."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/engine/run",
            json={
                "as_of_date": "2025-11-25",
                "aircraft_id": "AC-017",
                "dry_run": False,
            },
            headers=planner_auth,
        )
        assert res.status_code == 200
        summary = res.json()
        assert summary["as_of_date"] == "2025-11-25"
        assert summary["components_scored"] >= 20
        assert summary["duration_seconds"] >= 0.0
        assert summary["predictions_recorded"] >= 20
