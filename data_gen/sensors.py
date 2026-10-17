"""Physics-based sensor reading generation combining operating baseline, degradation signature, and noise."""

import math
import random

from data_gen.hierarchy import COMPONENT_TYPE_MAP
from data_gen.noise import NoiseInjector


class SensorGenerator:
    """Generates per-flight post-flight aggregate sensor readings for monitored components."""

    def __init__(self, noise_injector: NoiseInjector, rng: random.Random):
        self.noise_injector = noise_injector
        self.rng = rng

    def generate_readings_for_flight(
        self,
        flight: dict,
        component_health_pairs: list[tuple[str, str, float]],
    ) -> list[dict]:
        """Generate sensor summary records for each component on an aircraft flight.

        Args:
            flight: Dict with flight_id, ambient_temp_c, load_factor, etc.
            component_health_pairs: List of (component_id, component_type_id, true_health)

        Returns:
            List of sensor_readings dicts
        """
        flight_id = flight["flight_id"]
        temp = flight["ambient_temp_c"] or 20.0
        load = flight["load_factor"] or 1.0
        readings = []

        for comp_id, ct_id, true_health in component_health_pairs:
            ct_def = COMPONENT_TYPE_MAP.get(ct_id)
            if not ct_def:
                continue

            health_defect = max(0.0, min(1.0, 1.0 - true_health))

            for sensor in ct_def.sensors:
                # 1. Baseline from operating conditions
                baseline = (
                    sensor.baseline
                    + sensor.temp_coef * (temp - 20.0)
                    + sensor.load_coef * (load - 1.0)
                )

                # 2. Physics-inspired degradation signature
                if sensor.direction == "increase":
                    signature = sensor.delta_at_failure * (health_defect**1.6)
                elif sensor.direction == "decrease":
                    signature = sensor.delta_at_failure * (health_defect**1.6)
                elif sensor.direction == "drift":
                    oscillation = math.sin(hash(comp_id) % 100 + health_defect * 10)
                    signature = (
                        sensor.delta_at_failure * (health_defect**1.4) * (1.0 + 0.5 * oscillation)
                    )
                else:
                    signature = sensor.delta_at_failure * (health_defect**1.5)

                # Flight measurement noise
                measurement_noise = self.rng.gauss(0, sensor.noise_sigma)
                clean_mean = baseline + signature + measurement_noise
                clean_std = max(sensor.noise_sigma, 0.05 * abs(clean_mean))

                # 3. Apply noise injection (dropout, stuck, drift, spike, valid)
                mean_val, max_val, min_val, std_val, quality = self.noise_injector.apply_noise(
                    component_id=comp_id,
                    parameter=sensor.parameter,
                    clean_mean=clean_mean,
                    clean_std=clean_std,
                    flight_idx=hash(flight_id) % 1000,
                )

                readings.append(
                    {
                        "flight_id": flight_id,
                        "component_id": comp_id,
                        "parameter": sensor.parameter,
                        "mean": mean_val,
                        "max": max_val,
                        "min": min_val,
                        "std": std_val,
                        "quality_flag": quality,
                    }
                )

        return readings
