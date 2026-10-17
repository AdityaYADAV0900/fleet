"""CLI entrypoint for running the Predictive Maintenance Engine batch scoring job.

Usage:
  python -m app.engine.cli [--as-of YYYY-MM-DD] [--aircraft AC-017]
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date

from app.core.database import get_session_factory
from app.engine.scoring_job import run_scoring_job

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("engine.cli")


async def async_main(as_of: date | None = None, aircraft: str | None = None) -> int:
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            summary = await run_scoring_job(
                session=session,
                as_of_date=as_of,
                target_aircraft_id=aircraft,
            )

            print("\n" + "=" * 65)
            print("PREDICTIVE MAINTENANCE ENGINE — BATCH SCORING COMPLETE")
            print("=" * 65)
            print(f"  • Reference As-Of Date:     {summary.as_of_date}")
            print(f"  • Duration:                 {summary.duration_seconds:.2f} seconds")
            print(f"  • Active Components Scored: {summary.components_scored}")
            print(f"  • Model Predictions Saved:  {summary.predictions_recorded}")
            print(f"  • Anomaly Scores Recorded:  {summary.anomaly_scores_recorded}")
            print(f"  • Advisories Generated:     {summary.advisories_generated}")
            print(f"      - Priority P1:          {summary.p1_count}")
            print(f"      - Priority P2:          {summary.p2_count}")
            print(f"  • High-Risk Components:     {summary.high_risk_components}")
            print(f"  • Platform Alerts Fired:    {summary.alerts_generated}")
            print("=" * 65 + "\n")
            return 0
        except Exception as exc:
            logger.exception(f"Engine scoring job failed: {exc}")
            return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run predictive maintenance batch scoring engine.")
    parser.add_argument(
        "--as-of",
        dest="as_of",
        type=str,
        default=None,
        help="Target cutoff date in YYYY-MM-DD format (defaults to latest flight date)",
    )
    parser.add_argument(
        "--aircraft",
        dest="aircraft",
        type=str,
        default=None,
        help="Optional single aircraft filter (e.g. AC-017)",
    )
    args = parser.parse_args()

    as_of_date = None
    if args.as_of:
        try:
            as_of_date = date.fromisoformat(args.as_of)
        except ValueError:
            print(f"Error: Invalid date format '{args.as_of}'. Expected YYYY-MM-DD.")
            return 1

    return asyncio.run(async_main(as_of=as_of_date, aircraft=args.aircraft))


if __name__ == "__main__":
    sys.exit(main())
