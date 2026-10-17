"""Discrete-event Monte Carlo simulation engine for fleet availability (§7).

Simulates fleet availability over a forward horizon (14 to 60 days, default 30)
across N stochastic runs (default 300 runs), reproducing operational dynamics:
- Aircraft operational states (Available, Scheduled Maintenance, Unscheduled Repair, Awaiting Spares, Awaiting Workshop)
- Maintenance workshop bay capacity and queuing
- Component failures sampled from predictive risk/RUL hazard rates
- Spares inventory tracking, lead-time delays, and stock-out penalties
- Scheduled maintenance windows and early intervention
- Seeded Monte Carlo execution for reproducible P10/P50/P90 distributions
"""

from __future__ import annotations

import copy
import random
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class AircraftSimState:
    """Simulation state for an individual aircraft."""

    aircraft_id: str
    state: str = "Available"  # Available, Scheduled Maintenance, Unscheduled Repair, Awaiting Spares, Awaiting Workshop
    days_in_current_state: int = 0
    remaining_repair_days: int = 0
    assigned_bay: int | None = None
    pending_part_number: str | None = None
    daily_failure_prob: float = 0.015  # Derived from 14-day risk or RUL
    failure_part_number: str = "HYD-114"


@dataclass
class SpareSimConfig:
    """Spares stock and replenishment profile for simulation."""

    part_number: str
    on_hand: int = 5
    lead_time_days: int = 14
    incoming_receipts: list[tuple[int, int]] = field(default_factory=list)  # (day, qty)


@dataclass
class ScheduledMaintenanceTask:
    """Planned maintenance event scheduled for an aircraft."""

    aircraft_id: str
    start_day: int
    duration_days: int = 3


@dataclass
class SimulationConfig:
    """Master configuration for a Monte Carlo simulation run."""

    horizon_days: int = 30
    runs: int = 300
    seed: int = 42
    total_bays: int = 4
    default_repair_days_unscheduled: int = 3
    default_repair_days_scheduled: int = 3
    aircraft: list[AircraftSimState] = field(default_factory=list)
    spares: dict[str, SpareSimConfig] = field(default_factory=dict)
    scheduled_tasks: list[ScheduledMaintenanceTask] = field(default_factory=list)


@dataclass
class SimulationResult:
    """Aggregated output from Monte Carlo simulation."""

    horizon_days: int
    runs: int
    seed: int
    total_aircraft: int
    availability_p50: float
    availability_p10: float
    availability_p90: float
    aircraft_days_lost: float
    aircraft_days_lost_by_cause: dict[str, float]
    stockout_probability: float
    daily_trend: list[dict[str, Any]]  # [{day, p10, p50, p90, mean_avail}]


