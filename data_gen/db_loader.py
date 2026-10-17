"""High-performance PostgreSQL database loader using asyncpg streaming COPY."""

import os

import asyncpg

from data_gen.generator import FleetDataset


def normalize_db_url(url: str) -> str:
    """Ensure DB URL is in asyncpg format (postgresql://user:pass@host:port/dbname)."""
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    if "+psycopg" in url:
        url = url.replace("+psycopg", "")
    return url


async def bulk_load_to_db(dataset: FleetDataset, db_url: str | None = None) -> dict[str, int]:
    """Bulk load generated dataset into PostgreSQL database in topological FK dependency order."""
    if not db_url:
        db_url = os.getenv(
            "DATABASE_URL", "postgresql://fleetmaint:fleetmaint@localhost:5433/fleetmaint"
        )
    db_url = normalize_db_url(db_url)

    conn = await asyncpg.connect(db_url)
    counts = {}

    try:
        async with conn.transaction():
            # 1. Truncate all tables in reverse topological order
            tables_to_truncate = [
                "alerts",
                "twin_snapshots",
                "advisories",
                "predictions",
                "anomaly_scores",
                "simulation_truth",
                "aircraft_daily_status",
                "inventory_transactions",
                "maintenance_events",
                "work_orders",
                "fault_events",
                "sensor_readings",
                "flights",
                "inventory",
                "components",
                "scheduled_tasks",
                "aircraft",
                "agencies",
                "spare_parts",
                "component_types",
                "systems",
                "users",
            ]
            truncate_sql = (
                f"TRUNCATE TABLE {', '.join(tables_to_truncate)} RESTART IDENTITY CASCADE;"
            )
            await conn.execute(truncate_sql)

            # 2. Seed Systems
            cols = ["system_id", "name"]
            records = [(r["system_id"], r["name"]) for r in dataset.systems]
            await conn.copy_records_to_table("systems", records=records, columns=cols)
            counts["systems"] = len(records)

            # 3. Seed Component Types
            cols = [
                "component_type_id",
                "system_id",
                "name",
                "criticality",
                "design_life_hours",
                "mtbf_hours",
                "part_number",
                "is_repairable",
            ]
            records = [
                (
                    r["component_type_id"],
                    r["system_id"],
                    r["name"],
                    r["criticality"],
                    r["design_life_hours"],
                    r["mtbf_hours"],
                    r["part_number"],
                    r["is_repairable"],
                )
                for r in dataset.component_types
            ]
            await conn.copy_records_to_table("component_types", records=records, columns=cols)
            counts["component_types"] = len(records)

            # 4. Seed Spare Parts
            cols = [
                "part_number",
                "description",
                "criticality",
                "unit_cost",
                "lead_time_days",
                "reorder_level",
            ]
            records = [
                (
                    r["part_number"],
                    r["description"],
                    r["criticality"],
                    r["unit_cost"],
                    r["lead_time_days"],
                    r["reorder_level"],
                )
                for r in dataset.spare_parts
            ]
            await conn.copy_records_to_table("spare_parts", records=records, columns=cols)
            counts["spare_parts"] = len(records)

            # 5. Seed Agencies
            cols = [
                "agency_id",
                "name",
                "level",
                "bays",
                "capacity_hours_per_day",
                "avg_turnaround_days",
            ]
            records = [
                (
                    r["agency_id"],
                    r["name"],
                    r["level"],
                    r["bays"],
                    r["capacity_hours_per_day"],
                    r["avg_turnaround_days"],
                )
                for r in dataset.agencies
            ]
            await conn.copy_records_to_table("agencies", records=records, columns=cols)
            counts["agencies"] = len(records)

            # 6. Seed Aircraft
            cols = [
                "aircraft_id",
                "tail_code",
                "type_code",
                "commissioned_date",
                "total_flight_hours",
                "total_cycles",
                "base_id",
            ]
            records = [
                (
                    r["aircraft_id"],
                    r["tail_code"],
                    r["type_code"],
                    r["commissioned_date"],
                    r["total_flight_hours"],
                    r["total_cycles"],
                    r["base_id"],
                )
                for r in dataset.aircraft
            ]
            await conn.copy_records_to_table("aircraft", records=records, columns=cols)
            counts["aircraft"] = len(records)

            # 7. Seed Scheduled Tasks
            cols = [
                "task_id",
                "aircraft_id",
                "task_name",
                "interval_hours",
                "last_done_hours",
                "due_hours",
                "due_date",
            ]
            records = [
                (
                    r["task_id"],
                    r["aircraft_id"],
                    r["task_name"],
                    r["interval_hours"],
                    r["last_done_hours"],
                    r["due_hours"],
                    r["due_date"],
                )
                for r in dataset.scheduled_tasks
            ]
            await conn.copy_records_to_table("scheduled_tasks", records=records, columns=cols)
            counts["scheduled_tasks"] = len(records)

            # 8. Seed Components
            cols = [
                "component_id",
                "aircraft_id",
                "component_type_id",
                "serial_no",
                "installed_date",
                "hours_at_install",
                "hours_since_new",
                "status",
            ]
            records = [
                (
                    r["component_id"],
                    r["aircraft_id"],
                    r["component_type_id"],
                    r["serial_no"],
                    r["installed_date"],
                    r["hours_at_install"],
                    r["hours_since_new"],
                    r["status"],
                )
                for r in dataset.components
            ]
            await conn.copy_records_to_table("components", records=records, columns=cols)
            counts["components"] = len(records)

            # 9. Seed Inventory
            cols = [
                "part_number",
                "location_id",
                "on_hand",
                "reserved",
                "on_order",
                "expected_receipt_date",
            ]
            records = [
                (
                    r["part_number"],
                    r["location_id"],
                    r["on_hand"],
                    r["reserved"],
                    r["on_order"],
                    r["expected_receipt_date"],
                )
                for r in dataset.inventory
            ]
            await conn.copy_records_to_table("inventory", records=records, columns=cols)
            counts["inventory"] = len(records)

            # 10. Seed Flights
            cols = [
                "flight_id",
                "aircraft_id",
                "date",
                "duration_hours",
                "cycles",
                "ambient_temp_c",
                "altitude_band",
                "load_factor",
            ]
            records = [
                (
                    r["flight_id"],
                    r["aircraft_id"],
                    r["date"],
                    r["duration_hours"],
                    r["cycles"],
                    r["ambient_temp_c"],
                    r["altitude_band"],
                    r["load_factor"],
                )
                for r in dataset.flights
            ]
            await conn.copy_records_to_table("flights", records=records, columns=cols)
            counts["flights"] = len(records)

            # 11. Seed Sensor Readings
            cols = [
                "flight_id",
                "component_id",
                "parameter",
                "mean",
                "max",
                "min",
                "std",
                "quality_flag",
            ]
            records = [
                (
                    r["flight_id"],
                    r["component_id"],
                    r["parameter"],
                    r["mean"],
                    r["max"],
                    r["min"],
                    r["std"],
                    r["quality_flag"],
                )
                for r in dataset.sensor_readings
            ]
            await conn.copy_records_to_table("sensor_readings", records=records, columns=cols)
            counts["sensor_readings"] = len(records)

            # 12. Seed Fault Events
            cols = [
                "event_id",
                "aircraft_id",
                "component_id",
                "timestamp",
                "fault_code",
                "severity",
                "description",
                "source",
            ]
            records = [
                (
                    r["event_id"],
                    r["aircraft_id"],
                    r["component_id"],
                    r["timestamp"],
                    r["fault_code"],
                    r["severity"],
                    r["description"],
                    r["source"],
                )
                for r in dataset.fault_events
            ]
            await conn.copy_records_to_table("fault_events", records=records, columns=cols)
            counts["fault_events"] = len(records)

            # 13. Seed Work Orders
            cols = [
                "wo_id",
                "aircraft_id",
                "component_id",
                "advisory_id",
                "agency_id",
                "opened",
                "planned_start",
                "actual_start",
                "promised_done",
                "actual_done",
                "status",
                "priority",
                "delay_reason",
            ]
            records = [
                (
                    r["wo_id"],
                    r["aircraft_id"],
                    r["component_id"],
                    r["advisory_id"],
                    r["agency_id"],
                    r["opened"],
                    r["planned_start"],
                    r["actual_start"],
                    r["promised_done"],
                    r["actual_done"],
                    r["status"],
                    r["priority"],
                    r["delay_reason"],
                )
                for r in dataset.work_orders
            ]
            await conn.copy_records_to_table("work_orders", records=records, columns=cols)
            counts["work_orders"] = len(records)

            # 14. Seed Maintenance Events
            cols = [
                "event_id",
                "aircraft_id",
                "component_id",
                "type",
                "start",
                "end",
                "action",
                "labor_hours",
                "work_order_id",
                "root_cause",
            ]
            records = [
                (
                    r["event_id"],
                    r["aircraft_id"],
                    r["component_id"],
                    r["type"],
                    r["start"],
                    r["end"],
                    r["action"],
                    r["labor_hours"],
                    r["work_order_id"],
                    r["root_cause"],
                )
                for r in dataset.maintenance_events
            ]
            await conn.copy_records_to_table("maintenance_events", records=records, columns=cols)
            counts["maintenance_events"] = len(records)

            # 15. Seed Inventory Transactions
            cols = ["part_number", "date", "qty", "type", "work_order_id"]
            records = [
                (
                    r["part_number"],
                    r["date"],
                    r["qty"],
                    r["type"],
                    r["work_order_id"],
                )
                for r in dataset.inventory_transactions
            ]
            await conn.copy_records_to_table(
                "inventory_transactions", records=records, columns=cols
            )
            counts["inventory_transactions"] = len(records)

            # 16. Seed Aircraft Daily Status
            cols = ["aircraft_id", "date", "status", "reason", "recorded_at"]
            records = [
                (
                    r["aircraft_id"],
                    r["date"],
                    r["status"],
                    r["reason"],
                    r["recorded_at"],
                )
                for r in dataset.aircraft_daily_status
            ]
            await conn.copy_records_to_table("aircraft_daily_status", records=records, columns=cols)
            counts["aircraft_daily_status"] = len(records)

            # 17. Seed Simulation Truth
            cols = ["component_id", "date", "true_health", "degradation_phase", "is_failed"]
            records = [
                (
                    r["component_id"],
                    r["date"],
                    r["true_health"],
                    r["degradation_phase"],
                    r["is_failed"],
                )
                for r in dataset.simulation_truth
            ]
            await conn.copy_records_to_table("simulation_truth", records=records, columns=cols)
            counts["simulation_truth"] = len(records)

            # 18. Seed Default Demo Users for Application Roles
            demo_users = [
                ("commander", "pbkdf2:sha256:dev_hash_cmd", "commander"),
                ("planner", "pbkdf2:sha256:dev_hash_plan", "planner"),
                ("technician", "pbkdf2:sha256:dev_hash_tech", "technician"),
            ]
            await conn.copy_records_to_table(
                "users", records=demo_users, columns=["username", "password_hash", "role"]
            )
            counts["users"] = len(demo_users)

    finally:
        await conn.close()

    return counts
