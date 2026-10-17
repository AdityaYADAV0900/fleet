import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def test_alembic_upgrade_downgrade_cycle(test_db_url: str) -> None:
    """Verify that alembic upgrade head -> downgrade base -> upgrade head succeeds cleanly."""
    env = os.environ.copy()
    env["TEST_DATABASE_URL"] = test_db_url
    env["DATABASE_URL"] = test_db_url

    # 1. Downgrade to base first in case tables exist
    res_down_initial = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_down_initial.returncode == 0, f"Initial downgrade failed:\n{res_down_initial.stderr}"

    # 2. Upgrade to head
    res_up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_up.returncode == 0, f"Upgrade to head failed:\n{res_up.stderr}"

    # 3. Downgrade back to base
    res_down = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_down.returncode == 0, f"Downgrade to base failed:\n{res_down.stderr}"

    # 4. Re-upgrade to head so database is ready
    res_up_final = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(ROOT_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert res_up_final.returncode == 0, f"Final upgrade failed:\n{res_up_final.stderr}"
