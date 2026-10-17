"""Monte Carlo what-if availability scenario engine (§7).

Implements the four core decision-support scenarios defined in docs/plan.md §7:
1. schedule_maintenance: Schedule aircraft X for planned maintenance on date D
2. spare_unavailable: Critical spare stock set to 0 or lead time extended
3. early_vs_run_to_failure: Proactive early replacement vs run-to-failure
4. extra_capacity: Add workshop bay / extra shift capacity

Each scenario executes dual seeded Monte Carlo simulations (baseline vs scenario),
calculating P10/P50/P90 availability distributions, aircraft-days lost by cause,
and comparative deltas.
"""

from __future__ import annotations

import copy
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.availability.simulator import (
    AircraftSimState,
    FleetSimulator,
    ScheduledMaintenanceTask,
    SimulationConfig,
    SimulationResult,
    SpareSimConfig,
    create_default_simulation_config,
)
from app.models.fleet import Aircraft, Component
from app.models.platform import Prediction, ScenarioRun
from app.models.spares import Inventory, SparePart


async def build_simulation_config_from_db(
    session: AsyncSession | None,
    horizon_days: int = 30,
    runs: int = 300,
    seed: int = 42,
    as_of: date | None = None,
) -> SimulationConfig:
    """Build a simulation configuration initialized from current database state if available."""
    if session is None:
        return create_default_simulation_config(
            num_aircraft=20, horizon_days=horizon_days, runs=runs, seed=seed
        )

    # 1. Fetch aircraft
    ac_stmt = select(Aircraft).order_by(Aircraft.aircraft_id)
    ac_res = await session.execute(ac_stmt)
    aircraft_records = ac_res.scalars().all()

    if not aircraft_records:
        return create_default_simulation_config(
            num_aircraft=20, horizon_days=horizon_days, runs=runs, seed=seed
        )

    # 2. Latest predictions for failure risk
    pred_stmt = select(Component.aircraft_id, Prediction.risk_14d).join(
        Component, Component.component_id == Prediction.component_id
    )
    if as_of is not None:
        pred_stmt = pred_stmt.where(Prediction.as_of_date <= as_of)
    pred_stmt = pred_stmt.order_by(Prediction.as_of_date.desc(), Prediction.created_at.desc())
    pred_res = await session.execute(pred_stmt)
    pred_by_ac: dict[str, float] = {}
    for ac_id, risk_14d in pred_res.all():
        if ac_id and ac_id not in pred_by_ac:
            pred_by_ac[ac_id] = risk_14d

    sim_aircraft: list[AircraftSimState] = []
    for ac in aircraft_records:
        ac_id = ac.aircraft_id
        # Derive daily failure prob from risk_14d: p_daily = 1 - (1 - R_14)**(1/14)
        risk_14d = pred_by_ac.get(ac_id, 0.10)
        daily_hazard = float(1.0 - (1.0 - min(0.99, max(0.01, risk_14d))) ** (1.0 / 14.0))

        # Assign failure part
        part = "HYD-114" if "17" in ac_id or "02" in ac_id else "ENG-772"

        sim_aircraft.append(
            AircraftSimState(
                aircraft_id=ac_id,
                state="Available",
                daily_failure_prob=round(daily_hazard, 4),
                failure_part_number=part,
            )
        )

    # 3. Spares inventory
    spares_stmt = select(SparePart)
    spares_res = await session.execute(spares_stmt)
    spare_parts = spares_res.scalars().all()

    inv_stmt = select(Inventory)
    inv_res = await session.execute(inv_stmt)
    inventory_items = inv_res.scalars().all()
    stock_by_part = {item.part_number: item.on_hand for item in inventory_items}

    sim_spares: dict[str, SpareSimConfig] = {}
    for sp in spare_parts:
        on_hand = stock_by_part.get(sp.part_number, 3)
        sim_spares[sp.part_number] = SpareSimConfig(
            part_number=sp.part_number,
            on_hand=on_hand,
            lead_time_days=sp.lead_time_days,
        )

    if not sim_spares:
        sim_spares = {
            "HYD-114": SpareSimConfig(part_number="HYD-114", on_hand=3, lead_time_days=14),
            "ENG-772": SpareSimConfig(part_number="ENG-772", on_hand=2, lead_time_days=21),
            "AV-301": SpareSimConfig(part_number="AV-301", on_hand=5, lead_time_days=10),
        }

    return SimulationConfig(
        horizon_days=horizon_days,
        runs=runs,
        seed=seed,
        total_bays=4,
        aircraft=sim_aircraft,
        spares=sim_spares,
    )


