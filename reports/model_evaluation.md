# Model Evaluation & Diagnostic Report

> **SYNTHETIC DATA NOTICE:** All metrics and predictions reported here are evaluated exclusively on synthetic fleet operational data generated for decision-support prototyping. Ground truth health (`simulation_truth`) was strictly excluded from training and feature engineering.

*Generated at:* `2026-10-04 16:38:44 UTC`
*Repository Branch:* `phase-4-ml-pipeline`
*Target Environment:* Laptop CPU, No Deep Learning

---

## 1. Executive Summary

This report documents the offline training, validation, and held-out test evaluation of the three core machine learning models for the Integrated Predictive Maintenance & Fleet Availability Platform:
1. **Unsupervised Anomaly Detection:** Operating condition-regression residuals coupled with Isolation Forest.
2. **14-Day Failure Risk Classification:** Calibrated gradient boosted trees (LightGBM) evaluated against a standardized Logistic Regression baseline.
3. **Remaining Useful Life (RUL) Estimation:** Quantile LightGBM regression ($P_{10}, P_{50}, P_{90}$) evaluated against a linear health-trend extrapolation baseline.

Splits are strictly temporal (Train: 2023-01 to 2024-06; Val: 2024-07 to 2024-12; Test: 2025-01 to 2025-12).

---

## 2. Model Performance vs Baselines (Held-Out Test Period)

### A. 14-Day Failure Risk Classification

| Model | PR-AUC | ROC-AUC | Brier Score | Recall @ Prec $\ge$ 0.50 | Status |
|---|---|---|---|---|---|
| **Calibrated LightGBM** | **0.1518** | **0.8704** | **0.0094** | **0.1273** | **BEATS BASELINE** |
| Logistic Regression (Baseline) | 0.047 | 0.8143 | 0.5345 | 0.0 | Baseline |

**Key Findings:**
- LightGBM captures non-linear interactions between rolling slope, within-flight sensor flutter, and cumulative flight hours since overhaul.
- Sigmoid probability calibration ensures risk probabilities accurately reflect true empirical failure frequencies.

![Precision-Recall Curve](figures/pr_curve_comparison.png)
![Calibration Curve](figures/calibration_curve.png)

---

### B. Remaining Useful Life (RUL) Regression

Target is clipped at 60.0 days (standard C-MAPSS formulation).

| Model | MAE (days) | C-MAPSS Asymmetric Score | 10–90% Interval Coverage | Status |
|---|---|---|---|---|
| **Quantile LightGBM ($P_{50}$)** | **1.19** | **2.65** | **98.1%** | **BEATS BASELINE** |
| Linear Trend Extrapolation (Baseline) | 43.97 | 61.43 | N/A (point est.) | Baseline |

**Key Findings:**
- The $P_{10} - P_{90}$ quantile band covers ~98.1% of ground truth test observations, providing planners with an auditable confidence interval rather than a misleading single date.
- The asymmetric penalty penalises dangerous late predictions ($y_{pred} > y_{true}$) significantly more than early predictions.

![RUL Error Distribution](figures/rul_error_distribution.png)

---

### C. Unsupervised Anomaly Detection

| Method | False Alarm Rate (per 1,000 flights) | Degradation Recall | Mean Lead Time |
|---|---|---|---|
| **Residuals + Isolation Forest** | **223.2** | **82.9%** | **15.1 days** |
| Rolling $Z$-score (Baseline) | 620.32 | 88.1% | 15.1 days |

![Hero Aircraft AC-017 Anomaly Timeline](figures/hero_ac017_timeline.png)

---

## 3. Top Predictive Features (SHAP Global Attribution)

Global feature importance identified by SHAP TreeExplainer on the failure model:
1. `max_roll_mean_20`: Sustained multi-flight shift in condition-adjusted parameter residuals.
2. `max_roll_slope_20`: Rate of mechanical degradation progression over the last 20 sorties.
3. `hours_since_maint`: Total operating flight hours accumulated since previous shop replacement.
4. `sensor_reading_std`: Within-flight parameter flutter indicating bearing or valve instability.
5. `fault_count_14d`: Recorded Built-In-Test (BIT) warning codes in recent operational sorties.

---

## 4. Known Weaknesses and Limitations

1. **Synthetic Data Artifacts:** While sensor noise and sudden shock failure modes were realistically modeled in Phase 2, real aircraft systems encounter unknown environmental extremes and multi-parameter sensor corruption not fully represented in synthetic data.
2. **Sudden Shock Failures:** Component failure modes tagged as sudden shock in the simulator show near-zero lead time; this is expected physics, and the model's confidence notes must communicate this limitation clearly to maintenance engineers.
3. **Class Imbalance:** Due to the rarity of unscheduled replacement events relative to nominal flights, positive predictive value (precision) remains modest at low thresholds, making probability calibration and risk banding essential.
