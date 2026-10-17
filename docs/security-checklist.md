# Security & Access Control Checklist

**Project:** Integrated Predictive Maintenance & Fleet Availability Platform (PS 26249)  
**Classification:** Prototype / Synthetic Data Decision-Support System  
**Deployment Context:** Designed for local evaluation and native air-gapped / on-premise military network readiness.

---

## 1. System Scope & Operational Boundary

- [x] **Decision-Support Only:** Functionality is strictly confined to maintenance diagnostics, prognostic health indicators, fleet availability simulation, inventory planning, and work-order scheduling.
- [x] **No Operational / Tactical Functions:** Zero support for combat operations, weapons systems, targeting, mission planning, or tactical command.
- [x] **Synthetic Data Boundary:** All tail numbers, component serials, sensor signals, and flight logs are synthetically generated. No real airframe logs or classified data are processed or stored.
- [x] **Air-Gap Readiness:** The architecture requires no external internet calls or public SaaS dependencies during inference, training, or runtime. Models and assets run entirely on the local host.

---

## 2. Authentication Architecture

- [x] **Token Standard:** JSON Web Tokens (JWT) using `HS256` (HMAC with SHA-256) signature algorithm.
- [x] **Bearer Scheme:** Standard `Authorization: Bearer <token>` HTTP header enforcement across all protected endpoints.
- [x] **Expiration Lifetimes:** Configurable token time-to-live (`JWT_EXPIRE_MINUTES`, default 480 minutes). Expired tokens are immediately rejected with `401 Unauthorized`.
- [x] **Credential Hashing:** Passwords stored as salted cryptographic hashes using standard hashing libraries (`passlib` / `bcrypt`), preventing plaintext leakages.
- [x] **Session Validation:** Endpoint `GET /api/v1/auth/me` validates token cryptographic validity, signature integrity, and active user database existence on every session check.

---

## 3. Role-Based Access Control (RBAC) Matrix

The system enforces three distinct operational personas via FastAPI dependency injection (`require_roles`):

| Resource / Endpoint | HTTP Method | Commander (`C`) | Planner (`P`) | Technician (`T`) | Enforcement Mechanism |
|---|---|:---:|:---:|:---:|---|
| **Fleet Dashboard** (`/fleet/*`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Aircraft Detail** (`/aircraft/*`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Component Health** (`/components/*`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Predictive Queue** (`/advisories`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Advisory Transitions** (`/advisories/{id}`) | `PATCH` | ✅ Accept/Schedule | ✅ Accept/Schedule | ❌ **403 Forbidden** | `require_roles("commander", "planner")` |
| **Work Orders List** (`/work-orders`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Create Work Order** (`/work-orders`) | `POST` | ✅ Create | ✅ Create | ❌ **403 Forbidden** | `require_roles("commander", "planner")` |
| **Spares Inventory** (`/inventory/*`) | `GET` | ✅ Read | ✅ Read | ✅ Read | `get_current_user` |
| **Run Availability What-If** (`/scenarios/run`) | `POST` | ✅ Execute | ✅ Execute | ❌ **403 Forbidden** | `require_roles("commander", "planner")` |
| **Scoring Job Engine** (`/engine/run`) | `POST` | ✅ Trigger | ✅ Trigger | ❌ **403 Forbidden** | `require_roles("commander", "planner")` |
| **Sensor Ingestion** (`/ingest/sensor-readings`)| `POST` | ✅ Ingest | ✅ Ingest | ❌ **403 Forbidden** | `require_roles("commander", "planner")` |
| **System Health** (`/health`) | `GET` | ✅ Public | ✅ Public | ✅ Public | Unauthenticated liveness probe |

---

## 4. Input Validation & Injection Prevention

- [x] **Strict Pydantic v2 Typing:** All incoming request bodies and query parameters validate against strongly-typed Pydantic models. Malformed payloads return `422 Unprocessable Content`.
- [x] **Numeric & Range Boundaries:**
  - Probability / risk thresholds constrained to `[0.0, 1.0]`.
  - Pagination limits bounded (`page_size` max 200 or 500).
  - Date inputs validated to standard ISO-8601 (`YYYY-MM-DD`).
- [x] **SQL Injection Defense:** Complete reliance on SQLAlchemy 2.0 async ORM and asyncpg parameterized queries. Zero raw string concatenation in SQL queries.
- [x] **Safe Model Deserialization:** Local disk model artifacts loaded strictly from designated `models/` directory using validated internal loader pipelines.

---

## 5. Secrets Management & Environment Isolation

- [x] **No Hardcoded Secrets:** Credentials, keys, and connection strings load from `.env` via `pydantic-settings`.
- [x] **Version Control Exclusions:** `.env`, `.venv`, local `data/`, model artifacts, and test database instances are explicitly registered in `.gitignore`.
- [x] **Database Segregation:**
  - Production / Demo database: `fleetmaint`
  - Automated test database: `fleetmaint_test`
  - Automated tests execute exclusively against `TEST_DATABASE_URL` to prevent accidental mutation of demonstration data.
- [x] **CORS Origin Restriction:** Browser cross-origin access restricted to configured frontend hosts (`CORS_ORIGINS`, e.g., `http://localhost:5173`).

---

## 6. Auditability & Workflow Integrity

- [x] **Mandatory Dismissal Rationale:** Advisory status transitions to `dismissed` strictly require a non-empty `reason` string for traceability.
- [x] **Finite State Machine Enforcement:** Advisory state transitions follow a strict directed graph (`proposed` → `accepted` / `dismissed` → `scheduled` → `completed`). Arbitrary state skipping is rejected.
- [x] **Structured Logging:** Authentication events, batch scoring operations, and scenario simulations produce structured logs with timestamps and contextual identifiers.
