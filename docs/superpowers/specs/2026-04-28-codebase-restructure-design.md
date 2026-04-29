# Codebase Restructure: Design

**Date:** 2026-04-28
**Status:** Draft, awaiting user review

## Goal

Restructure the flat-layout DSSAT simulation codebase into a **modern installable Python package** (`src/` layout, `pyproject.toml`, console scripts) so it's easier to navigate, import, test, and eventually publish. Hard cutover in a single PR — no parallel old/new directory tree.

## Non-goals

- New features or behavior changes (this is structure-only)
- Splitting `scenarios.py` into multiple files (312 lines is fine; split is YAGNI)
- PyPI publication (the package becomes publishable, but actual upload is out of scope)
- Migrating off `setuptools` to `hatch`/`uv`/etc. (use setuptools, the standard)
- Refactoring DSSAT simulator internals — only the file location and import path change
- Test framework changes — pytest stays
- CI/CD setup — separate effort
- Pre-existing bugs found in earlier audit (Garut hardcoding, NASA fallback, etc.) — those are tracked separately, not part of this restructure

## Decisions captured from brainstorming

| Decision | Choice |
|---|---|
| Restructure scope | Full restructure (option F) |
| Package layout | Modern `src/` layout, publishable (option A) |
| Decomposition | Single PR with 8 sequential commits (option 1) |
| Console script name | `dssat-sim` |
| Old runner scripts | Keep as 2-3 line backward-compat wrappers (not delete) |
| Notebook | Delete `dssat-simulation.ipynb` |
| `requirements.txt` | Delete (replaced by `pyproject.toml`) |
| `simulation_results/` content | Delete contents, gitignore the dir |

## Target file structure

```
dssat-simulation/
├── pyproject.toml                    # NEW — package metadata, deps, console scripts
├── README.md                         # UPDATED — new structure & usage
├── .gitignore                        # UPDATED — venvs, .idea, .ipynb_checkpoints, results/
│
├── src/
│   └── dssat_sim/                    # the package
│       ├── __init__.py               # minimal public API exports
│       ├── simulator.py              # was dssat_simulator.py
│       ├── weather.py                # was get_weather.py
│       ├── presets.py                # was config.py (renamed for clarity)
│       ├── scenarios.py              # was scenario_generator.py
│       └── cli.py                    # unified CLI with subcommands
│
├── tests/                            # location unchanged, imports updated
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_generator.py
│   └── test_param_types.py
│
├── data/                             # NEW root for input data
│   ├── weather/                      # was weather_data/
│   ├── soil/                         # was soil_data/
│   └── scenarios/
│       └── scenario.csv              # was at root
│
├── examples/                         # NEW — usage examples
│   ├── scenario_config.yaml          # was scenario_config.example.yaml
│   └── .env.example                  # was at root
│
├── results/                          # NEW empty dir for runtime outputs (gitignored)
│
├── run_simulation.py                 # KEPT as compat wrapper (2 lines)
├── run_configured_simulation.py      # KEPT as compat wrapper (2-3 lines)
│
└── docs/                             # unchanged
    └── superpowers/
        ├── plans/
        └── specs/
```

### Files deleted

- `dssat-simulation.ipynb` — legacy precursor, fully superseded by `.py` modules
- `requirements.txt` — replaced by `pyproject.toml` direct deps + auto-resolved transitives
- `dssat_simulator.py` — moved into `src/dssat_sim/simulator.py`
- `config.py` — moved into `src/dssat_sim/presets.py`
- `get_weather.py` — moved into `src/dssat_sim/weather.py`
- `scenario_generator.py` — moved into `src/dssat_sim/scenarios.py`

### Files renamed (for path consistency)

- `weather_data/` → `data/weather/`
- `soil_data/` → `data/soil/`
- `simulation_results/` → `results/` (contents deleted, dir gitignored)
- `scenario.csv` → `data/scenarios/scenario.csv`
- `scenario_config.example.yaml` → `examples/scenario_config.yaml`
- `.env.example` → `examples/.env.example`

## Public API

### Console scripts

After `pip install -e .`:

```bash
dssat-sim simulate rice                      # run DSSAT simulation for preset crop
dssat-sim simulate sorghum
dssat-sim simulate --list                    # list available crop presets

dssat-sim generate examples/scenario_config.yaml --output out.csv
dssat-sim generate config.yaml --validate    # check config, no write
dssat-sim generate config.yaml --preview     # show first 5 rows, no write
dssat-sim generate config.yaml --force       # overwrite existing output

dssat-sim fetch-weather                      # uses examples/.env / project .env
dssat-sim fetch-weather --lat -7.22 --long 107.9 --start 2020-01-01 --end 2021-12-31

dssat-sim --help                             # top-level usage
```

### Importable Python API

