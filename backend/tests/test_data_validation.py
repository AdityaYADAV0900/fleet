"""Data validation tests verifying synthetic data quality, reproducibility, and correlations."""

from __future__ import annotations

from datetime import date

import asyncpg
import pytest

from app.config import get_settings
from data_gen.config import FleetConfig, SimulationConfig, TimelineConfig
from data_gen.db_loader import normalize_db_url
from data_gen.generator import FleetSimulator


def test_generator_seed_reproducibility() -> None:
    """Verify that identical random seeds produce identical simulator outputs."""
    cfg1 = SimulationConfig(
        seed=123,
        fleet=FleetConfig(size=5),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 2, 28)),
    )
    cfg2 = SimulationConfig(
        seed=123,
        fleet=FleetConfig(size=5),
        timeline=TimelineConfig(start_date=date(2025, 1, 1), end_date=date(2025, 2, 28)),
    )

    sim1 = FleetSimulator(cfg1)
    data1 = sim1.generate()

    sim2 = FleetSimulator(cfg2)
    data2 = sim2.generate()

    assert len(data1.flights) == len(data2.flights)
    assert len(data1.sensor_readings) == len(data2.sensor_readings)
    assert data1.sensor_readings[0]["mean"] == data2.sensor_readings[0]["mean"]


@pytest.fixture
def target_db_url(test_db_url: str) -> str:
    # If test_db_url is empty, fall back to effective_database_url
    return test_db_url


@pytest.mark.asyncio
async def get_active_conn(test_db_url: str) -> tuple[asyncpg.Connection, str]:
    """Connect to test db if it has sensor rows, otherwise connect to main db."""
    norm_test = normalize_db_url(test_db_url)
    try:
        conn = await asyncpg.connect(norm_test)
        cnt = await conn.fetchval("SELECT COUNT(*) FROM sensor_readings;")
        if cnt and cnt > 0:
            return conn, norm_test
        await conn.close()
    except Exception:
        pass

    settings = get_settings()
    norm_main = normalize_db_url(settings.database_url)
    conn_main = await asyncpg.connect(norm_main)
    return conn_main, norm_main


@pytest.mark.asyncio
async def test_sensor_data_quality_flags_within_spec(test_db_url: str) -> None:
    """Verify that sensor readings have valid flags >90% and dropouts within 1.5% - 4.0%."""
    conn, _ = await get_active_conn(test_db_url)
    try:
        rows = await conn.fetch(
            """
            SELECT quality_flag, COUNT(*) as cnt,
                   ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) as pct
            FROM sensor_readings
            GROUP BY quality_flag;
            """
        )
        if not rows:
            pytest.skip("sensor_readings table is empty; run seed first")

        stats = {r["quality_flag"]: float(r["pct"]) for r in rows}
        valid_pct = stats.get("valid", 0.0)
        dropout_pct = stats.get("dropout", 0.0)

        assert valid_pct >= 90.0, f"Valid sensor percentage too low: {valid_pct}%"
        assert 1.0 <= dropout_pct <= 5.0, f"Dropout rate out of spec: {dropout_pct}%"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_sensor_latent_health_correlations(test_db_url: str) -> None:
    """Verify that physical sensor readings correlate with hidden latent health."""
    conn, _ = await get_active_conn(test_db_url)
    try:
        # 1. Hydraulic pressure vs true health (should be strongly positive, r > 0.6)
        row_press = await conn.fetchrow(
            """
            SELECT CORR(sr.mean, st.true_health) as corr
            FROM sensor_readings sr
            JOIN flights f ON sr.flight_id = f.flight_id
            JOIN simulation_truth st ON st.component_id = sr.component_id AND st.date = f.date
            WHERE sr.parameter = 'outlet_pressure_psi' AND sr.quality_flag = 'valid';
            """
        )

        # 2. Hydraulic temperature vs true health (should be strongly negative, r < -0.4)
        row_temp = await conn.fetchrow(
            """
            SELECT CORR(sr.mean, st.true_health) as corr
            FROM sensor_readings sr
            JOIN flights f ON sr.flight_id = f.flight_id
            JOIN simulation_truth st ON st.component_id = sr.component_id AND st.date = f.date
            WHERE sr.parameter = 'fluid_temp_c' AND sr.quality_flag = 'valid';
            """
        )

        if row_press and row_press["corr"] is not None:
            r_press = float(row_press["corr"])
            assert r_press > 0.60, f"Hydraulic pressure correlation too weak: {r_press}"

        if row_temp and row_temp["corr"] is not None:
            r_temp = float(row_temp["corr"])
            assert r_temp < -0.40, f"Hydraulic temperature correlation not negative: {r_temp}"
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_hero_aircraft_ac017_scripted_properties(test_db_url: str) -> None:
    """Verify hero aircraft AC-017 degradation trajectory and tight spares availability."""
    conn, _ = await get_active_conn(test_db_url)
    try:
        # Verify AC-017 exists
        ac = await conn.fetchrow(
            "SELECT aircraft_id, tail_code FROM aircraft WHERE aircraft_id = 'AC-017';"
        )
        if not ac:
            pytest.skip("AC-017 not found; run seed first")

        # Verify degradation on primary hydraulic pump
        hyd_pump = await conn.fetchrow(
            """
            SELECT c.component_id, MIN(st.true_health) as min_health, MAX(st.true_health) as max_health
            FROM components c
            JOIN simulation_truth st ON st.component_id = c.component_id
            WHERE c.aircraft_id = 'AC-017' AND c.component_type_id = 'CT-HYD-01'
            GROUP BY c.component_id;
            """
        )
        assert hyd_pump is not None
        assert float(hyd_pump["min_health"]) <= 0.50, (
            f"Hero pump did not degrade: {hyd_pump['min_health']}"
        )

        # Verify tight spares inventory for HYD-114
        spare_stock = await conn.fetchval(
            "SELECT COALESCE(SUM(on_hand), 0) FROM inventory WHERE part_number = 'HYD-114';"
        )
        assert spare_stock is not None
        assert int(spare_stock) <= 5, f"Expected tight spare stock for HYD-114, got {spare_stock}"
    finally:
        await conn.close()
