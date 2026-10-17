# Native Local Development Setup Guide

**Integrated Predictive Maintenance & Fleet Availability Platform**  
*Problem Statement 26249: Air Power - Predictive Maintenance & Fleet Availability*

This repository is designed to run natively across **Windows**, **macOS**, and **Linux** without any Docker or container virtualization overhead.

---

## 1. Prerequisites

Ensure the following runtimes are installed natively on your workstation:

| Component | Minimum Version | Verification Command |
|---|---|---|
| **Python** | 3.11+ (3.11 - 3.13) | `python --version` (or `python3 --version`) |
| **Node.js** | 20+ LTS | `node --version` |
| **npm** | 10+ | `npm --version` |
| **PostgreSQL** | 16 (or 16+) | `psql --version` |

---

## 2. PostgreSQL Installation & Configuration

### A. Windows Installation
1. Download and install PostgreSQL 16 from the official EDB installer or via `winget`:
   ```powershell
   winget install PostgreSQL.PostgreSQL.16
   ```
2. Verify the Windows Service `postgresql-x64-16` is running:
   ```powershell
   Get-Service *postgres*
   ```
   *(Note: Default port is usually `5432`. If a second version is installed, it may run on `5433`).*

### B. macOS Installation
```bash
brew install postgresql@16
brew services start postgresql@16
```

### C. Linux (Ubuntu / Debian) Installation
```bash
sudo apt update
sudo apt install postgresql-16 postgresql-contrib
sudo systemctl enable --now postgresql
```

### D. Create the Database Role and Databases
Run the provided SQL script using `psql` as the `postgres` superuser:

**Windows (PowerShell / CMD):**
```powershell
& "C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -p 5432 -f database/setup_local.sql
# If your PG16 runs on port 5433, use -p 5433
```

**macOS / Linux:**
```bash
psql -U postgres -p 5432 -f database/setup_local.sql
```

This provisions:
- User role: `fleetmaint` (password: `fleetmaint`)
- Database: `fleetmaint` (application data)
- Database: `fleetmaint_test` (automated test fixtures)

---

## 3. Environment Configuration

Copy the example environment file into `.env`:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Review `.env` and confirm the `DATABASE_URL` matches your local PostgreSQL port:
```env
# Standard port 5432 (or 5433 if configured)
DATABASE_URL=postgresql+asyncpg://fleetmaint:fleetmaint@localhost:5432/fleetmaint
DATABASE_URL_TEST=postgresql+asyncpg://fleetmaint:fleetmaint@localhost:5432/fleetmaint_test

API_HOST=127.0.0.1
API_PORT=8000
ENVIRONMENT=development
CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]
SECRET_KEY=dev_secret_key_fleetmaint_decision_support_phase0
```

---

## 4. Python Virtual Environment Setup

From the repository root:

### Windows:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
```

### macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
```

---

## 5. Frontend Setup

From the repository root:
```bash
cd frontend
npm install
cd ..
```

---

## 6. Running with the Cross-Platform Task Runner

All operational workflows are managed via the standard Python task runner `scripts/tasks.py` without requiring `make` or platform-specific shell scripts:

### A. Start Development Servers (Backend + Frontend)
```bash
python scripts/tasks.py dev
```
- **Backend API**: `http://127.0.0.1:8000`
- **Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **Frontend Dashboard**: `http://localhost:5173`
- *Press `Ctrl+C` to stop both servers cleanly.*

### B. Run Automated Tests
```bash
python scripts/tasks.py test
```
Executes backend `pytest` tests and frontend `vitest` unit tests.

### C. Run Linting and Formatting
```bash
python scripts/tasks.py lint
```
Executes `ruff check`, `ruff format --check`, and frontend `eslint`.

### D. Check Migration Status
```bash
python scripts/tasks.py migrate
```
Prints the schema and migration status (Alembic migrations are configured in Phase 1).

---

## 7. Verification Checklist

1. Open `http://localhost:5173` in your browser.
2. Confirm the top banner displays `[SYNTHETIC DATA ONLY]`.
3. Confirm the status badges show:
   - **FastAPI Backend**: `Backend OK` (green)
   - **PostgreSQL Database**: `Database OK` (green)
4. Confirm `python scripts/tasks.py test` exits with `0` (all tests passed).
5. Confirm `python scripts/tasks.py lint` exits with `0` (all lint checks passed).
