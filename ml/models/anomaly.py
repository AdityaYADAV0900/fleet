"""Unsupervised anomaly detection module (Condition-Residuals + Isolation Forest).

Identifies unusual component behaviour on flights without relying on labelled failures.
Outputs normalized anomaly scores [0, 1] and parameter contribution rankings.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Combines operating-condition residuals with an Isolation Forest."""

    def __init__(
        self,
        contamination: float = 0.03,
        n_estimators: int = 100,
        random_state: int = 42,
    ) -> None:
        self.contamination = contamination
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=random_state,
            n_jobs=1,  # Laptop CPU friendly
        )
        self.feature_names: list[str] = []
        self.min_score: float = 0.0
        self.max_score: float = 1.0

    def fit(self, X: pd.DataFrame) -> AnomalyDetector:
        """Fit Isolation Forest on healthy / training feature distributions."""
        self.feature_names = list(X.columns)
        self.model.fit(X.to_numpy())

        # Calibrate scoring range
        raw_scores = -self.model.score_samples(X.to_numpy())
        self.min_score = float(np.percentile(raw_scores, 1))
        self.max_score = float(np.percentile(raw_scores, 99))
        if self.max_score <= self.min_score:
            self.max_score = self.min_score + 1.0

        return self

    def predict_score(self, X: pd.DataFrame) -> np.ndarray:
        """Return continuous normalized anomaly score in [0, 1]. Higher = more anomalous."""
        raw_scores = -self.model.score_samples(X.to_numpy())
        normalized = (raw_scores - self.min_score) / (self.max_score - self.min_score)
        return np.clip(normalized, 0.0, 1.0)

    def predict_binary(self, X: pd.DataFrame, threshold: float = 0.70) -> np.ndarray:
        """Return binary flag for severe anomaly (1 = anomalous, 0 = nominal)."""
        scores = self.predict_score(X)
        return (scores >= threshold).astype(int)

    def explain_anomaly(
        self,
        row: pd.Series,
        top_n: int = 3,
    ) -> dict[str, Any]:
        """Explain an anomalous observation by highest normalized feature deviations."""
        abs_vals = {}
        for col in self.feature_names:
            if col in row:
                abs_vals[col] = float(np.abs(row[col]))

        sorted_params = sorted(abs_vals.items(), key=lambda item: item[1], reverse=True)[:top_n]
        return {
            "top_features": [
                {"feature": k, "deviation_sigma": round(v, 2)}
                for k, v in sorted_params
            ]
        }


class RollingZScoreBaseline:
    """Simple baseline model using fixed sigma threshold on rolling max z-score."""

    def __init__(self, threshold_sigma: float = 2.5) -> None:
        self.threshold_sigma = threshold_sigma

    def predict_score(self, X: pd.DataFrame) -> np.ndarray:
        """Scores based on max absolute z-score scaled."""
        if "max_abs_z" in X.columns:
            z = X["max_abs_z"].to_numpy()
        else:
            z = np.max(np.abs(X.to_numpy()), axis=1)
        return np.clip(z / 4.0, 0.0, 1.0)

    def predict_binary(self, X: pd.DataFrame) -> np.ndarray:
        scores = self.predict_score(X)
        return (scores >= (self.threshold_sigma / 4.0)).astype(int)
