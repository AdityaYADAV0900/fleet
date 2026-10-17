"""Unit and integration tests for model persistence, reloading, and inference."""

import numpy as np
import pandas as pd

from ml.models.persistence import load_model_artifact


def test_reload_anomaly_detector_artifact() -> None:
    """Verify saved anomaly detector artifact reloads and predicts valid scores."""
    model, meta = load_model_artifact("anomaly_detector", version="v1")

    assert meta["model_name"] == "anomaly_detector"
    assert meta["version"] == "v1"
    assert "features" in meta
    assert len(meta["features"]) > 0
    assert "data_hash" in meta

    # Test prediction on dummy input
    features = meta["features"]
    dummy_df = pd.DataFrame(np.zeros((5, len(features))), columns=features)
    scores = model.predict_score(dummy_df)

    assert len(scores) == 5
    assert np.all(scores >= 0.0)
    assert np.all(scores <= 1.0)


def test_reload_failure_risk_artifact() -> None:
    """Verify saved failure risk artifact reloads and generates calibrated probabilities and SHAP."""
    model, meta = load_model_artifact("failure_risk", version="v1")

    assert meta["model_name"] == "failure_risk"
    assert "library_versions" in meta
    assert "lightgbm" in meta["library_versions"]

    features = meta["features"]
    dummy_df = pd.DataFrame(np.zeros((5, len(features))), columns=features)
    probs = model.predict_proba(dummy_df)

    assert len(probs) == 5
    assert np.all(probs >= 0.0)
    assert np.all(probs <= 1.0)

    # Test SHAP instance explanation
    explanation = model.explain_instance(dummy_df.iloc[[0]])
    assert "top_shap_factors" in explanation
    assert len(explanation["top_shap_factors"]) > 0


def test_reload_rul_regressor_artifact() -> None:
    """Verify saved RUL regressor artifact reloads and returns ordered quantiles."""
    model, meta = load_model_artifact("rul_regressor", version="v1")

    assert meta["model_name"] == "rul_regressor"

    features = meta["features"]
    dummy_df = pd.DataFrame(np.zeros((5, len(features))), columns=features)
    quants = model.predict_quantiles(dummy_df)

    assert "p10" in quants and "p50" in quants and "p90" in quants
    assert len(quants["p50"]) == 5
    # Verify monotonicity: p10 <= p50 <= p90
    assert np.all(quants["p10"] <= quants["p50"] + 1e-5)
    assert np.all(quants["p50"] <= quants["p90"] + 1e-5)
    assert np.all(quants["p10"] >= 0.0)
    assert np.all(quants["p90"] <= 60.0)
