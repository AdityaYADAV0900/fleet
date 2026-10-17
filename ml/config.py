"""ML Configuration and parameters for Phase 4."""

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Default demonstration seed
DEFAULT_SEED = 42

# Default temporal splits (3 full years of synthetic data: 2023 - 2025)
TRAIN_START_DATE = date(2023, 1, 1)
TRAIN_END_DATE = date(2024, 6, 30)  # 18 months

VAL_START_DATE = date(2024, 7, 1)
VAL_END_DATE = date(2024, 12, 31)  # 6 months

TEST_START_DATE = date(2025, 1, 1)
TEST_END_DATE = date(2025, 12, 31)  # 12 months

# Modeling parameters
FAILURE_HORIZON_DAYS_PRIMARY = 14
FAILURE_HORIZON_DAYS_SECONDARY = 30
RUL_MAX_DAYS_TARGET = 60.0

ROLLING_WINDOWS = [5, 20]  # flights


@dataclass
class MLConfig:
    seed: int = DEFAULT_SEED
    train_end: date = TRAIN_END_DATE
    val_end: date = VAL_END_DATE
    test_end: date = TEST_END_DATE
    models_dir: Path = MODELS_DIR
    reports_dir: Path = REPORTS_DIR
    figures_dir: Path = FIGURES_DIR
    horizon_days: int = FAILURE_HORIZON_DAYS_PRIMARY
    rul_max_days: float = RUL_MAX_DAYS_TARGET
    model_version: str = "v1"
    rolling_windows: list[int] = field(default_factory=lambda: [5, 20])
