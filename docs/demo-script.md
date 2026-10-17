# Demo Script — AeroPulse Fleet Availability & Predictive Maintenance Platform

**Problem Statement 26249 (MoD / DSSC):** Integrated Predictive Maintenance & Fleet Availability  
**Duration:** ~6–7 minutes  
**Target Audience:** Defense Maintenance Commanders, Logistics/Supply Officers, Technical Evaluators  
**Notice:** *All data in this demonstration is 100% synthetic. No classified defense data, weapons systems, or operational mission planning functions are included.*

---

## Preparation & Prerequisites

1. Ensure the platform is started via the one-command demo runner:
   ```bash
   python scripts/tasks.py demo
   ```
2. Open your web browser to:
   ```
   http://localhost:8000
   ```
3. Login using the **Quick Login** button **"Planner"** (or enter username `planner` / password `planner123`).

---

## 11-Step Walkthrough

### Step 1: Fleet Dashboard Overview (The Operational Dilemma)
* **Goal:** Establish current fleet readiness, observe the downward availability forecast, and spot early warning signals across fragmented sources.
* **Exact Actions:**
  1. Once logged in, you land on `/dashboard` (**Fleet Operational Cockpit**).
  2. Observe the top KPI bar:
     - **Fleet Availability:** ~82.5% (Target: 80.0%).
     - **30-Day Forecast Availability:** Trending downwards toward ~74.2% if no proactive maintenance is scheduled.
     - **Total Airframes:** 40 Generic Twin-Engine Transports across 3 operating bases.
     - **Spares at Risk:** 2 flagged items facing impending supply shortfalls.
  3. Look at the **System Health Matrix (Heatgrid)**:
     - Locate column **AC-017**.
     - Notice row **Hydraulics** is highlighted in **Amber / Degraded** (Health Index ~41%).
* **Talking Point:** *"Currently, the fleet looks mission-ready at ~82% availability. However, our 30-day Monte Carlo forecast reveals availability will degrade to 74% due to cascading unpredicted failures. Notice that on AC-017, the hydraulic system is already degrading."*

---

### Step 2: Spot the Issue (Aircraft Detail & Digital Twin)
* **Goal:** Drill down from the fleet view to airframe `AC-017` to inspect subsystem degradation.
* **Exact Actions:**
  1. Click the amber cell for **AC-017 (Hydraulics)** in the Heatgrid, OR click **"Aircraft Detail & Twin"** in the left navigation sidebar.
  2. Ensure the top aircraft selector is set to **AC-017**.
  3. Notice the **Airframe Status Banner**:
     - Tail Number: `AC-017`
     - Operational State: `FMC` (Fully Mission Capable) / `Degraded` subsystem.
     - System Overall Health Index: Has declined from ~68 down to 41 over the last 20 days.
  4. View the **Interactive SVG Aircraft Schematic**:
     - The **Hydraulics subsystem** is highlighted amber/red.
     - Primary driver component: `Hydraulic Main Pump (CMP-HYD-017)`.
* **Talking Point:** *"Conventional reactive logs still show AC-017 as flyable today. But the digital twin roll-up shows the hydraulic system health index has slipped from 68 down to 41, driven entirely by the main hydraulic pump."*

---

### Step 3: Sensor Trends (Component Health Inspection)
* **Goal:** Inspect physical telemetry for the hydraulic main pump to show that ML catches anomalies before fixed thresholds trip.
* **Exact Actions:**
  1. In the sidebar, click **"Component Health"** (or click the **"Inspect Component"** link on the AC-017 twin page).
  2. Confirm active component is **Primary Hydraulic Pump (CMP-HYD-017)** on `AC-017`.
  3. Examine the **Telemetry Time-Series Charts**:
     - **Outlet Pressure (PSI):** Notice the oscillatory amplitude increasing over the last 15–20 flight hours.
     - **Fluid Temperature (°C):** Notice an upward thermal drift of +12°C above baseline operating mean.
     - Notice the **Static Alarm Thresholds** (dashed red lines): The raw telemetry has NOT breached the legacy static trip limits.
* **Talking Point:** *"Under traditional scheduled or threshold maintenance, this pump would continue flying until in-flight cavitation or blowout. The raw values are within static tolerance limits, but multi-sensor correlations show abnormal instability."*

---

