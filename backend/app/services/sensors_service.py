"""Sensors, telemetry trends, fault events, and batch ingestion service."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.models.fleet import Component
from app.models.platform import AnomalyScore
from app.models.sensors import FaultEvent, Flight, SensorReading
from app.schemas.sensors import (
    AnomalyScoreOut,
    FaultEventOut,
    IngestResultOut,
    IngestRowError,
    SensorReadingItemIn,
    SensorReadingOut,
)


async def get_component_sensor_readings(
    session: AsyncSession,
    component_id: str,
    parameter: str | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 500,
) -> list[SensorReadingOut]:
    """Retrieve historical sensor trend readings for a component joined with flight date."""
    # Verify component exists
    comp_exists = await session.execute(
        select(Component.component_id).where(Component.component_id == component_id)
    )
    if not comp_exists.scalar_one_or_none():
        raise NotFoundError(f"Component '{component_id}' not found")

    query = (
        select(SensorReading, Flight.date)
        .join(Flight, SensorReading.flight_id == Flight.flight_id)
        .where(SensorReading.component_id == component_id)
    )

    if parameter:
        query = query.where(SensorReading.parameter == parameter)
    if from_date:
        query = query.where(Flight.date >= from_date)
    if to_date:
        query = query.where(Flight.date <= to_date)

    query = query.order_by(Flight.date.asc(), SensorReading.reading_id.asc()).limit(limit)
    result = await session.execute(query)

    items = []
    for sr, fl_date in result.all():
        out = SensorReadingOut(
            reading_id=sr.reading_id,
            flight_id=sr.flight_id,
            component_id=sr.component_id,
            parameter=sr.parameter,
            mean=sr.mean,
            max=sr.max,
            min=sr.min,
            std=sr.std,
            quality_flag=sr.quality_flag,
            date=fl_date,
        )
        items.append(out)

    return items


async def ingest_sensor_readings(
    session: AsyncSession,
    items: list[SensorReadingItemIn],
) -> IngestResultOut:
    """Validate and ingest a batch of post-flight sensor readings with per-row error reporting."""
    errors: list[IngestRowError] = []
    valid_records: list[SensorReading] = []

    # Pre-fetch foreign key candidates in batch to avoid N+1 queries
    flight_ids_in_batch = {item.flight_id for item in items}
    comp_ids_in_batch = {item.component_id for item in items}

    flights_res = await session.execute(
        select(Flight.flight_id).where(Flight.flight_id.in_(flight_ids_in_batch))
    )
    existing_flight_ids = set(flights_res.scalars().all())

    comps_res = await session.execute(
        select(Component.component_id).where(Component.component_id.in_(comp_ids_in_batch))
    )
    existing_comp_ids = set(comps_res.scalars().all())

    # Per-row validation
    for idx, item in enumerate(items):
        item_dict = item.model_dump()

        if item.flight_id not in existing_flight_ids:
            errors.append(
                IngestRowError(
                    row_index=idx,
                    field="flight_id",
                    message=f"Flight '{item.flight_id}' does not exist in operations database",
                    data=item_dict,
                )
            )
            continue

        if item.component_id not in existing_comp_ids:
            errors.append(
                IngestRowError(
                    row_index=idx,
                    field="component_id",
                    message=f"Component '{item.component_id}' does not exist in fleet catalog",
                    data=item_dict,
                )
            )
            continue

        if item.min > item.max:
            errors.append(
                IngestRowError(
                    row_index=idx,
                    field="min",
                    message=f"Minimum reading ({item.min}) exceeds maximum reading ({item.max})",
                    data=item_dict,
                )
            )
            continue

        valid_records.append(
            SensorReading(
                flight_id=item.flight_id,
                component_id=item.component_id,
                parameter=item.parameter,
                mean=item.mean,
                max=item.max,
                min=item.min,
                std=item.std,
                quality_flag=item.quality_flag,
            )
        )

    # Insert valid records
    if valid_records:
        session.add_all(valid_records)
        await session.commit()

    return IngestResultOut(
        total_submitted=len(items),
        accepted_count=len(valid_records),
        rejected_count=len(errors),
        errors=errors,
    )


async def list_fault_events(
    session: AsyncSession,
    aircraft_id: str | None = None,
    component_id: str | None = None,
    severity: str | None = None,
    limit: int = 100,
) -> list[FaultEventOut]:
    """Retrieve fault events with optional filters."""
    stmt = select(FaultEvent)
    if aircraft_id:
        stmt = stmt.where(FaultEvent.aircraft_id == aircraft_id)
    if component_id:
        stmt = stmt.where(FaultEvent.component_id == component_id)
    if severity:
        stmt = stmt.where(FaultEvent.severity == severity)

    stmt = stmt.order_by(FaultEvent.timestamp.desc()).limit(limit)
    res = await session.execute(stmt)
    return [FaultEventOut.model_validate(fe) for fe in res.scalars().all()]


async def get_component_anomalies(
    session: AsyncSession,
    component_id: str,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: int = 200,
) -> list[AnomalyScoreOut]:
    """Retrieve anomaly scores and detection flags for a component joined with flight date."""
    query = (
        select(AnomalyScore, Flight.date)
        .join(Flight, AnomalyScore.flight_id == Flight.flight_id)
        .where(AnomalyScore.component_id == component_id)
    )
    if from_date:
        query = query.where(Flight.date >= from_date)
    if to_date:
        query = query.where(Flight.date <= to_date)
    query = query.order_by(Flight.date.asc(), AnomalyScore.score_id.asc()).limit(limit)
    res = await session.execute(query)

    items = []
    for anom, fl_date in res.all():
        items.append(
            AnomalyScoreOut(
                score_id=anom.score_id,
                component_id=anom.component_id,
                flight_id=anom.flight_id,
                date=fl_date,
                score=anom.score,
                is_anomaly=anom.score >= 0.70,
                top_parameters=anom.top_parameters,
            )
        )
    return items
