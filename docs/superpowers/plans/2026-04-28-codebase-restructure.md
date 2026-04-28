# Codebase Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the flat-layout DSSAT codebase into a modern installable Python package (`src/` layout, `pyproject.toml`, `dssat-sim` console script) in a single PR with 8 sequential commits, each with verification gates.

**Architecture:** Move all library code into `src/dssat_sim/` (simulator, weather, presets, scenarios, cli). Add a unified argparse-based CLI dispatcher with three subcommands (`simulate`, `generate`, `fetch-weather`). Keep `run_simulation.py` and `run_configured_simulation.py` at root as 2-line backward-compat shims. Move data folders into `data/` and runtime outputs into `results/`. Delete legacy notebook and `requirements.txt`.

**Tech Stack:** Python 3.10+, setuptools (build), pytest (test), scipy/pandas/PyYAML/DSSATTools (existing deps).

**Spec reference:** `docs/superpowers/specs/2026-04-28-codebase-restructure-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `pyproject.toml` | NEW | Package metadata, deps, console script registration |
| `src/dssat_sim/__init__.py` | NEW | Public API re-exports (minimal) |
| `src/dssat_sim/simulator.py` | MOVED from `dssat_simulator.py` | DSSATSimulator class + new `run_preset()` helper |
| `src/dssat_sim/weather.py` | MOVED from `get_weather.py` | NASA POWER fetch |
| `src/dssat_sim/presets.py` | MOVED from `config.py` | Crop/weather/soil configuration constants |
| `src/dssat_sim/scenarios.py` | MOVED from `scenario_generator.py` | LHS scenario generator |
| `src/dssat_sim/cli.py` | NEW | argparse dispatcher for `dssat-sim` |
| `tests/conftest.py` | MODIFIED | Drop sys.path hack (no longer needed after install) |
| `tests/test_*.py` | MODIFIED | Imports updated `scenario_generator` → `dssat_sim.scenarios` |
| `run_simulation.py` | MODIFIED | Becomes 3-line backward-compat shim |
| `run_configured_simulation.py` | MODIFIED | Becomes 3-line backward-compat shim |
| `data/weather/` | MOVED from `weather_data/` | NASA weather CSVs |
| `data/soil/` | MOVED from `soil_data/` | SOIL.SOL profile |
| `data/scenarios/scenario.csv` | MOVED from `scenario.csv` | Pre-generated scenarios |
| `examples/scenario_config.yaml` | MOVED from `scenario_config.example.yaml` | Generator config example |
| `examples/.env.example` | MOVED from `.env.example` | Weather fetch env example |
| `.gitignore` | MODIFIED | Add `.idea/`, `.ipynb_checkpoints/`, `.dssat_env_x86/`, `*.egg-info/`, `build/`, `dist/`, `results/` |
| `dssat-simulation.ipynb` | DELETED | Legacy notebook |
| `requirements.txt` | DELETED | Replaced by pyproject.toml |
| `simulation_results/` | DELETED | Old artifacts (gitignored at new path) |
| `README.md` | MODIFIED | New install/usage instructions |

---

## Pre-flight: Branch & baseline capture

Do this once before Task 1. The baseline output is the regression check used in Tasks 4 and 8.

- [ ] **Step 1: Create feature branch**

```bash
git checkout master
git pull origin master
git checkout -b feat/codebase-restructure
git status   # should show clean working tree
```

- [ ] **Step 2: Capture baseline test result**

```bash
python3.10 -m pytest -v 2>&1 | tail -5
```

Expected: `57 passed`. Note this number — it's the regression target.

- [ ] **Step 3: Capture baseline LHS output**

```bash
python3.10 scenario_generator.py scenario_config.example.yaml --output /tmp/before.csv --force
md5 /tmp/before.csv | tee /tmp/before.md5
```

Save the md5; in Task 4 and Task 8 we re-generate and confirm md5 matches.

---

## Task 1: Foundation — pyproject.toml + package skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/dssat_sim/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

Create `pyproject.toml` with this exact content:

```toml
[build-system]
requires = ["setuptools>=61", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dssat-sim"
version = "0.1.0"
description = "DSSAT crop simulation toolkit with NASA POWER weather + LHS scenario generation"
readme = "README.md"
requires-python = ">=3.10"
authors = [{ name = "Dayatani" }]
dependencies = [
    "DSSATTools==3.0.0.post1",
    "pandas>=2.0",
    "python-dotenv>=1.0",
    "PyYAML>=6.0",
    "requests>=2.30",
    "scipy>=1.14",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-cov>=7.0"]

[project.scripts]
dssat-sim = "dssat_sim.cli:main"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 2: Create empty package init**

Create `src/dssat_sim/__init__.py`:

```python
"""dssat_sim — DSSAT crop simulation toolkit."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Install package in editable mode**

```bash
pip install -e .
```

Expected: ends with `Successfully installed dssat-sim-0.1.0` (or similar). No errors.

- [ ] **Step 4: Verify import**

```bash
python3.10 -c "import dssat_sim; print(dssat_sim.__version__)"
```

Expected: `0.1.0`

- [ ] **Step 5: Verify existing tests still pass (no scenarios.py changes yet)**

```bash
python3.10 -m pytest -v 2>&1 | tail -3
```

Expected: `57 passed`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/dssat_sim/__init__.py
git commit -m "chore: scaffold dssat_sim package and pyproject.toml"
```

---

## Task 2: Move scenarios.py + update test imports

**Files:**
- Move: `scenario_generator.py` → `src/dssat_sim/scenarios.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_generator.py`
- Modify: `tests/test_param_types.py`

- [ ] **Step 1: Move file with git history preserved**

```bash
git mv scenario_generator.py src/dssat_sim/scenarios.py
```

- [ ] **Step 2: Drop sys.path hack in conftest.py**

`tests/conftest.py` currently injects the project root onto `sys.path` so `import scenario_generator` works. After install, `dssat_sim` resolves via the installed package. Replace `tests/conftest.py` content with:

```python
"""pytest configuration. Empty after package install — kept for future fixtures."""
```

- [ ] **Step 3: Update test_param_types.py imports**

In `tests/test_param_types.py`, replace:

```python
from scenario_generator import (
    BundleParam,
    CategoricalParam,
    DateParam,
    FloatParam,
    IntParam,
)
```

with:

```python
from dssat_sim.scenarios import (
    BundleParam,
    CategoricalParam,
    DateParam,
    FloatParam,
    IntParam,
)
```

- [ ] **Step 4: Update test_config.py imports**

In `tests/test_config.py`, replace:

```python
from scenario_generator import Config, ConfigError, load_config, validate_config
```

with:

```python
from dssat_sim.scenarios import Config, ConfigError, load_config, validate_config
```

- [ ] **Step 5: Update test_generator.py imports**

In `tests/test_generator.py`, replace:

```python
from scenario_generator import (
    BundleParam,
    CategoricalParam,
    Config,
    CSV_COLUMNS,
    DateParam,
    FloatParam,
    IntParam,
    build_params,
    resolve_rows,
    sample_rows,
    write_csv,
)
```

with:

```python
from dssat_sim.scenarios import (
    BundleParam,
    CategoricalParam,
    Config,
    CSV_COLUMNS,
    DateParam,
    FloatParam,
    IntParam,
    build_params,
    resolve_rows,
    sample_rows,
    write_csv,
)
```

Also update the `PROJECT_ROOT` line and the subprocess invocation. Replace:

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_cli_generates_csv(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 5\n"
        "seed: 1\n"
        "parameters:\n"
        "  planting_date: {type: date, min: 2021-05-01, max: 2021-07-01}\n"
        "  plant_population: {type: float, min: 7, max: 15}\n"
    )
    out_path = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
```

with the new path:

```python
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_MODULE = PROJECT_ROOT / "src" / "dssat_sim" / "scenarios.py"


def test_cli_generates_csv(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 5\n"
        "seed: 1\n"
        "parameters:\n"
        "  planting_date: {type: date, min: 2021-05-01, max: 2021-07-01}\n"
        "  plant_population: {type: float, min: 7, max: 15}\n"
    )
    out_path = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(SCENARIOS_MODULE),
         str(cfg_path), "--output", str(out_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
```

Apply the same `SCENARIOS_MODULE` replacement (instead of `PROJECT_ROOT / "scenario_generator.py"`) in all 6 other CLI subprocess test invocations: `test_cli_invalid_config_exits_nonzero`, `test_cli_validate_only`, `test_cli_preview`, `test_cli_refuses_overwrite_without_force`, `test_cli_force_overwrites`, `test_example_config_generates_valid_csv`, `test_example_bundle_mode_via_yaml`.

(Note: in Task 4 these subprocess tests get rewired again to use the `dssat-sim` console script. For Task 2 we keep the same script-execution path, just at its new location.)

- [ ] **Step 6: Run full test suite**

```bash
python3.10 -m pytest -v 2>&1 | tail -5
```

Expected: `57 passed`.

- [ ] **Step 7: Verify package import**

```bash
python3.10 -c "from dssat_sim.scenarios import write_csv; print('ok')"
```

Expected: `ok`

- [ ] **Step 8: Commit**

```bash
git add src/dssat_sim/scenarios.py tests/conftest.py tests/test_config.py tests/test_generator.py tests/test_param_types.py
git commit -m "refactor: move scenario_generator into dssat_sim.scenarios package"
```

---

## Task 3: Move simulator, weather, presets

**Files:**
- Move (then `git add` since untracked): `dssat_simulator.py` → `src/dssat_sim/simulator.py`
- Move (then `git add` since untracked): `get_weather.py` → `src/dssat_sim/weather.py`
- Move (then `git add` since untracked): `config.py` → `src/dssat_sim/presets.py`
- Modify: `src/dssat_sim/__init__.py`

(These three source files were never committed during the initial setup, so they're untracked. `git mv` would fail on untracked files — use plain `mv` and `git add` at the new path.)

- [ ] **Step 1: Move simulator.py**

```bash
mkdir -p src/dssat_sim
mv dssat_simulator.py src/dssat_sim/simulator.py
```

No content changes in this task — just relocation. The simulator imports from `DSSATTools`, `pandas`, etc. (no internal cross-module imports).

- [ ] **Step 2: Move weather.py**

```bash
mv get_weather.py src/dssat_sim/weather.py
```

No content changes.

- [ ] **Step 3: Move presets.py**

```bash
mv config.py src/dssat_sim/presets.py
```

No content changes (paths inside `WEATHER_CONFIG`/`SOIL_CONFIG`/`OUTPUT_CONFIG` get updated in Task 6).

- [ ] **Step 4: Re-export DSSATSimulator in package init**

Replace `src/dssat_sim/__init__.py` with:

```python
"""dssat_sim — DSSAT crop simulation toolkit."""

from dssat_sim.simulator import DSSATSimulator

__version__ = "0.1.0"
__all__ = ["DSSATSimulator"]
```

- [ ] **Step 5: Verify imports**

```bash
python3.10 -c "from dssat_sim import DSSATSimulator; print('simulator ok')"
python3.10 -c "from dssat_sim.weather import generate_yearly_data_from_config; print('weather ok')"
python3.10 -c "from dssat_sim.presets import CROP_CONFIG; print('presets ok:', list(CROP_CONFIG.keys()))"
```

Expected:
```
simulator ok
weather ok
presets ok: ['rice', 'sorghum', 'maize']
```

- [ ] **Step 6: Run full test suite**

```bash
python3.10 -m pytest -v 2>&1 | tail -3
```

Expected: `57 passed`. (None of the existing tests touch simulator/weather/presets, but verify there's no collection regression.)

- [ ] **Step 7: Commit**

```bash
git add src/dssat_sim/simulator.py src/dssat_sim/weather.py src/dssat_sim/presets.py src/dssat_sim/__init__.py
git commit -m "refactor: move simulator, weather, and presets into dssat_sim package"
```

---

## Task 4: CLI dispatcher + run_preset() helper

**Files:**
- Create: `src/dssat_sim/cli.py`
- Modify: `src/dssat_sim/simulator.py` (append `run_preset()` helper)
- Modify: `src/dssat_sim/__init__.py` (export `run_preset`)
- Modify: `tests/test_generator.py` (rewire CLI subprocess tests to use `dssat-sim`)

- [ ] **Step 1: Add `run_preset()` to simulator.py**

Append this function to the end of `src/dssat_sim/simulator.py` (above the `if __name__ == "__main__":` block — keep that block as-is for direct execution support):

```python
def run_preset(crop_type: str):
    """Run a complete DSSAT simulation using a named preset from `dssat_sim.presets`.

    Args:
        crop_type: One of the keys in CROP_CONFIG (e.g., "rice", "sorghum", "maize").

    Returns:
        Whatever `DSSATSimulator.run_simulation()` returns.

    Raises:
        ValueError: If crop_type is not in CROP_CONFIG.
    """
    from dssat_sim.presets import (
        CROP_CONFIG,
        FIELD_CONFIG,
        OUTPUT_CONFIG,
        SIMULATION_CONFIG,
        SOIL_CONFIG,
        WEATHER_CONFIG,
    )

    if crop_type not in CROP_CONFIG:
        raise ValueError(
            f"Unknown crop preset: {crop_type!r}. Available: {list(CROP_CONFIG)}"
        )

    crop_cfg = CROP_CONFIG[crop_type]
    sim_cfg = SIMULATION_CONFIG.get(crop_type, SIMULATION_CONFIG["rice"])

    project_name = (
        f"{crop_type}_simulation_"
        f"{FIELD_CONFIG['location_name'].lower().replace(' ', '_').replace(',', '')}"
    )
    simulator = DSSATSimulator(project_name)

    print(f"Starting {crop_cfg['crop_type']} simulation for {FIELD_CONFIG['location_name']}")
    print("=" * 60)

    simulator.load_weather_data(
        weather_data_dir=WEATHER_CONFIG["data_dir"],
        station_code=WEATHER_CONFIG["station_code"],
        years=WEATHER_CONFIG["years"],
    )
    simulator.load_soil_profile(
        soil_id=SOIL_CONFIG["soil_id"],
        soil_file_path=SOIL_CONFIG["soil_file"],
        download_if_missing=True,
    )
    simulator.set_cultivar(
        crop_type=crop_cfg["crop_type"],
        cultivar_id=crop_cfg["cultivar_id"],
    )
    simulator.create_field(FIELD_CONFIG["field_id"])

    import os
    output_dir = os.path.join(OUTPUT_CONFIG["base_dir"], crop_type)
    if OUTPUT_CONFIG["create_subdirs"]:
        os.makedirs(output_dir, exist_ok=True)

    return simulator.run_simulation(
        output_dir=output_dir,
        initial_conditions=sim_cfg["initial_conditions"],
        planting=sim_cfg["planting"],
        simulation_controls=sim_cfg["simulation_controls"],
    )
```

- [ ] **Step 2: Update package __init__.py to export run_preset**

Replace `src/dssat_sim/__init__.py` with:

```python
"""dssat_sim — DSSAT crop simulation toolkit."""

from dssat_sim.simulator import DSSATSimulator, run_preset

__version__ = "0.1.0"
__all__ = ["DSSATSimulator", "run_preset"]
```

- [ ] **Step 3: Create the CLI dispatcher**

Create `src/dssat_sim/cli.py` with this exact content:

```python
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
```

- [ ] **Step 4: Reinstall to register console script**

```bash
pip install -e .
```

Expected: succeeds, registers `dssat-sim` console script.

- [ ] **Step 5: Verify CLI surface**

```bash
dssat-sim --help 2>&1 | head -10
```

Expected: shows usage with `simulate`, `generate`, `fetch-weather` listed as subcommands.

```bash
dssat-sim simulate --list
```

Expected:
```
Available crop presets:
  rice       Rice       cultivar=IB0003
  sorghum    Sorghum    cultivar=IB0026
  maize      Maize      cultivar=IB0001
```

- [ ] **Step 6: Verify generate works on the example**

```bash
dssat-sim generate scenario_config.example.yaml --output /tmp/after_task4.csv --force
md5 /tmp/after_task4.csv
```

Compare against `/tmp/before.md5` from pre-flight. The hashes must be identical (LHS is deterministic with same seed; restructure mustn't have changed any logic).

If different, stop and diagnose before proceeding.

- [ ] **Step 7: Rewire CLI subprocess tests in test_generator.py**

In `tests/test_generator.py`, replace the SCENARIOS_MODULE-based subprocess invocations with the `dssat-sim` console script. The pattern in each test is:

```python
result = subprocess.run(
    [sys.executable, str(SCENARIOS_MODULE),
     str(cfg_path), "--output", str(out_path)],
    capture_output=True, text=True, cwd=PROJECT_ROOT,
)
```

becomes:

```python
result = subprocess.run(
    ["dssat-sim", "generate", str(cfg_path), "--output", str(out_path)],
    capture_output=True, text=True,
)
```

Apply this transformation to all 8 CLI subprocess invocations. Adjust the trailing CLI args as follows:
- `test_cli_generates_csv` — args: `[str(cfg_path), "--output", str(out_path)]`
- `test_cli_invalid_config_exits_nonzero` — same
- `test_cli_validate_only` — args: `[str(cfg_path), "--output", str(out_path), "--validate"]`
- `test_cli_preview` — args: `[str(cfg_path), "--output", str(out_path), "--preview"]`
- `test_cli_refuses_overwrite_without_force` — args: `[str(cfg_path), "--output", str(out_path)]`
- `test_cli_force_overwrites` — args: `[str(cfg_path), "--output", str(out_path), "--force"]`
- `test_example_config_generates_valid_csv` — args: `[str(src), "--output", str(out_path), "--force"]`
- `test_example_bundle_mode_via_yaml` — args: `[str(cfg_path), "--output", str(out_path), "--force"]`

Each becomes prefixed with `["dssat-sim", "generate", ...]`.

The `SCENARIOS_MODULE` constant can be removed; keep `PROJECT_ROOT` only if used elsewhere. (`test_example_config_generates_valid_csv` uses `PROJECT_ROOT / "scenario_config.example.yaml"` — keep `PROJECT_ROOT` for that.)

- [ ] **Step 8: Run full test suite**

```bash
python3.10 -m pytest -v 2>&1 | tail -5
```

Expected: `57 passed`.

- [ ] **Step 9: Commit**

```bash
git add src/dssat_sim/cli.py src/dssat_sim/simulator.py src/dssat_sim/__init__.py tests/test_generator.py
git commit -m "feat: add dssat-sim CLI dispatcher with simulate/generate/fetch-weather"
```

---

## Task 5: Backward-compat wrappers

**Files:**
- Modify: `run_simulation.py` (full rewrite to 4-line shim)
- Modify: `run_configured_simulation.py` (full rewrite to 4-line shim)

(Both files were untracked in the initial repo state. Replacing their content + `git add` brings them under version control as the new shims.)

- [ ] **Step 1: Replace run_simulation.py**

Replace the entire content of `run_simulation.py` with:

```python
"""Backward-compat shim. Use `dssat-sim simulate rice` going forward."""
import sys
from dssat_sim.cli import main

sys.exit(main(["simulate", "rice"]))
```

- [ ] **Step 2: Replace run_configured_simulation.py**

Replace the entire content of `run_configured_simulation.py` with:

```python
"""Backward-compat shim. Use `dssat-sim simulate <crop>` going forward.

Forwards all args after the script name to `dssat-sim simulate`.
Examples:
    python run_configured_simulation.py rice     -> dssat-sim simulate rice
    python run_configured_simulation.py --list   -> dssat-sim simulate --list
"""
import sys
from dssat_sim.cli import main

sys.exit(main(["simulate"] + sys.argv[1:]))
```

- [ ] **Step 3: Smoke test the shims (no full DSSAT run, just import & dispatch)**

```bash
python3.10 run_configured_simulation.py --list
```

Expected:
```
Available crop presets:
  rice       Rice       cultivar=IB0003
  sorghum    Sorghum    cultivar=IB0026
  maize      Maize      cultivar=IB0001
```

```bash
python3.10 run_simulation.py 2>&1 | head -3
```

Expected: prints the "Starting Rice simulation..." banner from `run_preset("rice")` (then likely fails on missing weather data, which is fine — the goal here is import/dispatch, not full simulation).

- [ ] **Step 4: Run tests**

```bash
python3.10 -m pytest -v 2>&1 | tail -3
```

Expected: `57 passed`.

- [ ] **Step 5: Commit**

```bash
git add run_simulation.py run_configured_simulation.py
git commit -m "refactor: replace legacy runner scripts with dssat-sim CLI shims"
```

---

## Task 6: Move data folders + update path defaults

**Files:**
- Move: `weather_data/` → `data/weather/`
- Move: `soil_data/` → `data/soil/`
- Move: `scenario.csv` → `data/scenarios/scenario.csv`
- Move: `scenario_config.example.yaml` → `examples/scenario_config.yaml`
- Move: `.env.example` → `examples/.env.example`
- Modify: `src/dssat_sim/presets.py` (path defaults)
- Modify: `src/dssat_sim/simulator.py` (path defaults)
- Modify: `tests/test_generator.py` (example path in integration test)

- [ ] **Step 1: Create new directory tree**

```bash
mkdir -p data/scenarios examples
```

- [ ] **Step 2: Move data folders**

```bash
mv weather_data data/weather
mv soil_data data/soil
mv scenario.csv data/scenarios/scenario.csv
mv scenario_config.example.yaml examples/scenario_config.yaml
mv .env.example examples/.env.example
```

(`weather_data/`, `soil_data/`, and `scenario.csv` were untracked. `scenario_config.example.yaml` was tracked — `git mv` would work but plain `mv` + `git add` is simpler and consistent.)

- [ ] **Step 3: Update path defaults in presets.py**

In `src/dssat_sim/presets.py`, change the three default paths.

Replace:

```python
WEATHER_CONFIG = {
    "data_dir": "./weather_data",
```

with:

```python
WEATHER_CONFIG = {
    "data_dir": "data/weather",
```

Replace:

```python
SOIL_CONFIG = {
    "soil_id": "IBSG910085",
    "soil_file": "soil_data/SOIL.SOL",
```

with:

```python
SOIL_CONFIG = {
    "soil_id": "IBSG910085",
    "soil_file": "data/soil/SOIL.SOL",
```

Replace:

```python
OUTPUT_CONFIG = {
    "base_dir": "./simulation_results",
```

with:

```python
OUTPUT_CONFIG = {
    "base_dir": "results",
```

- [ ] **Step 4: Update simulator.py default paths**

In `src/dssat_sim/simulator.py`, update `load_weather_data` and `load_soil_profile` defaults.

Replace:

```python
    def load_weather_data(self, weather_data_dir: str = "./weather_data",
```

with:

```python
    def load_weather_data(self, weather_data_dir: str = "data/weather",
```

Replace:

```python
    def load_soil_profile(self, soil_id: str = "IBSG910085",
                         soil_file_path: str = "soil_data/SOIL.SOL",
```

with:

```python
    def load_soil_profile(self, soil_id: str = "IBSG910085",
                         soil_file_path: str = "data/soil/SOIL.SOL",
```

(The `if __name__ == "__main__":` example block in `simulator.py:main()` also references `./weather_data` and `soil_data/SOIL.SOL` and `./simulation_output`. Update those too — find each literal string and replace with the new path.)

- [ ] **Step 5: Update integration test path**

In `tests/test_generator.py`, find:

```python
def test_example_config_generates_valid_csv(tmp_path):
    src = PROJECT_ROOT / "scenario_config.example.yaml"
```

Replace with:

```python
def test_example_config_generates_valid_csv(tmp_path):
    src = PROJECT_ROOT / "examples" / "scenario_config.yaml"
```

- [ ] **Step 6: Run full test suite**

```bash
python3.10 -m pytest -v 2>&1 | tail -3
```

Expected: `57 passed`.

- [ ] **Step 7: Verify generate still works at new path**

```bash
dssat-sim generate examples/scenario_config.yaml --validate
```

Expected: `Config OK.`

```bash
dssat-sim generate examples/scenario_config.yaml --output /tmp/after_task6.csv --force
md5 /tmp/after_task6.csv
```

Expected: identical md5 to `/tmp/before.md5`.

- [ ] **Step 8: Commit**

```bash
git add data/ examples/ src/dssat_sim/presets.py src/dssat_sim/simulator.py tests/test_generator.py
git commit -m "refactor: move data folders to data/ and examples to examples/"
```

---

## Task 7: Cleanup legacy + .gitignore

**Files:**
- Delete: `dssat-simulation.ipynb`
- Delete: `requirements.txt`
- Delete: `simulation_results/` (untracked, just `rm -rf`)
- Modify: `.gitignore`

- [ ] **Step 1: Delete legacy notebook**

```bash
git rm dssat-simulation.ipynb
```

(Tracked file from initial commit — use `git rm`.)

- [ ] **Step 2: Delete requirements.txt**

```bash
git rm requirements.txt
```

(Tracked file — was added in the previous PR. Replaced by pyproject.toml.)

- [ ] **Step 3: Delete simulation_results contents**

```bash
rm -rf simulation_results
```

(Untracked, plain `rm`.)

- [ ] **Step 4: Update .gitignore**

Replace the entire content of `.gitignore` with:

```
.env
__pycache__/
.dssat_env/
.dssat_env_x86/
.neira/
.pytest_cache/
.idea/
.ipynb_checkpoints/
*.egg-info/
build/
dist/
results/
scenarios*.csv
```

- [ ] **Step 5: Confirm no stray tracked files appeared**

```bash
git status
```

Expected: `.gitignore` modified, `dssat-simulation.ipynb` and `requirements.txt` deleted, no other unexpected entries.

- [ ] **Step 6: Run full test suite**

```bash
python3.10 -m pytest -v 2>&1 | tail -3
```

Expected: `57 passed`.

- [ ] **Step 7: Verify CLI still works**

```bash
dssat-sim --help 2>&1 | head -5
dssat-sim generate examples/scenario_config.yaml --validate
```

Expected: help shows subcommands; generate validates OK.

- [ ] **Step 8: Commit**

```bash
git add .gitignore
git commit -m "chore: delete legacy notebook, requirements.txt, and stale results; tighten gitignore"
```

---

## Task 8: README + final verification

**Files:**
- Modify (or replace): `README.md`

- [ ] **Step 1: Replace README.md**

Replace the entire content of `README.md` with:

````markdown
# DSSAT Simulation Toolkit (`dssat-sim`)

A Python package for running DSSAT crop simulations with NASA POWER weather data and Latin Hypercube Sampling-based scenario generation.

## Install

```bash
pip install -e .[dev]
```

Requires Python 3.10+. On Apple Silicon Macs the DSSAT binary is x86_64-only — run under Rosetta 2:
```bash
arch -x86_64 pip install -e .[dev]
arch -x86_64 dssat-sim simulate rice
```

## Quick start

```bash
# List available crop presets
dssat-sim simulate --list

# Run a preset simulation (rice/sorghum/maize)
dssat-sim simulate rice

# Generate Latin Hypercube scenarios from a YAML config
dssat-sim generate examples/scenario_config.yaml --output scenarios.csv

# Validate a config without writing
dssat-sim generate examples/scenario_config.yaml --validate

# Fetch fresh NASA POWER weather data (uses examples/.env settings or CLI flags)
cp examples/.env.example .env       # edit lat/long/dates as needed
dssat-sim fetch-weather
```

## Project structure

```
dssat-simulation/
├── src/dssat_sim/         # the package
│   ├── simulator.py       # DSSATSimulator class + run_preset()
│   ├── weather.py         # NASA POWER fetch
│   ├── presets.py         # crop/weather/soil constants
│   ├── scenarios.py       # LHS scenario generator
│   └── cli.py             # `dssat-sim` console script entry
├── tests/                 # pytest suite (57 tests)
├── data/
│   ├── weather/           # weather CSVs (IDGR1901.csv, etc.)
│   ├── soil/              # SOIL.SOL profile
│   └── scenarios/         # pre-generated scenario CSVs
├── examples/
│   ├── scenario_config.yaml   # generator config example
│   └── .env.example           # weather fetch env example
├── results/               # runtime simulation output (gitignored)
├── docs/                  # design specs and implementation plans
├── pyproject.toml
└── README.md
```

## Python API

```python
from dssat_sim import DSSATSimulator, run_preset
from dssat_sim.scenarios import load_config, write_csv
from dssat_sim.weather import generate_yearly_data_from_config
from dssat_sim.presets import CROP_CONFIG, SIMULATION_CONFIG

# Run a preset directly
run_preset("rice")

# Or build a custom simulation
sim = DSSATSimulator("my_sim")
sim.load_weather_data(weather_data_dir="data/weather", years=[19, 20, 21])
sim.load_soil_profile()
sim.set_cultivar("Rice", "IB0003")
sim.create_field()
results = sim.run_simulation(output_dir="results/custom")

# Or generate scenarios programmatically
cfg = load_config("examples/scenario_config.yaml")
write_csv(cfg, "out.csv")
```

## Backward-compat scripts

The legacy entry points still work and now delegate to `dssat-sim`:

```bash
python run_simulation.py                      # → dssat-sim simulate rice
python run_configured_simulation.py rice      # → dssat-sim simulate rice
python run_configured_simulation.py --list    # → dssat-sim simulate --list
```

These are 3-line shims. Prefer `dssat-sim` for new scripts.

## Adding crops

Add an entry to `src/dssat_sim/presets.py`:
```python
CROP_CONFIG["wheat"] = {
    "crop_type": "Wheat", "cultivar_id": "IB0005", "crop_code": "WH",
}
SIMULATION_CONFIG["wheat"] = {
    "initial_conditions": {"crop_code": "WH", "initial_date": datetime(1980, 7, 3)},
    "planting": {"planting_date": datetime(2019, 11, 1), "population": 200},
    "simulation_controls": {"start_date": datetime(1980, 6, 17)},
}
```

Then: `dssat-sim simulate wheat`.

## Tests

```bash
pytest -v
```

Expected: 57 passing.

## Troubleshooting

**`ModuleNotFoundError: No module named 'dssat_sim'`** — run `pip install -e .` from the repo root.

**`Exec format error` when running `dssat-sim simulate`** — DSSAT binary is x86_64-only. Use `arch -x86_64` on Apple Silicon.

**Weather data missing** — run `dssat-sim fetch-weather` first to populate `data/weather/`.

**Soil file missing** — `dssat-sim simulate` auto-downloads from the DSSAT GitHub repo if `data/soil/SOIL.SOL` is absent.
````

- [ ] **Step 2: Final clean-install verification**

Verify the package installs cleanly into a fresh virtualenv (catches any `pyproject.toml` / metadata bugs):

```bash
python3.10 -m venv /tmp/dssat-clean-venv
/tmp/dssat-clean-venv/bin/pip install -e .[dev]
/tmp/dssat-clean-venv/bin/pytest -v 2>&1 | tail -3
```

Expected: install succeeds, `57 passed`.

- [ ] **Step 3: Final regression check on LHS output**

```bash
dssat-sim generate examples/scenario_config.yaml --output /tmp/after_final.csv --force
md5 /tmp/after_final.csv
```

Expected: identical md5 to `/tmp/before.md5` from pre-flight.

- [ ] **Step 4: Final CLI surface check**

```bash
dssat-sim --help | grep -E "simulate|generate|fetch-weather" | wc -l
```

Expected: `3` (all three subcommands listed).

```bash
dssat-sim simulate --list
```

Expected: lists 3 crop presets.

- [ ] **Step 5: Backward-compat shim check**

```bash
python3.10 run_configured_simulation.py --list
```

Expected: same output as `dssat-sim simulate --list`.

- [ ] **Step 6: Repo cleanliness check**

```bash
git status
```

Expected: only `README.md` modified. Nothing untracked except virtualenvs (which are gitignored).

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs: rewrite README for new package structure and dssat-sim CLI"
```

- [ ] **Step 8: Push and open PR**

```bash
git push -u origin feat/codebase-restructure
gh pr create --title "Restructure into dssat-sim package" --body "$(cat <<'EOF'
## Summary
- Restructured flat-layout codebase into `src/dssat_sim/` package
- Added `pyproject.toml` (replaces `requirements.txt`)
- New unified `dssat-sim` console script with three subcommands: `simulate`, `generate`, `fetch-weather`
- Kept `run_simulation.py` and `run_configured_simulation.py` as 3-line backward-compat shims
- Moved data folders into `data/`, examples into `examples/`, runtime output into `results/` (gitignored)
- Deleted legacy notebook, `requirements.txt`, stale `simulation_results/` artifacts

## Test plan
- [x] `pytest -v` → 57 passed (zero regression from baseline)
- [x] `dssat-sim generate examples/scenario_config.yaml --output /tmp/x.csv --force` produces byte-identical output to pre-restructure baseline (LHS deterministic)
- [x] `dssat-sim --help` lists all 3 subcommands
- [x] `dssat-sim simulate --list` shows rice/sorghum/maize
- [x] Backward-compat shims dispatch correctly: `python run_configured_simulation.py --list` matches `dssat-sim simulate --list`
- [x] Clean install in fresh venv: `pip install -e .[dev]` then `pytest -v` → 57 passed
- [x] No bug-fix or behavior changes (structure-only PR)

## Spec & plan
- Spec: `docs/superpowers/specs/2026-04-28-codebase-restructure-design.md`
- Plan: `docs/superpowers/plans/2026-04-28-codebase-restructure.md`
EOF
)"
```

---

## Self-Review

**Spec coverage** — every spec section maps to a task:

| Spec section | Implementing task(s) |
|---|---|
| Goal | All tasks |
| Decisions captured | All tasks reflect them |
| Target file structure | Tasks 1-7 (build it up incrementally) |
| Files deleted | Task 7 (`.ipynb`, `requirements.txt`); Task 5 replaces but doesn't delete the runners |
| Files renamed | Task 6 |
| Public API — console scripts | Task 4 |
| Public API — Python imports | Task 3 + Task 4 (`__init__.py` exports) |
| Backward-compat wrappers | Task 5 |
| `pyproject.toml` content | Task 1 |
| CLI dispatcher | Task 4 |
| Migration sequence (8 commits) | Tasks 1-8 |
| Risks & mitigations — test imports break | Each task ends with `pytest -v` |
| Risks & mitigations — LHS output drift | md5 baseline captured pre-flight, re-verified Task 4, Task 6, Task 8 |
| Risks & mitigations — venv conflict | Task 8 uses fresh `/tmp/dssat-clean-venv` |
| Risks & mitigations — wrapper signature | Task 5 wrappers reference `cli.main()` exactly as defined in Task 4 |
| Risks & mitigations — path defaults break user scripts | README documents migration in Task 8 |
| Risks & mitigations — venvs auto-tracked | Task 7 .gitignore + Task 8 `git status` check |
| Risks & mitigations — giant PR review | Task 8 PR body summarizes change set |
| Out of scope (no behavior changes) | Honored — every task that touches code is a move/rename/wiring change, not behavior |

No gaps.

**Placeholder scan** — no TBD/TODO/"add validation later"/"similar to" patterns. All steps contain working code or exact commands.

**Type / signature consistency**:
- `cli.main(argv: list[str] | None = None) -> int` defined in Task 4, called with that signature by both wrappers in Task 5.
- `run_preset(crop_type: str)` defined in Task 4, exported from `__init__.py` in Task 4, called by `_handle_simulate` in Task 4 cli.py.
- `_handle_generate` uses imports `load_config, validate_config, write_csv, resolve_rows, ConfigError` — all present in `dssat_sim.scenarios` from Task 2 onward (untouched in this restructure since they were already there).
- `_handle_fetch_weather` uses `generate_yearly_data_from_config` and `load_config` from `dssat_sim.weather` — both defined in the original `get_weather.py` (preserved by Task 3 move).
- `CROP_CONFIG`, `WEATHER_CONFIG`, `SOIL_CONFIG`, `OUTPUT_CONFIG`, `SIMULATION_CONFIG`, `FIELD_CONFIG` referenced in `run_preset()` (Task 4) — all present in `dssat_sim.presets` from Task 3 onward.

**Order-of-operations sanity** — important for moves:
- Tests reference `scenario_config.example.yaml` until Task 6, then switch to `examples/scenario_config.yaml`. Tests stay green throughout because the move and the test edit are in the **same commit (Task 6)**.
- CLI subprocess tests use `[sys.executable, str(SCENARIOS_MODULE), ...]` after Task 2 and switch to `["dssat-sim", "generate", ...]` in Task 4. Both forms work; `dssat-sim` requires the package to be installed (which it is, from Task 1). Tests stay green.
- `requirements.txt` deleted in Task 7. No task between Task 1 and Task 7 references it; the `pip install -e .` calls use `pyproject.toml`.
- `dssat-simulation.ipynb` deleted in Task 7. No earlier task references it.
