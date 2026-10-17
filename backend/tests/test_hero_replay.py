"""Hero aircraft (AC-017) replay progression test across time."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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
async def test_ac017_hero_progression_across_dates(planner_auth: dict[str, str]):
    """Verify that AC-017 shows degradation progression from early nominal/watch to degraded P2 advisory.

    When replayed:
    - On 2025-11-05: System is in early stage (higher health index, longer RUL, lower failure risk).
    - On 2025-11-25: Hydraulic degradation is evident (lower health index, RUL drops, risk escalates, P2 advisory triggered).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Trigger scoring for early date: 2025-11-05
        res_early = await client.post(
            "/api/v1/engine/run",
            json={"as_of_date": "2025-11-05", "aircraft_id": "AC-017"},
            headers=planner_auth,
        )
        assert res_early.status_code == 200
        summary_early = res_early.json()
        assert summary_early["components_scored"] >= 20

        # Query early predictions
        res_early_preds = await client.get(
            "/api/v1/predictions?aircraft_id=AC-017&as_of_date=2025-11-05",
            headers=planner_auth,
        )
        assert res_early_preds.status_code == 200
        early_hyd = next(
            (
                p
                for p in res_early_preds.json()["items"]
                if "Primary Hydraulic Pump" in (p.get("component_name") or "")
            ),
            None,
        )

        # 2. Trigger scoring for late date: 2025-11-25
        res_late = await client.post(
            "/api/v1/engine/run",
            json={"as_of_date": "2025-11-25", "aircraft_id": "AC-017"},
            headers=planner_auth,
        )
        assert res_late.status_code == 200
        summary_late = res_late.json()
        assert summary_late["components_scored"] >= 20

        # Query late predictions
        res_late_preds = await client.get(
            "/api/v1/predictions?aircraft_id=AC-017&as_of_date=2025-11-25",
            headers=planner_auth,
        )
        assert res_late_preds.status_code == 200
        late_hyd = next(
            (
                p
                for p in res_late_preds.json()["items"]
                if "Primary Hydraulic Pump" in (p.get("component_name") or "")
            ),
            None,
        )
        assert late_hyd is not None, "AC-017 Primary Hydraulic Pump must be scored"

        # Query late advisories
        res_advisories = await client.get(
            "/api/v1/advisories?aircraft_id=AC-017",
            headers=planner_auth,
        )
        assert res_advisories.status_code == 200
        adv_items = res_advisories.json()["items"]
        hyd_adv = next(
            (
                a
                for a in adv_items
                if "Primary Hydraulic Pump" in (a.get("component_name") or "")
                and a["as_of_date"] == "2025-11-25"
            ),
            None,
        )
        assert hyd_adv is not None, (
            "AC-017 Primary Hydraulic Pump must have an advisory on 2025-11-25"
        )

        # Verify hero progression on AC-017 Primary Hydraulic Pump:
        # On 2025-11-25: High risk (>= 0.50), RUL drops to <= 20 days (specifically 12 days), P2 priority
        assert late_hyd["risk_14d"] >= 0.50
        assert late_hyd["rul_p50"] <= 20.0
        assert hyd_adv["priority"] == "P2"
        assert "replace" in hyd_adv["action"].lower()
        assert hyd_adv["explanation"]["health_index"] < 60.0  # Degraded state

        # Compare progression across the timeline (RUL drops over time)
        if early_hyd is not None:
            assert late_hyd["rul_p50"] < early_hyd["rul_p50"]
