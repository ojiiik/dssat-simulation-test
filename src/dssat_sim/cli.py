"""Unified CLI for dssat-sim. Dispatches to simulate / generate / fetch-weather subcommands."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dssat-sim",
        description="DSSAT crop simulation toolkit.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sim_p = sub.add_parser("simulate", help="Run a DSSAT simulation using a crop preset")
    sim_p.add_argument("crop", nargs="?", help="Crop preset (rice/sorghum/maize)")
    sim_p.add_argument("--list", action="store_true", help="List available crop presets")

    gen_p = sub.add_parser("generate", help="Generate scenario CSV via Latin Hypercube Sampling")
    gen_p.add_argument("config", help="Path to YAML config")
    gen_p.add_argument("--output", help="Override `output` from config")
    gen_p.add_argument("--force", action="store_true", help="Overwrite existing output file")
    gen_p.add_argument("--validate", action="store_true", help="Validate config and exit")
    gen_p.add_argument("--preview", action="store_true",
                       help="Print first 5 rows + total count, do not write")

    fw_p = sub.add_parser("fetch-weather",
                          help="Fetch NASA POWER weather data and write yearly CSVs")
    fw_p.add_argument("--lat", type=float, help="Latitude (overrides .env)")
    fw_p.add_argument("--long", type=float, help="Longitude (overrides .env)")
    fw_p.add_argument("--start", help="Start date YYYY-MM-DD (overrides .env)")
    fw_p.add_argument("--end", help="End date YYYY-MM-DD (overrides .env)")
    fw_p.add_argument("--station-code", help="Weather station code (overrides .env)")
    fw_p.add_argument("--output-dir", default="data/weather",
                      help="Directory for output CSVs (default: data/weather)")

    return parser


def _handle_simulate(args) -> int:
    from dssat_sim.presets import CROP_CONFIG
    from dssat_sim.simulator import run_preset

    if args.list:
        print("Available crop presets:")
        for name, info in CROP_CONFIG.items():
            print(f"  {name:10s} {info['crop_type']:10s} cultivar={info['cultivar_id']}")
        return 0

    if not args.crop:
        print("Specify a crop or use --list. See `dssat-sim simulate --help`.",
              file=sys.stderr)
        return 2

    try:
        run_preset(args.crop)
        return 0
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


def _handle_generate(args) -> int:
    from dssat_sim.scenarios import (
        ConfigError,
        load_config,
        resolve_rows,
        validate_config,
        write_csv,
    )

    try:
        cfg = load_config(args.config)
        validate_config(cfg)
    except ConfigError as e:
        print(f"Config error: {e}", file=sys.stderr)
        return 2

    if args.validate:
        print("Config OK.")
        return 0

    output = Path(args.output or cfg.output)

    if not args.preview:
        if output.exists() and not args.force:
            print(f"Output {output} exists. Pass --force to overwrite.", file=sys.stderr)
            return 3
        write_csv(cfg, output)
        print(f"Wrote {cfg.n_samples} scenarios to {output}")
        return 0

    rows = resolve_rows(cfg)
    print(f"Total: {len(rows)} scenarios. First 5:")
    for i, row in enumerate(rows[:5], start=1):
        print(f"  {i}: {row}")
    return 0


def _handle_fetch_weather(args) -> int:
    from dssat_sim.weather import (
        generate_yearly_data_from_config,
        load_config as load_env_config,
    )

    cfg = load_env_config()
    if args.lat is not None:
        cfg["latitude"] = args.lat
    if args.long is not None:
        cfg["longitude"] = args.long
    if args.start:
        cfg["start_date"] = args.start
    if args.end:
        cfg["end_date"] = args.end
    if args.station_code:
        cfg["weather_station"] = args.station_code

    saved_files, _ = generate_yearly_data_from_config(cfg, output_dir=args.output_dir)
    print(f"Wrote {len(saved_files)} weather CSV files to {args.output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "simulate":
        return _handle_simulate(args)
    if args.command == "generate":
        return _handle_generate(args)
    if args.command == "fetch-weather":
        return _handle_fetch_weather(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
