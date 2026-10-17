"""Configuration dataclass and loader for data generation."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FleetConfig:
    size: int = 40
    tail_prefix: str = "AC-"
    type_code: str = "Generic-Twin-Engine-Transport"
    commissioned_start: date = date(2020, 1, 15)
    bases: list[str] = field(
        default_factory=lambda: ["BASE-NORTH", "BASE-SOUTH", "BASE-EAST", "BASE-WEST"]
    )


@dataclass
class TimelineConfig:
    start_date: date = date(2023, 1, 1)
    end_date: date = date(2025, 12, 31)
    live_demo_window_days: int = 60


@dataclass
class OperationsConfig:
    min_flights_per_day: float = 0.8
    max_flights_per_day: float = 1.4
    duration_min_hours: float = 1.0
    duration_max_hours: float = 2.5
    cycles_min: int = 1
    cycles_max: int = 2
    load_factor_min: float = 0.85
    load_factor_max: float = 1.25
    ambient_temp_mean_c: float = 20.0
    ambient_temp_seasonal_amp_c: float = 15.0


@dataclass
class DegradationConfig:
    gamma_shape: float = 2.0
    gamma_scale: float = 0.00006
    stress_weight: float = 0.35
    sudden_failure_prob: float = 0.15
    failure_threshold: float = 0.05
    warning_threshold: float = 0.30


@dataclass
class NoiseConfig:
    dropout_rate: float = 0.025
    stuck_rate: float = 0.010
    drift_rate: float = 0.010
    spike_rate: float = 0.005


@dataclass
class InventoryConfig:
    locations: list[str] = field(default_factory=lambda: ["BASE-MAIN", "DEPOT-01"])
    safety_stock_mult: float = 1.5


@dataclass
class SimulationConfig:
    seed: int = 42
    fleet: FleetConfig = field(default_factory=FleetConfig)
    timeline: TimelineConfig = field(default_factory=TimelineConfig)
    operations: OperationsConfig = field(default_factory=OperationsConfig)
    degradation: DegradationConfig = field(default_factory=DegradationConfig)
    noise: NoiseConfig = field(default_factory=NoiseConfig)
    inventory: InventoryConfig = field(default_factory=InventoryConfig)

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "SimulationConfig":
        """Load configuration from a YAML file or return defaults."""
        if config_path is None:
            default_path = Path(__file__).resolve().parent / "config.yaml"
            if default_path.is_file():
                config_path = default_path
            else:
                return cls()

        path = Path(config_path)
        if not path.is_file():
            return cls()

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        seed = data.get("seed", 42)

        fleet_data = data.get("fleet", {})
        comm_date = fleet_data.get("commissioned_start", "2020-01-15")
        if isinstance(comm_date, str):
            comm_date = date.fromisoformat(comm_date)

        fleet_cfg = FleetConfig(
            size=fleet_data.get("size", 40),
            tail_prefix=fleet_data.get("tail_prefix", "AC-"),
            type_code=fleet_data.get("type_code", "Generic-Twin-Engine-Transport"),
            commissioned_start=comm_date,
            bases=fleet_data.get("bases", ["BASE-NORTH", "BASE-SOUTH", "BASE-EAST", "BASE-WEST"]),
        )

        time_data = data.get("timeline", {})
        start_date = time_data.get("start_date", "2023-01-01")
        if isinstance(start_date, str):
            start_date = date.fromisoformat(start_date)
        end_date = time_data.get("end_date", "2025-12-31")
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)

        timeline_cfg = TimelineConfig(
            start_date=start_date,
            end_date=end_date,
            live_demo_window_days=time_data.get("live_demo_window_days", 60),
        )

        ops_data = data.get("operations", {})
        ops_cfg = OperationsConfig(
            min_flights_per_day=ops_data.get("min_flights_per_day", 0.8),
            max_flights_per_day=ops_data.get("max_flights_per_day", 1.4),
            duration_min_hours=ops_data.get("duration_min_hours", 1.0),
            duration_max_hours=ops_data.get("duration_max_hours", 2.5),
            cycles_min=ops_data.get("cycles_min", 1),
            cycles_max=ops_data.get("cycles_max", 2),
            load_factor_min=ops_data.get("load_factor_min", 0.85),
            load_factor_max=ops_data.get("load_factor_max", 1.25),
            ambient_temp_mean_c=ops_data.get("ambient_temp_mean_c", 20.0),
            ambient_temp_seasonal_amp_c=ops_data.get("ambient_temp_seasonal_amp_c", 15.0),
        )

        deg_data = data.get("degradation", {})
        deg_cfg = DegradationConfig(
            gamma_shape=deg_data.get("gamma_shape", 2.0),
            gamma_scale=deg_data.get("gamma_scale", 0.00006),
            stress_weight=deg_data.get("stress_weight", 0.35),
            sudden_failure_prob=deg_data.get("sudden_failure_prob", 0.15),
            failure_threshold=deg_data.get("failure_threshold", 0.05),
            warning_threshold=deg_data.get("warning_threshold", 0.30),
        )

        noise_data = data.get("noise", {})
        noise_cfg = NoiseConfig(
            dropout_rate=noise_data.get("dropout_rate", 0.025),
            stuck_rate=noise_data.get("stuck_rate", 0.010),
            drift_rate=noise_data.get("drift_rate", 0.010),
            spike_rate=noise_data.get("spike_rate", 0.005),
        )

        inv_data = data.get("inventory", {})
        inv_cfg = InventoryConfig(
            locations=inv_data.get("locations", ["BASE-MAIN", "DEPOT-01"]),
            safety_stock_mult=inv_data.get("safety_stock_mult", 1.5),
        )

        return cls(
            seed=seed,
            fleet=fleet_cfg,
            timeline=timeline_cfg,
            operations=ops_cfg,
            degradation=deg_cfg,
            noise=noise_cfg,
            inventory=inv_cfg,
        )
