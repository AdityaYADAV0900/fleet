"""Operating condition normalisation for sensor readings.

Removes nominal variation caused by operating context (ambient temperature,
altitude band, flight duration, load factor) by fitting a regression model
per parameter and returning condition-adjusted residuals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


class OperatingConditionNormalizer:
    """Fits condition-response models per sensor parameter to compute residuals."""

    def __init__(self, alpha: float = 1.0) -> None:
        self.alpha = alpha
        self.models: dict[str, Ridge] = {}
        self.medians: dict[str, float] = {}
        self.altitude_map = {"Low": 1.0, "Medium": 2.0, "High": 3.0}

    def _prepare_condition_matrix(self, flights_df: pd.DataFrame) -> np.ndarray:
        """Extract and clean numeric condition features."""
        duration = flights_df["duration_hours"].fillna(2.0).to_numpy()
        temp = flights_df["ambient_temp_c"].fillna(15.0).to_numpy()
        altitude = flights_df["altitude_band"].map(self.altitude_map).fillna(2.0).to_numpy()
        load = flights_df["load_factor"].fillna(1.0).to_numpy()

        return np.column_stack([duration, temp, altitude, load])

    def fit(self, merged_readings_flights: pd.DataFrame) -> OperatingConditionNormalizer:
        """Fit condition regressors on healthy / baseline flight readings.

        Expects columns: parameter, mean, duration_hours, ambient_temp_c, altitude_band, load_factor.
        """
        for param, group in merged_readings_flights.groupby("parameter"):
            if len(group) < 10:
                continue

            X = self._prepare_condition_matrix(group)
            y = group["mean"].to_numpy()

            model = Ridge(alpha=self.alpha)
            model.fit(X, y)

            self.models[str(param)] = model
            self.medians[str(param)] = float(np.median(y))

        return self

    def transform(self, merged_readings_flights: pd.DataFrame) -> pd.Series:
        """Compute condition-adjusted residual: residual = observed_mean - predicted_condition_mean."""
        residuals = np.zeros(len(merged_readings_flights), dtype=np.float64)

        for param, group in merged_readings_flights.groupby("parameter"):
            param_str = str(param)
            idx = group.index

            if param_str in self.models:
                X = self._prepare_condition_matrix(group)
                y_pred = self.models[param_str].predict(X)
                residuals[merged_readings_flights.index.get_indexer(idx)] = (
                    group["mean"].to_numpy() - y_pred
                )
            else:
                median = self.medians.get(param_str, 0.0)
                residuals[merged_readings_flights.index.get_indexer(idx)] = (
                    group["mean"].to_numpy() - median
                )

        return pd.Series(residuals, index=merged_readings_flights.index, name="residual")