class ScenarioEngine:
    """Orchestrates comparative Monte Carlo simulation runs."""

    @staticmethod
    def run_scenario(
        scenario_type: str,
        params: dict[str, Any],
        base_config: SimulationConfig,
    ) -> dict[str, Any]:
        """Execute baseline vs scenario simulation runs and compute comparative deltas."""
        # 1. Run Baseline
        baseline_sim = FleetSimulator(base_config)
        baseline_res: SimulationResult = baseline_sim.run()

        # 2. Clone and modify configuration for Scenario
        scen_config = copy.deepcopy(base_config)

        if scenario_type == "schedule_maintenance":
            # Schedule aircraft X for maintenance on start_day for duration_days
            target_ac_id = params.get("aircraft_id", "AC-017")
            start_day = int(params.get("start_day", 5))
            duration_days = int(params.get("duration_days", 3))

            scen_config.scheduled_tasks.append(
                ScheduledMaintenanceTask(
                    aircraft_id=target_ac_id,
                    start_day=start_day,
                    duration_days=duration_days,
                )
            )
            # Proactive maintenance eliminates/resets high failure risk
            for ac in scen_config.aircraft:
                if ac.aircraft_id == target_ac_id:
                    ac.daily_failure_prob = 0.003  # Reset to low baseline risk

        elif scenario_type == "spare_unavailable":
            # Set spare stock to 0 or extend lead time
            part_number = params.get("part_number", "HYD-114")
            stock_override = int(params.get("stock_override", 0))
            lead_time_override = int(params.get("lead_time_days", 45))

            if part_number in scen_config.spares:
                scen_config.spares[part_number].on_hand = stock_override
                scen_config.spares[part_number].lead_time_days = lead_time_override
            else:
                scen_config.spares[part_number] = SpareSimConfig(
                    part_number=part_number,
                    on_hand=stock_override,
                    lead_time_days=lead_time_override,
                )

        elif scenario_type == "early_vs_run_to_failure":
            # Proactive replacement early vs run to failure
            target_ac_id = params.get("aircraft_id", "AC-017")
            early_day = int(params.get("early_replace_day", 3))
            planned_duration = int(params.get("planned_duration_days", 1))

            scen_config.scheduled_tasks.append(
                ScheduledMaintenanceTask(
                    aircraft_id=target_ac_id,
                    start_day=early_day,
                    duration_days=planned_duration,
                )
            )
            for ac in scen_config.aircraft:
                if ac.aircraft_id == target_ac_id:
                    # In scenario, replaced early -> failure probability drops to near zero
                    ac.daily_failure_prob = 0.001

        elif scenario_type == "extra_capacity":
            # Increase workshop bay capacity
            bay_increase = int(params.get("bay_increase", 2))
            scen_config.total_bays += bay_increase

        else:
            raise ValueError(f"Unknown scenario type: '{scenario_type}'")

        # 3. Run Scenario
        scenario_sim = FleetSimulator(scen_config)
        scenario_res: SimulationResult = scenario_sim.run()

        # 4. Compute Deltas
        # Availability delta in percentage points
        avail_delta_pct = round(
            (scenario_res.availability_p50 - baseline_res.availability_p50) * 100.0, 2
        )
        days_lost_delta = round(
            scenario_res.aircraft_days_lost - baseline_res.aircraft_days_lost, 1
        )

        by_cause_delta = {
            "scheduled": round(
                scenario_res.aircraft_days_lost_by_cause["scheduled"]
                - baseline_res.aircraft_days_lost_by_cause["scheduled"],
                1,
            ),
            "unscheduled": round(
                scenario_res.aircraft_days_lost_by_cause["unscheduled"]
                - baseline_res.aircraft_days_lost_by_cause["unscheduled"],
                1,
            ),
            "supply_wait": round(
                scenario_res.aircraft_days_lost_by_cause["supply_wait"]
                - baseline_res.aircraft_days_lost_by_cause["supply_wait"],
                1,
            ),
            "agency_wait": round(
                scenario_res.aircraft_days_lost_by_cause["agency_wait"]
                - baseline_res.aircraft_days_lost_by_cause["agency_wait"],
                1,
            ),
        }

        scenario_id = f"sc_{uuid.uuid4().hex[:8]}"

        return {
            "id": scenario_id,
            "type": scenario_type,
            "params": params,
            "horizon_days": base_config.horizon_days,
            "runs": base_config.runs,
            "seed": base_config.seed,
            "baseline": {
                "availability_p50": baseline_res.availability_p50,
                "availability_p10": baseline_res.availability_p10,
                "availability_p90": baseline_res.availability_p90,
                "aircraft_days_lost": baseline_res.aircraft_days_lost,
                "stockout_probability": baseline_res.stockout_probability,
            },
            "scenario": {
                "availability_p50": scenario_res.availability_p50,
                "availability_p10": scenario_res.availability_p10,
                "availability_p90": scenario_res.availability_p90,
                "aircraft_days_lost": scenario_res.aircraft_days_lost,
                "stockout_probability": scenario_res.stockout_probability,
            },
            "delta": {
                "availability_pct_points": avail_delta_pct,
                "aircraft_days_lost": days_lost_delta,
            },
            "by_cause": by_cause_delta,
            "daily_trend": {
                "baseline": baseline_res.daily_trend,
                "scenario": scenario_res.daily_trend,
            },
        }


async def save_scenario_run(
    session: AsyncSession,
    scenario_result: dict[str, Any],
    created_by: str | None = None,
) -> ScenarioRun:
    """Persist a completed scenario execution into the scenario_runs database table."""
    record = ScenarioRun(
        id=scenario_result["id"],
        type=scenario_result["type"],
        params=scenario_result["params"],
        results={
            "baseline": scenario_result["baseline"],
            "scenario": scenario_result["scenario"],
            "delta": scenario_result["delta"],
            "by_cause": scenario_result["by_cause"],
            "horizon_days": scenario_result["horizon_days"],
            "runs": scenario_result["runs"],
        },
        seed=scenario_result["seed"],
        created_by=created_by,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def list_scenario_runs(
    session: AsyncSession,
    limit: int = 50,
) -> list[ScenarioRun]:
    """Retrieve history of saved what-if scenario runs."""
    stmt = select(ScenarioRun).order_by(ScenarioRun.created_at.desc()).limit(limit)
    res = await session.execute(stmt)
    return list(res.scalars().all())