```python
from dssat_sim import DSSATSimulator                  # main simulator class
from dssat_sim.scenarios import (                     # scenario generator
    Config, ConfigError,
    load_config, validate_config,
    write_csv, resolve_rows,
    FloatParam, IntParam, DateParam, CategoricalParam, BundleParam,
)
from dssat_sim.weather import fetch_nasa_power
from dssat_sim.presets import (
    WEATHER_CONFIG, SOIL_CONFIG, CROP_CONFIG,
    FIELD_CONFIG, SIMULATION_CONFIG, OUTPUT_CONFIG, DEFAULT_PRESET,
)
```

`__init__.py` re-exports `DSSATSimulator` so `from dssat_sim import DSSATSimulator` works directly. Submodules accessed by full path (no aggressive re-exporting — keeps `__init__` minimal).

### Backward-compat wrappers

`run_simulation.py` (at root, kept for legacy callers):
```python
"""Backward-compat shim. Use `dssat-sim simulate rice` going forward."""
import sys
from dssat_sim.cli import main
sys.exit(main(["simulate", "rice"]))
```

`run_configured_simulation.py` (at root, kept for legacy callers):
```python
"""Backward-compat shim. Use `dssat-sim simulate <crop>` going forward."""
import sys
from dssat_sim.cli import main
sys.exit(main(["simulate"] + sys.argv[1:]))
```

## `pyproject.toml`

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

## CLI dispatcher (`src/dssat_sim/cli.py`)

Single argparse with subparsers:

```python
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dssat-sim")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # `dssat-sim simulate <crop>`
    sim_p = subparsers.add_parser("simulate", help="Run DSSAT simulation")
    sim_p.add_argument("crop", nargs="?", help="Crop preset (rice/sorghum/maize)")
    sim_p.add_argument("--list", action="store_true")

    # `dssat-sim generate <config>`
    gen_p = subparsers.add_parser("generate", help="Generate scenario CSV via LHS")
    gen_p.add_argument("config")
    gen_p.add_argument("--output")
    gen_p.add_argument("--force", action="store_true")
    gen_p.add_argument("--validate", action="store_true")
    gen_p.add_argument("--preview", action="store_true")

    # `dssat-sim fetch-weather`
    fw_p = subparsers.add_parser("fetch-weather", help="Fetch NASA POWER weather")
    fw_p.add_argument("--lat", type=float)
    fw_p.add_argument("--long", type=float)
    fw_p.add_argument("--start")
    fw_p.add_argument("--end")
    fw_p.add_argument("--station-code")
    fw_p.add_argument("--output-dir")

    args = parser.parse_args(argv)
    if args.command == "simulate":
        return _handle_simulate(args)
    if args.command == "generate":
        return _handle_generate(args)
    if args.command == "fetch-weather":
        return _handle_fetch_weather(args)
    return 2
```

Handler functions delegate to existing module code (no rewrites):
- `_handle_generate(args)` → reuses `dssat_sim.scenarios` (existing argparse logic from `scenario_generator.py:main()` is lifted into the handler)
- `_handle_simulate(args)` → reuses `run_configured_simulation()` body, now imported from `dssat_sim.simulator` (or kept as a function in `cli.py` that constructs `DSSATSimulator` from `presets.py`)
- `_handle_fetch_weather(args)` → reuses `dssat_sim.weather.generate_yearly_data_from_config()`

## Migration sequence (8 commits in one PR)

The PR contains these commits in order. Each ends with a verification step. If any verification fails, **stop, fix, do not proceed.**

### Commit 1 — Foundation

**Adds:** `pyproject.toml`, `src/dssat_sim/__init__.py` (empty), `src/dssat_sim/__about__.py` (optional version constant).

**Verify:**
```bash
pip install -e .
python -c "import dssat_sim"   # exits 0
```

### Commit 2 — Move scenarios

**Moves:** `scenario_generator.py` → `src/dssat_sim/scenarios.py`. Update all `tests/test_*.py` imports from `from scenario_generator import X` to `from dssat_sim.scenarios import X`.

**Verify:**
```bash
pytest -v   # 57 passed
```

### Commit 3 — Move simulator, weather, presets

**Moves:**
- `dssat_simulator.py` → `src/dssat_sim/simulator.py`
- `get_weather.py` → `src/dssat_sim/weather.py`
- `config.py` → `src/dssat_sim/presets.py`

**Updates:** Internal imports inside moved files (`from config import` → `from dssat_sim.presets import`, etc.). `src/dssat_sim/__init__.py` re-exports `DSSATSimulator`.

**Verify:**
```bash
python -c "from dssat_sim import DSSATSimulator; print('ok')"
python -c "from dssat_sim.weather import fetch_nasa_power; print('ok')"
python -c "from dssat_sim.presets import CROP_CONFIG; print('ok')"
pytest -v   # 57 passed (no scenario test depends on these modules, but verify)
```

### Commit 4 — CLI dispatcher

**Adds:** `src/dssat_sim/cli.py`. Adds `[project.scripts]` to `pyproject.toml`.

**Verify:**
```bash
pip install -e .   # reinstall to register console script
dssat-sim --help
dssat-sim simulate --list
dssat-sim generate examples/scenario_config.yaml --validate   # path will resolve after Commit 6; for now use the still-at-root file
```

