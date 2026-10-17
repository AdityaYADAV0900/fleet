"""Aircraft daily availability status derivation module."""

from datetime import UTC, date, datetime


class StatusTracker:
    """Tracks and builds daily status records for all aircraft across the simulation timeline."""

    def __init__(self):
        self.daily_status_records: list[dict] = []

    def record_day(
        self,
        aircraft_id: str,
        current_date: date,
        status: str,
        reason: str | None = None,
    ) -> None:
        """Record status for an aircraft on a given calendar day."""
        rec_time = datetime(
            current_date.year, current_date.month, current_date.day, 23, 59, tzinfo=UTC
        )
        self.daily_status_records.append(
            {
                "aircraft_id": aircraft_id,
                "date": current_date,
                "status": status,
                "reason": reason,
                "recorded_at": rec_time,
            }
        )
