# PS 26249: Integrated Predictive Maintenance & Fleet Availability Platform

**Master plan (v2, no Docker).** Save this file as `docs/plan.md`. Section numbers (§) are referenced by the Antigravity prompts and by `AGENTS.md`, so do not renumber them.

**Environment constraint:** the whole system runs natively on a developer machine: Python virtual environment, Node.js/npm, a locally installed PostgreSQL, and the local filesystem. **Docker, containers and container orchestration are not used or required anywhere.**

**Labels used throughout**
- **[PS]** stated in the problem statement
- **[ASSUMPTION]** a reasonable engineering assumption
- **[REAL DATA]** would need real operational data to settle

**Problem statement (unmodified)**

| Field | Value |
|---|---|
| ID | 26249 |
| Title | Air Power - Predictive Maintenance & Fleet Availability |
| Organization / Department | Ministry of Defence (MoD) / Defence Services Staff College |
| Category / Theme | Software / Transportation & Logistics |
| Problem | Low aircraft availability due to fragmented and largely reactive maintenance practices across the air fleet. Maintenance data from aircraft health-monitoring systems, technical records, spares and maintenance agencies is not adequately integrated, resulting in delayed fault prediction, avoidable aircraft downtime and sub-optimal utilisation of critical assets. |
| Technology opportunity | AI/ML-based predictive maintenance, IoT/aircraft health monitoring, digital twins and an integrated maintenance analytics platform. |

---

# PART A: Understanding the problem

## 1. Problem analysis

### 1.1 The real-world problem
- **[PS]** Availability is low because maintenance is fragmented and mostly reactive. Four data sources are not integrated: health-monitoring systems, technical records, spares, and maintenance agencies.
- **[PS]** Stated consequences: delayed fault prediction, avoidable downtime, sub-optimal asset use.
- **[ASSUMPTION]** An aircraft is grounded for three kinds of reason:
  1. A fault occurs that nobody saw coming.
  2. The fault is known, but the spare is not in stock.
  3. The spare is in stock, but the workshop or agency is backlogged.

  Prediction alone fixes only the first. A credible solution must also cover spares and workshop capacity. This is the central insight of the solution.

### 1.2 Stakeholders [ASSUMPTION]

| Stakeholder | Need |
|---|---|
| Fleet / maintenance commander | Availability today and in 30 days; where the risk is |
| Maintenance planner | Which aircraft to pull, when, in what order |
| Line technician / engineer | Which component to inspect, and why it was flagged |
| Logistics / spares officer | Which spares will be needed; shortfalls |
| Maintenance agency / workshop manager | Incoming workload; turnaround tracking |
| Reliability engineer | Failure trends, MTBF, bad-actor components |

### 1.3 Decisions maintenance personnel face
1. Ground/inspect now or defer.
2. Replace a component early or keep flying.
3. Which scheduled tasks to bundle with an unscheduled one.
4. How to order a backlog when several aircraft need work.
5. Which spares to order or reposition, and when.
6. Which jobs go to the workshop versus in-house.
7. How many aircraft will be available next week or month.

### 1.4 Causes of low availability
Unscheduled failures; conservative fixed-interval replacement that wastes good parts yet misses random failures; waiting for parts; workshop turnaround delays and repeat defects; poor visibility across aircraft, parts and workshop load; clustering of scheduled servicing.

### 1.5 What "fragmented data" means
Each source lives in a separate system, format and ownership: sensor downloads, logbooks, a stores system, agency reports. They use different identifiers and timestamps and have no common key. Nobody can ask "which aircraft have a rising hydraulic-temperature trend, a long-lead-time pump, and a workshop already at capacity?" The solution therefore needs a **unified identifier model** (aircraft -> system -> component -> part number).

### 1.6 Realistic data sources

**Aircraft health-monitoring data**
- Per-flight or per-sortie summaries by parameter: engine temperatures, pressures, vibration, oil pressure/temperature, hydraulic pressure/temperature, bus voltages, fuel flow, cabin/ECS temperatures.
- Exceedance events, fault codes, built-in-test (BIT) messages, operating-condition context (flight hours, altitude band, ambient temperature, load).
- **[ASSUMPTION]** Real systems often download summaries post-flight rather than stream. Simulating per-flight aggregates is more honest than faking high-rate IoT.

**Technical records / logbooks**
- Snag (defect) reports: date, aircraft, system, description, severity.
- Rectification actions; component install/removal history with part and serial numbers.
- Flight hours, cycles, landings; scheduled inspection compliance and due dates; modifications.

**Spares and inventory**
- Part number, description, which components it fits, criticality, unit cost.
- Stock on hand/reserved, reorder level, lead time, supplier/depot.
- Issue/receipt transactions; repairable versus consumable; parts awaiting repair; quantity on order.

**Maintenance agency / workshop**
- Work-order ID, aircraft/component, agency, date received, promised and actual completion, status.
- Workshop capacity (bays, man-hours), turnaround times, teardown findings, repeat-defect flags.

### 1.7 Key KPIs
Fleet availability, aircraft-days lost (split by cause), MTBF, MTTR, maintenance turnaround time, unscheduled-to-scheduled maintenance ratio, backlog (open work orders and man-hours), spares fill rate / stock-outs, repeat-defect rate, predicted-versus-actual failure hit rate, lead time gained (days of warning before failure).

### 1.8 Fleet availability: definition and calculation
**[ASSUMPTION]** The PS does not define it. State this definition explicitly in the pitch.

Each aircraft-day is assigned exactly one state:
- **Available** (fully serviceable)
- **Unavailable, scheduled maintenance**
- **Unavailable, unscheduled repair**
- **Unavailable, awaiting spares**
- **Unavailable, awaiting workshop/agency**
- (Optional, not in MVP) **Partially available**: flyable with a non-critical defect

```
Fleet availability (%) = (sum of aircraft-days in Available state) / (sum of aircraft-days in period) x 100
```

Related standard measures:
- Inherent availability Ai = MTBF / (MTBF + MTTR)
- Operational availability Ao = MTBM / (MTBM + MDT), where MDT includes supply and administrative delay

Showing Ao beside Ai makes the point visually: the gap is the logistics and delay loss that predictive maintenance plus spares planning can recover.

### 1.9 Core concepts
- **Predictive maintenance:** use condition data to estimate when a component will degrade or fail, and intervene at the right time, avoiding both unplanned failures and wasteful early replacement.
- **Anomaly detection:** flag data that deviates from expected normal behaviour without needing labelled failures. Answers "is something unusual happening?"
- **Failure-risk prediction:** a probability that a component fails within a window (e.g. 14 days). Answers "how likely, and how soon?"
- **Remaining Useful Life (RUL):** estimated remaining time (days, flight hours or cycles) before a component reaches a failure or retirement threshold. Always report as a range.

| Maintenance type | Trigger | Weakness |
|---|---|---|
| Corrective | After failure | Unplanned downtime, possible secondary damage |
| Preventive | Fixed interval (hours/calendar) | Replaces healthy parts, misses random failures |
| Predictive | Measured condition | Needs data and model trust |

The platform does not abolish preventive maintenance. It adds a predictive layer on top and treats mandatory scheduled inspections as non-negotiable.

### 1.10 Digital twins and IoT
- **Digital twin (practical):** a software record of each aircraft and component holding configuration, current health, history and predicted degradation, and supporting what-if runs. Not a CFD/physics simulator (that would need proprietary design data).
- **IoT / health monitoring:** the data-acquisition layer. For this project: an ingestion API accepting post-flight sensor summaries, plus a simulator standing in for the aircraft. Extensible to live streaming later.

### 1.11 What the platform must support
Prioritising an at-risk list, recommending an action, checking spares, proposing a schedule, quantifying availability impact, and comparing alternatives, all with explanations.

### 1.12 What this plan deliberately avoids
- Real aircraft type names, fleet numbers, or real failure modes of any specific type.
- Combat, weapons or mission-planning functions.
- Claims of model accuracy on real data. All accuracy figures are on synthetic data and labelled so.
- Docker or any container technology.

---

# PART B: Solution concept

## 2. Modules

| # | Module | Status |
|---|---|---|
| 1 | Data Integration Layer | Essential |
| 2 | Fleet Overview Dashboard | Essential |
| 3 | Aircraft Health Monitoring (incl. anomaly detection) | Essential |
| 4 | Predictive Maintenance Engine (risk + RUL + recommendations) | Essential |
| 5 | Digital Twin (software-level) | Essential (named in the PS) |
| 6 | Spares / Inventory Intelligence | Essential |
| 7 | Maintenance Planning & Work Orders (includes agency tracking) | Essential |
| 8 | Fleet Availability Engine & Scenario Simulator | Essential |
| 9 | Alerts (rule-based, in-app) | Essential, minimal |
| 10 | Reports & Analytics | Optional (single page) |
| 11 | AI Maintenance Assistant (LLM) | Future scope / stretch |

Maintenance Agency Tracking is folded into module 7. Email/SMS notifications are future scope.

**Module details**

