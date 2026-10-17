# System Limitations, Synthetic Data Scope, & Operational Realities

**Problem Statement 26249 (MoD / DSSC):** Integrated Predictive Maintenance & Fleet Availability Platform  
**Document Version:** 1.0 (Phase 11 Release)  
**Authoritative Scope Notice:** *This document provides an honest, rigorous engineering disclosure of model boundaries, synthetic data assumptions, and the technical requirements necessary to transition this platform from prototype to operational deployment.*

---

## 1. Synthetic Data Architecture & Nature

### 1.1 Generation Methodology
All operational data in this platform—including flight logs, component degradation states, sensor telemetry streams, maintenance history, work orders, and inventory transactions—is **100% synthetically generated** by the `data_gen` simulation engine.

* **Aircraft Taxonomy:** Generic airframe designations (e.g., *Generic Twin-Engine Transport*, tail numbers `AC-001` through `AC-040`). No proprietary defense aircraft types, unit names, or operational deployments are modeled.
* **Component Degradation:** Modeled via coupled stochastic physical degradation equations (modified exponential wear curves, Weibull hazard functions, and Markov operational states). While grounded in domain physics (thermodynamic drift, pressure oscillations, vibration harmonics), they represent mathematical idealizations.
* **Noise and Artifacts:** Synthetic sensors incorporate Gaussian white noise, random telemetry dropout (simulating loss of data packets), sensor bias drift, and occasional spurious spike artifacts.
* **Ground Truth Boundary:** The platform maintains an isolated `simulation_truth` table for scoring verification. In compliance with strict engineering ethics, **no ML model or scoring engine has access to ground-truth failure counters during training or inference**.

### 1.2 Synthetic Simplifications
1. **Steady-State Cruise Bias:** Most synthetic sensor telemetry represents standardized steady-state flight phases. Transient aerodynamic turbulence, aggressive combat maneuvers, thermal shocks during rapid throttle transitions, and severe ambient weather extremes (e.g., desert sand ingestion, arctic icing) are simplified.
2. **Failure Mode Diversity:** The simulator implements high-frequency failure modes on selected hero subsystems (e.g., hydraulic main pump cavitation, turbine bearing wear, avionics power inverter degradation). An actual multi-role defense aircraft features thousands of discrete failure modes.

---

## 2. Machine Learning Pipeline Scope & Boundaries

### 2.1 Model Architectures
The ML pipeline intentionally employs robust, interpretable tabular models:
* **Anomaly Detection:** Unsupervised Isolation Forests trained per component class on nominal operating regimes.
* **Failure Risk Scoring:** Gradient-Boosted Trees (LightGBM) and Random Forest classifiers predicting probability of functional failure within a 14-day horizon.
* **Remaining Useful Life (RUL):** Quantile Gradient Boosting Regressors estimating median RUL along with P10 and P90 uncertainty intervals.
* **Explainability:** TreeSHAP (SHapley Additive exPlanations) attribution ranking feature contributions for each generated advisory.

### 2.2 Model Assumptions & Limitations
* **Tabular Feature Aggregation:** Time-series telemetry is aggregated into windowed statistical summaries (mean, standard deviation, RMS, min/max, oscillatory variance, and linear slope). The models do not employ raw high-frequency waveform deep learning (e.g., 1D-CNNs, LSTMs, Transformers) to avoid unexplainable black-box decisions.
* **Static Retraining Cycle:** The models operate in an offline-trained, batch-scored paradigm. There is no active online reinforcement learning or autonomous self-adaptation in flight.
* **Evaluation Context:** All reported metrics (ROC-AUC > 0.88, F1 > 0.80, RUL RMSE < 5.0 days) are evaluated strictly on synthetic test splits. **These metrics cannot and must not be extrapolated to real aircraft reliability figures.**

---

## 3. What Real Operational Data Would Change

Transitioning this platform to an operational defense environment (e.g., Base Maintenance Depots, Air Force Commands) would introduce substantial data complexity across five primary dimensions:

### 3.1 High-Frequency HUMS & Flight Data Recorders (FDR)
* **Sampling Rate & Bandwidth:** Real Health and Usage Monitoring Systems (HUMS) record vibration and strain channels at frequencies between 1 kHz and 50 kHz. Telemetry is downloaded via physical ground data receptacles (cartridges) after flight rather than streamed in real time.
* **Flight Regime Segmentation:** Telemetry must be dynamically segmented into distinct flight envelopes (startup, taxi, takeoff, climb, cruise, loiter, descent, landing, thrust-reversal). Sensor thresholds and anomaly baselines must adapt dynamically to each regime.
* **Sensor Degradation vs Component Degradation:** In real operations, sensor harness failures, thermocouple drift, and connector corrosion frequently mimic component failure signatures. Dedicated sensor validation algorithms are required.

### 3.2 Maintenance Logbooks & Unstructured Records
* **Free-Text Engineering Notes:** Historical maintenance records in military aviation typically consist of unstructured, abbreviated text written by ground crews under field conditions (e.g., *"LH pump chattering on descent, replaced filter element"*).
* **NLP & Knowledge Graph Integration:** Transitioning to real operations requires fine-tuned defense-domain NLP models to ingest legacy maintenance information systems, extract fault symptom codes, and link them to Master Minimum Equipment Lists (MMEL) and Fault Isolation Manuals (FIM).

### 3.3 Dynamic Spares Supply Chain & Logistics
* **Dynamic Lead Times:** Real procurement lead times fluctuate based on OEM production cycles, Foreign Military Sales (FMS) agreements, customs clearances, and emergency priority requisitions.
* **Cannibalization Management:** In high-tempo operational units, maintenance officers occasionally authorize component cannibalization (transferring a serviceable part from a grounded aircraft to a priority airframe). The logistics model would need to account for authorized cannibalization paths.
* **Shelf-Life & Batch Tracking:** Real inventory requires tracking time-sensitive items (O-rings, sealants, hydraulic fluid batches) and serialized rotables with tracking of accumulated flight cycles (TSN / TSO).

### 3.4 Multi-Bay Workshop Capacity & Certified Crew Scheduling
* **Trade Skill Constraints:** Aircraft maintenance requires certified technicians across distinct trades (Airframe, Propulsion, Avionics, Electrical, Armament). A bay may be empty, but work cannot proceed without certified inspectors.
* **Tooling & Test Rig Availability:** Major component swaps require specialized ground support equipment (GSE), hydraulic test rigs, and crane facilities whose availability must be dynamically scheduled.

### 3.5 Airworthiness Certification & Regulatory Compliance
* **DO-178C / DO-254 Compliance:** Software utilized to determine aircraft release or deferral must undergo rigorous Level B/C airworthiness certification by military airworthiness authorities (e.g., CEMILAC, FAA, EASA).
* **Prescriptive Advisory Guardrails:** ML models in defense aviation cannot autonomously ground aircraft or release maintenance. They serve strictly as **advisory decision-support systems**. All actionable work orders require sign-off by a qualified maintenance engineer (Chief Technical Officer).

---

## 4. Scope & Ethical Defense Guardrails

1. **Non-Combat & Non-Tactical:** The platform is strictly an engineering decision-support tool. It has zero capability for operational flight dispatch, tactical route planning, weapons payload assignment, or threat-response analysis.
2. **Human-in-the-Loop:** All automated advisories (`P1` through `P4`) are created in a `proposed` status. They require explicit manual review, acceptance, scheduling, or dismissal with recorded justifications.
3. **Transparent Traceability:** Every risk score and advisory is accompanied by SHAP explainability attributes, indicating the physical sensor metrics responsible for the recommendation.
