# Data Dictionary

**Integrated Predictive Maintenance & Fleet Availability Platform**  
*Hackathon Problem Statement 26249: Air Power - Predictive Maintenance & Fleet Availability*

> [!NOTE]  
> **Synthetic Data Disclaimer:** All data models, table schemas, and stored records represent generic, synthetic equipment and operational profiles (e.g., "Generic Twin-Engine Transport", tail codes like `AC-017`). They do not represent real military airframes, proprietary weapon systems, or classified maintenance procedures.

> [!IMPORTANT]  
> **ML Data Boundary:** The `simulation_truth` table contains latent synthetic health states. It is strictly intended for simulation evaluation, scoring validation, and demonstration verification. **It MUST NEVER be used as a training feature or label in any machine learning model pipeline.**

---

## 1. Entity-Relationship Overview

```
systems (1) ──< component_types (M) ──< components (M) >── (1) aircraft
                                              │
                      ┌───────────────────────┼────────────────────────┐
                      │                       │                        │
               sensor_readings           fault_events          maintenance_events
                      │                                                │
                   flights >──────────────────────────────────── aircraft
                      │
               anomaly_scores
                      │
                 predictions >── advisories ──> work_orders ──> agencies
                                      │              │
                                    alerts    inventory_transactions
                                                     │
                                                 inventory >── spare_parts
```

---

## 2. Table Specifications by Domain

### 2.1 Fleet Domain

#### `systems`
High-level functional system grouping of the aircraft (e.g., Propulsion, Hydraulics, Avionics, Electrical, Fuel, Landing Gear, ECS).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `system_id` | VARCHAR(50) | PK | Unique identifier for the aircraft system (e.g., `SYS-PROP`, `SYS-HYD`). |
| `name` | VARCHAR(100) | NOT NULL | Human-readable system name. |

---

#### `component_types`
Catalog of component specifications, engineering design limits, and base reliability parameters.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `component_type_id` | VARCHAR(50) | PK | Unique identifier for the component type (e.g., `CT-HYD-PUMP`). |
| `system_id` | VARCHAR(50) | FK (`systems.system_id`, ON DELETE CASCADE), NOT NULL | Owning functional system. |
| `name` | VARCHAR(100) | NOT NULL | Name of the component type (e.g., "Main Hydraulic Pump"). |
| `criticality` | INTEGER | NOT NULL, CHECK (1..5) | Operational criticality score from 1 (lowest) to 5 (mission critical). |
| `design_life_hours` | FLOAT | NOT NULL, CHECK (> 0) | Rated operational life in flight hours before overhaul or retirement. |
| `mtbf_hours` | FLOAT | NOT NULL, CHECK (> 0) | Mean Time Between Failures baseline in flight hours. |
| `part_number` | VARCHAR(50) | NOT NULL | Standard catalog part number (e.g., `HYD-114`). |
| `is_repairable` | BOOLEAN | NOT NULL, DEFAULT TRUE | Indicates whether the component is repairable/rotable or consumable. |

---

#### `aircraft`
Individual airframe entity representing an aircraft within the fleet.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `aircraft_id` | VARCHAR(50) | PK | Unique identifier for the aircraft (e.g., `AC-001`, `AC-017`). |
| `tail_code` | VARCHAR(50) | UNIQUE, NOT NULL | Operational tail number/code displayed on the airframe. |
| `type_code` | VARCHAR(50) | NOT NULL | Generic airframe designation (e.g., `Generic-Twin-Engine-Transport`). |
| `commissioned_date` | DATE | NOT NULL | Induction / commissioning date of the aircraft into fleet service. |
| `total_flight_hours`| FLOAT | NOT NULL, DEFAULT 0.0, CHECK (>= 0) | Cumulative flight hours accumulated by the airframe. |
| `total_cycles` | INTEGER | NOT NULL, DEFAULT 0, CHECK (>= 0) | Cumulative flight cycles / sorties completed. |
| `base_id` | VARCHAR(50) | NULLABLE | Current operating station or home base identifier. |

