"""Unit tests for ML feature engineering and condition normalisation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.features.operating_conditions import OperatingConditionNormalizer
from ml.features.pipeline import compute_rolling_slope


def test_compute_rolling_slope_linear_trend() -> None:
    """Verify compute_rolling_slope accurately measures constant slopes."""
    # Linear series y = 2.0 * x
    series = pd.Series([0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0])
    slopes = compute_rolling_slope(series, window=5)

    assert len(slopes) == len(series)
    # After warm-up, slope should be exactly 2.0
    for val in slopes.iloc[4:]:
        assert pytest.approx(val, abs=1e-5) == 2.0


def test_compute_rolling_slope_flat_and_small() -> None:
    """Verify compute_rolling_slope on constant series and small arrays."""
    flat = pd.Series([5.0] * 10)
    slopes_flat = compute_rolling_slope(flat, window=5)
    for val in slopes_flat:
        assert pytest.approx(val, abs=1e-5) == 0.0

    single = pd.Series([42.0])
    slopes_single = compute_rolling_slope(single, window=5)
    assert slopes_single.iloc[0] == 0.0


def test_operating_condition_normalizer() -> None:
    """Verify normalizer fits linear relation to condition parameters and computes residuals."""
    rng = np.random.default_rng(42)
    n = 100

    duration = rng.uniform(1.0, 4.0, size=n)
    ambient_temp = rng.uniform(-10.0, 40.0, size=n)
    altitude = rng.choice(["Low", "Medium", "High"], size=n)
    load = rng.uniform(0.8, 1.3, size=n)

    # True response: baseline = 100 + 0.5 * temp + 2.0 * duration
    noise = rng.normal(0, 0.1, size=n)
    y_mean = 100.0 + 0.5 * ambient_temp + 2.0 * duration + noise

    df = pd.DataFrame(
        {
            "parameter": ["temperature"] * n,
            "mean": y_mean,
            "duration_hours": duration,
            "ambient_temp_c": ambient_temp,
            "altitude_band": altitude,
            "load_factor": load,
        }
    )

    normalizer = OperatingConditionNormalizer(alpha=0.1)
    normalizer.fit(df)

    assert "temperature" in normalizer.models

    residuals = normalizer.transform(df)
    assert len(residuals) == n
    # Residual mean should be near 0
    assert pytest.approx(float(residuals.mean()), abs=0.2) == 0.0
    # Residual std should be close to injected noise std (0.1)
    assert float(residuals.std()) < 0.5


def test_operating_condition_normalizer_unseen_parameter() -> None:
    """Verify normalizer fallback for parameters not seen during fit."""
    fit_df = pd.DataFrame(
        {
            "parameter": ["pressure"] * 20,
            "mean": [3000.0] * 20,
            "duration_hours": [2.0] * 20,
            "ambient_temp_c": [20.0] * 20,
            "altitude_band": ["Medium"] * 20,
            "load_factor": [1.0] * 20,
        }
    )

    normalizer = OperatingConditionNormalizer()
    normalizer.fit(fit_df)

    test_df = pd.DataFrame(
        {
            "parameter": ["unseen_parameter"],
            "mean": [50.0],
            "duration_hours": [2.0],
            "ambient_temp_c": [20.0],
            "altitude_band": ["Medium"],
            "load_factor": [1.0],
        }
    )

    residuals = normalizer.transform(test_df)
    assert len(residuals) == 1
    # Fallback to median (0.0 if not stored) -> residual = 50.0 - 0.0
    assert residuals.iloc[0] == 50.0
