"""Unified Cloud Startup Script for AeroPulse.

Handles:
1. Waiting for PostgreSQL connection readiness
2. Database schema migration (Alembic)
3. Synthetic fleet data generation (if not already seeded)
4. Model training (if models not present)
5. Predictive engine initial scoring
6. Starting Uvicorn API server on the platform-assigned PORT
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


def run_cmd(cmd: list[str], env: dict, check: bool = True) -> int:
    print(f"\n[Cloud Init] Running: {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR), env=env)
    if check and res.returncode != 0:
        print(f"[Cloud Init] Warning: Command failed with exit code {res.returncode}")
    return res.returncode


def wait_for_database(env: dict, max_retries: int = 15, delay_sec: int = 4) -> bool:
    """Poll database connection until PostgreSQL is online and accepting connections."""
    print("\n--- [Pre-flight] Checking Database Connection ---")
    check_code = (
        "import asyncio, sys; "
        "from app.core.database import check_database_connection; "
        "res = asyncio.run(check_database_connection()); "
        "sys.exit(0 if res.get('status') == 'connected' else 1)"
    )

    for attempt in range(1, max_retries + 1):
        res = subprocess.run(
            [sys.executable, "-c", check_code],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            print(f"[Cloud Init] Database connected successfully on attempt {attempt}!")
            return True
        print(f"[Cloud Init] Waiting for database to initialize (attempt {attempt}/{max_retries})...")
        time.sleep(delay_sec)

    print("[Cloud Init] Database connection timed out. Proceeding with migrations anyway...")
    return False


def main() -> None:
    print("=" * 65)
    print("AeroPulse Cloud Platform Initialization")
    print("=" * 65)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    # 1. Wait for database readiness (Render database provision delay)
    wait_for_database(env)

    # 2. Run Alembic database migrations
    print("\n--- [1/4] Applying Database Migrations (Alembic) ---")
    run_cmd([sys.executable, "-m", "alembic", "upgrade", "head"], env=env, check=False)

    # 3. Seed synthetic fleet data (seed 42)
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

    # 4. Train ML Models if not present
    models_dir = ROOT_DIR / "models" / "failure_risk"
    skip_train = os.environ.get("SKIP_TRAIN", "false").lower() == "true"
    if not models_dir.exists() and not skip_train:
        print("\n--- [3/4] Training Offline ML Pipeline ---")
        run_cmd([sys.executable, "-m", "ml.train", "--all"], env=env, check=False)
    else:
        print("\n--- [3/4] ML models ready (training skipped) ---")

    # 5. Run Predictive Maintenance Scoring Engine
    print("\n--- [4/4] Executing Predictive Scoring Engine ---")
    run_cmd([sys.executable, "-m", "app.engine.cli"], env=env, check=False)

    # 6. Start Uvicorn Server (must bind to $PORT for Render health checks)
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
