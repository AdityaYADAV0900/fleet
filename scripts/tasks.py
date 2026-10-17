"""Cross-platform task runner for Integrated Predictive Maintenance & Fleet Availability Platform.

Supported commands:
    demo     One-command reproducible local demo (migrate, seed 42, train, engine, build, serve at :8000).
    dev      Start backend (uvicorn) and frontend (Vite) concurrently with graceful shutdown.
    build    Build frontend production bundle into frontend/dist.
    test     Run backend pytest suite and frontend vitest suite.
    lint     Run backend ruff checks/formatting and frontend eslint.
    seed     Generate synthetic fleet data and populate PostgreSQL database (Phase 2).
    train    Run offline ML training and evaluation pipeline (Phase 4).
    engine   Run predictive maintenance scoring engine to generate advisories and alerts (Phase 5).

Usage:
    python scripts/tasks.py demo
    python scripts/tasks.py dev
    python scripts/tasks.py build
    python scripts/tasks.py test
    python scripts/tasks.py lint
    python scripts/tasks.py migrate
    python scripts/tasks.py seed [--seed 42]
    python scripts/tasks.py train [--all]
    python scripts/tasks.py engine [--as-of YYYY-MM-DD] [--aircraft AC-017]
"""

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"


def get_npm_cmd() -> str:
    """Find the platform-appropriate npm executable."""
    npm_path = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if not npm_path:
        raise FileNotFoundError("Could not find 'npm' executable in PATH. Please install Node.js.")
    return npm_path


def run_dev() -> int:
    """Start uvicorn and Vite dev server concurrently; stop both on Ctrl+C."""
    print("=" * 65)
    print("Starting Integrated Predictive Maintenance Platform (Phase 0 Skeleton)")
    print("=" * 65)
    print("  • Backend:  http://127.0.0.1:8000 (API Docs: http://127.0.0.1:8000/docs)")
    print("  • Frontend: http://localhost:5173")
    print("  • Health:   http://localhost:5173/api/v1/health")
    print("Press Ctrl+C to terminate both servers gracefully.\n")

    npm_cmd = get_npm_cmd()

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    backend_proc = None
    frontend_proc = None

    try:
        # Start backend uvicorn process
        backend_args = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--reload",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
        backend_proc = subprocess.Popen(backend_args, cwd=str(BACKEND_DIR), env=env)

        # Start frontend Vite process
        frontend_args = [npm_cmd, "run", "dev"]
        frontend_proc = subprocess.Popen(
            frontend_args, cwd=str(FRONTEND_DIR), env=os.environ.copy()
        )

        # Monitor processes
        while True:
            b_poll = backend_proc.poll()
            f_poll = frontend_proc.poll()
            if b_poll is not None:
                print(f"\n[Backend] Process exited prematurely with code {b_poll}")
                break
            if f_poll is not None:
                print(f"\n[Frontend] Process exited prematurely with code {f_poll}")
                break
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n[Shutdown] Ctrl+C received. Gracefully stopping servers...")
    finally:
        for name, proc in [("Backend", backend_proc), ("Frontend", frontend_proc)]:
            if proc and proc.poll() is None:
                print(f"[Shutdown] Terminating {name} (PID: {proc.pid})...")
                try:
                    if sys.platform == "win32":
                        # Terminate process tree on Windows
                        subprocess.run(
                            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            check=False,
                        )
                    else:
                        proc.send_signal(signal.SIGTERM)
                    proc.wait(timeout=5)
                except Exception:
                    proc.kill()
        print("[Shutdown] All servers stopped successfully.")

    return 0


def run_test(args: list[str] | None = None) -> int:
    """Run pytest suite, frontend test suite, and optional Playwright e2e."""
    args = args or []
    run_e2e = "--e2e" in args or "--all" in args
    pytest_extra = [a for a in args if a not in ("--e2e", "--all")]

    print("=" * 60)
    print("Running Test Suites (Phase 10 Testing & Validation)")
    print("=" * 60)

    # 1. Backend & ML tests (Unit, API, DB, Data Validation, Regression, Integration)
    print("\n--- [1/2] Running Backend & ML Tests (pytest) ---")
    pytest_cmd = [sys.executable, "-m", "pytest"]
    if pytest_extra:
        pytest_cmd.extend(pytest_extra)
    pytest_res = subprocess.run(pytest_cmd, cwd=str(ROOT_DIR))
    if pytest_res.returncode != 0:
        print(f"\n[FAILED] Backend tests failed with exit code {pytest_res.returncode}")
        return pytest_res.returncode

    # 2. Frontend component & unit tests (vitest)
    print("\n--- [2/2] Running Frontend Tests (vitest) ---")
    npm_cmd = get_npm_cmd()
    frontend_res = subprocess.run([npm_cmd, "test"], cwd=str(FRONTEND_DIR))
    if frontend_res.returncode != 0:
        print(f"\n[FAILED] Frontend tests failed with exit code {frontend_res.returncode}")
        return frontend_res.returncode

    # 3. Optional / flag-triggered Playwright E2E
    if run_e2e:
        print("\n--- [3/3] Running End-to-End Walkthrough (Playwright) ---")
        node_env = os.environ.copy()
        node_env["NODE_PATH"] = str(FRONTEND_DIR / "node_modules")
        e2e_res = subprocess.run([npm_cmd, "run", "test:e2e"], cwd=str(FRONTEND_DIR), env=node_env)
        if e2e_res.returncode != 0:
            print(f"\n[FAILED] Playwright E2E tests failed with exit code {e2e_res.returncode}")
            return e2e_res.returncode

    print("\n" + "=" * 60)
    print("[SUCCESS] All test suites passed!")
    print("=" * 60)
    return 0


