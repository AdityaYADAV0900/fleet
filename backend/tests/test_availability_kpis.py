"""Unit tests for Fleet Availability KPI functions with exact hand-computed fixtures."""

from app.availability.kpis import (
    calculate_backlog,
    calculate_downtime_by_cause,
    calculate_failure_rate,
    calculate_fleet_availability,
    calculate_inherent_availability,
    calculate_mtbf,
    calculate_mttr,
    calculate_operational_availability,
    calculate_readiness_proxy,
    calculate_serviceability,
    calculate_spare_fill_rate,
    calculate_turnaround,
)


def test_hand_computed_fleet_availability():
    """Verify fleet availability percentage matches hand-computed fixture (§1.8).

    Fixture:
      Available: 85 days
      Scheduled Maintenance: 8 days
      Unscheduled Repair: 4 days
      Awaiting Spares: 2 days
      Awaiting Workshop: 1 day
      Total: 100 days
      Expected: 85.0%
    """
    days = {
        "Available": 85,
        "Scheduled Maintenance": 8,
        "Unscheduled Repair": 4,
        "Awaiting Spares": 2,
        "Awaiting Workshop": 1,
    }
    assert calculate_fleet_availability(days) == 85.0

    # Edge cases
    assert calculate_fleet_availability({}) == 100.0
    assert calculate_fleet_availability({"Available": 0, "Unscheduled Repair": 10}) == 0.0


def test_hand_computed_inherent_availability():
    """Verify Inherent Availability Ai = MTBF / (MTBF + MTTR).

    Fixture:
      MTBF = 475.0 hours
      MTTR = 25.0 hours
      Ai = 475 / (475 + 25) = 475 / 500 = 0.95 -> 95.0%
    """
    ai = calculate_inherent_availability(mtbf_hours=475.0, mttr_hours=25.0)
    assert ai == 95.0

    # 100% when no MTTR
    assert calculate_inherent_availability(mtbf_hours=500.0, mttr_hours=0.0) == 100.0


def test_hand_computed_operational_availability():
    """Verify Operational Availability Ao = MTBM / (MTBM + MDT).

    Fixture:
      MTBM = 240.0 hours
      MDT = 60.0 hours (including supply delay and agency queue)
      Ao = 240 / (240 + 60) = 240 / 300 = 0.80 -> 80.0%
    """
    ao = calculate_operational_availability(mtbm_hours=240.0, mdt_hours=60.0)
    assert ao == 80.0


def test_hand_computed_serviceability():
    """Verify snapshot aircraft serviceability fraction.

    Fixture:
      17 available out of 20 total airframes.
      Serviceability = 17 / 20 * 100 = 85.0%
    """
    assert calculate_serviceability(available_count=17, total_count=20) == 85.0
    assert calculate_serviceability(available_count=0, total_count=20) == 0.0
    assert calculate_serviceability(available_count=20, total_count=20) == 100.0


def test_hand_computed_downtime_by_cause():
    """Verify breakdown of downtime by cause matches hand-calculated proportions.

    Fixture:
      Scheduled: 20 days
      Unscheduled: 10 days
      Supply Wait: 6 days
      Agency Wait: 4 days
      Total downtime: 40 days
      Proportions:
        Scheduled: 20/40 = 50.0%
        Unscheduled: 10/40 = 25.0%
        Supply Wait: 6/40 = 15.0%
        Agency Wait: 4/40 = 10.0%
    """
    days = {
        "Available": 60,
        "Scheduled Maintenance": 20,
        "Unscheduled Repair": 10,
        "Awaiting Spares": 6,
        "Awaiting Workshop": 4,
    }
    split = calculate_downtime_by_cause(days)
    assert split["total_downtime_days"] == 40
    assert split["scheduled_days"] == 20
    assert split["unscheduled_days"] == 10
    assert split["supply_wait_days"] == 6
    assert split["agency_wait_days"] == 4
    assert split["scheduled_pct"] == 50.0
    assert split["unscheduled_pct"] == 25.0
    assert split["supply_wait_pct"] == 15.0
    assert split["agency_wait_pct"] == 10.0


def test_hand_computed_mtbf():
    """Verify MTBF = Operating Hours / Failure Count.

    Fixture:
      Operating Hours: 12,000.0
      Failures: 8
      MTBF = 12000 / 8 = 1,500.0 hours
    """
    assert calculate_mtbf(operating_hours=12000.0, failure_count=8) == 1500.0
    # Zero failures -> returns total operating hours
    assert calculate_mtbf(operating_hours=500.0, failure_count=0) == 500.0


def test_hand_computed_mttr():
    """Verify MTTR is the mean of active repair times.

    Fixture:
      Repair events: [8.0, 12.0, 16.0] hours
      Mean = 36.0 / 3 = 12.0 hours
    """
    assert calculate_mttr([8.0, 12.0, 16.0]) == 12.0
    assert calculate_mttr([]) == 0.0


def test_hand_computed_turnaround():
    """Verify turnaround time is the mean days from WO open to release.

    Fixture:
      Turnaround durations: [3.0, 5.0, 7.0] days
      Mean = 15.0 / 3 = 5.0 days
    """
    assert calculate_turnaround([3.0, 5.0, 7.0]) == 5.0
    assert calculate_turnaround([]) == 0.0


def test_hand_computed_failure_rate():
    """Verify failure rate per 1,000 flight hours.

    Fixture:
      Failures: 6
      Total flight hours: 15,000.0
      Rate = (6 / 15000) * 1000 = 0.4 failures / 1k hrs
    """
    assert calculate_failure_rate(failure_count=6, total_flight_hours=15000.0) == 0.4
    assert calculate_failure_rate(failure_count=0, total_flight_hours=10000.0) == 0.0


def test_hand_computed_backlog():
    """Verify backlog open orders and man-hours calculations."""
    res = calculate_backlog(open_orders_count=7, outstanding_labor_hours=56.5)
    assert res["open_orders"] == 7
    assert res["outstanding_man_hours"] == 56.5


def test_hand_computed_readiness_proxy():
    """Verify readiness proxy calculation.

    Fixture:
      Total fleet: 20
      Available airframes: 16 (AC-001 through AC-016)
      Airframes with open P1/P2 advisories: 4 (AC-001, AC-002, AC-017, AC-018)
      Airframes that are Available AND have NO P1/P2:
        AC-003 through AC-016 -> 14 airframes.
      Readiness proxy = 14 / 20 = 70.0%
    """
    available_ids = {f"AC-{i:03d}" for i in range(1, 17)}
    at_risk_ids = {"AC-001", "AC-002", "AC-017", "AC-018"}
    proxy = calculate_readiness_proxy(available_ids, at_risk_ids, total_aircraft=20)
    assert proxy == 70.0


def test_hand_computed_spare_fill_rate():
    """Verify spare fill rate percentage.

    Fixture:
      Total requests: 80
      Immediate issues without delay: 72
      Fill rate = 72 / 80 * 100 = 90.0%
    """
    assert calculate_spare_fill_rate(immediate_issues=72, total_demands=80) == 90.0
    assert calculate_spare_fill_rate(immediate_issues=0, total_demands=0) == 100.0
