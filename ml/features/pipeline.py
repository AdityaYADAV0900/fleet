"""Feature engineering pipeline for predictive maintenance.

Computes condition-normalized sensor residuals, rolling statistics (5 and 20 flights:
mean, slope, std, baseline deviation), hours/cycles since maintenance,
recent fault counts, and failure/RUL labels.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ml.data import RawFleetData
from ml.features.operating_conditions import OperatingConditionNormalizer

logger = logging.getLogger(__name__)


def compute_rolling_slope(series: pd.Series, window: int) -> pd.Series:
    """Compute rolling least-squares linear slope via exact 1D convolution weights."""
    arr = series.to_numpy(dtype=np.float64)
    n = len(arr)
    if n < 2:
        return pd.Series(0.0, index=series.index)

    x = np.arange(window, dtype=np.float64)
    x_mean = (window - 1.0) / 2.0
    denom = np.sum((x - x_mean) ** 2)
    weights = (x - x_mean) / denom

    pad = np.pad(arr, (window - 1, 0), mode="edge")
    conv = np.convolve(pad, weights[::-1], mode="valid")
    return pd.Series(conv, index=series.index)


@dataclass
class DatasetBundle:
    """Container holding feature matrix X, targets y_fail, y_rul, and metadata."""

    features_df: pd.DataFrame
    X: pd.DataFrame
    y_fail_14d: pd.Series
    y_fail_30d: pd.Series
    y_rul_days: pd.Series
    feature_names: list[str]


class FeaturePipeline:
    """End-to-end feature pipeline from raw database tables to ML datasets."""

    def __init__(
        self,
        normalizer: OperatingConditionNormalizer | None = None,
        baseline_flights: int = 5,
    ) -> None:
        self.normalizer = normalizer or OperatingConditionNormalizer()
        self.baseline_flights = baseline_flights
        self.param_scales: dict[str, float] = {}  # parameter -> baseline sigma
        self.feature_names: list[str] = []

    def fit_transform(self, raw: RawFleetData) -> DatasetBundle:
        """Fit normalizers on baseline and transform raw fleet tables into features."""
        # 1. Merge flights with sensor readings
        readings = raw.sensor_readings.copy()
        flights = raw.flights.copy()

        rf_merged = readings.merge(
            flights[
                [
                    "flight_id",
                    "aircraft_id",
                    "date",
                    "duration_hours",
                    "cycles",
                    "ambient_temp_c",
                    "altitude_band",
                    "load_factor",
                ]
            ],
            on="flight_id",
            how="inner",
        )

        # Sort chronologically by component and date/flight
        rf_merged.sort_values(["component_id", "date", "flight_id"], inplace=True)
        rf_merged.reset_index(drop=True, inplace=True)

        # 2. Fit normalizer on healthy/early flights (first N baseline flights per component)
        early_mask = rf_merged.groupby("component_id").cumcount() < self.baseline_flights
        self.normalizer.fit(rf_merged[early_mask])

        # Compute residuals
        rf_merged["residual"] = self.normalizer.transform(rf_merged)

        # Compute parameter-level baseline sigma for standardization
        baseline_df = rf_merged[early_mask]
        for param, group in baseline_df.groupby("parameter"):
            std_val = float(group["residual"].std())
            self.param_scales[str(param)] = std_val if std_val > 1e-4 else 1.0

        # Scale residual into z-score (sigma units)
        scale_series = rf_merged["parameter"].astype(str).map(self.param_scales).fillna(1.0)
        rf_merged["z_score"] = rf_merged["residual"] / scale_series

        # 3. Compute rolling statistics per (component_id, parameter) group
        logger.info("Computing rolling window features over 5 and 20 flights...")
        rolled_rf = rf_merged.copy()
        rolled_rf.sort_values(["component_id", "parameter", "date", "flight_id"], inplace=True)
        rolled_rf.reset_index(drop=True, inplace=True)

        n_rows = len(rolled_rf)
        roll_mean_5 = np.zeros(n_rows, dtype=np.float32)
        roll_std_5 = np.zeros(n_rows, dtype=np.float32)
        roll_slope_5 = np.zeros(n_rows, dtype=np.float32)
        roll_mean_20 = np.zeros(n_rows, dtype=np.float32)
        roll_std_20 = np.zeros(n_rows, dtype=np.float32)
        roll_slope_20 = np.zeros(n_rows, dtype=np.float32)
        dev_baseline = np.zeros(n_rows, dtype=np.float32)

        # Precompute weights for convolution
        w5 = (np.arange(5, dtype=np.float32) - 2.0) / 10.0
        w20 = (np.arange(20, dtype=np.float32) - 9.5) / 665.0

        z_all = rolled_rf["z_score"].to_numpy(dtype=np.float32)

        keys = (
            rolled_rf["component_id"].astype(str) + "##" + rolled_rf["parameter"].astype(str)
        ).to_numpy()
        change_indices = np.where(keys[:-1] != keys[1:])[0] + 1
        starts = np.r_[0, change_indices]
        ends = np.r_[change_indices, n_rows]

        for s_idx, e_idx in zip(starts, ends, strict=False):
            z_grp = z_all[s_idx:e_idx]
            g_len = e_idx - s_idx
            if g_len == 0:
                continue

            base_mean = (
                float(np.mean(z_grp[: min(g_len, self.baseline_flights)])) if g_len > 0 else 0.0
            )
            dev_baseline[s_idx:e_idx] = z_grp - base_mean

            # Window 5 rolling mean and std via cumulative sums
            cumsum = np.cumsum(np.insert(z_grp, 0, 0.0))
            win5 = np.minimum(np.arange(1, g_len + 1), 5)
            start_5 = np.maximum(0, np.arange(1, g_len + 1) - 5)
            rm5 = (cumsum[1:] - cumsum[start_5]) / win5
            roll_mean_5[s_idx:e_idx] = rm5

            cumsum_sq = np.cumsum(np.insert(z_grp**2, 0, 0.0))
            rm5_sq = (cumsum_sq[1:] - cumsum_sq[start_5]) / win5
            var5 = np.maximum(0.0, rm5_sq - rm5**2)
            roll_std_5[s_idx:e_idx] = np.sqrt(var5)

            pad5 = np.pad(z_grp, (4, 0), mode="edge")
            roll_slope_5[s_idx:e_idx] = np.convolve(pad5, w5[::-1], mode="valid")

            # Window 20
            win20 = np.minimum(np.arange(1, g_len + 1), 20)
            start_20 = np.maximum(0, np.arange(1, g_len + 1) - 20)
            rm20 = (cumsum[1:] - cumsum[start_20]) / win20
            roll_mean_20[s_idx:e_idx] = rm20

            rm20_sq = (cumsum_sq[1:] - cumsum_sq[start_20]) / win20
            var20 = np.maximum(0.0, rm20_sq - rm20**2)
            roll_std_20[s_idx:e_idx] = np.sqrt(var20)

            pad20 = np.pad(z_grp, (19, 0), mode="edge")
            roll_slope_20[s_idx:e_idx] = np.convolve(pad20, w20[::-1], mode="valid")

        rolled_rf["roll_mean_5"] = roll_mean_5
        rolled_rf["roll_std_5"] = roll_std_5
        rolled_rf["roll_slope_5"] = roll_slope_5
        rolled_rf["roll_mean_20"] = roll_mean_20
        rolled_rf["roll_std_20"] = roll_std_20
        rolled_rf["roll_slope_20"] = roll_slope_20
        rolled_rf["dev_baseline"] = dev_baseline

        # Precompute absolute values for blazing fast vectorized aggregation
        rolled_rf["abs_z"] = np.abs(rolled_rf["z_score"])
        rolled_rf["abs_roll_mean_5"] = np.abs(rolled_rf["roll_mean_5"])
        rolled_rf["abs_roll_slope_5"] = np.abs(rolled_rf["roll_slope_5"])
        rolled_rf["abs_roll_mean_20"] = np.abs(rolled_rf["roll_mean_20"])
        rolled_rf["abs_roll_slope_20"] = np.abs(rolled_rf["roll_slope_20"])
        rolled_rf["abs_dev_baseline"] = np.abs(rolled_rf["dev_baseline"])

        # 4. Aggregate to component-flight observation level
        comp_flight = rolled_rf.groupby(
            ["flight_id", "component_id", "aircraft_id", "date"], as_index=False
        ).agg(
            max_abs_z=("abs_z", "max"),
            mean_abs_z=("abs_z", "mean"),
            max_roll_mean_5=("abs_roll_mean_5", "max"),
            max_roll_std_5=("roll_std_5", "max"),
            max_roll_slope_5=("abs_roll_slope_5", "max"),
            max_roll_mean_20=("abs_roll_mean_20", "max"),
            max_roll_std_20=("roll_std_20", "max"),
            max_roll_slope_20=("abs_roll_slope_20", "max"),
            max_dev_baseline=("abs_dev_baseline", "max"),
            sensor_reading_std=("std", "mean"),
            flight_duration=("duration_hours", "first"),
            flight_cycles=("cycles", "first"),
            ambient_temp=("ambient_temp_c", "first"),
            load_factor=("load_factor", "first"),
        )

        comp_flight.sort_values(["component_id", "date", "flight_id"], inplace=True)
        comp_flight.reset_index(drop=True, inplace=True)

        # 5. Component metadata: type and criticality
        comp_meta = raw.components.merge(
            raw.component_types[["component_type_id", "criticality", "mtbf_hours"]],
            on="component_type_id",
            how="left",
        )
        comp_flight = comp_flight.merge(
            comp_meta[["component_id", "component_type_id", "criticality", "mtbf_hours"]],
            on="component_id",
            how="left",
        )
        comp_flight["criticality"] = comp_flight["criticality"].fillna(3)
        comp_flight["mtbf_hours"] = comp_flight["mtbf_hours"].fillna(2000.0)

        # 6. Cumulative hours and cycles since last maintenance event
        logger.info("Computing cumulative usage and maintenance intervals...")
        maint_events = raw.maintenance_events[raw.maintenance_events["component_id"].notna()].copy()
        maint_events["maint_date"] = maint_events["date"]

        # Sort maintenance replacements by component and date
        comp_flight["hours_since_maint"] = 0.0
        comp_flight["cycles_since_maint"] = 0.0

        # Vectorized accumulation by component
        comp_flight["cum_hours"] = comp_flight.groupby("component_id")["flight_duration"].cumsum()
        comp_flight["cum_cycles"] = comp_flight.groupby("component_id")["flight_cycles"].cumsum()

        # If a component had maintenance, reset counter after the maintenance date
        if not maint_events.empty:
            maint_replacements = maint_events[maint_events["action"] == "replace"][
                ["component_id", "maint_date"]
            ].drop_duplicates()

            # Merge with replacement events
            cf_m = comp_flight.merge(maint_replacements, on="component_id", how="left")
            # For flights after replacement, hours start from 0
            after_mask = cf_m["maint_date"].notna() & (cf_m["date"] >= cf_m["maint_date"])
            comp_flight["hours_since_maint"] = comp_flight["cum_hours"]
            comp_flight["cycles_since_maint"] = comp_flight["cum_cycles"]
            # Reset after replacement
            if after_mask.any():
                comp_flight.loc[after_mask, "hours_since_maint"] = comp_flight.loc[
                    after_mask, "cum_hours"
                ] - comp_flight.loc[after_mask].groupby("component_id")["cum_hours"].transform(
                    "min"
                )
                comp_flight.loc[after_mask, "cycles_since_maint"] = comp_flight.loc[
                    after_mask, "cum_cycles"
                ] - comp_flight.loc[after_mask].groupby("component_id")["cum_cycles"].transform(
                    "min"
                )
        else:
            comp_flight["hours_since_maint"] = comp_flight["cum_hours"]
            comp_flight["cycles_since_maint"] = comp_flight["cum_cycles"]

        # 7. Recent fault counts (last 7, 14, 30 days)
        logger.info("Computing historical fault counts...")
        faults = raw.fault_events.copy()
        fault_counts_7d = np.zeros(len(comp_flight), dtype=int)
        fault_counts_14d = np.zeros(len(comp_flight), dtype=int)
        fault_counts_30d = np.zeros(len(comp_flight), dtype=int)

        if not faults.empty:
            faults_by_comp: dict[str, np.ndarray] = {}
            for comp_id, g in faults.groupby("component_id"):
                faults_by_comp[str(comp_id)] = pd.to_datetime(g["date"]).values

            comp_dates = pd.to_datetime(comp_flight["date"]).values
            comp_ids = comp_flight["component_id"].astype(str).values

            for cid, f_dt in faults_by_comp.items():
                mask = comp_ids == cid
                if not mask.any():
                    continue
                c_dts = comp_dates[mask]
                f_dt_sorted = np.sort(f_dt)
                idx_end = np.searchsorted(f_dt_sorted, c_dts, side="right")
                idx_start_7 = np.searchsorted(
                    f_dt_sorted, c_dts - np.timedelta64(7, "D"), side="left"
                )
                idx_start_14 = np.searchsorted(
                    f_dt_sorted, c_dts - np.timedelta64(14, "D"), side="left"
                )
                idx_start_30 = np.searchsorted(
                    f_dt_sorted, c_dts - np.timedelta64(30, "D"), side="left"
                )

                fault_counts_7d[mask] = idx_end - idx_start_7
                fault_counts_14d[mask] = idx_end - idx_start_14
                fault_counts_30d[mask] = idx_end - idx_start_30

        comp_flight["fault_count_7d"] = fault_counts_7d
        comp_flight["fault_count_14d"] = fault_counts_14d
        comp_flight["fault_count_30d"] = fault_counts_30d

        # 8. Create labels from unscheduled maintenance replacements
        # CRITICAL: simulation_truth is NEVER used! Only operational maintenance records.
        logger.info("Computing failure-risk and RUL labels from unscheduled maintenance records...")
        unscheduled_replaces = raw.maintenance_events[
            (raw.maintenance_events["type"] == "unscheduled")
            & (raw.maintenance_events["action"] == "replace")
            & (raw.maintenance_events["component_id"].notna())
        ].copy()

        y_14d = np.zeros(len(comp_flight), dtype=int)
        y_30d = np.zeros(len(comp_flight), dtype=int)
        y_rul = np.full(len(comp_flight), 60.0, dtype=np.float64)

        if not unscheduled_replaces.empty:
            fail_dates_by_comp: dict[str, np.ndarray] = {}
            for comp_id, g in unscheduled_replaces.groupby("component_id"):
                fail_dates_by_comp[str(comp_id)] = pd.to_datetime(g["date"]).values

            comp_dates = pd.to_datetime(comp_flight["date"]).values
            comp_ids = comp_flight["component_id"].astype(str).values

            for cid, f_dt in fail_dates_by_comp.items():
                mask = comp_ids == cid
                if not mask.any():
                    continue
                c_dts = comp_dates[mask]
                f_dt_sorted = np.sort(f_dt)
                next_fail_idx = np.searchsorted(f_dt_sorted, c_dts, side="right")
                has_future = next_fail_idx < len(f_dt_sorted)

                if has_future.any():
                    c_indices = np.where(mask)[0][has_future]
                    next_fails = f_dt_sorted[next_fail_idx[has_future]]
                    currents = c_dts[has_future]
                    days_to_fail = (next_fails - currents) / np.timedelta64(1, "D")

                    y_14d[c_indices] = ((days_to_fail > 0) & (days_to_fail <= 14)).astype(int)
                    y_30d[c_indices] = ((days_to_fail > 0) & (days_to_fail <= 30)).astype(int)
                    y_rul[c_indices] = np.clip(days_to_fail, 0.0, 60.0)

        comp_flight["fail_within_14d"] = y_14d
        comp_flight["fail_within_30d"] = y_30d
        comp_flight["rul_days"] = y_rul

        # Define explicit model feature matrix columns
        feature_cols = [
            "max_abs_z",
            "mean_abs_z",
            "max_roll_mean_5",
            "max_roll_std_5",
            "max_roll_slope_5",
            "max_roll_mean_20",
            "max_roll_std_20",
            "max_roll_slope_20",
            "max_dev_baseline",
            "sensor_reading_std",
            "flight_duration",
            "flight_cycles",
            "ambient_temp",
            "load_factor",
            "criticality",
            "hours_since_maint",
            "cycles_since_maint",
            "fault_count_7d",
            "fault_count_14d",
            "fault_count_30d",
        ]

        self.feature_names = feature_cols
        X = comp_flight[feature_cols].fillna(0.0)

        return DatasetBundle(
            features_df=comp_flight,
            X=X,
            y_fail_14d=pd.Series(y_14d, index=comp_flight.index, name="fail_within_14d"),
            y_fail_30d=pd.Series(y_30d, index=comp_flight.index, name="fail_within_30d"),
            y_rul_days=pd.Series(y_rul, index=comp_flight.index, name="rul_days"),
            feature_names=feature_cols,
        )