class FleetSimulator:
    """Discrete-event Monte Carlo simulator for aircraft fleet availability."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config

    def run(self) -> SimulationResult:
        """Execute N Monte Carlo simulation runs and aggregate distribution metrics."""
        cfg = self.config
        num_aircraft = len(cfg.aircraft)
        if num_aircraft == 0:
            raise ValueError("Simulation configuration must contain at least one aircraft.")

        horizon = cfg.horizon_days
        runs = cfg.runs

        # Daily availability curves: shape (runs, horizon)
        daily_avail_matrix = np.zeros((runs, horizon), dtype=np.float64)

        # Downtime days accumulator per run
        run_downtime_scheduled = np.zeros(runs, dtype=np.float64)
        run_downtime_unscheduled = np.zeros(runs, dtype=np.float64)
        run_downtime_spares = np.zeros(runs, dtype=np.float64)
        run_downtime_workshop = np.zeros(runs, dtype=np.float64)
        run_stockout_occurred = np.zeros(runs, dtype=bool)

        # Use seeded RNG for master run reproducibility
        master_rng = random.Random(cfg.seed)

        for r in range(runs):
            run_seed = master_rng.randint(0, 2**31 - 1)
            run_rng = random.Random(run_seed)

            # Deep copy initial aircraft states and spares
            aircraft_list = [copy.copy(ac) for ac in cfg.aircraft]
            spares_stock = {p: s.on_hand for p, s in cfg.spares.items()}

            # Track pending spare receipts: day -> [(part_number, qty)]
            receipts_schedule: dict[int, list[tuple[str, int]]] = {}
            for part_no, s_cfg in cfg.spares.items():
                for r_day, r_qty in s_cfg.incoming_receipts:
                    receipts_schedule.setdefault(r_day, []).append((part_no, r_qty))

            # Workshop bay manager
            available_bays = cfg.total_bays
            workshop_queue: list[AircraftSimState] = []

            # Populate initial states
            for ac in aircraft_list:
                if ac.state in ("Scheduled Maintenance", "Unscheduled Repair"):
                    if available_bays > 0:
                        available_bays -= 1
                    else:
                        ac.state = "Awaiting Workshop"
                        workshop_queue.append(ac)
                elif ac.state == "Awaiting Workshop":
                    workshop_queue.append(ac)

            # Map scheduled tasks by day
            scheduled_by_day: dict[int, list[ScheduledMaintenanceTask]] = {}
            for task in cfg.scheduled_tasks:
                scheduled_by_day.setdefault(task.start_day, []).append(task)

            # Step through each day of the horizon
            for day in range(horizon):
                # 1. Process arriving spare receipts
                if day in receipts_schedule:
                    for part_no, qty in receipts_schedule[day]:
                        spares_stock[part_no] = spares_stock.get(part_no, 0) + qty

                # 2. Check aircraft awaiting spares: if stock arrived, move to workshop queue
                for ac in aircraft_list:
                    if ac.state == "Awaiting Spares" and ac.pending_part_number:
                        p_need = ac.pending_part_number
                        if spares_stock.get(p_need, 0) > 0:
                            spares_stock[p_need] -= 1
                            ac.state = "Awaiting Workshop"
                            ac.pending_part_number = None
                            workshop_queue.append(ac)

                # 3. Advance active maintenance in bays
                for ac in aircraft_list:
                    if ac.state in ("Scheduled Maintenance", "Unscheduled Repair"):
                        ac.remaining_repair_days -= 1
                        if ac.remaining_repair_days <= 0:
                            # Repair complete -> release bay, return to Available
                            ac.state = "Available"
                            ac.remaining_repair_days = 0
                            available_bays = min(cfg.total_bays, available_bays + 1)

                # 4. Admit aircraft from workshop queue into free bays
                while available_bays > 0 and len(workshop_queue) > 0:
                    next_ac = workshop_queue.pop(0)
                    available_bays -= 1
                    # Set active state
                    if next_ac.remaining_repair_days <= 0:
                        next_ac.remaining_repair_days = cfg.default_repair_days_unscheduled
                    next_ac.state = "Unscheduled Repair"

                # 5. Trigger scheduled maintenance events starting today
                if day in scheduled_by_day:
                    for task in scheduled_by_day[day]:
                        target_ac = next(
                            (a for a in aircraft_list if a.aircraft_id == task.aircraft_id),
                            None,
                        )
                        if target_ac and target_ac.state == "Available":
                            target_ac.remaining_repair_days = task.duration_days
                            if available_bays > 0:
                                available_bays -= 1
                                target_ac.state = "Scheduled Maintenance"
                            else:
                                target_ac.state = "Awaiting Workshop"
                                workshop_queue.append(target_ac)

                # 6. Sample stochastic component failures on Available aircraft
                for ac in aircraft_list:
                    if ac.state == "Available":
                        # Stochastic failure Bernoulli trial
                        if run_rng.random() < ac.daily_failure_prob:
                            part_needed = ac.failure_part_number
                            current_stock = spares_stock.get(part_needed, 0)

                            if current_stock > 0:
                                # Part available immediately
                                spares_stock[part_needed] -= 1
                                ac.remaining_repair_days = cfg.default_repair_days_unscheduled
                                if available_bays > 0:
                                    available_bays -= 1
                                    ac.state = "Unscheduled Repair"
                                else:
                                    ac.state = "Awaiting Workshop"
                                    workshop_queue.append(ac)
                            else:
                                # Stock-out!
                                run_stockout_occurred[r] = True
                                ac.state = "Awaiting Spares"
                                ac.pending_part_number = part_needed
                                ac.remaining_repair_days = cfg.default_repair_days_unscheduled
                                # Order replacement part with standard lead time
                                s_conf = cfg.spares.get(part_needed)
                                lead_time = s_conf.lead_time_days if s_conf else 14
                                arrival_day = day + lead_time
                                receipts_schedule.setdefault(arrival_day, []).append(
                                    (part_needed, 1)
                                )

                # 7. Record daily state counts
                avail_count = sum(1 for a in aircraft_list if a.state == "Available")
                sched_count = sum(1 for a in aircraft_list if a.state == "Scheduled Maintenance")
                unsched_count = sum(1 for a in aircraft_list if a.state == "Unscheduled Repair")
                spares_count = sum(1 for a in aircraft_list if a.state == "Awaiting Spares")
                workshop_count = sum(1 for a in aircraft_list if a.state == "Awaiting Workshop")

                daily_avail_matrix[r, day] = avail_count / num_aircraft
                run_downtime_scheduled[r] += sched_count
                run_downtime_unscheduled[r] += unsched_count
                run_downtime_spares[r] += spares_count
                run_downtime_workshop[r] += workshop_count

        # =====================================================================
        # AGGREGATE RESULTS ACROSS RUNS
        # =====================================================================
        # Overall period availability per run (mean over horizon)
        run_overall_avail = np.mean(daily_avail_matrix, axis=1)

        p10_overall = float(np.percentile(run_overall_avail, 10))
        p50_overall = float(np.percentile(run_overall_avail, 50))
        p90_overall = float(np.percentile(run_overall_avail, 90))

        # Downtime days lost (median across runs)
        scheduled_lost = float(np.median(run_downtime_scheduled))
        unscheduled_lost = float(np.median(run_downtime_unscheduled))
        supply_lost = float(np.median(run_downtime_spares))
        agency_lost = float(np.median(run_downtime_workshop))
        total_lost = scheduled_lost + unscheduled_lost + supply_lost + agency_lost

        stockout_prob = float(np.mean(run_stockout_occurred))

        # Daily percentiles curve
        daily_trend: list[dict[str, Any]] = []
        for d in range(horizon):
            day_slice = daily_avail_matrix[:, d]
            daily_trend.append(
                {
                    "day": d + 1,
                    "p10": round(float(np.percentile(day_slice, 10)), 4),
                    "p50": round(float(np.percentile(day_slice, 50)), 4),
                    "p90": round(float(np.percentile(day_slice, 90)), 4),
                    "mean_avail": round(float(np.mean(day_slice)), 4),
                }
            )

        return SimulationResult(
            horizon_days=horizon,
            runs=runs,
            seed=cfg.seed,
            total_aircraft=num_aircraft,
            availability_p50=round(p50_overall, 4),
            availability_p10=round(p10_overall, 4),
            availability_p90=round(p90_overall, 4),
            aircraft_days_lost=round(total_lost, 1),
            aircraft_days_lost_by_cause={
                "scheduled": round(scheduled_lost, 1),
                "unscheduled": round(unscheduled_lost, 1),
                "supply_wait": round(supply_lost, 1),
                "agency_wait": round(agency_lost, 1),
            },
            stockout_probability=round(stockout_prob, 4),
            daily_trend=daily_trend,
        )


def create_default_simulation_config(
    num_aircraft: int = 20,
    horizon_days: int = 30,
    runs: int = 300,
    seed: int = 42,
    total_bays: int = 4,
    default_spare_stock: int = 3,
) -> SimulationConfig:
    """Construct a realistic default simulation config with synthetic aircraft."""
    aircraft: list[AircraftSimState] = []
    for i in range(1, num_aircraft + 1):
        ac_id = f"AC-{i:03d}"
        # Set varied realistic failure hazards (daily prob ~0.005 - 0.035, corresponding to 7% - 40% 14-day risk)
        risk = 0.008 + (i % 6) * 0.005
        # Pick part
        part = "HYD-114" if (i % 2 == 0) else ("ENG-772" if (i % 3 == 0) else "AV-301")
        # Aircraft 17 is hero aircraft with higher risk
        if i == 17:
            risk = 0.045
            part = "HYD-114"
        aircraft.append(
            AircraftSimState(
                aircraft_id=ac_id,
                state="Available",
                daily_failure_prob=risk,
                failure_part_number=part,
            )
        )

    spares = {
        "HYD-114": SpareSimConfig(
            part_number="HYD-114", on_hand=default_spare_stock, lead_time_days=14
        ),
        "ENG-772": SpareSimConfig(
            part_number="ENG-772", on_hand=default_spare_stock, lead_time_days=21
        ),
        "AV-301": SpareSimConfig(
            part_number="AV-301", on_hand=default_spare_stock, lead_time_days=10
        ),
    }

    return SimulationConfig(
        horizon_days=horizon_days,
        runs=runs,
        seed=seed,
        total_bays=total_bays,
        aircraft=aircraft,
        spares=spares,
    )
