"""Data loading module for offline ML pipeline.

Loads operational tables (flights, sensor_readings, fault_events, maintenance_events,
components, component_types) from PostgreSQL.

CRITICAL RULE (AGENTS.md):
Never load or use the `simulation_truth` table for model training or feature engineering.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import asyncpg
import pandas as pd

_BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import get_settings  # noqa: E402

logger = logging.getLogger(__name__)


@dataclass
class RawFleetData:
    """Container holding raw operational DataFrames extracted from the database."""

    flights: pd.DataFrame
    sensor_readings: pd.DataFrame
    fault_events: pd.DataFrame
    maintenance_events: pd.DataFrame
    components: pd.DataFrame
    component_types: pd.DataFrame


async def _fetch_query(conn: asyncpg.Connection, query: str, args: tuple = ()) -> pd.DataFrame:
    """Helper to execute an asyncpg query and return a pandas DataFrame."""
    rows = await conn.fetch(query, *args)
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows, columns=list(rows[0].keys()))


async def load_raw_data_async(as_of_date: date | None = None) -> RawFleetData:
    """Query operational database tables up to an optional cut-off date.

    Notice: simulation_truth is NEVER queried or joined.
    """
    settings = get_settings()
    dsn = settings.database_url.replace("+asyncpg", "").replace("+psycopg", "")
    conn = await asyncpg.connect(dsn)

    try:
        # 1. Flights
        if as_of_date:
            flights_df = await _fetch_query(
                conn,
                """
                SELECT flight_id, aircraft_id, date, duration_hours, cycles,
                       ambient_temp_c, altitude_band, load_factor
                FROM flights
                WHERE date <= $1
                ORDER BY date, flight_id
                """,
                (as_of_date,),
            )
        else:
            flights_df = await _fetch_query(
                conn,
                """
                SELECT flight_id, aircraft_id, date, duration_hours, cycles,
                       ambient_temp_c, altitude_band, load_factor
                FROM flights
                ORDER BY date, flight_id
                """,
            )

        # 2. Components & Types
        components_df = await _fetch_query(
            conn,
            """
            SELECT component_id, aircraft_id, component_type_id, installed_date
            FROM components
            """,
        )

        component_types_df = await _fetch_query(
            conn,
            """
            SELECT component_type_id, system_id, name, criticality, design_life_hours, mtbf_hours
            FROM component_types
            """,
        )

        # 3. Sensor readings (only valid quality flags)
        if as_of_date:
            readings_df = await _fetch_query(
                conn,
                """
                SELECT r.flight_id, r.component_id, r.parameter,
                       r.mean, r.max, r.min, r.std
                FROM sensor_readings r
                JOIN flights f ON r.flight_id = f.flight_id
                WHERE r.quality_flag = 'valid' AND f.date <= $1
                """,
                (as_of_date,),
            )
        else:
            readings_df = await _fetch_query(
                conn,
                """
                SELECT flight_id, component_id, parameter, mean, max, min, std
                FROM sensor_readings
                WHERE quality_flag = 'valid'
                """,
            )

        # 4. Fault events
        if as_of_date:
            faults_df = await _fetch_query(
                conn,
                """
                SELECT event_id, aircraft_id, component_id, timestamp, severity, fault_code
                FROM fault_events
                WHERE timestamp <= $1
                ORDER BY timestamp
                """,
                (pd.Timestamp(as_of_date).tz_localize("UTC") + pd.Timedelta(days=1),),
            )
        else:
            faults_df = await _fetch_query(
                conn,
                """
                SELECT event_id, aircraft_id, component_id, timestamp, severity, fault_code
                FROM fault_events
                ORDER BY timestamp
                """,
            )

        # 5. Maintenance events
        if as_of_date:
            maint_df = await _fetch_query(
                conn,
                """
                SELECT event_id, aircraft_id, component_id, type, action, start, "end", labor_hours
                FROM maintenance_events
                WHERE start <= $1
                ORDER BY start
                """,
                (pd.Timestamp(as_of_date).tz_localize("UTC") + pd.Timedelta(days=1),),
            )
        else:
            maint_df = await _fetch_query(
                conn,
                """
                SELECT event_id, aircraft_id, component_id, type, action, start, "end", labor_hours
                FROM maintenance_events
                ORDER BY start
                """,
            )

    finally:
        await conn.close()

    # Convert date / datetime types
    if not flights_df.empty:
        flights_df["date"] = pd.to_datetime(flights_df["date"]).dt.date
    if not faults_df.empty:
        faults_df["timestamp"] = pd.to_datetime(faults_df["timestamp"])
        faults_df["date"] = faults_df["timestamp"].dt.date
    if not maint_df.empty:
        maint_df["start"] = pd.to_datetime(maint_df["start"])
        maint_df["date"] = maint_df["start"].dt.date
        if "end" in maint_df.columns:
            maint_df["end"] = pd.to_datetime(maint_df["end"])

    return RawFleetData(
        flights=flights_df,
        sensor_readings=readings_df,
        fault_events=faults_df,
        maintenance_events=maint_df,
        components=components_df,
        component_types=component_types_df,
    )


def load_raw_data(as_of_date: date | None = None) -> RawFleetData:
    """Synchronous entrypoint for loading raw data."""
    import asyncio

    return asyncio.run(load_raw_data_async(as_of_date))