If the example YAML hasn't been moved yet (Commit 6), use the current path:
```bash
dssat-sim generate scenario_config.example.yaml --output /tmp/after.csv --force
diff /tmp/before.csv /tmp/after.csv   # byte-identical (deterministic LHS seed)
```

### Commit 5 — Backward-compat wrappers

**Replaces:**
- `run_simulation.py` (full content) with the 2-line shim above
- `run_configured_simulation.py` (full content) with the 2-line shim above

**Verify:**
```bash
python run_simulation.py --help 2>&1 | head -5      # should show simulate help / start running
python run_configured_simulation.py --list           # should list crops
```

(Full DSSAT execution requires the binary; if not installed locally, smoke test is "command starts and reaches the simulator code without ImportError.")

### Commit 6 — Move data folders

**Moves:**
- `weather_data/` → `data/weather/`
- `soil_data/` → `data/soil/`
- `scenario.csv` → `data/scenarios/scenario.csv`
- `scenario_config.example.yaml` → `examples/scenario_config.yaml`
- `.env.example` → `examples/.env.example`
- `simulation_results/` → `results/` (move dir, then delete contents in next commit)

**Updates:** Any path references in source code:
- `dssat_simulator.py`-now-`simulator.py`: weather/soil paths → keep configurable, update default to `data/weather`, `data/soil`
- `presets.py`: `WEATHER_CONFIG["data_dir"]` default `"./weather_data"` → `"data/weather"`. `SOIL_CONFIG["soil_file"]` `"soil_data/SOIL.SOL"` → `"data/soil/SOIL.SOL"`. `OUTPUT_CONFIG["base_dir"]` `"./simulation_results"` → `"results"`.
- `tests/test_generator.py`: integration test reads `scenario_config.example.yaml`; update to `examples/scenario_config.yaml`.

**Verify:**
```bash
pytest -v   # 57 passed
dssat-sim generate examples/scenario_config.yaml --validate   # finds the file
```

### Commit 7 — Cleanup legacy

**Deletes:**
- `dssat-simulation.ipynb`
- `requirements.txt`
- All contents of `results/` (the moved-from `simulation_results/` artifacts)

**Updates `.gitignore`:**
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

`results/` is fully gitignored — the directory is created at runtime by simulator/CLI code on first use (e.g., `os.makedirs("results", exist_ok=True)`). No `.gitkeep` placeholder needed. The `scenarios*.csv` pattern (plural prefix) intentionally does not match the kept-tracked `data/scenarios/scenario.csv` (singular), so no `!` exception is required.

**Verify:**
```bash
pytest -v   # 57 passed
git status  # confirm no stray tracked files
```

### Commit 8 — README + final pass

**Updates `README.md`:** new install instructions (`pip install -e .[dev]`), new console script usage, updated file structure section, updated examples.

**Final verification gate (all must pass before merge):**
```bash
# Clean install from scratch
python3.10 -m venv /tmp/dssat-venv
source /tmp/dssat-venv/bin/activate
pip install -e .[dev]

# Tests pass
pytest -v   # 57 passed

# Generator deterministic — output matches pre-restructure baseline
dssat-sim generate examples/scenario_config.yaml --output /tmp/x.csv --force
diff /tmp/x.csv /tmp/before.csv   # empty output (byte-identical)

# CLI surface complete
dssat-sim --help | grep -E "simulate|generate|fetch-weather"   # all 3 listed

# Backward compat
python run_simulation.py 2>&1 | head -3   # no ImportError, reaches simulator code
python run_configured_simulation.py --list   # lists crops
```

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Test imports break after move | Each commit verifies `pytest`. Stop & fix at the first failure. |
| LHS output changes due to import order side effects | Pre-capture baseline `before.csv`, diff against `after.csv` after Commit 4 and Commit 8. Must be byte-identical. |
| `pip install -e .` conflicts with existing `.dssat_env_x86/` venv | Use a fresh venv for final verification. Existing venvs untouched. |
| Backward-compat wrapper breaks because `cli.main()` signature changed mid-PR | `cli.main()` signature locked in Commit 4 design. Wrappers added in Commit 5 reference that signature. |
| Path defaults in `presets.py` break existing user scripts that pass relative paths | Defaults change but parameters stay overridable. Document migration path in README. |
| `.dssat_env/` and `.dssat_env_x86/` accidentally git-added | `.gitignore` updated in Commit 7. Run `git status` as final check. |
| Reviewer can't review one giant PR | Single-PR is user's explicit choice. The 8 sequenced commits with verification steps make commit-by-commit review feasible if needed. |

## Out of scope (explicit non-goals reiterated)

- DSSAT simulator behavior changes
- New features in scenario generator
- Bug fixes from earlier audit (Garut hardcoding, NASA fallback fabrication, year-format ambiguity, etc.) — separate efforts
- CI/CD setup
- PyPI publication
- Test reorganization (test files stay in `tests/`)
