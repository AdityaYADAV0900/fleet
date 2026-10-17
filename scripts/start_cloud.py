"""Unified Cloud Startup Script for AeroPulse.

Handles:
1. Database schema migration (Alembic)
2. Synthetic fleet data generation (if not already seeded)
3. Model training (if models not present)
4. Predictive engine initial scoring
5. Starting Uvicorn API server on the platform-assigned PORT
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


def run_cmd(cmd: list[str], env: dict, check: bool = True) -> int:
    print(f"\n[Cloud Init] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env)
    if check and res.returncode != 0:
        print(f"[Cloud Init] ERROR: Command failed with exit code {res.returncode}")
        sys.exit(res.returncode)
    return res.returncode


def main() -> None:
    print("=" * 65)
    print("AeroPulse Cloud Platform Initialization")
    print("=" * 65)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    # 1. Run Alembic database migrations
    print("\n--- [1/4] Applying Database Migrations (Alembic) ---")
    run_cmd([sys.executable, "-m", "alembic", "upgrade", "head"], env=env)

    # 2. Seed synthetic fleet data (seed 42)
    skip_seed = os.environ.get("SKIP_SEED", "false").lower() == "true"
    if not skip_seed:
        print("\n--- [2/4] Seeding Synthetic Fleet Data (seed 42) ---")
        run_cmd(
            [sys.executable, "-m", "data_gen", "generate", "--seed", "42"],
            env=env,
            check=False,
        )
    else:
        print("\n--- [2/4] Skipping synthetic data seeding (SKIP_SEED=true) ---")

    # 3. Train ML Models if not present
    model_file = ROOT_DIR / "models" / "lgb_failure_risk.joblib"
    skip_train = os.environ.get("SKIP_TRAIN", "false").lower() == "true"
    if not model_file.exists() and not skip_train:
        print("\n--- [3/4] Training Offline ML Pipeline ---")
        run_cmd([sys.executable, "-m", "ml.train", "--all"], env=env, check=False)
    else:
        print("\n--- [3/4] ML models ready (training skipped) ---")

    # 4. Run Predictive Maintenance Scoring Engine
    print("\n--- [4/4] Executing Predictive Scoring Engine ---")
    run_cmd([sys.executable, "-m", "app.engine.cli"], env=env, check=False)

    # 5. Start Uvicorn Server
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print("\n" + "=" * 65)
    print(f"[Cloud Live] Starting FastAPI Uvicorn on {host}:{port}")
    print("=" * 65)

    server_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        host,
        "--port",
        str(port),
    ]
    subprocess.run(server_cmd, cwd=str(BACKEND_DIR), env=env)


if __name__ == "__main__":
    main()
