"""Noise injection module for sensor readings."""

import random

from data_gen.config import NoiseConfig


class NoiseInjector:
    """Injects realistic sensor anomalies: dropouts, stuck values, drift, and outlier spikes."""

    def __init__(self, config: NoiseConfig, rng: random.Random):
        self.config = config
        self.rng = rng
        self.last_stuck_values: dict[str, float] = {}
        # Components flagged for non-failing sensor drift (false positive generator)
        self.drift_components: set[str] = set()

    def register_drift_component(self, component_id: str) -> None:
        """Register a component whose sensors will experience false drift."""
        self.drift_components.add(component_id)

    def apply_noise(
        self,
        component_id: str,
        parameter: str,
        clean_mean: float,
        clean_std: float,
        flight_idx: int,
    ) -> tuple[float, float, float, float, str]:
        """Apply noise profile and return (mean, max, min, std, quality_flag)."""
        key = f"{component_id}:{parameter}"
        roll = self.rng.random()

        # 1. Dropout (2.5%)
        if roll < self.config.dropout_rate:
            # Zero-out reading
            return 0.0, 0.0, 0.0, 0.0, "dropout"

        # 2. Outlier Spike (0.5%)
        elif roll < (self.config.dropout_rate + self.config.spike_rate):
            spike_mult = self.rng.choice([2.5, 3.8, -2.2])
            spike_val = clean_mean + spike_mult * max(clean_std, 1.0) * 8.0
            return (
                round(clean_mean + 0.3 * (spike_val - clean_mean), 2),
                round(max(clean_mean + 2 * clean_std, spike_val), 2),
                round(clean_mean - 2 * clean_std, 2),
                round(clean_std * 3.5, 2),
                "spike",
            )

        # 3. Stuck Value (1.0%)
        elif roll < (self.config.dropout_rate + self.config.spike_rate + self.config.stuck_rate):
            if key in self.last_stuck_values:
                stuck_val = self.last_stuck_values[key]
            else:
                stuck_val = clean_mean
                self.last_stuck_values[key] = stuck_val
            return round(stuck_val, 2), round(stuck_val, 2), round(stuck_val, 2), 0.0, "stuck"

        # 4. Sensor Drift (1.0% random or designated drift component)
        elif component_id in self.drift_components or roll < (
            self.config.dropout_rate
            + self.config.spike_rate
            + self.config.stuck_rate
            + self.config.drift_rate
        ):
            drift_offset = 0.05 * min(50, flight_idx % 100) * clean_mean * 0.08
            drift_mean = clean_mean + drift_offset
            half_range = max(clean_std * 2.2, 0.05 * abs(drift_mean))
            return (
                round(drift_mean, 2),
                round(drift_mean + half_range, 2),
                round(drift_mean - half_range, 2),
                round(clean_std * 1.2, 2),
                "drift",
            )

        # 5. Normal Valid Reading
        else:
            self.last_stuck_values[key] = clean_mean
            half_range = max(clean_std * 2.0, 0.04 * abs(clean_mean))
            return (
                round(clean_mean, 2),
                round(clean_mean + half_range + self.rng.uniform(0, clean_std), 2),
                round(clean_mean - half_range - self.rng.uniform(0, clean_std), 2),
                round(clean_std, 2),
                "valid",
            )
