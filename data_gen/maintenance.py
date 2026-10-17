"""Maintenance events, fault events, work orders, and turnaround delay modeling."""

import random
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from data_gen.hierarchy import COMPONENT_TYPE_MAP
from data_gen.spares import SparesManager


@dataclass
class ActiveGrounding:
    aircraft_id: str
    component_id: str | None
    maintenance_type: str  # 'scheduled' or 'unscheduled'
    start_date: date
    end_date: date
    spare_wait_end_date: date | None
    queue_wait_end_date: date | None
    action: str  # 'replace', 'repair', 'inspect'
    work_order_id: str


class MaintenanceManager:
    """Orchestrates work orders, fault codes, maintenance actions, and downtime tracking."""

    def __init__(self, spares_mgr: SparesManager, rng: random.Random):
        self.spares_mgr = spares_mgr
        self.rng = rng
        self.event_counter = 1
        self.wo_counter = 1
        self.fault_counter = 1
        self.comp_replacement_counter = 10000

        self.fault_events: list[dict] = []
        self.work_orders: list[dict] = []
        self.maintenance_events: list[dict] = []
        self.active_groundings: dict[str, ActiveGrounding] = {}  # aircraft_id -> ActiveGrounding
        self.new_components_installed: list[dict] = []

    def is_aircraft_grounded(self, aircraft_id: str, current_date: date) -> tuple[bool, str | None]:
        """Check if an aircraft is currently grounded, and if so, return (True, status_reason)."""
        if aircraft_id not in self.active_groundings:
            return False, None

        grounding = self.active_groundings[aircraft_id]
        if current_date > grounding.end_date:
            # Grounding has completed
            del self.active_groundings[aircraft_id]
            return False, None

        # Determine exact downtime subtype
        if grounding.maintenance_type == "scheduled":
            return True, "Scheduled Maintenance"

        # Unscheduled downtime breakdown
        if grounding.spare_wait_end_date and current_date <= grounding.spare_wait_end_date:
            return True, "Awaiting Spares"
        elif grounding.queue_wait_end_date and current_date <= grounding.queue_wait_end_date:
            return True, "Awaiting Workshop"
        else:
            return True, "Unscheduled Repair"

    def trigger_warning_fault(
        self,
        aircraft_id: str,
        component_id: str,
        component_type_id: str,
        current_date: date,
        health: float,
    ) -> None:
        """Record minor or medium fault code warning as degradation sets in."""
        ct_def = COMPONENT_TYPE_MAP.get(component_type_id)
        name = ct_def.name if ct_def else "Subsystem"
        fault_id = f"EVT-{self.fault_counter:06d}"
        self.fault_counter += 1

        sev = "medium" if health < 0.20 else "low"
        code = f"BIT-{component_type_id[-4:]}-{'WARN' if sev == 'low' else 'DEGR'}"
        ts = datetime(current_date.year, current_date.month, current_date.day, 14, 30, tzinfo=UTC)

        self.fault_events.append(
            {
                "event_id": fault_id,
                "aircraft_id": aircraft_id,
                "component_id": component_id,
                "timestamp": ts,
                "fault_code": code,
                "severity": sev,
                "description": f"Pre-failure parameter variance exceedance detected on {name}.",
                "source": "BIT",
            }
        )

    def trigger_failure_maintenance(
        self,
        aircraft_id: str,
        component_id: str,
        component_type_id: str,
        current_date: date,
        is_sudden: bool = False,
    ) -> tuple[dict, str]:
        """Trigger unscheduled replacement and work order for a failed component.

        Returns:
            (new_component_record, new_component_id)
        """
        ct_def = COMPONENT_TYPE_MAP.get(component_type_id)
        ct_name = ct_def.name if ct_def else "Component"
        part_no = ct_def.part_number if ct_def else "GEN-PART"
        crit = ct_def.criticality if ct_def else 4

        # 1. Critical Fault Event
        fault_id = f"EVT-{self.fault_counter:06d}"
        self.fault_counter += 1
        ts = datetime(current_date.year, current_date.month, current_date.day, 16, 0, tzinfo=UTC)
        self.fault_events.append(
            {
                "event_id": fault_id,
                "aircraft_id": aircraft_id,
                "component_id": component_id,
                "timestamp": ts,
                "fault_code": f"BIT-{component_type_id[-4:]}-FAIL",
                "severity": "critical",
                "description": f"Operational failure trip / limit exceedance on {ct_name}.",
                "source": "BIT",
            }
        )

        # 2. Work Order
        wo_id = f"WO-{self.wo_counter:05d}"
        self.wo_counter += 1

        # Assign agency based on criticality and level
        if crit >= 5:
            agency_id = self.rng.choice(["AG-BASE-01", "AG-DEPOT-01"])
        else:
            agency_id = self.rng.choice(["AG-LINE-01", "AG-BASE-01"])

        # Spares check
        avail, spare_wait_days = self.spares_mgr.request_spare(
            part_number=part_no,
            current_date=current_date,
            work_order_id=wo_id,
            location_id="BASE-MAIN",
        )

        # Agency queue delay (0-2 days depending on level)
        queue_wait_days = 0 if agency_id == "AG-LINE-01" else self.rng.randint(1, 3)

        # Active repair duration (0.5 to 2.5 days)
        repair_days = max(1, round(self.rng.uniform(0.8, 2.5)))
        labor_hours = round(repair_days * 8.0 * self.rng.uniform(0.9, 1.4), 1)

        total_downtime_days = spare_wait_days + queue_wait_days + repair_days

        start_time = ts
        spare_end_date = (
            current_date + timedelta(days=spare_wait_days) if spare_wait_days > 0 else None
        )
        queue_end_date = (
            (current_date + timedelta(days=spare_wait_days + queue_wait_days))
            if queue_wait_days > 0
            else None
        )
        end_time = ts + timedelta(days=total_downtime_days)

        delay_reason = None
        if spare_wait_days > 0:
            delay_reason = "Awaiting Spares Replenishment"
        elif queue_wait_days > 0:
            delay_reason = "Awaiting Agency Bay Availability"

        self.work_orders.append(
            {
                "wo_id": wo_id,
                "aircraft_id": aircraft_id,
                "component_id": component_id,
                "advisory_id": None,
                "agency_id": agency_id,
                "opened": start_time,
                "planned_start": start_time + timedelta(days=spare_wait_days + queue_wait_days),
                "actual_start": start_time + timedelta(days=spare_wait_days + queue_wait_days),
                "promised_done": end_time,
                "actual_done": end_time,
                "status": "completed",
                "priority": "P1" if crit >= 4 else "P2",
                "delay_reason": delay_reason,
            }
        )

        # 3. Maintenance Event
        me_id = f"ME-{self.event_counter:05d}"
        self.event_counter += 1
        self.maintenance_events.append(
            {
                "event_id": me_id,
                "aircraft_id": aircraft_id,
                "component_id": component_id,
                "type": "unscheduled",
                "start": start_time,
                "end": end_time,
                "action": "replace",
                "labor_hours": labor_hours,
                "work_order_id": wo_id,
                "root_cause": (
                    f"Latent mechanical degradation of internal assemblies in {ct_name}."
                    if not is_sudden
                    else f"Unheralded sudden shock failure in {ct_name}."
                ),
            }
        )

        # Record grounding
        self.active_groundings[aircraft_id] = ActiveGrounding(
            aircraft_id=aircraft_id,
            component_id=component_id,
            maintenance_type="unscheduled",
            start_date=current_date,
            end_date=current_date + timedelta(days=total_downtime_days),
            spare_wait_end_date=spare_end_date,
            queue_wait_end_date=queue_end_date,
            action="replace",
            work_order_id=wo_id,
        )

        # 4. Install replacement component with fresh serial
        self.comp_replacement_counter += 1
        new_comp_id = f"CMP-{self.comp_replacement_counter:05d}"
        new_serial = f"SN-{part_no}-{self.comp_replacement_counter:05d}"
        new_comp_record = {
            "component_id": new_comp_id,
            "aircraft_id": aircraft_id,
            "component_type_id": component_type_id,
            "serial_no": new_serial,
            "installed_date": current_date + timedelta(days=total_downtime_days),
            "hours_at_install": 0.0,
            "hours_since_new": 0.0,
            "status": "installed",
        }
        self.new_components_installed.append(new_comp_record)

        return new_comp_record, new_comp_id

    def trigger_scheduled_maintenance(
        self,
        aircraft_id: str,
        current_date: date,
        task_name: str,
        duration_days: int = 2,
    ) -> None:
        """Trigger scheduled preventive servicing / inspection event."""
        wo_id = f"WO-{self.wo_counter:05d}"
        self.wo_counter += 1
        agency_id = "AG-BASE-01" if "Major" in task_name else "AG-LINE-01"
        ts = datetime(current_date.year, current_date.month, current_date.day, 7, 0, tzinfo=UTC)
        end_time = ts + timedelta(days=duration_days)

        self.work_orders.append(
            {
                "wo_id": wo_id,
                "aircraft_id": aircraft_id,
                "component_id": None,
                "advisory_id": None,
                "agency_id": agency_id,
                "opened": ts,
                "planned_start": ts,
                "actual_start": ts,
                "promised_done": end_time,
                "actual_done": end_time,
                "status": "completed",
                "priority": "P3",
                "delay_reason": None,
            }
        )

        me_id = f"ME-{self.event_counter:05d}"
        self.event_counter += 1
        self.maintenance_events.append(
            {
                "event_id": me_id,
                "aircraft_id": aircraft_id,
                "component_id": None,
                "type": "scheduled",
                "start": ts,
                "end": end_time,
                "action": "inspect",
                "labor_hours": round(duration_days * 12.0, 1),
                "work_order_id": wo_id,
                "root_cause": None,
            }
        )

        self.active_groundings[aircraft_id] = ActiveGrounding(
            aircraft_id=aircraft_id,
            component_id=None,
            maintenance_type="scheduled",
            start_date=current_date,
            end_date=current_date + timedelta(days=duration_days),
            spare_wait_end_date=None,
            queue_wait_end_date=None,
            action="inspect",
            work_order_id=wo_id,
        )
