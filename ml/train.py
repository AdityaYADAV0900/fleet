"""Training and evaluation pipeline CLI entrypoint.

Executes offline ML training for:
(A) Anomaly Detection (Residuals + Isolation Forest)
(B) 14-Day Failure Risk (Calibrated LightGBM vs Logistic Regression baseline)
(C) Remaining Useful Life (Quantile LightGBM vs Linear Trend baseline)

CRITICAL RULE (AGENTS.md):
simulation_truth is NEVER used as a feature or target.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any

from ml.config import (
    DEFAULT_SEED,
    MLConfig,
)
from ml.data import load_raw_data
from ml.evaluation import (
    build_markdown_report,
    evaluate_anomaly_detector,
    evaluate_failure_model,
    evaluate_rul_model,
    generate_evaluation_plots,
)
from ml.features import FeaturePipeline
from ml.models import (
    AnomalyDetector,
    FailureRiskBaseline,
    FailureRiskModel,
    LinearHealthTrendRULBaseline,
    QuantileRULModel,
    RollingZScoreBaseline,
    save_model_artifact,
)
from ml.splits import create_temporal_splits, verify_temporal_integrity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ml.train")


def train_pipeline(
    train_anomaly: bool = True,
    train_failure: bool = True,
    train_rul: bool = True,
    config: MLConfig | None = None,
) -> dict[str, Any]:
    """Execute end-to-end training, evaluation, artifact persistence, and report generation."""
    cfg = config or MLConfig()
    start_time = time.time()
    logger.info("=" * 65)
    logger.info("Starting Offline ML Pipeline (Phase 4)")
    logger.info(f"Target Seed: {cfg.seed} | Version: {cfg.model_version}")
    logger.info(
        f"Temporal Boundaries: Train <= {cfg.train_end} | Val <= {cfg.val_end} | Test <= {cfg.test_end}"
    )
    logger.info("=" * 65)

    # 1. Load operational data (excluding simulation_truth)
    logger.info("Loading fleet operational records from PostgreSQL...")
    raw_data = load_raw_data()
    logger.info(
        f"Loaded: {len(raw_data.flights)} flights, {len(raw_data.sensor_readings)} readings, "
        f"{len(raw_data.maintenance_events)} maintenance events, {len(raw_data.fault_events)} faults."
    )

    # 2. Feature engineering
    logger.info(
        "Running feature engineering pipeline (operating condition normalization, rolling stats)..."
    )
    pipeline = FeaturePipeline()
    bundle = pipeline.fit_transform(raw_data)
    df = bundle.features_df
    X = bundle.X
    feature_names = bundle.feature_names
    logger.info(f"Engineered {len(X)} observations across {len(feature_names)} features.")

    # 3. Create temporal train/val/test splits
    logger.info("Partitioning dataset with strict temporal boundaries...")
    split = create_temporal_splits(df, train_end=cfg.train_end, val_end=cfg.val_end)
    integrity = verify_temporal_integrity(split, df)
    if not integrity["is_valid"]:
        logger.error(f"Temporal leakage detected in splits: {integrity['errors']}")
        raise RuntimeError("Temporal boundary violation in split creation.")

    logger.info(
        f"Splits created: Train={integrity['train_count']} ({split.train_dates[0]} to {split.train_dates[1]}), "
        f"Val={integrity['val_count']} ({split.val_dates[0]} to {split.val_dates[1]}), "
        f"Test={integrity['test_count']} ({split.test_dates[0]} to {split.test_dates[1]})"
    )

    X_train, y_fail_train, y_rul_train = (
        X.iloc[split.train_idx],
        bundle.y_fail_14d.iloc[split.train_idx],
        bundle.y_rul_days.iloc[split.train_idx],
    )
    X_val, y_fail_val, y_rul_val = (
        X.iloc[split.val_idx],
        bundle.y_fail_14d.iloc[split.val_idx],
        bundle.y_rul_days.iloc[split.val_idx],
    )
    X_test, y_fail_test, y_rul_test = (
        X.iloc[split.test_idx],
        bundle.y_fail_14d.iloc[split.test_idx],
        bundle.y_rul_days.iloc[split.test_idx],
    )

    results: dict[str, Any] = {}
    eval_bundle: dict[str, Any] = {}

    # 4. Anomaly Detection
    if train_anomaly:
        logger.info("\n--- Training Model A: Anomaly Detection (Residuals + Isolation Forest) ---")
        anomaly_model = AnomalyDetector(random_state=cfg.seed)
        anomaly_model.fit(X_train)

        anomaly_base = RollingZScoreBaseline()

        # Evaluate on held-out test split
        test_scores = anomaly_model.predict_score(X_test)
        base_scores = anomaly_base.predict_score(X_test)

        test_comp_df = df.iloc[split.test_idx].copy()
        anomaly_metrics = evaluate_anomaly_detector(test_scores, test_comp_df)
        base_anomaly_metrics = evaluate_anomaly_detector(base_scores, test_comp_df)

        logger.info(
            f"[Anomaly Model] FAR / 1k flights: {anomaly_metrics['false_alarm_rate_per_1000']}, Lead time: {anomaly_metrics['mean_detection_lead_time_days']}d"
        )
        logger.info(
            f"[Anomaly Base]  FAR / 1k flights: {base_anomaly_metrics['false_alarm_rate_per_1000']}, Lead time: {base_anomaly_metrics['mean_detection_lead_time_days']}d"
        )

        # Persist artifact
        save_model_artifact(
            name="anomaly_detector",
            version=cfg.model_version,
            model=anomaly_model,
            features=feature_names,
            metrics={"model": anomaly_metrics, "baseline": base_anomaly_metrics},
            data_df=X_train,
            output_base_dir=cfg.models_dir,
        )

        eval_bundle["anomaly"] = {
            "model_metrics": anomaly_metrics,
            "base_metrics": base_anomaly_metrics,
        }
        results["anomaly"] = anomaly_metrics

    # 5. Failure Risk Model (14-Day)
    if train_failure:
        logger.info(
            "\n--- Training Model B: 14-Day Failure Risk (Calibrated LightGBM vs Baseline) ---"
        )
        # Baseline
        base_fail = FailureRiskBaseline(random_state=cfg.seed)
        base_fail.fit(X_train, y_fail_train)
        base_probs = base_fail.predict_proba(X_test)
        base_metrics = evaluate_failure_model(y_fail_test.to_numpy(), base_probs)

        # LightGBM with Sigmoid Calibration
        fail_model = FailureRiskModel(random_state=cfg.seed)
        fail_model.fit(X_train, y_fail_train, X_val, y_fail_val)
        model_probs = fail_model.predict_proba(X_test)
        model_metrics = evaluate_failure_model(y_fail_test.to_numpy(), model_probs)

        logger.info(
            f"[Failure Baseline] PR-AUC: {base_metrics['pr_auc']}, Brier: {base_metrics['brier_score']}"
        )
        logger.info(
            f"[Failure LightGBM] PR-AUC: {model_metrics['pr_auc']}, Brier: {model_metrics['brier_score']}"
        )

        # Persist artifact
        save_model_artifact(
            name="failure_risk",
            version=cfg.model_version,
            model=fail_model,
            features=feature_names,
            metrics={"model": model_metrics, "baseline": base_metrics},
            data_df=X_train,
            output_base_dir=cfg.models_dir,
        )

        eval_bundle["failure"] = {
            "model_metrics": model_metrics,
            "base_metrics": base_metrics,
            "y_test": y_fail_test.to_numpy(),
            "model_probs": model_probs,
            "base_probs": base_probs,
        }
        results["failure"] = model_metrics

    # 6. Remaining Useful Life (RUL) Model
    if train_rul:
        logger.info("\n--- Training Model C: RUL Regression (Quantile LightGBM vs Baseline) ---")
        # Baseline
        base_rul = LinearHealthTrendRULBaseline()
        base_rul.fit(X_train, y_rul_train)
        base_pred = base_rul.predict(X_test)
        base_rul_metrics = evaluate_rul_model(y_rul_test.to_numpy(), base_pred)

        # Quantile LightGBM
        rul_model = QuantileRULModel(random_state=cfg.seed)
        rul_model.fit(X_train, y_rul_train, X_val, y_rul_val)
        quants = rul_model.predict_quantiles(X_test)
        model_rul_metrics = evaluate_rul_model(
            y_true=y_rul_test.to_numpy(),
            y_pred_p50=quants["p50"],
            y_pred_p10=quants["p10"],
            y_pred_p90=quants["p90"],
        )

        logger.info(
            f"[RUL Baseline] MAE: {base_rul_metrics['mae']} days, Asym Score: {base_rul_metrics['asymmetric_score']}"
        )
        logger.info(
            f"[RUL Quantile] MAE: {model_rul_metrics['mae']} days, Coverage 10-90: {model_rul_metrics['interval_coverage_p10_p90'] * 100:.1f}%"
        )

        # Persist artifact
        save_model_artifact(
            name="rul_regressor",
            version=cfg.model_version,
            model=rul_model,
            features=feature_names,
            metrics={"model": model_rul_metrics, "baseline": base_rul_metrics},
            data_df=X_train,
            output_base_dir=cfg.models_dir,
        )

        eval_bundle["rul"] = {
            "model_metrics": model_rul_metrics,
            "base_metrics": base_rul_metrics,
            "y_test": y_rul_test.to_numpy(),
            "model_p50": quants["p50"],
            "base_pred": base_pred,
        }
        results["rul"] = model_rul_metrics

    # 7. Extract AC-017 Hero Aircraft Progression for Report Plotting
    hero_comp_mask = df["aircraft_id"] == "AC-017"
    if hero_comp_mask.any() and train_anomaly:
        hero_df = df[hero_comp_mask].copy()
        hero_scores = anomaly_model.predict_score(X[hero_comp_mask])
        hero_df["anomaly_score"] = hero_scores
        eval_bundle["hero_df"] = hero_df

    # 8. Render Diagnostic Figures and Markdown Report
    logger.info("\nGenerating diagnostic plots and reports/model_evaluation.md...")
    plots = generate_evaluation_plots(eval_bundle, output_dir=cfg.figures_dir)
    report_file = build_markdown_report(
        eval_bundle, plots, output_path=cfg.reports_dir / "model_evaluation.md"
    )
    logger.info(f"Evaluation report generated: {report_file}")

    duration = time.time() - start_time
    logger.info(f"\n[Phase 4 ML Pipeline Completed Successfully in {duration:.1f}s]")
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline ML Training & Evaluation Pipeline")
    parser.add_argument(
        "--all", action="store_true", help="Train all models (anomaly, failure, RUL)"
    )
    parser.add_argument(
        "--model", choices=["anomaly", "failure", "rul"], help="Train a specific model"
    )
    parser.add_argument("--version", default="v1", help="Version tag for model artifacts")
    parser.add_argument(
        "--seed", type=int, default=DEFAULT_SEED, help="Random seed for reproducibility"
    )

    args = parser.parse_args()

    train_all = args.all or (args.model is None)
    train_anomaly = train_all or (args.model == "anomaly")
    train_failure = train_all or (args.model == "failure")
    train_rul = train_all or (args.model == "rul")

    config = MLConfig(
        seed=args.seed,
        model_version=args.version,
    )

    try:
        train_pipeline(
            train_anomaly=train_anomaly,
            train_failure=train_failure,
            train_rul=train_rul,
            config=config,
        )
    except Exception as exc:
        logger.exception(f"Training pipeline failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