1. **Data Integration Layer.** *Purpose:* unify the four sources under one schema. *Input:* CSV/Parquet or API payloads (sensors, logbook, spares, agency). *Processing:* schema validation, ID mapping, timestamp normalisation, duplicate/missing handling, data-quality scoring. *Output:* clean relational tables plus a data-quality report. *Why:* directly solves "fragmented".
2. **Fleet Overview.** *User:* commander. *Output:* availability %, aircraft by state, top risks, upcoming maintenance, spares alerts.
3. **Aircraft Health Monitoring.** *User:* engineer. *Processing:* residual-based and Isolation Forest anomaly scoring. *Output:* trend charts with anomaly markers and per-system health index. *Why:* the evidence behind every prediction.
4. **Predictive Maintenance Engine.** *User:* planner/engineer. *Processing:* failure-risk model, RUL model, rule-based priority. *Output:* a Maintenance Advisory per component (§5). *Why:* the core AI/ML value.
5. **Digital Twin.** *Processing:* state update after each inference run. *Output:* interactive aircraft -> system -> component view with health state and history. *Why:* named in the PS; gives the integrated view.
6. **Spares Intelligence.** *Input:* stock, lead times, predicted component demand. *Output:* "available / short by N / lead time exceeds RUL". *Why:* addresses supply-wait downtime.
7. **Maintenance Planning & Work Orders.** *Input:* advisories, spares, bay/agency capacity. *Output:* work-order list, proposed slots, expected downtime. *Why:* turns insight into action.
8. **Availability Engine & Simulator.** *Input:* fleet state, schedule, spares. *Output:* current and forecast availability; scenario A vs B comparisons. *Why:* shows the PS outcome quantitatively.
9. **Alerts.** Risk above threshold, spare shortfall versus RUL, overdue inspection, backlog above limit.

### MVP definition
Modules 1-9 with one fleet, 7 systems, about 20 component types, and three predictive models (anomaly detection, failure risk, RUL), plus the rule-based priority and the simulation. The delay model, spare-demand forecast and LLM assistant are stretch goals.

---

# PART C: Data strategy

## 3. Synthetic data

### Design principles
1. **Latent-health simulation.** Each component has a hidden health index that degrades over time. Sensors are noisy functions of that hidden state plus operating conditions. Failures occur when health crosses a threshold. This is the construction used by NASA's public C-MAPSS turbofan dataset and gives ML real structure to learn.
2. **Correlation by design.** Components in a system share stress factors; operating conditions shift sensor baselines.
3. **Ground truth stays hidden.** True health is stored in `simulation_truth` and must never be used as an ML feature. It is for evaluation and demo scripting only.

### Parameters [ASSUMPTION; all configurable]

| Item | Choice |
|---|---|
| Fleet | 40 aircraft of one **generic** type ("Generic Twin-Engine Transport") |
| Period | 3 years of history (2023-01 to 2025-12) plus a "current" window; last ~60 days kept unlabelled for the live demo |
| Utilisation | ~0.8-1.5 flights per aircraft-day, 1-2.5 flight hours each |
| Sensor granularity | one summary row per flight per monitored parameter (mean, max, min, std) |
| Seed | 42 (reproducible) |

### Hierarchy
Fleet -> Aircraft -> System -> Component -> (optional) part instance.

| System | Example components |
|---|---|
| Propulsion (engine) | Compressor, Turbine, Oil system, Fuel control unit |
| Hydraulics | Pump, Actuator, Reservoir/filter |
| Electrical | Generator, Battery, Bus controller |
| Landing gear | Brake assembly, Strut, Tyre |
| Avionics | Flight computer, Display unit, Sensor suite |
| Fuel | Boost pump, Fuel quantity sensor |
| Environmental (ECS) | Cooling pack, Pressure controller |

About 20 component types per aircraft, so roughly 800 component instances in the fleet.

### Entities and key columns

**Reference**
- `aircraft(aircraft_id, tail_code, type_code, commissioned_date, total_flight_hours, total_cycles, base_id)`
- `systems(system_id, name)`
- `component_types(component_type_id, system_id, name, criticality 1-5, design_life_hours, mtbf_hours, part_number, is_repairable)`
- `components(component_id, aircraft_id, component_type_id, serial_no, installed_date, hours_at_install, hours_since_new, status)`

**Operations**
- `flights(flight_id, aircraft_id, date, duration_hours, cycles, ambient_temp_c, altitude_band, load_factor)`
- `sensor_readings(reading_id, flight_id, component_id, parameter, mean, max, min, std, quality_flag)`
- `fault_events(event_id, aircraft_id, component_id, timestamp, fault_code, severity, description, source)`

**Maintenance**
- `maintenance_events(event_id, aircraft_id, component_id, type [scheduled/unscheduled/inspection], start, end, action [replace/repair/inspect], labor_hours, work_order_id, root_cause)`
- `work_orders(wo_id, aircraft_id, component_id, agency_id, opened, planned_start, actual_start, promised_done, actual_done, status, priority, delay_reason)`
- `agencies(agency_id, name, level [line/base/depot], bays, capacity_hours_per_day, avg_turnaround_days)`
- `scheduled_tasks(task_id, aircraft_id, task_name, interval_hours, last_done_hours, due_hours, due_date)`

**Spares**
- `spare_parts(part_number, description, criticality, unit_cost, lead_time_days, reorder_level)`
- `inventory(part_number, location_id, on_hand, reserved, on_order, expected_receipt_date)`
- `inventory_transactions(txn_id, part_number, date, qty, type [issue/receipt/repair-return], work_order_id)`

**Derived / platform-generated** (see §15): `aircraft_daily_status`, `anomaly_scores`, `predictions`, `advisories`, `twin_snapshots`, `alerts`, `scenario_runs`, `model_runs`, `users`, and `simulation_truth(component_id, date, true_health)` (hidden from ML).

### How each element is simulated

- **Component degradation.** Health starts near 1.0 and decreases via a stochastic process (gamma or Wiener with drift). Drift depends on stress (higher ambient temperature and load wear faster). Each component draws a per-unit "personality" so failures are not perfectly predictable. Failure = health reaches 0, or a random shock for ~15% of failures that give little warning. These sudden failures are deliberate: they keep the model honest and support a limitations discussion.
- **Sensor readings.** `reading = baseline(operating conditions) + signature(health) + noise`. Signatures are parameter-specific and drift as health declines (vibration rises, hydraulic pressure drops or oscillates, oil temperature creeps up, bus voltage destabilises). Multiple parameters respond with different sensitivities and lags. Operating conditions shift baselines, so naive fixed thresholds fail and residual/normalised approaches work.
- **Missing and noisy data.** 2-5% random dropout, occasional stuck-at values, sensor drift on a few non-failing sensors (false-alarm sources), outlier spikes, a few flights with missing downloads. Add `quality_flag`.
- **Failures.** Each creates a `fault_event` (possibly preceded by minor fault codes) and an unscheduled `maintenance_event`; the true failure date is stored in the truth table.
- **Maintenance events.** Scheduled (periodic inspections and time-based replacements, the preventive baseline), unscheduled (failure-triggered). After replacement, health resets with a new serial number. Duration drawn from a distribution by task type.
- **Spares.** Initial stock per part set by a reorder rule; issues consume parts on maintenance events; receipts arrive after random lead times (very long for some critical items); occasional zero-stock periods produce real supply waits.
- **Work orders and delays.** Each maintenance event spawns a work order. Delay causes: awaiting spares (conditional on stock), agency queue (conditional on load), awaiting manpower, awaiting inspection. `turnaround = repair time + queue wait + spare wait + noise`.
- **Realistic correlations** come from shared stress drivers, propagation (a degrading hydraulic pump raises actuator stress), agency load driving delay, spare criticality and lead time driving supply waits, and utilisation driving wear.
- **Hero aircraft.** Reserve 3-4 scripted aircraft with guaranteed storylines for the demo (e.g. `AC-017` hydraulic pump degradation with tight spares). Disclose that these are scripted.
- **Storage.** Generated data is written to PostgreSQL. Optional Parquet/CSV exports go to the local `data/` folder (git-ignored) for ML experiments.

### Validation against public data
Run the RUL and anomaly pipeline once on NASA's public **C-MAPSS** turbofan dataset as a side script and sanity check. It demonstrates the code works on data you did not generate. Not core.

---

# PART D: AI/ML strategy

## 4. Model-by-model

**General rules.** Every task has a simple baseline first. Splits are temporal and grouped by component/aircraft to prevent leakage. Random row splits are not allowed.

### A. Anomaly detection
- **Formulation:** unsupervised "is this flight's behaviour unusual for this component under these conditions?"
- **Features:** sensor summary statistics normalised for operating condition; rolling windows (last 5 and 20 flights): mean, slope, std, deviation from the component's own baseline.
- **Target:** none. Evaluate against known degradation onset in synthetic truth.
- **Baseline:** fixed thresholds / rolling z-score.
- **Candidates:** residual model (regress sensor on operating conditions, flag large residuals), Isolation Forest, autoencoder.
- **Recommended:** residual model + Isolation Forest. Fast and explainable (the residual says which parameter and by how much). No autoencoder in the MVP.
- **Metrics:** detection lead time (days before failure of the first sustained alert), false-alarm rate per 1,000 flights, recall of degradation episodes.
- **Display:** anomaly score timeline with shaded alert regions; top contributing parameters.

### B. Failure prediction
- **Formulation:** for each component on each day, classify whether it fails within the next H days (H = 14; also 30).
- **Features:** rolling sensor statistics and slopes, anomaly scores, hours since new / since last maintenance, cycles, recent fault counts, stress summaries, component type, criticality.
- **Target:** `fail_within_H_days`.
- **Baseline:** logistic regression.
- **Candidates:** logistic regression, Random Forest, XGBoost, LightGBM.
- **Recommended:** LightGBM with calibrated probabilities; logistic regression stays as the interpretable baseline; SHAP for per-prediction explanation.
- **Imbalance:** class weights; PR-AUC as headline metric. No SMOTE.
- **Metrics:** PR-AUC, recall at fixed precision, calibration curve / Brier score, lead-time distribution of true alerts.
- **Display:** risk score 0-100, risk band (Low / Watch / High / Critical), SHAP bar chart.