def run_lint() -> int:
    """Run ruff checks, format check, and frontend eslint."""
    print("=" * 60)
    print("Running Code Quality and Linter Checks")
    print("=" * 60)

    # 1. Ruff lint
    print("\n--- [1/3] Running Python Linter (ruff check) ---")
    ruff_check = subprocess.run([sys.executable, "-m", "ruff", "check", "."], cwd=str(ROOT_DIR))
    if ruff_check.returncode != 0:
        return ruff_check.returncode

    # 2. Ruff format check
    print("\n--- [2/3] Checking Python Formatting (ruff format --check) ---")
    ruff_fmt = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."], cwd=str(ROOT_DIR)
    )
    if ruff_fmt.returncode != 0:
        return ruff_fmt.returncode

    # 3. Frontend eslint
    print("\n--- [3/3] Running Frontend Linter (eslint) ---")
    npm_cmd = get_npm_cmd()
    eslint_res = subprocess.run([npm_cmd, "run", "lint"], cwd=str(FRONTEND_DIR))
    if eslint_res.returncode != 0:
        return eslint_res.returncode

    print("\n" + "=" * 60)
    print("[SUCCESS] All lint and formatting checks passed!")
    print("=" * 60)
    return 0


def run_migrate(args: list[str] | None = None) -> int:
    """Run Alembic database migrations."""
    print("=" * 60)
    print("Running Database Migrations (Alembic)")
    print("=" * 60)

    alembic_args = [sys.executable, "-m", "alembic"]
    if not args:
        # Default action: upgrade head
        alembic_args.extend(["upgrade", "head"])
    else:
        alembic_args.extend(args)

    print(f"Executing: {' '.join(alembic_args)}\n")
    res = subprocess.run(alembic_args, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print(f"\n[FAILED] Migration failed with exit code {res.returncode}")
        return res.returncode

    # If distinct test database is configured, ensure it is also migrated
    test_db = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL_TEST")
    main_db = os.environ.get("DATABASE_URL")
    if test_db and main_db and test_db != main_db:
        print(f"\nApplying migrations to test database: {test_db.split('@')[-1]}")
        test_env = os.environ.copy()
        test_env["DATABASE_URL"] = test_db
        test_env["TEST_DATABASE_URL"] = test_db
        res_test = subprocess.run(alembic_args, cwd=str(ROOT_DIR), env=test_env)
        if res_test.returncode != 0:
            print(f"\n[FAILED] Test database migration failed with exit code {res_test.returncode}")
            return res_test.returncode

    print("\n" + "=" * 60)
    print("[SUCCESS] Database migration completed successfully!")
    print("=" * 60)
    return 0


def run_seed(args: list[str] | None = None) -> int:
    """Run synthetic data generator to seed the database."""
    print("=" * 60)
    print("Seeding Synthetic Fleet Data (data_gen)")
    print("=" * 60)

    gen_args = [sys.executable, "-m", "data_gen", "generate"]
    if args:
        gen_args.extend(args)
    else:
        gen_args.extend(["--seed", "42"])

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    res = subprocess.run(gen_args, cwd=str(ROOT_DIR), env=env)
    if res.returncode != 0:
        print(f"\n[FAILED] Data seeding failed with exit code {res.returncode}")
        return res.returncode
    return 0


def run_train(args: list[str] | None = None) -> int:
    """Run offline ML training and evaluation pipeline (Phase 4)."""
    print("=" * 60)
    print("Running ML Training & Evaluation Pipeline (ml.train)")
    print("=" * 60)

    train_args = [sys.executable, "-m", "ml.train"]
    if args:
        train_args.extend(args)
    else:
        train_args.append("--all")

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    res = subprocess.run(train_args, cwd=str(ROOT_DIR), env=env)
    if res.returncode != 0:
        print(f"\n[FAILED] ML pipeline training failed with exit code {res.returncode}")
        return res.returncode
    return 0


def run_engine(args: list[str] | None = None) -> int:
    """Run predictive maintenance scoring engine to generate advisories and alerts (Phase 5)."""
    print("=" * 60)
    print("Running Predictive Maintenance Engine (app.engine.cli)")
    print("=" * 60)

    engine_args = [sys.executable, "-m", "app.engine.cli"]
    if args:
        engine_args.extend(args)

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    res = subprocess.run(engine_args, cwd=str(ROOT_DIR), env=env)
    if res.returncode != 0:
        print(f"\n[FAILED] Engine batch execution failed with exit code {res.returncode}")
        return res.returncode
    return 0


def run_build_frontend() -> int:
    """Build the frontend production assets into frontend/dist."""
    print("=" * 60)
    print("Building Frontend Production Bundle (Vite)")
    print("=" * 60)
    npm_cmd = get_npm_cmd()
    res = subprocess.run([npm_cmd, "run", "build"], cwd=str(FRONTEND_DIR))
    if res.returncode != 0:
        print(f"\n[FAILED] Frontend production build failed with exit code {res.returncode}")
        return res.returncode
    print("\n[SUCCESS] Frontend production build completed (frontend/dist ready).")
    return 0


def run_demo(args: list[str] | None = None) -> int:
    """One-command reproducible local demo (Phase 11).

    Executes:
      1. Database migrations (migrate)
      2. Seed synthetic fleet data (seed --seed 42)
      3. Train ML models (train --all)
      4. Run predictive maintenance scoring engine (engine)
      5. Build frontend production assets (build)
      6. Start backend serving frontend/dist at http://localhost:8000
    """
    args = args or []
    skip_migrate = "--skip-migrate" in args
    skip_seed = "--skip-seed" in args
    skip_train = "--skip-train" in args
    skip_engine = "--skip-engine" in args
    skip_build = "--skip-build" in args

    port = "8000"
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = args[idx + 1]

    print("=" * 70)
    print("Starting One-Command Reproducible Local Demo (Phase 11)")
    print("Integrated Predictive Maintenance & Fleet Availability Platform")
    print("=" * 70)

    # 1. Run migrations
    if not skip_migrate:
        print("\n--- [Step 1/5] Applying Database Migrations (Alembic) ---")
        rc = run_migrate()
        if rc != 0:
            return rc
    else:
        print("\n--- [Step 1/5] Database migrations skipped (--skip-migrate) ---")

    # 2. Seed synthetic data (seed 42)
    if not skip_seed:
        print("\n--- [Step 2/5] Seeding Synthetic Fleet Data (seed 42) ---")
        rc = run_seed(["--seed", "42"])
        if rc != 0:
            return rc
    else:
        print("\n--- [Step 2/5] Data seeding skipped (--skip-seed) ---")

    # 3. Train ML pipeline
    if not skip_train:
        print("\n--- [Step 3/5] Training ML Pipeline Models ---")
        rc = run_train(["--all"])
        if rc != 0:
            return rc
    else:
        print("\n--- [Step 3/5] ML training skipped (--skip-train) ---")

    # 4. Run scoring engine
    if not skip_engine:
        print("\n--- [Step 4/5] Running Predictive Maintenance Scoring Engine ---")
        rc = run_engine([])
        if rc != 0:
            return rc
    else:
        print("\n--- [Step 4/5] Engine execution skipped (--skip-engine) ---")

    # 5. Build frontend production assets
    if not skip_build:
        print("\n--- [Step 5/5] Building Frontend Production Bundle ---")
        rc = run_build_frontend()
        if rc != 0:
            return rc
    else:
        print("\n--- [Step 5/5] Frontend build skipped (--skip-build) ---")

    # 6. Start the unified demo server
    print("\n" + "=" * 70)
    print(f"AeroPulse Platform Demo Live: http://localhost:{port}")
    print("=" * 70)
    print(f"  • Web Cockpit: http://localhost:{port}")
    print(f"  • API Docs:    http://localhost:{port}/docs")
    print(f"  • Health:      http://localhost:{port}/api/v1/health")
    print("  • Demo Script: docs/demo-script.md (11-step walkthrough)")
    print("  • Quick Login: Click 'Planner' on login page or use demo credentials")
    print("\nPress Ctrl+C to terminate the demo server.\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(BACKEND_DIR) + os.pathsep + str(ROOT_DIR) + os.pathsep + env.get("PYTHONPATH", "")
    )

    server_args = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        port,
    ]

    proc = None
    try:
        proc = subprocess.Popen(server_args, cwd=str(BACKEND_DIR), env=env)
        proc.wait()
    except KeyboardInterrupt:
        print("\n[Shutdown] Ctrl+C received. Gracefully stopping demo server...")
    finally:
        if proc and proc.poll() is None:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                else:
                    proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("[Shutdown] Demo server stopped successfully.")

    return 0


def print_help() -> None:
    print(__doc__)


def main() -> int:
    if len(sys.argv) < 2:
        print_help()
        return 1

    cmd = sys.argv[1].lower()
    extra_args = sys.argv[2:]
    if cmd == "demo":
        return run_demo(extra_args)
    elif cmd == "dev":
        return run_dev()
    elif cmd == "build":
        return run_build_frontend()
    elif cmd == "test":
        return run_test(extra_args)
    elif cmd == "lint":
        return run_lint()
    elif cmd == "migrate":
        return run_migrate(extra_args)
    elif cmd == "seed":
        return run_seed(extra_args)
    elif cmd == "train":
        return run_train(extra_args)
    elif cmd == "engine":
        return run_engine(extra_args)
    elif cmd in ("-h", "--help", "help"):
        print_help()
        return 0
    else:
        print(
            f"Unknown command: '{cmd}'. Supported commands: demo, dev, build, test, lint, migrate, seed, train, engine"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
