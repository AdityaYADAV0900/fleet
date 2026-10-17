"""Sensors, flights, fault events, and ingestion schemas."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class FlightOut(BaseModel):
    flight_id: str
    aircraft_id: str
    date: dt_date
    duration_hours: float
    cycles: int
    ambient_temp_c: float | None = None
    altitude_band: str | None = None
    load_factor: float | None = None

    class Config:
        from_attributes = True


class SensorReadingOut(BaseModel):
    reading_id: int
    flight_id: str
    component_id: str
    parameter: str
    mean: float
    max: float
    min: float
    std: float
    quality_flag: str
    date: dt_date | None = None

    class Config:
        from_attributes = True


class SensorReadingItemIn(BaseModel):
    flight_id: str = Field(..., min_length=1, description="Associated flight sortie ID")
    component_id: str = Field(..., min_length=1, description="Monitored component instance ID")
    parameter: str = Field(..., min_length=1, description="Telemetry parameter name")
    mean: float = Field(..., description="Post-flight mean value")
    max: float = Field(..., description="Post-flight maximum value")
    min: float = Field(..., description="Post-flight minimum value")
    std: float = Field(..., ge=0.0, description="Post-flight standard deviation")
    quality_flag: Literal["valid", "dropout", "stuck", "drift", "spike", "missing"] = Field(
        default="valid", description="Data quality classification"
    )


class IngestSensorReadingsRequest(BaseModel):
    readings: list[SensorReadingItemIn] = Field(
        ..., min_length=1, description="Batch list of sensor summary readings to ingest"
    )


class IngestRowError(BaseModel):
    row_index: int
    field: str
    message: str
    data: dict | None = None


class IngestResultOut(BaseModel):
    total_submitted: int
    accepted_count: int
    rejected_count: int
    errors: list[IngestRowError]


class FaultEventOut(BaseModel):
    event_id: str
    aircraft_id: str
    component_id: str
    timestamp: datetime
    fault_code: str
    severity: str
    description: str
    source: str

    class Config:
        from_attributes = True


class AnomalyScoreOut(BaseModel):
    score_id: int
    component_id: str
    flight_id: str
    date: dt_date | None = None
    score: float
    is_anomaly: bool = False
    top_parameters: dict[str, Any] | None = None

    class Config:
        from_attributes = True