---

#### `components`
Specific physical, serialized instances of components installed on airframes or stocked.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `component_id` | VARCHAR(50) | PK | Unique component instance identifier (e.g., `CMP-001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE SET NULL), NULLABLE | Current airframe where installed (null if uninstalled in depot/storage). |
| `component_type_id`| VARCHAR(50)| FK (`component_types.component_type_id`, ON DELETE RESTRICT), NOT NULL | Type specification of this physical unit. |
| `serial_no` | VARCHAR(50) | UNIQUE, NOT NULL | Manufacturer physical serial number. |
| `installed_date` | DATE | NULLABLE | Date installed on the current aircraft. |
| `hours_at_install` | FLOAT | NOT NULL, DEFAULT 0.0, CHECK (>= 0) | Airframe flight hours at time of component installation. |
| `hours_since_new` | FLOAT | NOT NULL, DEFAULT 0.0, CHECK (>= 0) | Cumulative operational hours accumulated by this physical component. |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'installed', CHECK ('installed', 'in_stock', 'under_repair', 'scrapped') | Lifecycle operational status. |

---

#### `aircraft_daily_status`
Historical and daily availability log tracking the single official state of each aircraft per calendar day.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | Surrogate primary key. |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Airframe identifier. |
| `date` | DATE | NOT NULL | Operational calendar date. |
| `status` | VARCHAR(50) | NOT NULL, CHECK ('Available', 'Scheduled Maintenance', 'Unscheduled Repair', 'Awaiting Spares', 'Awaiting Workshop') | Standard fleet availability status classification. |
| `reason` | TEXT | NULLABLE | Human or automated narrative explaining non-availability cause. |
| `recorded_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp when status was logged. |

**Indexes & Keys:**
- `UNIQUE(aircraft_id, date)`
- `INDEX(aircraft_id, date)`

---

### 2.2 Sensors & Operations Domain

#### `flights`
Sorties and flight missions executed by fleet aircraft.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `flight_id` | VARCHAR(50) | PK | Unique flight sortie record ID (e.g., `FL-00001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Airframe that performed the sortie. |
| `date` | DATE | NOT NULL | Date sortie took place. |
| `duration_hours`| FLOAT | NOT NULL, CHECK (> 0) | Flight duration in hours. |
| `cycles` | INTEGER | NOT NULL, DEFAULT 1, CHECK (>= 0) | Flight cycles (takeoff/landing) incurred. |
| `ambient_temp_c`| FLOAT | NULLABLE | Mean ambient outside air temperature in Celsius. |
| `altitude_band` | VARCHAR(50) | NULLABLE | Flight regime / cruising altitude band (e.g., `Low`, `Medium`, `High`). |
| `load_factor` | FLOAT | NULLABLE, CHECK (load_factor IS NULL OR load_factor >= 0) | Average aircraft payload/stress factor during flight. |

**Indexes:**
- `INDEX(aircraft_id, date)`

---

#### `sensor_readings`
Post-flight summary statistics aggregated per monitored component parameter.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `reading_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `flight_id` | VARCHAR(50) | FK (`flights.flight_id`, ON DELETE CASCADE), NOT NULL | Associated flight. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Component being monitored. |
| `parameter` | VARCHAR(50) | NOT NULL | Parameter name (e.g., `hydraulic_pressure`, `oil_temp`, `vibration`). |
| `mean` | FLOAT | NOT NULL | Mean value recorded during sortie. |
| `max` | FLOAT | NOT NULL | Maximum peak recorded during sortie. |
| `min` | FLOAT | NOT NULL | Minimum value recorded during sortie. |
| `std` | FLOAT | NOT NULL | Standard deviation across the sortie. |
| `quality_flag` | VARCHAR(20) | NOT NULL, DEFAULT 'valid', CHECK ('valid', 'dropout', 'stuck', 'drift', 'spike', 'missing') | Data quality and sensor fidelity indicator. |

**Indexes:**
- `INDEX(component_id, flight_id)`
- `INDEX(flight_id)`

---

#### `fault_events`
Exceedance occurrences, Built-In-Test (BIT) discrete fault codes, and snag reports.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | VARCHAR(50) | PK | Unique event identifier (e.g., `EVT-00001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Aircraft where fault occurred. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Affected component. |
| `timestamp` | TIMESTAMPTZ | NOT NULL | Exact time of fault registration. |
| `fault_code` | VARCHAR(50) | NOT NULL | Standardized diagnostic fault code (e.g., `FC-HYD-041`). |
| `severity` | VARCHAR(20) | NOT NULL, CHECK ('low', 'medium', 'high', 'critical') | Severity classification. |
| `description` | TEXT | NOT NULL | Technical description of the fault condition. |
| `source` | VARCHAR(50) | NOT NULL, DEFAULT 'BIT' | Diagnostic telemetry source (e.g., `BIT`, `pilot_log`, `ground_test`). |

**Indexes:**
- `INDEX(aircraft_id, timestamp)`
- `INDEX(component_id, timestamp)`

---

### 2.3 Maintenance Domain

#### `agencies`
Maintenance entities, line squadrons, workshops, and base depots.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `agency_id` | VARCHAR(50) | PK | Unique agency identifier (e.g., `AG-LINE-01`, `AG-DEPOT`). |
| `name` | VARCHAR(100) | NOT NULL | Agency name (e.g., "Line Maintenance Squadron 1", "Central Depot"). |
| `level` | VARCHAR(50) | NOT NULL, CHECK ('line', 'base', 'depot') | Maintenance echelon level. |
| `bays` | INTEGER | NOT NULL, CHECK (>= 1) | Physical hangar maintenance bays available. |
| `capacity_hours_per_day` | FLOAT | NOT NULL, CHECK (> 0) | Total labor man-hour capacity available per working day. |
| `avg_turnaround_days` | FLOAT | NOT NULL, CHECK (> 0) | Benchmark turnaround time in days for standard jobs. |

---

#### `scheduled_tasks`
Scheduled preventive inspection intervals and compliance tracking per aircraft.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `task_id` | VARCHAR(50) | PK | Unique scheduled task ID (e.g., `ST-0001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Assigned aircraft. |
| `task_name` | VARCHAR(100) | NOT NULL | Compliance task title (e.g., "100-Hour Hydraulic Servicing"). |
| `interval_hours`| FLOAT | NOT NULL, CHECK (> 0) | Maximum flight hours allowable between inspections. |
| `last_done_hours`| FLOAT | NOT NULL, DEFAULT 0.0, CHECK (>= 0) | Aircraft total hours when last performed. |
| `due_hours` | FLOAT | NOT NULL, CHECK (>= 0) | Next aircraft total hours when task must be complied with. |
| `due_date` | DATE | NULLABLE | Calendar limit date if dual-interval task. |

---

#### `work_orders`
Official maintenance execution work orders dispatched to repair agencies.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `wo_id` | VARCHAR(50) | PK | Unique work order ID (e.g., `WO-0001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Subject aircraft. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE SET NULL), NULLABLE | Target component (if component-specific). |
| `advisory_id` | VARCHAR(50) | NULLABLE | Originating predictive maintenance advisory (if initiated by ML). |
| `agency_id` | VARCHAR(50) | FK (`agencies.agency_id`, ON DELETE RESTRICT), NOT NULL | Assigned maintenance agency or workshop. |
| `opened` | TIMESTAMPTZ | NOT NULL | Timestamp when work order was created. |
| `planned_start`| TIMESTAMPTZ | NULLABLE | Planned schedule start time. |
| `actual_start` | TIMESTAMPTZ | NULLABLE | Actual hangar bay induction time. |
| `promised_done`| TIMESTAMPTZ | NULLABLE | Agency committed completion target. |
| `actual_done` | TIMESTAMPTZ | NULLABLE | Actual completion and return-to-service time. |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'open', CHECK ('open', 'in_progress', 'awaiting_spares', 'awaiting_agency', 'completed', 'cancelled') | Current execution state. |
| `priority` | VARCHAR(10) | NOT NULL, DEFAULT 'P2', CHECK ('P1', 'P2', 'P3', 'P4') | Priority rating (P1 = emergency grounding, P4 = routine). |
| `delay_reason` | TEXT | NULLABLE | Explanation of delays (e.g., awaiting parts, bay conflict). |

**Indexes:**
- `INDEX(status, agency_id)`
- `INDEX(aircraft_id)`

---

#### `maintenance_events`
Discrete maintenance interventions performed on an airframe or component.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `event_id` | VARCHAR(50) | PK | Unique maintenance event ID (e.g., `ME-0001`). |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NOT NULL | Airframe serviced. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE SET NULL), NULLABLE | Component replaced or repaired. |
| `type` | VARCHAR(50) | NOT NULL, CHECK ('scheduled', 'unscheduled', 'inspection') | Maintenance classification type. |
| `start` | TIMESTAMPTZ | NOT NULL | Maintenance initiation time. |
| `end` | TIMESTAMPTZ | NULLABLE, CHECK ("end" IS NULL OR "end" >= "start") | Maintenance completion time. |
| `action` | VARCHAR(50) | NOT NULL, CHECK ('replace', 'repair', 'inspect', 'defer') | Engineering action taken. |
| `labor_hours` | FLOAT | NOT NULL, DEFAULT 0.0, CHECK (>= 0) | Total labor man-hours expended. |
| `work_order_id`| VARCHAR(50) | FK (`work_orders.wo_id`, ON DELETE SET NULL), NULLABLE | Parent work order. |
| `root_cause` | TEXT | NULLABLE | Engineering investigation findings / failure mode cause. |

**Indexes:**
- `INDEX(aircraft_id, start)`
- `INDEX(component_id, start)`

---

### 2.4 Spares & Inventory Domain

#### `spare_parts`
Master inventory parts catalog for line-replaceable units, sub-assemblies, and consumables.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `part_number` | VARCHAR(50) | PK | Unique standard part number (e.g., `HYD-114`). |
| `description` | VARCHAR(200)| NOT NULL | Comprehensive technical part description. |
| `criticality` | INTEGER | NOT NULL, CHECK (1..5) | Essentiality code from 1 to 5. |
| `unit_cost` | FLOAT | NOT NULL, CHECK (>= 0) | Standard acquisition / replacement unit cost. |
| `lead_time_days`| INTEGER | NOT NULL, CHECK (>= 0) | Supplier procurement lead time in days. |
| `reorder_level`| INTEGER | NOT NULL, CHECK (>= 0) | Inventory minimum threshold triggering reorder requisition. |

---

#### `inventory`
Current stock balance, reserved quantities, and replenishments per stocking warehouse/base.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `inventory_id` | INTEGER | PK, AUTOINCREMENT | Surrogate primary key. |
| `part_number` | VARCHAR(50) | FK (`spare_parts.part_number`, ON DELETE CASCADE), NOT NULL | Catalog part number. |
| `location_id` | VARCHAR(50) | NOT NULL | Stocking location / supply depot ID (e.g., `BASE-MAIN`, `DEPOT-01`). |
| `on_hand` | INTEGER | NOT NULL, DEFAULT 0, CHECK (>= 0) | Unreserved physical stock immediately available on shelf. |
| `reserved` | INTEGER | NOT NULL, DEFAULT 0, CHECK (>= 0) | Stock reserved for scheduled work orders. |
| `on_order` | INTEGER | NOT NULL, DEFAULT 0, CHECK (>= 0) | Quantity in transit or ordered on purchase contracts. |
| `expected_receipt_date` | DATE | NULLABLE | Projected delivery date for on-order stock. |

**Indexes & Keys:**
- `UNIQUE(part_number, location_id)`
- `INDEX(part_number, location_id)`

---

#### `inventory_transactions`
Material movement journal recording consumption, replenishments, and returns.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `txn_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `part_number` | VARCHAR(50) | FK (`spare_parts.part_number`, ON DELETE CASCADE), NOT NULL | Part being moved. |
| `date` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp of transaction. |
| `qty` | INTEGER | NOT NULL | Quantity moved (positive for receipts, negative for issues). |
| `type` | VARCHAR(50) | NOT NULL, CHECK ('issue', 'receipt', 'repair-return', 'adjustment') | Movement classification. |
| `work_order_id`| VARCHAR(50) | FK (`work_orders.wo_id`, ON DELETE SET NULL), NULLABLE | Work order demanding the part (if issue). |

**Indexes:**
- `INDEX(part_number, date)`

---

### 2.5 Platform & Decision Support Domain

#### `users`
Authenticated system users and role assignments.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | INTEGER | PK, AUTOINCREMENT | User identifier. |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | Login username. |
| `password_hash`| VARCHAR(255)| NOT NULL | Secure salted cryptographic password hash. |
| `role` | VARCHAR(50) | NOT NULL, CHECK ('commander', 'planner', 'technician') | Role-based access control tier. |

---

#### `simulation_truth`
> [!CAUTION]  
> **GROUND TRUTH TABLE FOR EVALUATION ONLY - DO NOT USE FOR MODEL TRAINING.**  
> Contains synthetic hidden physical health variables generated by the data generator.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `truth_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Target component. |
| `date` | DATE | NOT NULL | Date of true health state evaluation. |
| `true_health` | FLOAT | NOT NULL, CHECK (0.0..1.0) | True latent health index (1.0 = brand new, 0.0 = hard failure). |
| `degradation_phase` | VARCHAR(50) | NULLABLE | Phase tag (e.g., `linear_wear`, `exponential_crack`, `sudden_shock`). |
| `is_failed` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether true failure occurred on this day. |

**Indexes:**
- `INDEX(component_id, date)`

---

#### `anomaly_scores`
Unsupervised condition monitoring anomaly scores from residual regressors and Isolation Forest models.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `score_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Component evaluated. |
| `flight_id` | VARCHAR(50) | FK (`flights.flight_id`, ON DELETE CASCADE), NOT NULL | Sortie evaluated. |
| `score` | FLOAT | NOT NULL | Normalized anomaly score (higher indicates greater abnormality). |
| `top_parameters` | JSON | NULLABLE | Top contributing sensor residuals with z-scores/sigma deviations. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Inference execution timestamp. |

**Indexes:**
- `INDEX(component_id, flight_id)`

---

#### `predictions`
Supervised ML inference outputs: failure probability within 14 and 30 days and Remaining Useful Life (RUL) quantiles.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `prediction_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Subject component. |
| `as_of_date` | DATE | NOT NULL | Cutoff evaluation date for features used. |
| `risk_14d` | FLOAT | NOT NULL, CHECK (0.0..1.0) | Calibrated probability of failure occurring within 14 days. |
| `risk_30d` | FLOAT | NOT NULL, CHECK (0.0..1.0) | Calibrated probability of failure occurring within 30 days. |
| `rul_p10` | FLOAT | NOT NULL | 10th percentile conservative estimate of remaining days. |
| `rul_p50` | FLOAT | NOT NULL | 50th percentile (median) estimate of remaining days. |
| `rul_p90` | FLOAT | NOT NULL | 90th percentile optimistic estimate of remaining days. |
| `model_version` | VARCHAR(50) | NOT NULL | Model artifact version identifier used for inference. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Inference execution timestamp. |

**Indexes & Constraints:**
- `UNIQUE(component_id, as_of_date, model_version)`
- `CHECK(rul_p10 <= rul_p50 AND rul_p50 <= rul_p90)`
- `INDEX(component_id, as_of_date DESC)`

---

#### `advisories`
Synthesized decision-support maintenance advisories combining ML risk, spares availability, and bay capacity.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `advisory_id` | VARCHAR(50) | PK | Unique advisory ID (e.g., `ADV-0001`). |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NOT NULL | Subject component. |
| `as_of_date` | DATE | NOT NULL | Advisory baseline date. |
| `priority` | VARCHAR(10) | NOT NULL, CHECK ('P1', 'P2', 'P3', 'P4') | Computed action priority rating. |
| `action` | VARCHAR(100)| NOT NULL | Concrete recommendation (e.g., "Replace within 7 days"). |
| `status` | VARCHAR(50) | NOT NULL, DEFAULT 'proposed', CHECK ('proposed', 'accepted', 'scheduled', 'completed', 'dismissed') | Human-in-the-loop workflow disposition. |
| `dismiss_reason`| TEXT | NULLABLE | Mandatory justification if dismissed by planner/commander. |
| `explanation` | JSON | NULLABLE | Structured factor breakdown (SHAP values, sensor sigmas, stress). |
| `spare_status` | VARCHAR(100)| NULLABLE | Real-time spares check (e.g., "Pump P/N HYD-114, 1 in stock, available"). |
| `expected_downtime_days` | FLOAT | NULLABLE | Estimated days lost if serviced now vs run to failure. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Advisory creation timestamp. |

**Indexes:**
- `INDEX(component_id, as_of_date)`
- `INDEX(status, priority)`

---

#### `twin_snapshots`
Digital twin state snapshots across fleet, aircraft, system, and component nodes for historical replay.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `snapshot_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `node_type` | VARCHAR(50) | NOT NULL, CHECK ('fleet', 'aircraft', 'system', 'component') | Hierarchy level. |
| `node_id` | VARCHAR(50) | NOT NULL | Node key (e.g., `fleet`, `AC-017`, `SYS-HYD`, `CMP-001`). |
| `as_of_date` | DATE | NOT NULL | Replay snapshot date. |
| `health_index` | FLOAT | NOT NULL, CHECK (0.0..100.0) | Criticality-weighted aggregated Health Index score (0-100). |
| `state` | VARCHAR(50) | NOT NULL, CHECK ('Healthy', 'Watch', 'Degraded', 'Critical', 'Failed', 'Under maintenance') | Categorical condition state. |
| `risk` | FLOAT | NULLABLE | Worst-driver component failure probability. |
| `rul_p50` | FLOAT | NULLABLE | Median remaining useful life days. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Snapshot generation timestamp. |

**Indexes:**
- `INDEX(node_id, as_of_date)`

---

#### `alerts`
Real-time operational alerts highlighting threshold excursions, overdue tasks, or spare shortfalls.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `alert_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `type` | VARCHAR(50) | NOT NULL | Alert trigger type (`risk_threshold`, `spare_shortfall`, `overdue_inspection`, `backlog`). |
| `severity` | VARCHAR(20) | NOT NULL, CHECK ('low', 'medium', 'high', 'critical') | Alert severity level. |
| `aircraft_id` | VARCHAR(50) | FK (`aircraft.aircraft_id`, ON DELETE CASCADE), NULLABLE | Associated aircraft (if applicable). |
| `component_id` | VARCHAR(50) | FK (`components.component_id`, ON DELETE CASCADE), NULLABLE | Associated component (if applicable). |
| `advisory_id` | VARCHAR(50) | NULLABLE | Linked advisory ID. |
| `message` | TEXT | NOT NULL | Alert banner notification message. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Timestamp created. |
| `acknowledged` | BOOLEAN | NOT NULL, DEFAULT FALSE | Whether acknowledged by a planner or technician. |

**Indexes:**
- `INDEX(severity, acknowledged)`

---

#### `scenario_runs`
Stored Monte Carlo availability simulator runs comparing alternative maintenance and spare policies.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | VARCHAR(50) | PK | Unique scenario run ID (e.g., `sc_0042`). |
| `type` | VARCHAR(50) | NOT NULL | Scenario type (e.g., `spare_unavailable`, `schedule_maintenance`). |
| `params` | JSON | NOT NULL | Input scenario parameters (part numbers, lead times, capacity deltas). |
| `results` | JSON | NOT NULL | Simulation outputs (baseline vs scenario availability P10/P50/P90, days lost). |
| `seed` | INTEGER | NOT NULL, DEFAULT 42 | Random seed for exact reproducibility. |
| `created_by` | VARCHAR(50) | NULLABLE | Username who executed the simulation. |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Run timestamp. |

---

#### `model_runs`
Audit and lineage log for offline trained model artifacts and performance evaluations.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `run_id` | BIGINT | PK, AUTOINCREMENT | Primary key. |
| `model_name` | VARCHAR(100)| NOT NULL | Name of the model (e.g., `failure_predictor`, `rul_estimator`). |
| `version` | VARCHAR(50) | NOT NULL | Version tag (e.g., `v1.0.0`). |
| `metrics` | JSON | NOT NULL | Test set evaluation metrics (PR-AUC, Brier score, MAE, interval coverage). |
| `trained_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() | Training completion timestamp. |

---

## 3. Summary of Indexes and Integrity Constraints

| Constraint Name | Target Table | Type | Target Columns / Expression |
|---|---|---|---|
| `uq_aircraft_tail_code` | `aircraft` | UNIQUE | `(tail_code)` |
| `uq_components_serial_no` | `components` | UNIQUE | `(serial_no)` |
| `uq_aircraft_daily_status_aircraft_date` | `aircraft_daily_status` | UNIQUE | `(aircraft_id, date)` |
| `uq_inventory_part_location` | `inventory` | UNIQUE | `(part_number, location_id)` |
| `uq_predictions_component_date_version` | `predictions` | UNIQUE | `(component_id, as_of_date, model_version)` |
| `uq_users_username` | `users` | UNIQUE | `(username)` |
| `ix_sensor_readings_component_id_flight_id` | `sensor_readings` | INDEX | `(component_id, flight_id)` |
| `ix_flights_aircraft_id_date` | `flights` | INDEX | `(aircraft_id, date)` |
| `ix_aircraft_daily_status_aircraft_date` | `aircraft_daily_status` | INDEX | `(aircraft_id, date)` |
| `ix_predictions_component_as_of_date` | `predictions` | INDEX | `(component_id, as_of_date DESC)` |
| `ix_work_orders_status_agency_id` | `work_orders` | INDEX | `(status, agency_id)` |
| `ix_inventory_part_number_location_id` | `inventory` | INDEX | `(part_number, location_id)` |
| `ix_twin_snapshots_node_id_as_of_date` | `twin_snapshots` | INDEX | `(node_id, as_of_date)` |
| `ix_advisories_component_as_of_date` | `advisories` | INDEX | `(component_id, as_of_date)` |
| `ck_inventory_on_hand_non_negative` | `inventory` | CHECK | `on_hand >= 0` |
| `ck_maintenance_events_end_after_start` | `maintenance_events` | CHECK | `"end" IS NULL OR "end" >= "start"` |
| `ck_component_types_criticality_range` | `component_types` | CHECK | `criticality >= 1 AND criticality <= 5` |
| `ck_simulation_truth_health_range` | `simulation_truth` | CHECK | `true_health >= 0.0 AND true_health <= 1.0` |
