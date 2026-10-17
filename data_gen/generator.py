"""Main simulation orchestrator coordinating degradation, flights, sensors, and maintenance."""

import random
from dataclasses import dataclass
from datetime import timedelta

from data_gen.config import SimulationConfig
from data_gen.degradation import DegradationEngine
from data_gen.flights import FlightGenerator
from data_gen.hero import HERO_MAP
from data_gen.hierarchy import (
    AGENCIES,
    COMPONENT_TYPES,
    SYSTEMS,
    build_aircraft_records,
    build_initial_components,
    build_scheduled_tasks,
    build_spare_parts_catalog,
)
from data_gen.maintenance import MaintenanceManager
from data_gen.noise import NoiseInjector
from data_gen.sensors import SensorGenerator
from data_gen.spares import SparesManager
from data_gen.status import StatusTracker


@dataclass
class FleetDataset:
    systems: list[dict]
    component_types: list[dict]
    spare_parts: list[dict]
    agencies: list[dict]
    aircraft: list[dict]
    scheduled_tasks: list[dict]
    components: list[dict]
    inventory: list[dict]
    flights: list[dict]
    sensor_readings: list[dict]
    fault_events: list[dict]
    work_orders: list[dict]
    maintenance_events: list[dict]
    inventory_transactions: list[dict]
    aircraft_daily_status: list[dict]
    simulation_truth: list[dict]


