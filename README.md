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
