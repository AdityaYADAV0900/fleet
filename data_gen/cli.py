"""Command Line Interface for the synthetic data generator."""

import argparse
import asyncio
import os
import sys
import time

from data_gen.config import SimulationConfig
from data_gen.db_loader import bulk_load_to_db
from data_gen.generator import FleetSimulator
from data_gen.report import generate_data_quality_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data_gen",
        description="Integrated Predictive Maintenance Synthetic Fleet Data Generator",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # generate command
    gen_parser = subparsers.add_parser(
        "generate", help="Generate fleet dataset and populate database"
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic generation (default: 42)",
    )
    gen_parser.add_argument("--config", type=str, default=None, help="Path to config YAML file")
    gen_parser.add_argument(
        "--database-url", type=str, default=None, help="PostgreSQL connection URL"
    )
    gen_parser.add_argument(
        "--no-db", action="store_true", help="Generate in memory only without loading to DB"
    )
    gen_parser.add_argument(
        "--no-report", action="store_true", help="Skip generating data quality report after DB load"
    )
    gen_parser.add_argument(
        "--report-path", type=str, default=None, help="Path to write markdown quality report"
    )

    # report command
    rep_parser = subparsers.add_parser(
        "report", help="Generate data quality markdown report from existing database"
    )
    rep_parser.add_argument(
        "--database-url", type=str, default=None, help="PostgreSQL connection URL"
    )
    rep_parser.add_argument(
        "--output", type=str, default=None, help="Path to output markdown report"
    )

    return parser


def run_generate(args: argparse.Namespace) -> int:
    start_time = time.time()
    print("=" * 65)
    print("Synthetic Fleet Data Generator (Phase 2)")
    print("=" * 65)

    config = SimulationConfig.load(args.config)
    if args.seed is not None:
        config.seed = args.seed

    print(f"  • Fleet Size:  {config.fleet.size} aircraft ({config.fleet.type_code})")
    print(f"  • Timeline:    {config.timeline.start_date} to {config.timeline.end_date}")
    print(f"  • Seed:        {config.seed}")
    print("\n[1/3] Simulating fleet flights, latent degradation, and sensors...")

    simulator = FleetSimulator(config)
    dataset = simulator.generate()
    sim_time = time.time() - start_time
    print(f"      Completed in {sim_time:.2f}s:")
    print(f"      - Flights:         {len(dataset.flights):,}")
    print(f"      - Sensor readings: {len(dataset.sensor_readings):,}")
    print(f"      - Fault events:    {len(dataset.fault_events):,}")
    print(f"      - Work orders:     {len(dataset.work_orders):,}")
    print(f"      - Daily statuses:  {len(dataset.aircraft_daily_status):,}")

    if args.no_db:
        print("\n[Notice] --no-db set. Skipping database insertion.")
        return 0

    print("\n[2/3] Bulk streaming into PostgreSQL via binary COPY...")
    db_start = time.time()
    db_url = args.database_url or os.getenv("DATABASE_URL")
    counts = asyncio.run(bulk_load_to_db(dataset, db_url=db_url))
    db_time = time.time() - db_start
    print(f"      Database population completed in {db_time:.2f}s!")
    for table, count in counts.items():
        print(f"      - {table:<25} {count:>8,} rows")

    if not args.no_report:
        print("\n[3/3] Generating Data Quality Report (reports/data_quality.md)...")
        rep_start = time.time()
        asyncio.run(generate_data_quality_report(db_url=db_url, output_path=args.report_path))
        rep_time = time.time() - rep_start
        print(f"      Report written in {rep_time:.2f}s.")

    total_time = time.time() - start_time
    print("\n" + "=" * 65)
    print(f"[SUCCESS] Synthetic fleet generation complete in {total_time:.2f} seconds!")
    print("=" * 65)
    return 0


def run_report(args: argparse.Namespace) -> int:
    print("=" * 60)
    print("Generating Data Quality Report from PostgreSQL")
    print("=" * 60)
    db_url = args.database_url or os.getenv("DATABASE_URL")
    asyncio.run(generate_data_quality_report(db_url=db_url, output_path=args.output))
    print("[SUCCESS] Data quality report generated successfully.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    if argv is None:
        argv = sys.argv[1:]

    # Default to generate --seed 42 if no subcommand provided
    if not argv:
        argv = ["generate", "--seed", "42"]

    args = parser.parse_args(argv)
    if args.command == "generate":
        return run_generate(args)
    elif args.command == "report":
        return run_report(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
