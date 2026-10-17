"""Unit tests for temporal and grouped dataset splitting."""

from datetime import date

import pandas as pd

from ml.splits import create_temporal_splits, verify_temporal_integrity


def test_temporal_split_ordering() -> None:
    """Verify that temporal splits do not allow samples from future into train/val."""
    dates = pd.date_range("2023-01-01", "2025-12-31", freq="D").date
    df = pd.DataFrame(
        {
            "date": dates,
            "aircraft_id": ["AC-001"] * len(dates),
            "val": range(len(dates)),
        }
    )

    train_end = date(2024, 6, 30)
    val_end = date(2024, 12, 31)

    split = create_temporal_splits(df, train_end=train_end, val_end=val_end)
    integrity = verify_temporal_integrity(split, df)

    assert integrity["is_valid"] is True
    assert len(integrity["errors"]) == 0
    assert integrity["train_count"] == 547  # Days in 2023 + first 6 months of 2024
    assert integrity["val_count"] == 184  # 2024-07-01 to 2024-12-31
    assert integrity["test_count"] == 365  # Full year 2025

    # Check boundaries
    assert split.train_dates[1] <= train_end
    assert split.val_dates[0] > train_end
    assert split.val_dates[1] <= val_end
    assert split.test_dates[0] > val_end


def test_holdout_aircraft_grouping() -> None:
    """Verify that aircraft-grouped holdout excludes specified aircraft from training."""
    dates = pd.date_range("2023-01-01", "2023-01-10", freq="D").date
    aircraft = ["AC-001", "AC-002", "AC-003", "AC-004"]
    records = []
    for d in dates:
        for ac in aircraft:
            records.append({"date": d, "aircraft_id": ac})
    df = pd.DataFrame(records)

    split = create_temporal_splits(
        df,
        train_end=date(2023, 1, 5),
        val_end=date(2023, 1, 7),
        holdout_aircraft_pct=0.25,
        seed=42,
    )

    train_aircraft = df.iloc[split.train_idx]["aircraft_id"].unique()
    assert len(train_aircraft) <= 3  # At least 1 aircraft held out