### C. Remaining Useful Life
- **Formulation:** regress days (or flight hours) to failure with a **clipped target** (cap at 60 days), the standard C-MAPSS trick, since a component far from failure is simply "healthy".
- **Features:** as B plus health-indicator trend and slope.
- **Baseline:** linear extrapolation of a smoothed health indicator to its threshold.
- **Candidates:** gradient-boosted regression, survival models (Cox/Weibull via `lifelines`), LSTM/GRU.
- **Recommended:** LightGBM with quantile outputs (10th/50th/90th). Optionally a Weibull survival model as a cross-check and to handle censoring. No LSTM in MVP (harder to explain and tune); future scope.
- **Metrics:** MAE; C-MAPSS-style asymmetric score (late predictions penalised more); interval coverage (the 10-90 band should contain truth ~80% of the time).
- **Display:** "RUL ~ 18 days (range 11-27)" with a RUL-over-time plot.

### D. Maintenance priority
- **Formulation:** transparent **rule-based score, not ML**. Priority must be auditable and tunable, and there is no ground-truth label for "correct priority".
- **Formula (weights configurable in YAML):** `priority = w1*risk + w2*criticality + w3*(1/RUL) + w4*spare_shortfall_penalty + w5*availability_impact`
- **Output:** P1-P4 with the contributing factors.

### E. Spare parts demand forecasting
- **Formulation:** expected demand per part over 30/60/90 days.
- **Features:** predicted failures from B/C, scheduled-task demand, historical issue rates, utilisation.
- **Baseline:** moving-average historical consumption.
- **Recommended:** demand = scheduled demand + expected predicted-failure demand (sum of calibrated failure probabilities over the horizon), compared against the baseline. Croston's method optional for intermittent parts.
- **Metrics:** MAE or pinball loss; stock-out hit rate in backtest.
- **Display:** "Part X: expected demand 3 (1-5) in 30 days; stock 2; lead time 45 days -> shortfall risk".

### F. Fleet availability forecasting
- **Recommended: simulation, not ML** (Monte Carlo, §7), driven by risk scores, schedules, spares and capacity. Report P10/P50/P90. Optional seasonal/naive baseline for comparison.

### G. Maintenance delay prediction (stretch)
- **Formulation:** predict work-order turnaround days.
- **Features:** component type, agency, agency queue length, spare availability, priority, day of week.
- **Baseline:** agency mean turnaround. **Recommended:** LightGBM regression. **Metric:** MAE versus baseline.

### Summary
Three core ML models, one optional, a rule engine, and a simulation. No deep learning in the MVP. Everything runs on a laptop CPU.

---

# PART E: Predictive maintenance logic

## 5. The pipeline

```
Sensor/flight data -> Processing -> Features -> Health indicators -> Anomaly detection
  -> Risk / RUL -> Priority -> Recommended action -> Spares check -> Scheduling -> Availability impact
```

| Stage | Produces |
|---|---|
| 1. Data processing | Clean, validated, time-aligned readings with a data-quality flag |
| 2. Feature engineering | Rolling means, slopes, volatility, deviation from component baseline, condition-normalised values, counters since last maintenance |
| 3. Health indicator (HI) | One 0-100 score per component from weighted normalised parameters (or a PCA first component). System and aircraft HI roll up, weighted by criticality |
| 4. Anomaly detection | Anomaly score plus top contributing parameters |
| 5. Risk / RUL | Failure probability (14/30 days); RUL with 10-90 range |
| 6. Priority | P1-P4 with factor breakdown |
| 7. Recommended action | One of: continue monitoring / inspect at next opportunity / schedule replacement within X days / ground now |
| 8. Spares check | Required part number, stock status, lead time versus RUL |
| 9. Scheduling | Proposed maintenance window using bay and workshop capacity, bundled with scheduled tasks where possible |
| 10. Availability impact | Predicted aircraft-days lost under "act now" versus "wait" |

### The Maintenance Advisory object
The central output; it replaces the unhelpful "component will fail":

```
Aircraft AC-017 | Hydraulics | Main pump
Health state: Degraded (HI 41/100, down from 68 over 20 days)
Risk: 14-day failure probability 0.62 (High)
RUL: ~12 days (range 7-19)
Contributing parameters: outlet-pressure oscillation up (+3.1 sigma), fluid temperature up (+2.4 sigma)
Recommended action: replace within 7 days
Priority: P2
Spare: Pump P/N HYD-114, 1 in stock (reserved: 0), available
Expected downtime: ~2.5 days (incl. bay wait)
Availability impact: replace now -2.5 aircraft-days; run to failure -9.0 expected
Confidence/limits: model confidence moderate; 18% of this pump class fails without warning
```

### Guard rails
- Calibrated probabilities and ranges, never a single failure date.
- A confidence note (data quality, model uncertainty).
- Mandatory scheduled inspections are never overridden by the model.
- Human-in-the-loop advisory status: Proposed -> Accepted -> Scheduled -> Completed / Dismissed (with reason). Dismissal reasons are a monitoring signal.

---

# PART F: Digital twin and availability

## 6. Digital twin

**Definition [ASSUMPTION]:** a continuously updated software model of the fleet that stores structure, state, history and prediction for every aircraft and component, and can be queried and simulated. Not a physics simulation.

### Data model
```
Fleet -> Aircraft -> System -> Component
  node: { id, type, config, health_index, health_state, risk, rul, last_updated,
          maintenance_history[], predicted_trajectory[] }
```

### Health states
Healthy (HI >= 80) -> Watch (60-80) -> Degraded (40-60) -> Critical (< 40 or risk > 0.7) -> Failed -> Under maintenance -> back to Healthy (new part). Thresholds configurable. Roll-up: an aircraft's state is the worst state among its critical components, with the driving component shown.

### Component lifecycle
Installed -> in service (hours and cycles accumulate) -> degradation -> maintenance trigger (predicted or scheduled) -> removed -> repaired or scrapped -> returned to stores or replaced. Serial numbers are tracked through the cycle.

### ML updates
After each batch inference run (daily in the demo, or on new data), the engine writes HI, anomaly score, risk, RUL and a `twin_snapshots` row. Current state = latest snapshot; history = snapshot series. A time slider replays past states.

### User interaction
Fleet -> aircraft -> system map -> component panel (sensor trend, advisory, history) -> "Run what-if".

### Visualisations
- Fleet heat-grid (aircraft x system, coloured by state).
- Generic 2D aircraft schematic in SVG with systems highlighted by health (far cheaper than Three.js; use Three.js only if time remains, and only as polish).
- Hierarchical tree.
- Degradation trajectory with projected threshold crossing.
- Maintenance history timeline.

### What-if scenarios
Replace now vs defer 10 days; spare unavailable; two aircraft need the same bay at once.

## 7. Fleet availability engine

### Metrics

| Metric | Definition |
|---|---|
| Fleet availability | §1.8 |
| Aircraft serviceability | Fraction of aircraft currently available (snapshot) |
| Downtime | Aircraft-days unavailable, split by cause (scheduled, unscheduled, supply wait, agency wait) |
| MTBF | Operating hours / number of failures, per component type |
| MTTR | Mean active repair time |
| Turnaround time | Mean time from work-order open to aircraft release, including waits |
| Failure rate | Failures per 1,000 flight hours |
| Readiness proxy | Fraction of aircraft that are available and have no open P1/P2 advisory (a proxy, not operational readiness) |
| Component health | Distribution of HI states |
| Spare availability | Fill rate; parts with stock below predicted demand |
| Backlog | Open work orders and outstanding man-hours |

### How decisions affect availability
- Early replacement costs a short, known, **planned** downtime, schedulable when spares and bays are free.
- Deferred replacement risks a longer **unplanned** outage, possibly with supply wait and queue.
- Bundling tasks reduces total downtime.
- Spare shortfalls turn a short repair into a long outage; ordering early is high-leverage.

### Simulation engine
Lightweight **Monte Carlo discrete-event simulation**, 14-60 day horizon, ~200-500 runs:
- **State:** aircraft states, open work orders, bay occupancy, spare stock and incoming receipts.
- **Events:** component failures (sampled from model risk/RUL), repairs, receipts, scheduled-task starts.
- **Outputs:** availability curve with P10/P50/P90, aircraft-days lost by cause, stock-out probability.

### Scenario types

| Scenario | Interventions |
|---|---|
| Schedule aircraft X for maintenance on date D | Aircraft removed from the pool for the estimated duration; planned instead of risked downtime |
| Critical spare unavailable | Stock set to 0 or lead time extended; the repair waits |
| Address predicted failure early | Replacement moved earlier versus baseline run-to-failure |
| Add one bay / extra shift | Capacity changed |

Each run returns a side-by-side comparison (baseline vs scenario) with deltas. These are decision-support simulations on synthetic maintenance data, not operational planning.

---

# PART G: Architecture and UX

## 8. System architecture

```
[Simulator / CSV importers] -> [Ingestion API + validation]
                                   |
                    [PostgreSQL (local install): relational + readings]
                                   |
   [ML pipeline (CLI, batch)] -> [models/ on local disk] -> [Inference inside FastAPI]
                                   |
        [Twin updater] [Alert engine] [Availability engine / simulator]
                                   |
                         [FastAPI REST API layer]
                                   |
                           [React dashboard]
```

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Vite + TypeScript + Tailwind; ECharts; React Router; TanStack Query | Standard, well supported by coding agents. No Three.js initially |
| Backend | Python 3.11 + FastAPI served by uvicorn; Pydantic, SQLAlchemy 2, Alembic, psycopg 3 | Same language as ML; auto API docs help the demo |
| Database | **PostgreSQL 16, installed natively** (plain; TimescaleDB not justified) | A few million sensor rows is easy for indexed Postgres; it is a proper relational DB for the schema, constraints and window queries. Mention Timescale as a scaling path |
| Ingestion | REST endpoints + CLI loader. No Kafka/MQTT | Honest for batch post-flight downloads; streaming is a future path |
| ML | pandas, NumPy, scikit-learn, LightGBM, SHAP, joblib, lifelines (optional). No PyTorch in MVP | Explainable, trains on a laptop |
| Model serving | Load joblib artifacts from `models/` at FastAPI startup; batch scoring job plus on-demand endpoint | No separate model server needed |
| Scheduling | CLI script (`scripts/tasks.py`) or APScheduler | Enough for a demo |
| Alerts | Rule engine writing to `alerts`, shown in UI | MVP |
| Auth | JWT; roles Commander / Planner / Technician; seeded demo users | Role-based views, password hashing, input validation |
| Logging/monitoring | Structured logging, `/health` (includes DB check), model-run logs in DB, simple drift check | Production-style without a full observability stack |
| Task runner | `scripts/tasks.py` (plain Python) | Works the same on Windows, macOS and Linux (no `make` needed) |
| Version control | Git + GitHub | Required |
| CI (optional, stretch) | GitHub Actions running lint/tests with a natively installed PostgreSQL on the runner | Not required for the project; skip if time is short |

