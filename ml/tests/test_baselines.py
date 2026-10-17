"""Acceptance tests verifying models beat baselines on held-out test data."""

from ml.models.persistence import load_model_artifact


def test_anomaly_detector_beats_baseline() -> None:
    """Verify anomaly detector has lower false alarm rate than fixed threshold baseline."""
    _, meta = load_model_artifact("anomaly_detector", version="v1")
    metrics = meta["metrics"]

    model_far = metrics["model"]["false_alarm_rate_per_1000"]
    base_far = metrics["baseline"]["false_alarm_rate_per_1000"]

    assert model_far < base_far, (
        f"Anomaly detector FAR ({model_far}) should beat baseline FAR ({base_far})"
    )


def test_failure_model_beats_baseline() -> None:
    """Verify calibrated failure model beats logistic regression on PR-AUC and Brier score."""
    _, meta = load_model_artifact("failure_risk", version="v1")
    metrics = meta["metrics"]

    model_pr = metrics["model"]["pr_auc"]
    base_pr = metrics["baseline"]["pr_auc"]

    model_brier = metrics["model"]["brier_score"]
    base_brier = metrics["baseline"]["brier_score"]

    assert model_pr > base_pr, f"Failure risk PR-AUC ({model_pr}) must beat baseline ({base_pr})"
    assert model_brier < base_brier, (
        f"Failure risk Brier score ({model_brier}) must beat baseline ({base_brier})"
    )


def test_rul_model_beats_baseline() -> None:
    """Verify quantile RUL regressor beats linear health trend on MAE."""
    _, meta = load_model_artifact("rul_regressor", version="v1")
    metrics = meta["metrics"]

    model_mae = metrics["model"]["mae"]
    base_mae = metrics["baseline"]["mae"]

    assert model_mae < base_mae, f"Quantile RUL MAE ({model_mae}d) must beat baseline ({base_mae}d)"
    # Check 10-90% interval coverage is substantial (>70%)
    coverage = metrics["model"]["interval_coverage_p10_p90"]
    assert coverage is not None and coverage >= 0.70, (
        f"Quantile interval coverage ({coverage}) should be at least 70%"
    )
