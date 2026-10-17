from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class User(Base):
    """Platform application user with role-based access control."""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('commander', 'planner', 'technician')",
            name="ck_users_role_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # 'commander', 'planner', 'technician'

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


class SimulationTruth(Base):
    """GROUND TRUTH TABLE FOR EVALUATION ONLY.

    CRITICAL RULE (AGENTS.md & plan.md):
    This table stores latent synthetic ground-truth health states.
    It MUST NEVER be used as a feature or target for ML model training.
    Strictly reserved for model evaluation, verification, and demo scripting.
    """

    __tablename__ = "simulation_truth"
    __table_args__ = (
        Index("ix_simulation_truth_component_date", "component_id", "date"),
        CheckConstraint(
            "true_health >= 0.0 AND true_health <= 1.0",
            name="ck_simulation_truth_health_range",
        ),
        {"comment": "GROUND TRUTH FOR EVALUATION ONLY - DO NOT USE FOR MODEL TRAINING"},
    )

    truth_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    true_health: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 (failed) to 1.0 (perfect)
    degradation_phase: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # linear, exponential, sudden
    is_failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<SimulationTruth(comp={self.component_id}, date={self.date}, health={self.true_health:.2f})>"


class AnomalyScore(Base):
    """Unsupervised anomaly detection outputs per component flight."""

    __tablename__ = "anomaly_scores"
    __table_args__ = (
        Index("ix_anomaly_scores_component_flight", "component_id", "flight_id"),
    )

    score_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    flight_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("flights.flight_id", ondelete="CASCADE"), nullable=False
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)  # Normalized anomaly score
    top_parameters: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<AnomalyScore(comp={self.component_id}, flight={self.flight_id}, score={self.score:.3f})>"


class Prediction(Base):
    """Model inference outputs: failure risk and remaining useful life quantiles."""

    __tablename__ = "predictions"
    __table_args__ = (
        UniqueConstraint(
            "component_id", "as_of_date", "model_version",
            name="uq_predictions_component_date_version"
        ),
        Index("ix_predictions_component_as_of_date", "component_id", "as_of_date"),
        CheckConstraint(
            "risk_14d >= 0.0 AND risk_14d <= 1.0",
            name="ck_predictions_risk_14d_range",
        ),
        CheckConstraint(
            "risk_30d >= 0.0 AND risk_30d <= 1.0",
            name="ck_predictions_risk_30d_range",
        ),
        CheckConstraint(
            "rul_p10 <= rul_p50 AND rul_p50 <= rul_p90",
            name="ck_predictions_rul_quantiles_monotonic",
        ),
    )

    prediction_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    risk_14d: Mapped[float] = mapped_column(Float, nullable=False)  # Calibrated probability [0, 1]
    risk_30d: Mapped[float] = mapped_column(Float, nullable=False)  # Calibrated probability [0, 1]
    rul_p10: Mapped[float] = mapped_column(Float, nullable=False)   # 10th percentile remaining days
    rul_p50: Mapped[float] = mapped_column(Float, nullable=False)   # Median remaining days
    rul_p90: Mapped[float] = mapped_column(Float, nullable=False)   # 90th percentile remaining days
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction(comp={self.component_id}, date={self.as_of_date}, "
            f"risk_14d={self.risk_14d:.2f}, rul_p50={self.rul_p50:.1f})>"
        )


class Advisory(Base):
    """Decision-support maintenance advisory generated from predictions, rules, and spares."""

    __tablename__ = "advisories"
    __table_args__ = (
        Index("ix_advisories_component_as_of_date", "component_id", "as_of_date"),
        Index("ix_advisories_status_priority", "status", "priority"),
        Index("ix_advisories_as_of_date", "as_of_date"),
        CheckConstraint(
            "priority IN ('P1', 'P2', 'P3', 'P4')",
            name="ck_advisories_priority_valid",
        ),
        CheckConstraint(
            "status IN ('proposed', 'accepted', 'scheduled', 'completed', 'dismissed')",
            name="ck_advisories_status_valid",
        ),
    )

    advisory_id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'ADV-0001'
    component_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=False
    )
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)  # P1 - P4
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="proposed", nullable=False)
    dismiss_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    explanation: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    spare_status: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    expected_downtime_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<Advisory(id={self.advisory_id}, comp={self.component_id}, prio={self.priority}, status={self.status})>"


class TwinSnapshot(Base):
    """Hierarchical health state snapshot for fleet digital twin replay."""

    __tablename__ = "twin_snapshots"
    __table_args__ = (
        Index("ix_twin_snapshots_node_id_as_of_date", "node_id", "as_of_date"),
        CheckConstraint(
            "node_type IN ('fleet', 'aircraft', 'system', 'component')",
            name="ck_twin_snapshots_node_type_valid",
        ),
        CheckConstraint(
            "health_index >= 0.0 AND health_index <= 100.0",
            name="ck_twin_snapshots_health_index_range",
        ),
        CheckConstraint(
            "state IN ('Healthy', 'Watch', 'Degraded', 'Critical', 'Failed', 'Under maintenance')",
            name="ck_twin_snapshots_state_valid",
        ),
    )

    snapshot_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)  # fleet, aircraft, system, component
    node_id: Mapped[str] = mapped_column(String(50), nullable=False)  # ID of the node
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    health_index: Mapped[float] = mapped_column(Float, nullable=False)  # 0 to 100
    state: Mapped[str] = mapped_column(String(50), nullable=False)  # Healthy, Watch, Degraded, Critical, etc.
    risk: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rul_p50: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<TwinSnapshot(node={self.node_id}, date={self.as_of_date}, hi={self.health_index:.1f}, state={self.state})>"


class Alert(Base):
    """Platform alerts for high risk, spares shortfall, or overdue maintenance."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_severity_acknowledged", "severity", "acknowledged"),
        CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_alerts_severity_valid",
        ),
    )

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # risk_threshold, spare_shortfall, overdue, backlog
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # low, medium, high, critical
    aircraft_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("aircraft.aircraft_id", ondelete="CASCADE"), nullable=True
    )
    component_id: Mapped[Optional[str]] = mapped_column(
        String(50), ForeignKey("components.component_id", ondelete="CASCADE"), nullable=True
    )
    advisory_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Alert(id={self.alert_id}, type={self.type}, sev={self.severity}, ack={self.acknowledged})>"


class ScenarioRun(Base):
    """What-if Monte Carlo availability scenario simulation run."""

    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)  # e.g., 'sc_0042'
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'spare_unavailable'
    params: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    results: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, default=42, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ScenarioRun(id={self.id}, type={self.type}, seed={self.seed})>"


class ModelRun(Base):
    """Audit log of offline ML training runs and metadata."""

    __tablename__ = "model_runs"

    run_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ModelRun(id={self.run_id}, model={self.model_name}, version={self.version})>"
