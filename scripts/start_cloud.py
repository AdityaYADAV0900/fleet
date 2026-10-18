"""Unified Cloud Startup Script for AeroPulse.

1. Runs database schema migration (Alembic)
2. Spawns background task for idempotent initial seeding & scoring
3. Promptly starts Uvicorn API server on 0.0.0.0:$PORT (< 3 seconds)
"""

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"


def background_seed_and_score(env: dict) -> None:
    """Run initial seeding and scoring in background without blocking server startup."""
    time.sleep(5)  # Let uvicorn bind and healthchecks respond first
    print("\n[Background Init] Checking database state...", flush=True)

    # Check if data already exists to prevent duplicate execution
    check_query = (
        "import asyncio, sys; "
        "from app.core.database import get_session_factory; "
        "from app.models.fleet import Aircraft; "
        "from sqlalchemy import select, func; "
        "async def check(): "
        "    async with get_session_factory()() as s: "
        "        count = (await s.execute(select(func.count()).select_from(Aircraft))).scalar(); "
        "        sys.exit(0 if (count or 0) > 0 else 1); "
        "asyncio.run(check())"
    )

    skip_seed = os.environ.get("SKIP_SEED", "false").lower() == "true"
    if not skip_seed:
        res = subprocess.run(
            [sys.executable, "-c", check_query],
            cwd=str(BACKEND_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            print("[Background Init] Database already contains fleet data. Skipping seeding.", flush=True)
        else:
            cloud_cfg = ROOT_DIR / "data_gen" / "config_cloud.yaml"
            gen_cmd = [sys.executable, "-m", "data_gen", "generate", "--seed", "42"]
            if cloud_cfg.is_file():
                print(f"[Background Init] Fresh database detected. Seeding with cloud-optimized profile ({cloud_cfg.name})...", flush=True)
                gen_cmd.extend(["--config", str(cloud_cfg)])
            else:
                print("[Background Init] Fresh database detected. Seeding synthetic data (seed 42)...", flush=True)

            subprocess.run(
                gen_cmd,
                cwd=str(ROOT_DIR),
                env=env,
                check=False,
            )

    # Run initial scoring run if needed
    skip_score = os.environ.get("SKIP_SCORE", "false").lower() == "true"
    if not skip_score:
        print("[Background Init] Running predictive scoring engine...", flush=True)
        subprocess.run(
            [sys.executable, "-m", "app.engine.cli"],
            cwd=str(ROOT_DIR),
            env=env,
            check=False,
        )
        print("[Background Init] Complete! All initial data and advisories ready.\n", flush=True)


def main() -> None:
    print("=" * 65)
    print("AeroPulse Cloud Platform Startup")
    print("=" * 65)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    # 1. Run Alembic database migrations (fast, ~2s)
    print("\n[Step 1/2] Applying Database Migrations (Alembic)...")
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(ROOT_DIR),
        env=env,
        check=False,
    )

    # 2. Launch background worker for initial seeding & scoring (non-blocking)
    print("\n[Step 2/2] Spawning background worker for fleet data verification...")
    worker = threading.Thread(target=background_seed_and_score, args=(env,), daemon=True)
    worker.start()

    # 3. Promptly start Uvicorn server on PORT (< 3s)
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")
    print("\n" + "=" * 65)
    print(f"[AeroPulse Live] Starting Uvicorn immediately on {host}:{port}")
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
