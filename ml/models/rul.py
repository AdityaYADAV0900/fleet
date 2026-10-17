"""Remaining Useful Life (RUL) regression model with quantile outputs (P10/P50/P90).

Compares a Quantile LightGBM Regressor against a linear health-trend baseline.
Target is clipped at 60.0 days (standard C-MAPSS formulation).
"""

from __future__ import annotations

import logging
from typing import Optional

import lightgbm as lgb
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class LinearHealthTrendRULBaseline:
    """Baseline extrapolating linear degradation trend to failure limit."""

    def __init__(self, failure_sigma_threshold: float = 3.5, max_rul: float = 60.0) -> None:
        self.threshold = failure_sigma_threshold
        self.max_rul = max_rul

    def fit(self, X: pd.DataFrame, y: pd.Series) -> LinearHealthTrendRULBaseline:
        # Simple heuristic baseline: learns global scaling between deviation and RUL
        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Estimate remaining life based on current rolling anomaly severity and trend."""
        z = X["max_roll_mean_20"].to_numpy() if "max_roll_mean_20" in X.columns else X["max_abs_z"].to_numpy()
        slope = X["max_roll_slope_20"].to_numpy() if "max_roll_slope_20" in X.columns else np.zeros_like(z)

        # Baseline formula: as z approaches threshold or slope is positive, RUL shrinks
        effective_z = np.maximum(0.0, z) + np.maximum(0.0, slope * 5.0)
        rul_est = self.max_rul * (1.0 - np.clip(effective_z / self.threshold, 0.0, 1.0))
        return np.clip(rul_est, 0.0, self.max_rul)


class QuantileRULModel:
    """LightGBM quantile regression model predicting 10th, 50th, and 90th percentiles."""

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        max_rul: float = 60.0,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.max_rul = max_rul
        self.random_state = random_state

        self.models: dict[float, lgb.LGBMRegressor] = {}
        self.feature_names: list[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> QuantileRULModel:
        """Train three separate quantile regressors for alphas 0.1, 0.5, and 0.9."""
        self.feature_names = list(X_train.columns)
        y_clipped = np.clip(y_train.to_numpy(), 0.0, self.max_rul)

        quantiles = [0.1, 0.5, 0.9]
        for q in quantiles:
            reg = lgb.LGBMRegressor(
                objective="quantile",
                alpha=q,
                n_estimators=self.n_estimators,
                learning_rate=self.learning_rate,
                num_leaves=self.num_leaves,
                max_depth=self.max_depth,
                random_state=self.random_state,
                n_jobs=1,
                verbosity=-1,
            )
            reg.fit(X_train, y_clipped)
            self.models[q] = reg

        return self

    def predict_quantiles(self, X: pd.DataFrame) -> dict[str, np.ndarray]:
        """Predict P10, P50, and P90 with monotonic ordering enforced."""
        p10 = np.clip(self.models[0.1].predict(X), 0.0, self.max_rul)
        p50 = np.clip(self.models[0.5].predict(X), 0.0, self.max_rul)
        p90 = np.clip(self.models[0.9].predict(X), 0.0, self.max_rul)

        # Enforce monotonicity: p10 <= p50 <= p90
        p50 = np.maximum(p10, p50)
        p90 = np.maximum(p50, p90)

        return {
            "p10": p10,
            "p50": p50,
            "p90": p90,
        }

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Return median (P50) RUL prediction."""
        return self.predict_quantiles(X)["p50"]