class FleetSimulator:
    """End-to-end reproducible simulator for fleet operations, health degradation, and maintenance."""

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rng = random.Random(config.seed)

    def generate(self) -> FleetDataset:
        """Run the full fleet simulation over the configured timeline."""
        # 1. Initialize Subsystems and Managers
        spares_mgr = SparesManager(self.config.inventory, self.rng)
        noise_injector = NoiseInjector(self.config.noise, self.rng)
        deg_engine = DegradationEngine(self.config.degradation, self.rng)
        flight_gen = FlightGenerator(self.config.operations, self.rng)
        sensor_gen = SensorGenerator(noise_injector, self.rng)
        maint_mgr = MaintenanceManager(spares_mgr, self.rng)
        status_tracker = StatusTracker()

        # 2. Build Reference Hierarchy
        systems_records = [{"system_id": s.system_id, "name": s.name} for s in SYSTEMS]
        comp_types_records = [
            {
                "component_type_id": ct.component_type_id,
                "system_id": ct.system_id,
                "name": ct.name,
                "criticality": ct.criticality,
                "design_life_hours": ct.design_life_hours,
                "mtbf_hours": ct.mtbf_hours,
                "part_number": ct.part_number,
                "is_repairable": ct.is_repairable,
            }
            for ct in COMPONENT_TYPES
        ]
        spares_catalog = build_spare_parts_catalog()
        agencies_records = list(AGENCIES)

        # 3. Build Aircraft and Initial Components
        aircraft_records = build_aircraft_records(
            size=self.config.fleet.size,
            tail_prefix=self.config.fleet.tail_prefix,
            type_code=self.config.fleet.type_code,
            comm_start=self.config.fleet.commissioned_start,
            bases=self.config.fleet.bases,
            rng=self.rng,
        )
        aircraft_map = {ac["aircraft_id"]: ac for ac in aircraft_records}

        components_records, initial_health_map = build_initial_components(
            aircraft_list=aircraft_records,
            rng=self.rng,
        )
        components_map = {c["component_id"]: c for c in components_records}

        # Track active installed components per aircraft: ac_id -> list of component_id
        active_components_by_aircraft: dict[str, list[str]] = {}
        for c in components_records:
            ac_id = c["aircraft_id"]
            if ac_id not in active_components_by_aircraft:
                active_components_by_aircraft[ac_id] = []
            active_components_by_aircraft[ac_id].append(c["component_id"])

        # Register initial components in degradation engine
        for c in components_records:
            cid = c["component_id"]
            deg_engine.register_component(
                component_id=cid,
                component_type_id=c["component_type_id"],
                aircraft_id=c["aircraft_id"],
                initial_health=initial_health_map[cid],
                hours_since_new=c["hours_since_new"],
            )

        # Register a couple components for false-alarm sensor drift
        drift_candidates = [c["component_id"] for c in components_records[:15]]
        for dc in self.rng.sample(drift_candidates, min(3, len(drift_candidates))):
            noise_injector.register_drift_component(dc)

        # 4. Spares and Inventory Initialization
        # Apply hero override: tight spares for AC-017 hydraulic pump
        hero_overrides = {}
        if "AC-017" in HERO_MAP and HERO_MAP["AC-017"].force_spare_stock:
            hero_overrides.update(HERO_MAP["AC-017"].force_spare_stock)
        inventory_records = spares_mgr.initialize_inventory(hero_overrides)

        # 5. Scheduled Tasks
        scheduled_tasks_records = build_scheduled_tasks(aircraft_records)
        tasks_by_ac: dict[str, list[dict]] = {}
        for st in scheduled_tasks_records:
            ac_id = st["aircraft_id"]
            if ac_id not in tasks_by_ac:
                tasks_by_ac[ac_id] = []
            tasks_by_ac[ac_id].append(st)

        # Containers for operational outputs
        all_flights: list[dict] = []
        all_readings: list[dict] = []
        simulation_truth_records: list[dict] = []
        truth_counter = 1

        # Track warning faults emitted to avoid repeating every flight
        emitted_warnings: set[str] = set()

        # 6. Simulation Timeline Loop (Day by Day)
        start_date = self.config.timeline.start_date
        end_date = self.config.timeline.end_date
        total_days = (end_date - start_date).days + 1

        for day_offset in range(total_days):
            current_date = start_date + timedelta(days=day_offset)

            # A. Process arriving spare shipments
            spares_mgr.process_daily_deliveries(current_date)

            # B. Check aircraft statuses for today
            available_aircraft_today: list[str] = []

            for ac in aircraft_records:
                ac_id = ac["aircraft_id"]
                is_grounded, ground_status = maint_mgr.is_aircraft_grounded(ac_id, current_date)

                if is_grounded and ground_status:
                    status_tracker.record_day(
                        aircraft_id=ac_id,
                        current_date=current_date,
                        status=ground_status,
                        reason=f"Maintenance grounding active ({ground_status}).",
                    )
                else:
                    # Aircraft is available
                    status_tracker.record_day(
                        aircraft_id=ac_id,
                        current_date=current_date,
                        status="Available",
                        reason=None,
                    )
                    available_aircraft_today.append(ac_id)

            # C. Check scheduled maintenance tasks compliance
            for ac_id in list(available_aircraft_today):
                ac = aircraft_map[ac_id]
                for st in tasks_by_ac.get(ac_id, []):
                    if ac["total_flight_hours"] >= st["due_hours"]:
                        # Trigger scheduled maintenance!
                        maint_mgr.trigger_scheduled_maintenance(
                            aircraft_id=ac_id,
                            current_date=current_date,
                            task_name=st["task_name"],
                            duration_days=2
                            if "100" in st["task_name"]
                            else (4 if "300" in st["task_name"] else 8),
                        )
                        st["last_done_hours"] = ac["total_flight_hours"]
                        st["due_hours"] = ac["total_flight_hours"] + st["interval_hours"]
                        available_aircraft_today.remove(ac_id)
                        break

            # D. Generate flight sorties for today
            daily_flights = flight_gen.generate_flights_for_day(
                current_date=current_date,
                available_aircraft_ids=available_aircraft_today,
            )
            all_flights.extend(daily_flights)

            # E. Process each flight: wear, health, sensors, failures
            for fl in daily_flights:
                ac_id = fl["aircraft_id"]
                duration = fl["duration_hours"]
                cycles = fl["cycles"]

                # Update aircraft totals
                ac = aircraft_map[ac_id]
                ac["total_flight_hours"] = round(ac["total_flight_hours"] + duration, 1)
                ac["total_cycles"] += cycles

                # Collect health pairs for sensor generation
                comp_health_pairs: list[tuple[str, str, float]] = []
                installed_comp_ids = list(active_components_by_aircraft.get(ac_id, []))

                for comp_id in installed_comp_ids:
                    comp_rec = components_map[comp_id]
                    ct_id = comp_rec["component_type_id"]

                    # Step degradation
                    true_h, phase, is_failed = deg_engine.step_degradation(comp_id, fl)
                    comp_rec["hours_since_new"] = round(comp_rec["hours_since_new"] + duration, 1)

                    # Record ground truth
                    simulation_truth_records.append(
                        {
                            "truth_id": truth_counter,
                            "component_id": comp_id,
                            "date": current_date,
                            "true_health": true_h,
                            "degradation_phase": phase,
                            "is_failed": is_failed,
                        }
                    )
                    truth_counter += 1

                    # Check warning fault
                    if (
                        true_h < self.config.degradation.warning_threshold
                        and comp_id not in emitted_warnings
                    ):
                        maint_mgr.trigger_warning_fault(
                            aircraft_id=ac_id,
                            component_id=comp_id,
                            component_type_id=ct_id,
                            current_date=current_date,
                            health=true_h,
                        )
                        emitted_warnings.add(comp_id)

                    # Check failure event
                    if is_failed:
                        comp_rec["status"] = "scrapped"
                        # Trigger unscheduled maintenance and replacement
                        new_comp_rec, new_comp_id = maint_mgr.trigger_failure_maintenance(
                            aircraft_id=ac_id,
                            component_id=comp_id,
                            component_type_id=ct_id,
                            current_date=current_date,
                            is_sudden=(phase == "sudden"),
                        )
                        # Replace in active list
                        components_map[new_comp_id] = new_comp_rec
                        components_records.append(new_comp_rec)
                        active_components_by_aircraft[ac_id].remove(comp_id)
                        active_components_by_aircraft[ac_id].append(new_comp_id)
                        # Register new component in degradation engine
                        deg_engine.register_component(
                            component_id=new_comp_id,
                            component_type_id=ct_id,
                            aircraft_id=ac_id,
                            initial_health=1.0,
                            hours_since_new=0.0,
                        )

                    comp_health_pairs.append((comp_id, ct_id, true_h))

                # Generate sensor readings for this flight
                flight_readings = sensor_gen.generate_readings_for_flight(
                    flight=fl,
                    component_health_pairs=comp_health_pairs,
                )
                all_readings.extend(flight_readings)

        # 7. Final Package
        return FleetDataset(
            systems=systems_records,
            component_types=comp_types_records,
            spare_parts=spares_catalog,
            agencies=agencies_records,
            aircraft=aircraft_records,
            scheduled_tasks=scheduled_tasks_records,
            components=components_records,
            inventory=inventory_records,
            flights=all_flights,
            sensor_readings=all_readings,
            fault_events=maint_mgr.fault_events,
            work_orders=maint_mgr.work_orders,
            maintenance_events=maint_mgr.maintenance_events,
            inventory_transactions=spares_mgr.transactions,
            aircraft_daily_status=status_tracker.daily_status_records,
            simulation_truth=simulation_truth_records,
        )