### Step 4: Anomaly Detection Timeline
* **Goal:** Demonstrate the Isolation Forest anomaly detector detecting early-stage failure signatures.
* **Exact Actions:**
  1. Scroll down to the **Anomaly Score Timeline** on the Component Health page.
  2. Observe the anomaly score curve:
     - The anomaly threshold (0.60) was first sustained **~19 days before simulated catastrophic failure**.
     - Shaded anomaly windows mark the onset of fluid degradation and micro-cavitation.
* **Talking Point:** *"Our ML anomaly detector flagged sustained statistical deviation 19 days in advance of physical failure. This gives logistics teams nearly three weeks of lead time."*

---

### Step 5: Failure Risk & Remaining Useful Life (RUL)
* **Goal:** Examine probabilistic RUL predictions and hazard risk probabilities.
* **Exact Actions:**
  1. View the **Risk & Remaining Useful Life** section:
     - **Failure Risk Gauge:** High risk level (0.62 probability of functional failure within 14 days; was 0.12 twenty days ago).
     - **RUL Prediction:** Estimated **12 days** remaining useful life.
     - **Confidence Band (P10–P90):** 7 to 19 days (illustrating statistical uncertainty).
  2. Use the **Time Replay Slider** (if stepping through historical degradation):
     - Drag to T-15 days: Risk is 0.22, RUL ~28 days.
     - Drag to Current Date: Risk jumps to 0.62, RUL drops to 12 days.
* **Talking Point:** *"The platform provides actionable uncertainty bounds: median RUL is 12 days, with a conservative lower bound of 7 days. This defines our decision window."*

---

### Step 6: Prescriptive Advisory & SHAP Drivers
* **Goal:** Review the automated prescriptive maintenance advisory and explainable AI breakdown.
* **Exact Actions:**
  1. Observe the **Active Advisory Card**:
     - **Advisory ID:** `ADV-AC017-HYD-01`
     - **Priority:** `P2 (High Priority)`
     - **Action:** *"Replace hydraulic main pump within 7 days"*
     - **Status:** `Proposed`
  2. Inspect the **Explainability / Feature Drivers** panel:
     - **SHAP Impact #1:** `outlet_pressure_psi_oscillation` (+38% hazard contribution)
     - **SHAP Impact #2:** `fluid_temp_c_drift` (+26% hazard contribution)
     - **SHAP Impact #3:** `operating_hours_since_overhaul` (+14%)
* **Talking Point:** *"AeroPulse does not provide a black box. Maintenance chiefs see the exact physical drivers from SHAP attribution explaining why the engine recommends replacement."*

---

### Step 7: Spares Inventory Check (The Bottleneck)
* **Goal:** Connect component health with base inventory and supply-chain lead times.
* **Exact Actions:**
  1. Click **"Spares Inventory"** in the sidebar (or click the **"Check Stock"** badge on the advisory).
  2. Find part `HYD-PUMP-442` (Hydraulic Main Pump assembly):
     - **Stock on Hand:** 1 unit in depot storage.
     - **Reserved:** 0 units.
     - **Net Available:** 1 unit.
     - **Procurement Lead Time:** 45 days.
  3. Look at the **Fleet-Level Demand & Lead-Time Scatter Plot**:
     - Notice that another airframe (`AC-023`) also has a pump exhibiting initial wear.
     - If AC-017 consumes the only in-stock pump, the fleet will experience a **shortfall in ~3 weeks**.
* **Talking Point:** *"Here is the power of integrated decision-support. There is 1 pump in stock. If we wait for AC-017 to fail in the field, we face catastrophic unscheduled AOG and a 45-day OEM supply lead time."*

---

### Step 8: Maintenance Scheduling & Bay Bundling
* **Goal:** Convert the advisory into scheduled work bundled with upcoming routine inspections.
* **Exact Actions:**
  1. In the sidebar, click **"Planning & Work Orders"**.
  2. Click **"Propose Maintenance Slot"** or review the automated schedule for `AC-017`:
     - System proposes scheduling at **Bay 2 (Base Alpha Depot)**.
     - Bundling: Combines pump replacement with a scheduled **50-flight-hour periodic airframe check** due in 4 days.
     - **Expected Downtime:** 2.5 days (co-located work package).
* **Talking Point:** *"Rather than grounding the aircraft twice, the planner bundles the hydraulic pump swap into an upcoming routine 50-hour inspection bay slot, keeping scheduled maintenance downtime to just 2.5 days."*

---

