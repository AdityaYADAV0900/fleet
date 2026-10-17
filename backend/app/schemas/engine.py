"""Pydantic schemas for predictive maintenance engine, predictions, advisories, and alerts."""

from __future__ import annotations

from datetime import date as dt_date
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PredictionOut(BaseModel):
    """Prediction output schema for component failure risk and RUL."""

    prediction_id: int
    component_id: str
    aircraft_id: str | None = None
    tail_code: str | None = None
    system_name: str | None = None
    component_name: str | None = None
    as_of_date: dt_date
    risk_14d: float = Field(ge=0.0, le=1.0)
    risk_30d: float = Field(ge=0.0, le=1.0)
    rul_p10: float
    rul_p50: float
    rul_p90: float
    model_version: str
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisoryOut(BaseModel):
    """Maintenance Advisory decision-support schema."""

    advisory_id: str
    component_id: str
    aircraft_id: str | None = None
    tail_code: str | None = None
    system_name: str | None = None
    component_name: str | None = None
    as_of_date: dt_date
    priority: str  # P1, P2, P3, P4
    action: str  # e.g., "replace within 7 days"
    status: str  # proposed, accepted, scheduled, completed, dismissed
    dismiss_reason: str | None = None
    explanation: dict[str, Any] | None = None
    spare_status: str | None = None
    expected_downtime_days: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdvisoryUpdateIn(BaseModel):
    """Payload to update an advisory's status in human-in-the-loop workflow."""

    status: str = Field(
        ...,
        description="Target status: accepted, scheduled, completed, or dismissed",
    )
    reason: str | None = Field(
        None,
        description="Mandatory dismissal reason if status is 'dismissed'",
    )


class AlertOut(BaseModel):
    """Platform operational alert schema."""

    alert_id: int
    type: str  # risk_threshold, spare_shortfall, overdue, backlog
    severity: str  # low, medium, high, critical
    aircraft_id: str | None = None
    component_id: str | None = None
    advisory_id: str | None = None
    message: str
    created_at: datetime
    acknowledged: bool

    class Config:
        from_attributes = True


class AlertAckIn(BaseModel):
    """Payload to acknowledge an alert."""

    acknowledged: bool = True


class EngineRunIn(BaseModel):
    """Request payload to manually trigger the predictive maintenance scoring engine."""

    as_of_date: dt_date | None = Field(
        None,
        description="Reference cutoff date for batch scoring. Defaults to latest flight date.",
    )
    aircraft_id: str | None = Field(
        None,
        description="Optional single aircraft filter (e.g. 'AC-017') for targeted scoring.",
    )


class EngineRunSummaryOut(BaseModel):
    """Summary of batch scoring engine execution."""

    as_of_date: dt_date
    duration_seconds: float
    components_scored: int
    predictions_recorded: int
    anomaly_scores_recorded: int
    advisories_generated: int
    alerts_generated: int
    p1_count: int
    p2_count: int
    high_risk_components: int
