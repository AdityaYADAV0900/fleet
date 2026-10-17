# Synthetic Data Quality Report

*Generated at:* `2026-10-04 16:37:53 UTC`  
*Synthetic Fleet:* 40 Generic Twin-Engine Transports | 3 Years (2023 - 2025)

> [!NOTE]
> **Synthetic Data Label:** All data is synthetically simulated for hackathon problem statement 26249. No operational, classified, or real-world military airframe records are represented.

## 1. Table Row Counts

| Table Name | Record Count | Status |
|---|---|---|
| `systems` | 7 | ✅ OK |
| `component_types` | 20 | ✅ OK |
| `spare_parts` | 20 | ✅ OK |
| `agencies` | 3 | ✅ OK |
| `aircraft` | 40 | ✅ OK |
| `scheduled_tasks` | 120 | ✅ OK |
| `components` | 1,297 | ✅ OK |
| `inventory` | 40 | ✅ OK |
| `flights` | 40,946 | ✅ OK |
| `sensor_readings` | 941,758 | ✅ OK |
| `fault_events` | 1,127 | ✅ OK |
| `work_orders` | 1,517 | ✅ OK |
| `maintenance_events` | 1,517 | ✅ OK |
| `inventory_transactions` | 521 | ✅ OK |
| `aircraft_daily_status` | 43,840 | ✅ OK |
| `simulation_truth` | 818,920 | ✅ OK |
| `users` | 3 | ✅ OK |

## 2. Sensor Data Quality and Noise Injection

| Quality Flag | Readings Count | Percentage | Spec Alignment |
|---|---|---|---|
| `valid` | 891,634 | 94.68% | ✅ Normal Signal (> 90%) |
| `dropout` | 23,626 | 2.51% | ✅ Within Spec (2.0% - 3.5%) |
| `drift` | 12,313 | 1.31% | ✅ Expected Noise Profile |
| `stuck` | 9,568 | 1.02% | ✅ Expected Noise Profile |
| `spike` | 4,617 | 0.49% | ✅ Expected Noise Profile |

## 3. Physical Signal Correlation (Sensor vs Latent Health)

Measures whether sensor telemetry carries true degradation signal versus hidden `simulation_truth`:

| Parameter | Component Type | Physical Direction | Pearson Correlation ($r$) | Signal Strength |
|---|---|---|---|---|
| `outlet_pressure_psi` | Hydraulic Pump | Pressure drops with wear | **+0.954** | ✅ Strong Positive |
| `fluid_temp_c` | Hydraulic Pump | Fluid heats with wear | **-0.744** | ✅ Strong Negative |
| `vib_ips` | Engine Compressor | Vibration rises with wear | **-0.976** | ✅ Strong Negative |

## 4. Unscheduled Failure Counts per Component Type

| Component ID | Name | Part Number | Design MTBF | Unscheduled Failures |
|---|---|---|---|---|
| `CT-LG-03` | Main Landing Gear Tyre Set | `LG-303` | 750h | 106 |
| `CT-ELEC-01` | Main Integrated Drive Generator | `ELEC-201` | 2,400h | 72 |
| `CT-LG-01` | Multi-Disc Brake Assembly | `LG-301` | 1,400h | 47 |
| `CT-HYD-03` | Return Line Reservoir Filter | `HYD-116` | 1,500h | 43 |
| `CT-ELEC-02` | Emergency Backup Battery | `ELEC-202` | 1,600h | 40 |
| `CT-HYD-01` | Primary Hydraulic Pump | `HYD-114` | 1,800h | 38 |
| `CT-ECS-01` | Air Cycle Cooling Pack | `ECS-601` | 2,200h | 31 |
| `CT-PROP-02` | High Pressure Turbine | `PROP-102` | 2,200h | 28 |
| `CT-PROP-01` | Main Engine Compressor | `PROP-101` | 2,600h | 22 |
| `CT-FUEL-01` | High Pressure Fuel Boost Pump | `FUEL-501` | 2,600h | 20 |
| `CT-AVION-03` | Air Data Sensor Suite | `AV-403` | 3,000h | 12 |
| `CT-HYD-02` | Flight Control Servoactuator | `HYD-115` | 2,800h | 10 |
| `CT-ECS-02` | Cabin Pressure Regulating Controller | `ECS-602` | 3,200h | 8 |
| `CT-FUEL-02` | Capacitance Fuel Quantity Transmitter | `FUEL-502` | 3,500h | 4 |
| `CT-LG-02` | Main Oleo Shock Strut | `LG-302` | 4,500h | 4 |
| `CT-PROP-03` | Engine Oil Scavenge Pump | `PROP-103` | 3,500h | 4 |
| `CT-ELEC-03` | Primary Power Bus Controller | `ELEC-203` | 4,000h | 3 |
| `CT-AVION-01` | Flight Management Core Computer | `AV-401` | 5,000h | 2 |
| `CT-AVION-02` | Primary Multi-Function Display | `AV-402` | 4,000h | 2 |
| `CT-PROP-04` | Digital Fuel Control Unit | `PROP-104` | 3,200h | 1 |

## 5. Fleet Availability Status Distribution

| Daily State | Aircraft-Days | Percentage | Operational Meaning |
|---|---|---|---|
| **Available** | 38,365 | 87.51% | Fully serviceable and ready for sorties |
| **Scheduled Maintenance** | 2,908 | 6.63% | Undergoing routine phase/calendar inspection |
| **Awaiting Spares** | 1,139 | 2.60% | Grounded waiting for replacement part |
| **Unscheduled Repair** | 768 | 1.75% | Active corrective defect rectification |
| **Awaiting Workshop** | 660 | 1.51% | Grounded waiting for maintenance bay queue |

## 6. Hero Aircraft Verification (AC-017 Hydraulic Degradation Arc)

- **Aircraft Tail:** `AC-017`
- **Target Component:** Primary Hydraulic Pump (`CT-HYD-01`), Serial `SN-HYD-114-00325`
- **Latent Health Range:** Max `0.84`, Min `0.40`
- **Final Latent Health (as of end of 2025):** `0.41` (target ~0.41 - Degraded)
- **Truth Records Recorded:** 1059 days

### AC-017 Spares Inventory Status (`HYD-114`):

| Location | On Hand | Reserved | On Order | Status |
|---|---|---|---|---|
| `BASE-MAIN` | 1 | 0 | 0 | ⚠️ TIGHT SPARES (Hero Arc) |
| `DEPOT-01` | 1 | 0 | 0 | ⚠️ TIGHT SPARES (Hero Arc) |

## 7. Schema Integrity and Invariant Verification

- **Non-Negative Stock Invariant:** `min(on_hand) >= 0`: ✅ PASS (No negative inventory)
- **Foreign Key Integrity:** ✅ Validated via PostgreSQL relational constraints and CASCADE rules.
- **Simulation Truth Protection:** ✅ Ground truth is stored in `simulation_truth` table, isolated from model features.