### Step 9: Availability Impact Calculation
* **Goal:** Quantify the exact downtime and operational availability saved by acting early.
* **Exact Actions:**
  1. On the Planning screen, observe the **Availability Impact Analysis**:
     - **Proactive Replacement Option:**
       * Bay downtime: 2.5 aircraft-days lost.
       * Supply wait: 0 days (uses current shelf stock).
       * Net availability cost: **-2.5 aircraft-days**.
     - **Reactive Run-to-Failure Counterfactual:**
       * Unscheduled blowout downtime: 4.0 days repairs.
       * Supply wait for emergency expedited part: 5.0 days.
       * Secondary damage risk to hydraulic lines: +2.0 days.
       * Net availability cost: **-9.0 to -11.0 aircraft-days**.
     - **Net Operational Gain:** **+6.5 to +8.5 aircraft-days saved** on this single airframe event.
* **Talking Point:** *"Proactive intervention costs 2.5 days. Waiting for failure costs 9 to 11 days including supply wait. That is an 8-day availability dividend for fleet readiness."*

---

### Step 10: Scenario Simulator (What-If Availability Modeling)
* **Goal:** Run Monte Carlo availability simulations comparing operational decisions side by side.
* **Exact Actions:**
  1. In the sidebar, click **"Scenario Simulator"**.
  2. Notice the side-by-side comparison cards:
     - **Scenario A (Baseline):** Reactive maintenance policy; 30-day median availability = **74.1%** (P10–P90 band: 69.4%–78.2%).
     - **Scenario B (Early Proactive Replacement):** Replace AC-017 hydraulic pump on Day 4; 30-day median availability = **81.8%** (+7.7% readiness uplift, 32 fleet aircraft-days saved).
     - **Scenario C (Supply Stockout Delay):** Zero stock, 45-day lead time; availability falls to **68.5%**.
  3. Observe the Monte Carlo fan chart showing confidence bands across the 100 simulation paths.
* **Talking Point:** *"Commanders can simulate multiple futures in seconds. Scenario B shows our intervention preserves an 81.8% availability posture across the 30-day operational window."*

---

### Step 11: Summary & Wrap-Up
* **Goal:** Reinforce how the platform resolves MoD PS 26249.
* **Exact Actions:**
  1. Click back to **"Fleet Dashboard"**.
  2. Highlight the 4 pillars successfully synthesized into a single decision cycle:
     - **Sensors:** Multi-parameter telemetry anomaly detection.
     - **Digital Twin:** Hierarchy health roll-up from component to airframe to fleet.
     - **Spares:** Real-time stock reservation and lead-time risk mitigation.
     - **Scheduling & Simulation:** Bundled bay slots and Monte Carlo availability proof.
  3. Point to the **Synthetic Data Declaration** banner at the bottom of the page.
* **Talking Point:** *"By breaking down silos between health monitoring, logbook history, spares inventory, and bay capacity, AeroPulse shifts maintenance from reactive panic to proactive availability engineering."*

---

## Demo Checklist & Quick Reference

| Step | Page | Key UI Element | Target Value |
|---|---|---|---|
| **1** | `/dashboard` | Top KPI Bar & Heatgrid | Availability: ~82%, Forecast: ~74%, AC-017 Amber |
| **2** | `/aircraft` | Airframe Schematic | AC-017 Hydraulics Degraded (HI: 41) |
| **3** | `/components` | Telemetry Charts | Outlet oscillation & +12°C fluid temp drift |
| **4** | `/components` | Anomaly Timeline | Sustained anomaly ~19 days before simulated failure |
| **5** | `/components` | Risk Gauge & RUL Band | Risk: 0.62, RUL: 12 days (Band: 7–19d) |
| **6** | `/components` | Advisory Card & SHAP | Replace within 7 days, P2, SHAP top drivers |
| **7** | `/spares` | Spares Inventory Table | Part `HYD-PUMP-442`: 1 on hand, 45d lead time |
| **8** | `/planning` | Bay Slot Gantt | Bay 2 slot bundled with 50h check (2.5d downtime) |
| **9** | `/planning` | Impact Delta | Replace now: -2.5d vs Run-to-failure: -9.0d |
| **10** | `/scenarios` | Simulator Comparison | Baseline: 74% vs Proactive: 81.8% availability |
| **11** | `/dashboard` | Synthetic Data Banner | Full decision loop demonstrated, 100% synthetic |
