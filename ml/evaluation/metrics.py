"""Evaluation metrics for predictive maintenance models.

Calculates PR-AUC, recall at fixed precision, Brier score, MAE, asymmetric score,
interval coverage (P10-P90), detection lead time, and false alarm rate.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    auc,
    brier_score_loss,
    mean_absolute_error,
    precision_recall_curve,
    roc_auc_score,
)


def evaluate_failure_model(
    y_true: np.ndarray,
    y_prob: np.ndarray,
) -> dict[str, Any]:
    """Calculate PR-AUC, ROC-AUC, Brier score, and recall at fixed precision thresholds."""
    y_true_arr = np.asarray(y_true, dtype=int)
    y_prob_arr = np.asarray(y_prob, dtype=float)

    # 1. Brier score
    brier = float(brier_score_loss(y_true_arr, y_prob_arr))

    # 2. PR-AUC and ROC-AUC
    if len(np.unique(y_true_arr)) > 1:
        roc_auc = float(roc_auc_score(y_true_arr, y_prob_arr))
        precisions, recalls, thresholds = precision_recall_curve(y_true_arr, y_prob_arr)
        pr_auc = float(auc(recalls, precisions))

        # Recall at precision >= 0.50 and >= 0.70
        rec_at_p50 = 0.0
        rec_at_p70 = 0.0
        for p, r in zip(precisions, recalls, strict=False):
            if p >= 0.50 and r > rec_at_p50:
                rec_at_p50 = float(r)
            if p >= 0.70 and r > rec_at_p70:
                rec_at_p70 = float(r)
    else:
        roc_auc = 0.5
        pr_auc = float(np.mean(y_true_arr))
        rec_at_p50 = 0.0
        rec_at_p70 = 0.0

    return {
        "pr_auc": round(pr_auc, 4),
        "roc_auc": round(roc_auc, 4),
        "brier_score": round(brier, 4),
        "recall_at_precision_50": round(rec_at_p50, 4),
        "recall_at_precision_70": round(rec_at_p70, 4),
        "sample_count": len(y_true_arr),
        "positive_count": int(np.sum(y_true_arr)),
        "prevalence": round(float(np.mean(y_true_arr)), 4),
    }


def compute_c_mapss_asymmetric_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Asymmetric scoring function penalising late predictions (y_pred > y_true) more heavily than early."""
    diff = y_pred - y_true  # > 0 means late prediction (dangerous)
    score = np.where(
        diff < 0,
        np.exp(-diff / 13.0) - 1.0,  # Early prediction
        np.exp(diff / 10.0) - 1.0,  # Late prediction
    )
    return float(np.mean(score))


def evaluate_rul_model(
    y_true: np.ndarray,
    y_pred_p50: np.ndarray,
    y_pred_p10: np.ndarray | None = None,
    y_pred_p90: np.ndarray | None = None,
) -> dict[str, Any]:
    """Calculate MAE, asymmetric score, and interval coverage on 10-90 quantile band."""
    y_t = np.asarray(y_true, dtype=float)
    y_p = np.asarray(y_pred_p50, dtype=float)

    mae = float(mean_absolute_error(y_t, y_p))
    asym_score = compute_c_mapss_asymmetric_score(y_t, y_p)

    coverage = None
    if y_pred_p10 is not None and y_pred_p90 is not None:
        p10 = np.asarray(y_pred_p10, dtype=float)
        p90 = np.asarray(y_pred_p90, dtype=float)
        in_interval = (y_t >= p10) & (y_t <= p90)
        coverage = round(float(np.mean(in_interval)), 4)

    return {
        "mae": round(mae, 2),
        "asymmetric_score": round(asym_score, 2),
        "interval_coverage_p10_p90": coverage,
        "sample_count": len(y_t),
    }


def evaluate_anomaly_detector(
    scores: np.ndarray,
    comp_flight_df: pd.DataFrame,
    threshold: float = 0.70,
) -> dict[str, Any]:
    """Calculate detection lead time, false alarm rate per 1,000 flights, and recall of degradation."""
    df = comp_flight_df.copy()
    df["anomaly_score"] = scores
    df["is_alert"] = (scores >= threshold).astype(int)

    # 1. False alarm rate: on samples where true RUL is > 45 days (healthy)
    healthy_mask = df["rul_days"] >= 45.0
    healthy_flights = int(healthy_mask.sum())
    false_alarms = int(df.loc[healthy_mask, "is_alert"].sum())
    far_per_1000 = (
        round(float(false_alarms / max(1, healthy_flights) * 1000.0), 2)
        if healthy_flights > 0
        else 0.0
    )

    # 2. Detection lead time and recall of degradation
    # Components that experienced failure (rul_days <= 14 at some point)
    degrading_mask = (df["rul_days"] > 0) & (df["rul_days"] <= 30)
    degrading_flights = int(degrading_mask.sum())
    degrading_alerts = int(df.loc[degrading_mask, "is_alert"].sum())
    recall_degradation = (
        round(float(degrading_alerts / max(1, degrading_flights)), 4)
        if degrading_flights > 0
        else 0.0
    )

    # Mean lead time of alerts before failure
    alerting_before_failure = df[
        (df["is_alert"] == 1) & (df["rul_days"] > 0) & (df["rul_days"] <= 30)
    ]
    mean_lead_time_days = (
        round(float(alerting_before_failure["rul_days"].mean()), 1)
        if not alerting_before_failure.empty
        else 0.0
    )

    return {
        "false_alarm_rate_per_1000": far_per_1000,
        "degradation_recall": recall_degradation,
        "mean_detection_lead_time_days": mean_lead_time_days,
        "total_observations": len(df),
        "alert_count": int(df["is_alert"].sum()),
    }