**Database decision.** PostgreSQL is chosen because the schema relies on foreign keys, CHECK constraints, indexes and window queries, and because it is more credible for a "production-style" claim. The cost is one native installation. All database access goes through SQLAlchemy with one `DATABASE_URL`, so the code is not tied to Postgres-only features unless a phase needs them. A SQLite fallback is deliberately **not** planned, to avoid maintaining two dialects. If PostgreSQL installation proves impossible on your machine, tell me and we will re-plan.

**AI assistant (stretch).** An LLM chat answering from your own API only (never free text), e.g. "Why is AC-017 flagged?". Add only after everything else works. The MVP uses deterministic template-based explanations generated from advisory fields, which cannot hallucinate.

### 8.1 Local (non-containerized) deployment strategy

**Processes you run**

| # | Process | How it runs | Port |
|---|---|---|---|
| 1 | PostgreSQL | Native OS service, started once and left running | 5432 |
| 2 | Backend API (+ in-process model serving, alert engine, twin, simulator) | `uvicorn backend.app.main:app --reload` from the repo root with the venv active | 8000 |
| 3 | Frontend dev server | `npm run dev` inside `frontend/` (Vite proxies `/api` to port 8000, so no CORS trouble) | 5173 |
| 4 | Batch jobs (run on demand) | `python scripts/tasks.py seed / train / engine` | none |

**Demo mode (single process).** After `npm run build`, FastAPI serves the built files from `frontend/dist`, so the whole app is available at `http://localhost:8000` with one terminal plus PostgreSQL. Use this for the final demo.

**Setup, conceptually (run once)**
1. Install Git, Python 3.11, Node.js 20+ (LTS) and PostgreSQL 16 natively. Do not install Docker.
2. Clone the repo and create the virtual environment at the repo root:
   - Windows PowerShell: `python -m venv .venv` then `.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
3. Install Python dependencies: `pip install -r requirements.txt -r requirements-dev.txt`
4. Install frontend dependencies: `cd frontend && npm install && cd ..`
5. Create the local database and role (see §15.1), then copy `.env.example` to `.env` and review values.
6. Create the schema: `python scripts/tasks.py migrate`
7. Generate data: `python scripts/tasks.py seed`
8. Train models: `python scripts/tasks.py train`
9. Run the engine once: `python scripts/tasks.py engine`
10. Start everything: `python scripts/tasks.py dev` (starts backend and frontend), or start the two servers in two terminals.

**Environment variables (`.env` at the repo root; never committed)**

| Variable | Purpose | Example |
|---|---|---|
| `DATABASE_URL` | Main database | `postgresql+psycopg://fleet:fleet_dev_pw@localhost:5432/fleetmaint` |
| `TEST_DATABASE_URL` | Separate database used by tests | `postgresql+psycopg://fleet:fleet_dev_pw@localhost:5432/fleetmaint_test` |
| `JWT_SECRET` | Token signing key (generate a random string) | long random value |
| `JWT_EXPIRE_MINUTES` | Token lifetime | `480` |
| `MODEL_DIR` | Model artifact folder | `models` |
| `DATA_DIR` | Generated datasets folder | `data` |
| `CORS_ORIGINS` | Allowed browser origins | `http://localhost:5173` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `DEFAULT_SEED` | Seed for data generation | `42` |

The frontend reads `VITE_API_BASE_URL` (default `/api/v1`, handled by the Vite proxy) from `frontend/.env`. The passwords above are throwaway local-development values only.

**Local configuration notes**
- All Python commands are run from the **repo root** with the virtual environment active, so `backend`, `ml` and `data_gen` are importable as top-level packages.
- Everything is stored on the local filesystem: `models/` (artifacts), `data/` (exports), `reports/` (generated reports).
- `scripts/tasks.py` is the only task runner. It must not depend on `make` or on shell-specific features.

## 9. Screens

Seven screens; others merged or cut.

**1. Fleet Dashboard**
- *Purpose:* instant fleet picture. *KPIs:* availability % (today, 7-day, 30-day forecast), aircraft by state, open P1/P2 advisories, backlog, parts at risk.
- *Charts:* availability trend with forecast band; downtime-by-cause stacked bar; aircraft x system health heat-grid.
- *Tables:* top-10 risk advisories; upcoming maintenance. *Filters:* date range, base, system. *Alerts:* banner strip.
- *Drill-down:* aircraft -> Aircraft Detail; advisory -> Component Health.

**2. Aircraft Detail (with Digital Twin tab)**
- *Purpose:* everything about one aircraft. *KPIs:* HI, state, flight hours since last inspection, open work orders.
- *Views:* system schematic and tree, component list with HI/risk/RUL, history timeline.
- *Interactions:* component -> Component Health; "What-if" -> Simulator pre-filled.

**3. Component Health**
- *Purpose:* the evidence behind a flag. *Charts:* multi-parameter sensor trends with anomaly shading and operating-condition overlay; HI trajectory with projected threshold crossing; SHAP contributors; RUL band.
- *Panel:* Maintenance Advisory card with Accept / Dismiss / Schedule.

**4. Predictive Maintenance (risk queue)**
- *Purpose:* the planner's worklist. *Table:* all advisories by priority with risk, RUL, spare status, expected downtime, recommended action. *Filters:* priority, system, spare status, aircraft. *Interaction:* bulk-select to plan.

**5. Maintenance Planning & Work Orders**
- *Purpose:* convert advisories into scheduled work. *Views:* Gantt-style timeline by aircraft and bay; work-order table with agency, status, promised vs actual dates, delay reason.
- *KPIs:* backlog, turnaround, on-time rate. *Interaction:* select a slot and see availability impact immediately.

**6. Spares Inventory**
- *Purpose:* connect demand to stock. *Table:* part, stock, reserved, on order, lead time, 30-day expected demand, status (OK / At risk / Short). *Charts:* demand-vs-stock bars; lead time versus RUL scatter. *Alerts:* shortfall.

**7. Scenario Simulator**
- *Purpose:* decision support. *Inputs:* scenario type and parameters. *Outputs:* baseline vs scenario availability curves with bands, aircraft-days-lost delta, stock-out probability. *Interaction:* save and compare up to three scenarios.

Optional eighth: **Analytics** (MTBF, MTTR, failure rate, model-performance panel), one scrollable page, cut if time is short. AI Assistant is a stretch.

---

# PART H: Demo

## 10. Demo story (about 6-7 minutes)

Use scripted hero aircraft `AC-017` with a degrading hydraulic main pump. Spare stock is deliberately tight so the supply-wait point lands.

| Step | UI state | Data visible |
|---|---|---|
| 1. Fleet Dashboard | Availability ~82%, 30-day forecast trending to ~74% | Aircraft states; heat-grid with AC-017 hydraulics amber; 2 spares-at-risk flags |
| 2. Spot the issue | Click AC-017 cell; Aircraft Detail opens | System "Degraded"; HI 68 -> 41 over 20 days |
| 3. Sensor trends | Component page, hydraulic pump | Outlet-pressure oscillation and fluid temperature drifting; fixed thresholds have not fired |
| 4. Anomaly | Anomaly score timeline | First sustained anomaly marked ~19 days before the simulated failure |
| 5. Risk and RUL | Risk gauge and RUL band | Risk rising 0.12 -> 0.62 (replay with time slider); RUL 12 days (7-19) |
| 6. Advisory | Advisory card | "Replace within 7 days", P2, SHAP drivers shown |
| 7. Spare check | Spares panel | 1 pump in stock, but a second aircraft's pump is also trending: fleet-level shortfall in ~3 weeks; lead time 45 days |
| 8. Schedule | Planning screen | Bay slot proposed, bundled with a due inspection; expected downtime 2.5 days |
| 9. Availability impact | Planner shows delta | Replace now: -2.5 aircraft-days; run-to-failure expected: -9 aircraft-days (incl. supply wait) |
| 10. Scenarios | Simulator, three runs side by side | (a) baseline; (b) replace early; (c) spare unavailable |
| 11. Close | Dashboard | Before/after: availability uplift, downtime reduction, labelled "synthetic data" |

Figures above are illustrative targets for the scripted data; the actual numbers come from the generated data and must be verified, not hard-coded.

**Why it solves the PS:** all four fragmented sources (sensors, logbook history, spares, agency/bay data) appear on one screen, producing earlier warning, an action, and a measured availability benefit.

---

# PART I: Implementation

## 11. Phased roadmap

Each phase has an independent, testable output. One branch per phase. Do not skip ahead. **No phase creates or requires Docker, container files or container tooling.**

