"""Model artifact persistence with metadata.json and hash audit trails."""

from __future__ import annotations

import hashlib
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import joblib
import pandas as pd

from ml.config import MODELS_DIR

logger = logging.getLogger(__name__)


def compute_data_hash(df: pd.DataFrame) -> str:
    """Compute sha256 checksum of dataframe contents for audit reproducibility."""
    hasher = hashlib.sha256()
    # Hash column names and shape
    hasher.update(str(list(df.columns)).encode("utf-8"))
    hasher.update(str(df.shape).encode("utf-8"))
    # Hash sample values
    sample_records = df.head(100).to_json(orient="records")
    hasher.update(sample_records.encode("utf-8"))
    return hasher.hexdigest()[:16]


def save_model_artifact(
    name: str,
    version: str,
    model: Any,
    features: list[str],
    metrics: dict[str, Any],
    data_df: Optional[pd.DataFrame] = None,
    output_base_dir: Optional[Path] = None,
) -> Path:
    """Persist model artifact and metadata.json to versioned directory."""
    base_dir = output_base_dir or MODELS_DIR
    target_dir = base_dir / name / version
    target_dir.mkdir(parents=True, exist_ok=True)

    model_path = target_dir / "model.joblib"
    meta_path = target_dir / "metadata.json"

    # Save model binary
    joblib.dump(model, model_path)

    # Prepare metadata
    data_hash = compute_data_hash(data_df) if data_df is not None else "unknown"

    try:
        import lightgbm
        lgb_ver = lightgbm.__version__
    except Exception:
        lgb_ver = "unknown"

    try:
        import sklearn
        sklearn_ver = sklearn.__version__
    except Exception:
        sklearn_ver = "unknown"

    try:
        import shap
        shap_ver = shap.__version__
    except Exception:
        shap_ver = "unknown"

    metadata = {
        "model_name": name,
        "version": version,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "features": features,
        "feature_count": len(features),
        "metrics": metrics,
        "data_hash": data_hash,
        "python_version": sys.version.split()[0],
        "library_versions": {
            "lightgbm": lgb_ver,
            "scikit-learn": sklearn_ver,
            "shap": shap_ver,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    logger.info(f"Saved model artifact [{name}:{version}] to {target_dir}")
    return target_dir


def load_model_artifact(
    name: str,
    version: Optional[str] = None,
    base_dir: Optional[Path] = None,
) -> tuple[Any, dict[str, Any]]:
    """Load model artifact and metadata from disk."""
    root = base_dir or MODELS_DIR
    model_dir = root / name

    if not model_dir.exists():
        raise FileNotFoundError(f"Model directory does not exist: {model_dir}")

    if version is None:
        # Find latest version subfolder
        subdirs = [d for d in model_dir.iterdir() if d.is_dir()]
        if not subdirs:
            raise FileNotFoundError(f"No versions found in {model_dir}")
        target_dir = sorted(subdirs, key=lambda d: d.name)[-1]
    else:
        target_dir = model_dir / version

    model_path = target_dir / "model.joblib"
    meta_path = target_dir / "metadata.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Missing model binary at {model_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing metadata at {meta_path}")

    model = joblib.load(model_path)
    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return model, metadata
