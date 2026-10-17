"""Flight sortie generator modeling aircraft missions and operating conditions."""

import math
import random
from datetime import date

from data_gen.config import OperationsConfig


class FlightGenerator:
    """Generates daily flight sorties for available aircraft."""

    def __init__(self, config: OperationsConfig, rng: random.Random):
        self.config = config
        self.rng = rng
        self.flight_counter = 1

    def compute_ambient_temp(self, current_date: date) -> float:
        """Compute seasonal ambient temperature in Celsius with daily variance."""
        day_of_year = current_date.timetuple().tm_yday
        # Sinusoidal seasonal wave: peaks in July (~day 190-200), lowest in January (~day 15-20)
        phase = 2 * math.pi * (day_of_year - 105) / 365.25
        seasonal = (
            self.config.ambient_temp_mean_c
            + self.config.ambient_temp_seasonal_amp_c * math.sin(phase)
        )
        daily_noise = self.rng.gauss(0, 3.5)
        return round(seasonal + daily_noise, 1)

    def generate_flights_for_day(
        self,
        current_date: date,
        available_aircraft_ids: list[str],
    ) -> list[dict]:
        """Generate flight sorties for aircraft available to fly on this date."""
        flights = []
        ambient_temp = self.compute_ambient_temp(current_date)

        for ac_id in available_aircraft_ids:
            # Determine how many flights today (0, 1, or 2)
            prob_fly = self.rng.uniform(
                self.config.min_flights_per_day, self.config.max_flights_per_day
            )
            num_flights = int(prob_fly) + (
                1 if self.rng.random() < (prob_fly - int(prob_fly)) else 0
            )

            for _ in range(num_flights):
                flight_id = f"FL-{self.flight_counter:06d}"
                self.flight_counter += 1

                duration = round(
                    self.rng.uniform(
                        self.config.duration_min_hours,
                        self.config.duration_max_hours,
                    ),
                    2,
                )
                cycles = self.rng.randint(self.config.cycles_min, self.config.cycles_max)
                load_factor = round(
                    self.rng.uniform(
                        self.config.load_factor_min,
                        self.config.load_factor_max,
                    ),
                    2,
                )

                # Altitude band distribution
                alt_choice = self.rng.random()
                if alt_choice < 0.25:
                    alt_band = "LOW"
                elif alt_choice < 0.75:
                    alt_band = "MEDIUM"
                else:
                    alt_band = "HIGH"

                flights.append(
                    {
                        "flight_id": flight_id,
                        "aircraft_id": ac_id,
                        "date": current_date,
                        "duration_hours": duration,
                        "cycles": cycles,
                        "ambient_temp_c": ambient_temp,
                        "altitude_band": alt_band,
                        "load_factor": load_factor,
                    }
                )

        return flights