### Phase 0: Repository and local environment
- **Objective:** a runnable native skeleton: backend, frontend, database connectivity, task runner.
- **Prerequisites:** GitHub repo; Python 3.11, Node 20+ and PostgreSQL 16 installed natively; local role and databases created per §15.1.
- **Create:** repo structure (§13), `README.md`, `.gitignore`, `.env.example`, `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `scripts/tasks.py` (commands: `migrate` placeholder, `dev`, `test`, `lint`), `docs/local-setup.md` (install and database steps for Windows, macOS, Linux), `database/setup_local.sql`, `AGENTS.md`; `backend/` FastAPI app with `GET /health` that also checks the DB connection; `frontend/` Vite + React + TS + Tailwind page that displays backend health, with a Vite proxy for `/api`.
- **APIs:** `GET /health`. **DB:** connectivity only; no tables yet. **ML:** none. **Frontend:** placeholder page.
- **Tests:** backend smoke test; DB connectivity test against `TEST_DATABASE_URL`; frontend builds.
- **Expected output:** `python scripts/tasks.py dev` starts both servers; the browser page shows "backend OK, database OK".
- **DoD:** health check works end to end; lint and tests pass; setup is documented well enough for a fresh clone to follow; committed.

### Phase 1: Data model
- **Objective:** full relational schema as migrations.
- **Prerequisites:** Phase 0.
- **Create:** SQLAlchemy models by domain, Alembic migrations, `docs/data-dictionary.md`; `tasks.py migrate` now runs Alembic.
- **DB:** all tables in §3 and §15 with keys, indexes, CHECK constraints.
- **Tests:** migrations apply and roll back on the test database; constraint tests (FK, uniqueness, enums, ranges).
- **DoD:** a fresh database is created from migrations with no manual steps; data dictionary matches models.

### Phase 2: Synthetic data generation
- **Objective:** reproducible simulator that populates the DB.
- **Prerequisites:** Phase 1.
- **Create:** `data_gen/` (config, hierarchy builder, flight generator, degradation engine, sensor generator, maintenance/work-order/delay generator, spares generator, noise injector, daily-status derivation, truth writer), hero-aircraft scenario file, CLI `python -m data_gen generate --seed 42`, `tasks.py seed`, data-quality report script.
- **Tests:** seed reproducibility; row counts; no negative stock; FK integrity; missing-data rates within spec; sensor-vs-true-health correlation present.
- **DoD:** one command yields ~40 aircraft x 3 years; the quality report passes; hero aircraft have the intended arcs; generation completes in a reasonable time on a laptop (target: a few minutes).

### Phase 3: Backend foundation
- **Objective:** read APIs, auth, validated ingestion.
- **Prerequisites:** Phase 2.
- **Create:** routers, services and schemas for fleet, aircraft, components, sensors, maintenance, work orders, inventory, agencies; JWT auth with three seeded roles; `POST /ingest/sensor-readings` with per-row error reporting; pagination and filtering; structured logging; consistent error format.
- **Tests:** per-endpoint API tests; auth (401/403); ingestion validation.
- **DoD:** OpenAPI docs list all endpoints; all tests pass.

### Phase 4: ML pipeline
- **Objective:** train, evaluate and persist anomaly, failure-risk and RUL models.
- **Prerequisites:** Phase 3 with populated DB.
- **Create:** `ml/` (data loading, feature engineering, labels, temporal + grouped splits, anomaly module, failure model, RUL model, evaluation, SHAP, artifact saving to `models/`, `python -m ml.train --all`, `tasks.py train`), `reports/model_evaluation.md` with plots.
- **Tests:** no-leakage test; time-split test; metrics above baseline; artifact reload test.
- **DoD:** models beat baselines on the held-out period; evaluation report exists; artifacts versioned; full training completes on a laptop CPU in a reasonable time.

### Phase 5: Predictive maintenance engine
- **Objective:** convert model outputs into advisories and alerts.
- **Prerequisites:** Phase 4.
- **Create:** `backend/app/engine/` (health indicator, scoring job, advisory generator with YAML priority weights, recommended-action rules, template explanations, spares check, alert rules, advisory status workflow); endpoints `GET /predictions`, `GET /advisories`, `PATCH /advisories/{id}`, `GET /alerts`, `POST /engine/run`; `tasks.py engine`.
- **DB:** writes to `anomaly_scores`, `predictions`, `advisories`, `alerts`.
- **Tests:** rule-table unit tests; advisory schema tests; hero-aircraft test; API tests.
- **DoD:** one run produces advisories for the whole fleet; AC-017 shows the expected progression when replayed across dates.

### Phase 6: Fleet availability engine
- **Objective:** KPIs and Monte Carlo scenarios.
- **Prerequisites:** Phase 5.
- **Create:** `backend/app/availability/` (KPIs, simulator, scenarios); endpoints `GET /kpis`, `GET /fleet/summary`, `GET /fleet/availability/trend`, `POST /scenarios/run`, `GET /scenarios`.
- **Tests:** KPIs match hand-computed fixtures; seeded reproducibility; monotonic sanity checks (no spares never raises availability; more capacity never lowers it).
- **DoD:** all four scenario types return comparable outputs; a 30-day, 300-run scenario runs in about 10 seconds or less.

### Phase 7: Digital twin
- **Objective:** twin state model, snapshots and replay.
- **Prerequisites:** Phase 5 (and Phase 6 for what-if).
- **Create:** `backend/app/twin/` (state model, roll-up, snapshot writer, endpoints `GET /twin/aircraft/{id}`, `GET /twin/fleet`, `GET /twin/component/{id}`, `POST /twin/whatif`).
- **Tests:** roll-up logic; state transitions; replay returns the correct historical state for AC-017.
- **DoD:** the twin API answers for any aircraft and date.

### Phase 8: Frontend dashboard
- **Objective:** the seven screens on real APIs.
- **Prerequisites:** Phases 3-7.
- **Create:** app shell, routing, login, role-aware nav, typed API client, TanStack Query hooks, shared components (KpiCard, StatusBadge, DataTable, TimeSeriesChart with anomaly shading, Heatgrid, AdvisoryCard), screens in order: Fleet Dashboard, Aircraft Detail (+ twin tab, SVG schematic), Component Health, Predictive Maintenance, Planning & Work Orders, Spares, Scenario Simulator.
- **Tests:** component tests; build and lint pass.
- **DoD:** every screen loads real data and the drill-downs in §9 work.

### Phase 9: Integration and polish
- **Objective:** the demo runs end to end with no manual DB edits.
- **Prerequisites:** Phase 8.
- **Do:** walk the §10 demo, list gaps, fix them; time-replay control across screens; indexes/caching where pages exceed ~1 s; consistent filters, units, colours, empty states; advisory Accept/Schedule actions update planning and availability views.
- **DoD:** each demo step reachable by clicks only; no console errors; pages load in under ~2 s on seeded data.

### Phase 10: Testing and validation
- **Objective:** prove the system works.
- **Create:** missing unit/API/DB tests; integration tests (data -> scoring -> advisory -> scenario); Playwright e2e for the demo path (runs against the locally started app); fixed-seed scenario regression tests; data validation checks; refreshed model-evaluation report; `docs/security-checklist.md`; `tasks.py test` running everything. Optional stretch: a GitHub Actions workflow that installs PostgreSQL natively on the runner and runs lint and tests (no container services).
- **DoD:** all §17 criteria met or explicitly listed as gaps.

### Phase 11: Demo and local deployment
- **Objective:** one-command reproducible local demo plus documentation.
- **Create:** `tasks.py demo` (migrate, seed, train, engine, build frontend, start the backend serving `frontend/dist` on port 8000); static-file serving of the built frontend in FastAPI; `docs/demo-script.md`; README with architecture diagram and setup; `docs/limitations.md`.
- **DoD:** a fresh clone on a machine with the prerequisites installed reproduces the demo by following the README; no Docker involved at any point.

## 12. Antigravity execution strategy

### How to work
1. Create the GitHub repo first. Put `AGENTS.md` in the root and this file at `docs/plan.md`. Check Antigravity's current documentation for how it loads persistent rules; if unsupported, tell it in each prompt to read `AGENTS.md`.
2. **One phase = one branch** (e.g. `phase-2-synthetic-data`). Review the diff, run tests yourself, merge only when green, tag the commit (`phase-2-done`).
3. Start each phase in a **fresh agent session**.
4. Ask for a short plan before coding and approve it against this document.
5. Keep terminal-command approval on the cautious setting at least for the first phases, and read database-related commands before approving them.
6. If the agent drifts, revert the commit and re-prompt with tighter constraints.
7. Review each phase's evidence (test output, evaluation report, screenshots) before starting the next.

### Prompts
Paste each into a fresh Antigravity session. Every prompt assumes the native, Docker-free environment described in §8.1.

**Phase 0**
```
You are implementing PHASE 0 (Repository & Local Environment). Read AGENTS.md first.
OBJECTIVE: A runnable native skeleton: FastAPI backend, React+Vite+TS+Tailwind frontend, database connectivity to a
locally installed PostgreSQL, and a cross-platform task runner. NO Docker, Dockerfiles, docker-compose or any
container configuration, anywhere.
STATE: The repo is empty except AGENTS.md and docs/plan.md. The developer has already installed Python 3.11,
Node 20+ and PostgreSQL 16 natively and created the database role/databases described in docs/plan.md §15.1.
CREATE: the directory structure in docs/plan.md §13 (empty folders with .gitkeep where needed);
backend/ with a FastAPI app (backend/app/main.py), GET /api/v1/health that also checks the database connection,
config loaded from environment variables (see docs/plan.md §8.1), pytest setup, ruff config;
frontend/ with Vite React TS + Tailwind, a placeholder page that calls /api/v1/health and displays backend and database
status, and a Vite dev-server proxy so /api forwards to http://localhost:8000;
root files: .gitignore (include .venv, .env, node_modules, data/, models/ contents, reports output), .env.example,
requirements.txt, requirements-dev.txt, pytest.ini (so tests run from the repo root), README.md;
database/setup_local.sql (creates role and databases fleetmaint and fleetmaint_test);
docs/local-setup.md (step-by-step native setup for Windows, macOS and Linux, including PostgreSQL install and
creating the role/databases, venv creation and activation, npm install);
scripts/tasks.py: a plain-Python, cross-platform task runner with commands: dev (start uvicorn and the Vite dev
server together and stop both on Ctrl+C), test (pytest and frontend tests), lint (ruff and eslint), migrate (a clear
"not implemented until Phase 1" message). It must not depend on make or shell-specific syntax.
MAY MODIFY: only the files above.
ACCEPTANCE: from the repo root with the venv active, `python scripts/tasks.py dev` starts both servers and the browser
page shows backend OK and database OK; `python scripts/tasks.py test` and `python scripts/tasks.py lint` pass;
the frontend production build succeeds; docs/local-setup.md is accurate.
Inspect first, plan, implement, run checks, report, STOP. Do not add tables, models, ML or other endpoints.
```

**Phase 1**
```
You are implementing PHASE 1 (Data Model). Read AGENTS.md and docs/plan.md §3 and §15.
OBJECTIVE: The complete relational schema as SQLAlchemy models + Alembic migrations on the local PostgreSQL.
STATE: Phase 0 skeleton exists and runs natively.
CREATE: backend/app/models/* (one module per domain: fleet, sensors, maintenance, spares, platform),
Alembic setup (backend/alembic, alembic.ini) and an initial migration, wire `python scripts/tasks.py migrate` to
run Alembic, docs/data-dictionary.md (every table/column/meaning), tests for constraints using TEST_DATABASE_URL.
REQUIREMENTS: primary/foreign keys, indexes (e.g. sensor_readings(component_id, flight_id), flights(aircraft_id, date),
aircraft_daily_status(aircraft_id, date), predictions(component_id, as_of_date)), CHECK constraints for enums/ranges.
The simulation_truth table must be clearly marked as not for model training. No Docker.
ACCEPTANCE: `alembic upgrade head` on an empty database succeeds, `downgrade base` succeeds,
constraint tests pass, the data dictionary matches the models.
Inspect, plan (wait for approval), implement, test, report, STOP. No data generation, no new APIs.
```

**Phase 2**
```
You are implementing PHASE 2 (Synthetic Data Generation). Read AGENTS.md and docs/plan.md §3.
OBJECTIVE: A reproducible simulator that populates the local PostgreSQL database with realistic synthetic fleet data.
STATE: The schema exists via Alembic migrations (Phase 1).
CREATE: data_gen/ package with: config (YAML: fleet size 40, 3 years, seed, noise rates),
hierarchy builder (7 systems, ~20 component types, generic names), flight generator,
latent-health degradation engine (gamma/Wiener process, stress-dependent drift, per-unit variation,
~15% sudden failures), sensor generator (reading = baseline(op-conditions) + signature(health) + noise),
maintenance/work-order/delay generator (spare wait + agency queue + repair time),
spares/inventory generator (reorder logic, lead times, occasional stock-outs),
noise injector (2-5% dropout, stuck values, drift, spikes, quality_flag),
aircraft_daily_status derivation, simulation_truth writes,
hero-aircraft scenario file (3-4 scripted aircraft incl. AC-017 hydraulic pump degradation with tight spares),
CLI: `python -m data_gen generate --seed 42`, wire `python scripts/tasks.py seed`, and a data-quality report script
(markdown output). Use bulk inserts (COPY or executemany batches) so generation finishes in a few minutes on a laptop.
ACCEPTANCE: one command fills the database; same seed gives identical data; the quality report shows
row counts, missing rates, failure counts per component type, correlation between sensors and true health;
tests for reproducibility, FK integrity, non-negative stock.
Do NOT train models or build APIs. Inspect, plan, implement, run, report, STOP.
```

**Phase 3**
```
You are implementing PHASE 3 (Backend Foundation). Read AGENTS.md and docs/plan.md §14, §15.
OBJECTIVE: REST APIs for reading the integrated data, JWT auth with roles, and a validated ingestion endpoint.
STATE: Schema (Phase 1) and populated database (Phase 2) exist.
CREATE: routers/services/schemas for fleet, aircraft, components, sensors, maintenance, work orders,
inventory, agencies; JWT login with roles (commander, planner, technician) and seeded demo users;
role checks (technician read-only); POST /ingest/sensor-readings with Pydantic validation and per-row error reporting;
pagination and filtering; structured JSON logging; consistent error format.
Endpoints per docs/plan.md §14 for these domains only. No prediction/scenario/twin endpoints yet.
ACCEPTANCE: OpenAPI docs complete; API tests per endpoint; auth tests (401, 403); ingestion validation tests;
all tests and lint pass.
Inspect, plan, implement, test, report, STOP.
```

**Phase 4**
```
You are implementing PHASE 4 (ML Pipeline). Read AGENTS.md and docs/plan.md §4, §16.
OBJECTIVE: Train, evaluate and persist: (A) anomaly detection, (B) 14-day failure-risk model, (C) RUL model.
STATE: The database is populated with synthetic data; simulation_truth exists but MUST NOT be used as a feature.
CREATE: ml/ package: data loading from the database, feature engineering (rolling mean/slope/std over 5 and 20 flights,
operating-condition normalisation, hours/cycles since maintenance, fault counts), label creation,
time-based AND grouped-by-aircraft train/val/test splits,
anomaly module (condition-regression residuals + Isolation Forest), failure model (logistic regression baseline + LightGBM, calibrated),
RUL model (linear health-trend baseline + LightGBM quantile 10/50/90, target clipped at 60 days),
evaluation (PR-AUC, recall@precision, Brier, MAE, interval coverage, detection lead time), SHAP outputs,
artifact saving to models/<name>/<version>/ on the local filesystem with metadata.json (features, metrics, data hash, date),
CLI `python -m ml.train --all`, wire `python scripts/tasks.py train`, and a generated reports/model_evaluation.md with plots.
Everything must run on a laptop CPU; no GPU, no deep learning.
ACCEPTANCE: models beat baselines on the held-out test period; a leakage test proves features only use past data;
artifacts reload and predict; the report exists.
Do NOT build advisory logic or APIs. Inspect, plan, implement, run, report honestly (including weaknesses), STOP.
```

**Phase 5**
```
You are implementing PHASE 5 (Predictive Maintenance Engine). Read AGENTS.md and docs/plan.md §5.
OBJECTIVE: Convert model outputs into Maintenance Advisories and alerts.
STATE: Trained model artifacts in models/; database with data; backend APIs from Phase 3.
CREATE: backend/app/engine/: health_indicator.py, scoring_job.py (batch inference for a given as_of_date,
writes anomaly_scores/predictions), advisory.py (priority rules with configurable weights in YAML,
recommended-action rules, template-based plain-language explanation, SHAP top factors, confidence note),
spares_check.py (part requirement, stock, lead time vs RUL), alert_rules.py (risk threshold, shortfall vs RUL,
overdue inspections, backlog), advisory status workflow (proposed/accepted/scheduled/completed/dismissed+reason),
endpoints: GET /predictions, GET /advisories, PATCH /advisories/{id}, GET /alerts, POST /engine/run,
and wire `python scripts/tasks.py engine`.
ACCEPTANCE: one run produces advisories for the full fleet; the AC-017 hero advisory shows the expected progression
when replayed across dates; rule unit tests; API tests.
Do NOT implement availability simulation or twin. Inspect, plan, implement, test, report, STOP.
```

**Phase 6**
```
You are implementing PHASE 6 (Fleet Availability Engine). Read AGENTS.md and docs/plan.md §7.
OBJECTIVE: KPI calculations and a Monte Carlo scenario simulator.
STATE: Phases 0-5 complete.
CREATE: backend/app/availability/: kpis.py (availability, serviceability, downtime by cause, MTBF, MTTR,
turnaround, failure rate, backlog, readiness proxy, spare fill rate), simulator.py (discrete-event Monte Carlo:
aircraft states, bays, work orders, spare stock/receipts, failures sampled from risk/RUL; N runs; seeded; P10/P50/P90),
scenarios.py (schedule-maintenance, spare-unavailable, early-vs-run-to-failure, extra-capacity),
endpoints: GET /kpis, GET /fleet/summary, GET /fleet/availability/trend, POST /scenarios/run, GET /scenarios.
ACCEPTANCE: KPI functions match hand-computed fixtures; simulations reproducible with a seed;
sanity tests (removing spares never raises availability; adding capacity never lowers it);
a 30-day, 300-run scenario runs in about 10 seconds or less.
Inspect, plan, implement, test, report, STOP.
```

**Phase 7**
```
You are implementing PHASE 7 (Digital Twin). Read AGENTS.md and docs/plan.md §6.
OBJECTIVE: A software-level digital twin service: hierarchy, health-state roll-up, snapshots, replay.
STATE: Phases 0-6 complete.
CREATE: backend/app/twin/: state model (Healthy/Watch/Degraded/Critical/Failed/Under maintenance, configurable thresholds),
roll-up (component -> system -> aircraft, criticality-weighted, worst-component driver reported),
snapshot writer called after each engine run (twin_snapshots),
endpoints: GET /twin/fleet, GET /twin/aircraft/{id}, GET /twin/component/{id},
GET /twin/aircraft/{id}?as_of=DATE (replay), POST /twin/whatif (delegates to the scenario engine).
ACCEPTANCE: roll-up tests; state-transition tests; replay returns the correct historical state for AC-017.
No UI work. Inspect, plan, implement, test, report, STOP.
```

**Phase 8**
```
You are implementing PHASE 8 (Frontend Dashboard). Read AGENTS.md and docs/plan.md §9.
OBJECTIVE: The seven screens, driven by the real backend APIs.
STATE: Backend APIs for all domains exist (Phases 3-7).
CREATE: app shell, routing, login, role-aware nav, typed API client, TanStack Query hooks,
shared components (KpiCard, StatusBadge, DataTable, TimeSeriesChart with anomaly shading, Heatgrid, AdvisoryCard),
and screens in this order, checking in after each: Fleet Dashboard; Aircraft Detail (+ twin tab, SVG schematic);
Component Health; Predictive Maintenance queue; Maintenance Planning & Work Orders; Spares; Scenario Simulator.
Use ECharts, Tailwind. Show a persistent "Synthetic data" label. Loading, empty and error states on all data views.
The app must work with the Vite dev server (proxy to the backend) and with a production build.
ACCEPTANCE: build, lint and component tests pass; each screen shows real data; the drill-downs in docs/plan.md §9 work.
Do NOT change backend contracts without reporting it. Inspect, plan (wait for approval), implement, report, STOP.
```

**Phase 9**
```
You are implementing PHASE 9 (Integration & Polish). Read AGENTS.md and docs/plan.md §10.
OBJECTIVE: Make the full demo script run end to end without manual database edits.
STATE: Phases 0-8 complete.
DO: walk the 11-step demo in docs/plan.md §10, list every gap or bug, fix them; add a time-replay control that
drives the as-of date across screens; add database indexes/caching where pages are slow (>1s); polish consistency
(filters, units, colours, empty states); ensure advisory Accept/Schedule actions update planning and availability views.
ACCEPTANCE: each demo step reachable by clicks only; no console errors; pages load in under ~2s on the seeded data.
Report the gap list and fixes. STOP.
```

**Phase 10**
```
You are implementing PHASE 10 (Testing & Validation). Read AGENTS.md and docs/plan.md §17.
OBJECTIVE: Prove the system works and document it.
CREATE: missing unit/API/DB tests to reach sensible coverage of services and engine rules (tests use TEST_DATABASE_URL);
integration tests (data -> scoring -> advisory -> scenario); Playwright e2e for the demo path run against the locally
started app; fixed-seed scenario regression tests; data validation checks; refreshed reports/model_evaluation.md;
docs/security-checklist.md (auth, input validation, secrets, role access); make `python scripts/tasks.py test` run everything.
OPTIONAL (only if everything else is done): a GitHub Actions workflow that installs PostgreSQL natively on the runner
and runs lint and tests. Do not use container-based services.
ACCEPTANCE: all criteria in docs/plan.md §17 are met or explicitly listed as gaps.
Do not add features. Report results. STOP.
```

**Phase 11**
```
You are implementing PHASE 11 (Demo & Local Deployment). Read AGENTS.md.
OBJECTIVE: One-command reproducible local demo and documentation, with no Docker.
CREATE: `python scripts/tasks.py demo` (migrate, seed with seed 42, train, run engine, build the frontend, start the
backend serving frontend/dist at http://localhost:8000); static-file serving of the built frontend in FastAPI;
docs/demo-script.md (the 11 steps with exact clicks and expected values); README with architecture diagram (mermaid),
setup, screenshot placeholders; docs/limitations.md (synthetic data, model scope, what real data would change).
Do not change functionality. Verify by following the README from a clean clone. Report. STOP.
```

## 13. Repository structure

```
/
├── AGENTS.md                  # Rules every agent session follows
├── README.md
├── .env.example               # Template for local configuration (copy to .env)
├── .gitignore
├── requirements.txt           # Runtime Python dependencies
├── requirements-dev.txt       # Test/lint dependencies
├── pytest.ini                 # Lets tests run from the repo root
├── backend/
│   ├── app/
│   │   ├── main.py  config.py
│   │   ├── api/               # routers (HTTP layer only)
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── models/            # SQLAlchemy ORM
│   │   ├── services/          # business logic (data access, ingestion)
│   │   ├── engine/            # scoring, advisories, alerts
│   │   ├── availability/      # KPIs + Monte Carlo simulator
│   │   ├── twin/              # twin state, roll-up, snapshots
│   │   └── core/              # auth, logging, errors
│   ├── alembic/  alembic.ini  tests/
├── ml/                        # offline training code
│   ├── features/  models/  evaluation/  cli.py  tests/
├── data_gen/                  # synthetic data simulator
├── database/                  # local PostgreSQL setup SQL and notes (no container files)
├── models/                    # versioned model artifacts on local disk (git-ignored)
├── frontend/
│   └── src/ (pages/ components/ api/ hooks/ types/)  tests/
├── data/                      # generated datasets/exports (git-ignored)
├── reports/                   # model evaluation, data-quality reports
├── scripts/                   # tasks.py task runner and utilities
├── docs/                      # plan.md, local-setup, data-dictionary, demo-script, limitations, security
├── e2e/                       # Playwright tests
└── .github/workflows/         # optional CI (stretch)
```

**Responsibilities.** `backend` serves and orchestrates; `ml` trains offline; `data_gen` creates synthetic data; `database` holds local PostgreSQL setup SQL; `models` holds artifacts the backend loads; `scripts` holds the cross-platform task runner; `docs` holds the plan and agent reference material. There is no `docker/` directory. Keeping `ml` and `data_gen` out of `backend` isolates each phase's work for the coding agent.

## 14. API design

All endpoints under `/api/v1`. Auth is a JWT bearer token. Roles: **C**ommander, **P**lanner, **T**echnician. "Read" means all roles.

| Method | Endpoint | Purpose | Request / key params | Response (abridged) | Auth | Consumer |
|---|---|---|---|---|---|---|
| POST | `/auth/login` | Get token | `{username, password}` | `{access_token, role}` | none | Login |
| GET | `/fleet/summary` | Dashboard KPIs | `as_of` | `{availability_pct, by_state, open_p1, open_p2, backlog, parts_at_risk}` | Read | Fleet Dashboard |
| GET | `/fleet/availability/trend` | History and forecast | `from, to, horizon` | `{points:[{date, avail, p10, p90}]}` | Read | Dashboard |
| GET | `/aircraft` | List aircraft | `state, base, page` | list with state, HI, top risk | Read | Dashboard, tables |
| GET | `/aircraft/{id}` | Detail | none | aircraft, systems, component summary | Read | Aircraft Detail |
| GET | `/components/{id}/sensors` | Sensor trends | `parameter, from, to` | series + anomaly flags | Read | Component Health |
| GET | `/components/{id}/health` | HI/risk/RUL history | `from, to` | `{hi:[...], risk:[...], rul:[...]}` | Read | Component Health |
| GET | `/predictions` | Latest predictions | `aircraft_id, system, min_risk` | list | Read | Predictive |
| GET | `/advisories` | Risk queue | `priority, status, spare_status` | list of advisory objects (§5) | Read | Predictive |
| PATCH | `/advisories/{id}` | Accept/dismiss/schedule | `{status, reason?}` | updated advisory | P, C | Component Health |
| GET | `/work-orders` | Work orders | `status, agency, aircraft` | list | Read | Planning |
| POST | `/work-orders` | Create from advisory | `{advisory_id, agency_id, planned_start}` | work order + impact preview | P, C | Planning |
| GET | `/maintenance/schedule` | Bay timeline | `from, to` | slots by bay/aircraft | Read | Planning |
| GET | `/inventory` | Stock status | `status, part` | parts with demand forecast | Read | Spares |
| GET | `/inventory/{part}/forecast` | Demand forecast | `horizon` | `{expected, p10, p90, shortfall_prob}` | Read | Spares |
| GET | `/alerts` | Active alerts | `severity` | list | Read | Banner |
| GET | `/kpis` | KPI set | `from, to, group_by` | MTBF/MTTR/turnaround etc. | Read | Analytics |
| POST | `/scenarios/run` | Run what-if | `{type, params, horizon, runs}` | `{id, baseline, scenario, delta}` | P, C | Simulator |
| GET | `/scenarios` | Saved scenarios | none | list | P, C | Simulator |
| GET | `/twin/fleet` | Fleet twin | `as_of?` | fleet tree with states | Read | Dashboard |
| GET | `/twin/aircraft/{id}` | Twin state | `as_of?` | tree with states | Read | Aircraft Detail |
| GET | `/twin/component/{id}` | Component twin | `as_of?` | state, history, trajectory | Read | Component Health |
| POST | `/twin/whatif` | Twin what-if | scenario params | scenario result | P, C | Aircraft Detail |
| POST | `/engine/run` | Trigger scoring | `{as_of}` | run summary | C | Admin/demo |
| POST | `/ingest/sensor-readings` | Ingest | batch of readings | accepted/rejected counts | P, C | Integration layer |
| GET | `/health` | Liveness + DB check | none | `{status, database}` | none | Ops, Phase 0 page |

**Example: `POST /scenarios/run`**
```json
{ "type": "spare_unavailable", "params": {"part_number": "HYD-114", "lead_time_days": 60},
  "horizon_days": 30, "runs": 300, "seed": 7 }
```
Response (illustrative):
```json
{ "id": "sc_0042",
  "baseline": {"availability_p50": 0.81, "p10": 0.77, "p90": 0.84, "aircraft_days_lost": 48.2},
  "scenario": {"availability_p50": 0.76, "p10": 0.70, "p90": 0.81, "aircraft_days_lost": 71.5},
  "delta": {"availability_pct_points": -5.0, "aircraft_days_lost": 23.3},
  "by_cause": {"supply_wait": 21.0, "scheduled": 0.0, "unscheduled": 2.3} }
```

**Example: `PATCH /advisories/{id}`** request: `{"status": "scheduled", "reason": null}`

## 15. Database design

**Conceptual ER**
```
aircraft 1--* components *--1 component_types *--1 systems
aircraft 1--* flights 1--* sensor_readings *--1 components
components 1--* fault_events
aircraft/components 1--* maintenance_events *--1 work_orders *--1 agencies
component_types *--1 spare_parts 1--* inventory 1--* inventory_transactions
components 1--* anomaly_scores | predictions | twin_snapshots | advisories
advisories 0..1--* work_orders
aircraft 1--* aircraft_daily_status
scenario_runs (standalone)   alerts (references aircraft/component/advisory)
users (id, username, password_hash, role)   simulation_truth (components; hidden from ML)
```

**Tables.** Those in §3, plus:
- `anomaly_scores(component_id, flight_id, score, top_parameters JSON)`
- `predictions(prediction_id, component_id, as_of_date, risk_14d, risk_30d, rul_p10, rul_p50, rul_p90, model_version)`
- `advisories(advisory_id, component_id, as_of_date, priority, action, status, dismiss_reason, explanation JSON, spare_status, expected_downtime_days, created_at)`
- `twin_snapshots(snapshot_id, node_type, node_id, as_of_date, health_index, state, risk, rul_p50)`
- `alerts(alert_id, type, severity, aircraft_id, component_id, message, created_at, acknowledged)`
- `scenario_runs(id, type, params JSON, results JSON, seed, created_by, created_at)`
- `users(id, username, password_hash, role)`
- `model_runs(model_name, version, metrics JSON, trained_at)`

**Key indexes:** `sensor_readings(component_id, flight_id)`, `flights(aircraft_id, date)`, `predictions(component_id, as_of_date DESC)`, `aircraft_daily_status(aircraft_id, date)`, `work_orders(status, agency_id)`, `inventory(part_number, location_id)`, `twin_snapshots(node_id, as_of_date)`.

**Key constraints:** FK integrity everywhere; `UNIQUE(component_id, as_of_date, model_version)` on predictions; CHECK on enums (state, priority, status), `on_hand >= 0`, `end >= start`, severity range; a component belongs to one aircraft at a time.

### 15.1 Installing and configuring PostgreSQL locally (no Docker)

1. **Install PostgreSQL 16 natively.**
   - Windows: download the installer from postgresql.org (the EDB installer). Keep the default port 5432, set a password for the `postgres` superuser and remember it, and let it install the command-line tools (`psql`).
   - macOS: install via Homebrew (`brew install postgresql@16`, then start the service with `brew services start postgresql@16`), or use the Postgres.app download.
   - Linux (Debian/Ubuntu): install the `postgresql` package with `apt`; the service starts automatically.
2. **Confirm the server is running** by connecting with `psql` as the `postgres` user (on Linux this is typically `sudo -u postgres psql`).
3. **Create a development role and two databases** (also saved as `database/setup_local.sql`):
   ```sql
   CREATE ROLE fleet WITH LOGIN PASSWORD 'fleet_dev_pw';
   CREATE DATABASE fleetmaint OWNER fleet;
   CREATE DATABASE fleetmaint_test OWNER fleet;
   ```
   The password is a throwaway local value. `fleetmaint` holds the demo data; `fleetmaint_test` is used by automated tests so tests never touch demo data.
4. **Put the connection strings in `.env`** (see §8.1): `DATABASE_URL` and `TEST_DATABASE_URL` using the `postgresql+psycopg://` form.
5. **Verify** with `psql -U fleet -d fleetmaint -h localhost -c "SELECT 1;"`, then with the Phase 0 `/health` endpoint, which reports database status.
6. **Schema management** is done only through Alembic (`python scripts/tasks.py migrate`). To reset a database during development, drop and recreate it with `psql`, then run `migrate` and `seed` again.
7. **Common problems:** the service is not running; port 5432 is occupied by another PostgreSQL; wrong password; on Windows, `psql` not on PATH (use the SQL Shell from the Start menu or add the PostgreSQL `bin` folder to PATH).

No tuning is needed for this data volume. The default PostgreSQL configuration is adequate for a few million sensor rows.

## 16. ML development pipeline

```
Ingestion -> Validation -> Cleaning -> Feature engineering -> Split -> Training -> Tuning
  -> Evaluation -> Explainability -> Persistence -> Inference -> Monitoring
```

| Stage | What happens |
|---|---|
| Ingestion | Read from PostgreSQL into pandas. Never read `simulation_truth` for features |
| Validation | Schema, range and missing-rate checks (Pandera or custom) |
| Cleaning | Limited forward-fill for dropouts, clip spikes, flag stuck sensors; keep `quality_flag` as a feature |
| Features | Strictly past-only windows. A unit test asserts that changing future data does not change features |
| Split | Time-based (e.g. train 2023-2024, validate H1 2025, test H2 2025) and component-grouped so a unit's rows never span splits |
| Training | Baseline first, then the main model |
| Tuning | Small randomised/Optuna search with time-series cross-validation; keep it modest |
| Evaluation | Metrics from §4 plus plots in `reports/` |
| Explainability | SHAP for tree models; per-parameter residuals for anomalies |
| Persistence | `models/<name>/<version>/model.joblib` + `metadata.json` (features, metrics, data hash, date, library versions) on the local filesystem |
| Inference | Backend loads the latest version from `MODEL_DIR` at startup; `scoring_job` builds features as of a date and writes `predictions` |
| Monitoring | Log score distributions per run, compare to training distribution, compare predicted versus realised failures, surface a drift flag in Analytics |

## 17. Testing and validation

| Type | What | Acceptance criterion (initial targets; tune after seeing results) |
|---|---|---|
| Unit | Rules, KPIs, roll-up, feature functions | All rules and KPI functions covered |
| API | Each endpoint, auth, validation | All endpoints tested; 401/403 verified |
| Database | Migrations, constraints (on `fleetmaint_test`) | Up/down migrations clean |
| Data validation | Synthetic data quality | Reproducible by seed; missing rate within spec; sensor-health correlation present |
| ML evaluation | Held-out time period | Failure model PR-AUC clearly above baseline; RUL MAE better than the linear baseline; RUL 10-90 interval coverage about 75-85%; median detection lead time of several days with a low false-alarm rate |
| Integration | data -> score -> advisory -> scenario | Hero aircraft produces the expected advisory trajectory |
| Frontend | Component tests, build, lint | Pass |
| E2E | Playwright runs the §10 path against the locally started app | Completes with no manual steps |
| Scenario | Fixed-seed regression | Monotonic sanity checks hold; results reproducible |
| Fresh-clone | Follow README on a clean machine | Demo reproduces without Docker |

Do not commit to numeric model thresholds before seeing the first honest baseline results. Set them afterwards and state them in the pitch. Always report that results are on synthetic data.

## 18. Hackathon / evaluation readiness

**[Inference]** The PS gives no evaluation rubric. The following are reasonable expectations, not facts.

| Likely focus | How it is addressed |
|---|---|
| Integration of fragmented data (PS wording) | Data layer unifying four sources; data-quality report; one-screen view |
| AI/ML credibility | Baselines vs models, temporal splits, honest metrics, calibration, lead time |
| Predictive, not just reactive | Anomaly -> risk -> RUL -> action chain with lead time gained |
| Digital twin and IoT (named in PS) | Twin hierarchy with replay; ingestion API standing in for a health-monitoring feed |
| Availability outcome | Availability engine and scenario comparisons |
| Explainability | SHAP, parameter contributions, rule-based priority |
| Real-world applicability | Limitations doc; plan for swapping synthetic data for real exports; human-in-the-loop workflow |
| UI/UX | Decision-maker-oriented screens and drill-downs |
| Scalability | Notes on Timescale, stream ingestion, separate model server as scale paths |
| Security | Role-based access, JWT, validation; note a real deployment would sit on an accredited/air-gapped network |

**Final presentation should include:** the problem in one slide (three causes of downtime); architecture diagram; data strategy and why synthetic; one honest model-evaluation slide; the live or recorded demo; the availability uplift in the scenario comparison; limitations and what real data would change; roadmap.

**Do not claim:** accuracy on real aircraft, readiness for operational use, or compliance with any military airworthiness standard.

---

# PART J

## 19. Final master implementation plan

1. **Architecture:** §8 (native FastAPI + local PostgreSQL + batch ML + React; no containers).
2. **Tech stack:** React/Vite/TS/Tailwind/ECharts; FastAPI/SQLAlchemy/Alembic/psycopg; PostgreSQL 16 (no Timescale); pandas/scikit-learn/LightGBM/SHAP; Python venv; npm; `scripts/tasks.py`.
3. **Modules:** §2.
4. **Data architecture:** §3 (40 generic aircraft, 3 years, latent-health simulation, hero aircraft, hidden truth table).
5. **ML architecture:** §4 and §16 (anomaly: residual + Isolation Forest; failure risk: LightGBM; RUL: quantile LightGBM; rule-based priority; simulation-based availability forecasting).
6. **Database schema:** §3 and §15, local setup in §15.1.
7. **API architecture:** §14.
8. **Frontend structure:** §9 and §13 (`frontend/src`).
9. **Repository structure:** §13.
10. **Implementation order:** Phases 0 -> 11 (§11), one branch each, merged only when green.
11. **Antigravity prompts:** §12.
12. **Testing strategy:** §17.
13. **Demo flow:** §10.
14. **Deployment:** native local run per §8.1; final demo served from one process after `npm run build`.
15. **Final Definition of Done:**
    - A fresh clone on a machine with Python, Node and PostgreSQL installed reproduces the full demo by following the README, with no Docker and no manual edits.
    - All tests, lint and build pass locally via `python scripts/tasks.py test` and `lint`.
    - Models beat baselines on the held-out period, with an honest evaluation report.
    - The §10 demo path works click by click.
    - Three scenario comparisons run and show availability differences.
    - Docs include architecture, local setup, data dictionary, limitations and demo script.
    - The UI and docs clearly state that all data is synthetic.

### Assumptions to keep visible
- The generic fleet, sensor-summary granularity, 40 aircraft and 3 years are design choices, not from the PS.
- The availability definition (§1.8) is a design choice; state it explicitly.
- PostgreSQL 16 as the single supported database is a design choice (§8).
- Real data would change feature distributions, failure modes, ID mapping and data quality. Say so in the pitch.
