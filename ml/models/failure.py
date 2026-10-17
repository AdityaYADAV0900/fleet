"""14-day failure risk prediction model with calibration and SHAP explainability.

Compares a LightGBM classifier against a standardized Logistic Regression baseline.
Applies probability calibration (sigmoid) and SHAP tree explainer for local feature attribution.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class FailureRiskBaseline:
    """Interpretable baseline using class-weighted Logistic Regression."""

    def __init__(self, random_state: int = 42) -> None:
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "clf",
                    LogisticRegression(
                        class_weight="balanced",
                        random_state=random_state,
                        max_iter=1000,
                    ),
                ),
            ]
        )
        self.feature_names: list[str] = []

    def fit(self, X: pd.DataFrame, y: pd.Series) -> FailureRiskBaseline:
        self.feature_names = list(X.columns)
        self.pipeline.fit(X, y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Returns 1D array of failure probabilities [0, 1]."""
        return self.pipeline.predict_proba(X)[:, 1]

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)


class FailureRiskModel:
    """LightGBM classifier with probability calibration and SHAP explanations."""

    def __init__(
        self,
        n_estimators: int = 150,
        learning_rate: float = 0.05,
        num_leaves: int = 31,
        max_depth: int = 6,
        random_state: int = 42,
    ) -> None:
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.max_depth = max_depth
        self.random_state = random_state

        self.booster: Optional[lgb.LGBMClassifier] = None
        self.calibrator: Optional[CalibratedClassifierCV] = None
        self.explainer: Optional[shap.TreeExplainer] = None
        self.feature_names: list[str] = []

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
    ) -> FailureRiskModel:
        """Train LightGBM on train split and calibrate probabilities on val split."""
        self.feature_names = list(X_train.columns)

        # Calculate positive class weight to combat imbalance
        n_neg = int((y_train == 0).sum())
        n_pos = int((y_train == 1).sum())
        scale_pos_weight = float(n_neg / max(1, n_pos))

        self.booster = lgb.LGBMClassifier(
            n_estimators=self.n_estimators,
            learning_rate=self.learning_rate,
            num_leaves=self.num_leaves,
            max_depth=self.max_depth,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            n_jobs=1,
            verbosity=-1,
        )

        self.calibrator = CalibratedClassifierCV(
            estimator=self.booster,
            method="sigmoid",
            cv=3,
        )
        self.calibrator.fit(X_train, y_train)

        # Initialize SHAP explainer on one of the calibrated fold boosters
        try:
            fitted_booster = self.calibrator.calibrated_classifiers_[0].estimator
            self.explainer = shap.TreeExplainer(fitted_booster)
        except Exception as exc:
            logger.warning(f"Could not initialize SHAP TreeExplainer: {exc}")
            self.explainer = None

        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        """Return calibrated failure probability [0, 1]."""
        if self.calibrator is not None:
            return self.calibrator.predict_proba(X)[:, 1]
        elif self.booster is not None:
            return self.booster.predict_proba(X)[:, 1]
        else:
            raise RuntimeError("Model is not fitted yet.")

    def predict(self, X: pd.DataFrame, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)

    def explain_instance(self, instance_df: pd.DataFrame, top_n: int = 5) -> dict[str, Any]:
        """Generate SHAP local explanation for a specific prediction instance."""
        if self.explainer is None:
            return {"error": "SHAP explainer not available"}

        shap_values = self.explainer.shap_values(instance_df)
        if isinstance(shap_values, list):
            # For binary classifier, class 1 is at index 1
            vals = shap_values[1][0]
        else:
            vals = shap_values[0]

        impacts = []
        for feat, val in zip(self.feature_names, vals, strict=False):
            impacts.append({"feature": feat, "shap_impact": round(float(val), 4)})

        impacts.sort(key=lambda x: abs(x["shap_impact"]), reverse=True)
        return {
            "top_shap_factors": impacts[:top_n],
            "base_value": float(self.explainer.expected_value[1] if isinstance(self.explainer.expected_value, (list, np.ndarray)) else self.explainer.expected_value),
        }
