"""Temporal and grouped split generators for time-series fleet data.

CRITICAL RULE (AGENTS.md):
Random row splits are forbidden. Splits must be strictly temporal and grouped
by component / aircraft to prevent data leakage across time and entity boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class SplitResult:
    """Indices and date bounds for train, validation, and test partitions."""

    train_idx: np.ndarray
    val_idx: np.ndarray
    test_idx: np.ndarray
    train_dates: tuple[date, date]
    val_dates: tuple[date, date]
    test_dates: tuple[date, date]


def create_temporal_splits(
    df: pd.DataFrame,
    train_end: date,
    val_end: date,
    date_col: str = "date",
    aircraft_col: str = "aircraft_id",
    holdout_aircraft_pct: float = 0.0,
    seed: int = 42,
) -> SplitResult:
    """Create temporal train/val/test splits, optionally holding out a set of aircraft for pure spatial generalization.

    Default:
    - Train: date <= train_end
    - Val: train_end < date <= val_end
    - Test: date > val_end
    """
    dates = pd.to_datetime(df[date_col]).dt.date

    train_mask = dates <= train_end
    val_mask = (dates > train_end) & (dates <= val_end)
    test_mask = dates > val_end

    if holdout_aircraft_pct > 0.0 and aircraft_col in df.columns:
        rng = np.random.RandomState(seed)
        unique_aircraft = np.sort(df[aircraft_col].unique())
        n_holdout = max(1, int(len(unique_aircraft) * holdout_aircraft_pct))
        holdout_aircraft = set(rng.choice(unique_aircraft, size=n_holdout, replace=False))

        # Train on non-holdout only; test includes both temporal future and holdout
        train_mask &= ~df[aircraft_col].isin(holdout_aircraft)

    train_idx = np.where(train_mask)[0]
    val_idx = np.where(val_mask)[0]
    test_idx = np.where(test_mask)[0]

    train_d = (
        (dates.iloc[train_idx].min(), dates.iloc[train_idx].max())
        if len(train_idx) > 0
        else (train_end, train_end)
    )
    val_d = (
        (dates.iloc[val_idx].min(), dates.iloc[val_idx].max())
        if len(val_idx) > 0
        else (train_end, val_end)
    )
    test_d = (
        (dates.iloc[test_idx].min(), dates.iloc[test_idx].max())
        if len(test_idx) > 0
        else (val_end, val_end)
    )

    return SplitResult(
        train_idx=train_idx,
        val_idx=val_idx,
        test_idx=test_idx,
        train_dates=train_d,
        val_dates=val_d,
        test_dates=test_d,
    )


def verify_temporal_integrity(
    split: SplitResult, df: pd.DataFrame, date_col: str = "date"
) -> dict[str, Any]:
    """Sanity check that no sample in train occurs after any sample in val or test."""
    dates = pd.to_datetime(df[date_col]).dt.date

    max_train = dates.iloc[split.train_idx].max() if len(split.train_idx) > 0 else None
    min_val = dates.iloc[split.val_idx].min() if len(split.val_idx) > 0 else None
    max_val = dates.iloc[split.val_idx].max() if len(split.val_idx) > 0 else None
    min_test = dates.iloc[split.test_idx].min() if len(split.test_idx) > 0 else None

    is_valid = True
    errors = []

    if max_train and min_val and max_train >= min_val:
        is_valid = False
        errors.append(f"Train date {max_train} overlaps with val date {min_val}")

    if max_val and min_test and max_val >= min_test:
        is_valid = False
        errors.append(f"Val date {max_val} overlaps with test date {min_test}")

    return {
        "is_valid": is_valid,
        "errors": errors,
        "train_count": len(split.train_idx),
        "val_count": len(split.val_idx),
        "test_count": len(split.test_idx),
    }
