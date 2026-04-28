# Scenario Generator: Design

**Date:** 2026-04-28
**Status:** Draft, awaiting user review

## Goal

Replace the hand-curated `scenario.csv` (240 rows) with a **YAML-driven Latin Hypercube Sampling (LHS) generator** that produces the same 17-column CSV format. A single tool serves two use cases:

- **Use case A — Sensitivity analysis.** Each parameter sampled independently. Enables downstream Sobol/Morris-style attribution of yield variance to individual inputs.
- **Use case B — Yield prediction / training data.** Correlated parameters bundled into named treatments (e.g., `LowInput`, `HighInput`) so generated scenarios stay agronomically realistic.

The user toggles between A and B by writing the YAML differently — no CLI flag, no separate code path.

## Non-goals (v1)

- Cultivar coefficient sampling (DSSAT P1, P2R, G1, etc. — calibration use case)
- Multi-location sampling (lat/long/elevation as parameters)
- Initial soil condition sampling (per-layer SH2O / SNH4 / SNO3)
- User-supplied conditional expressions in YAML (e.g., `{x} if {y} > 0 else null`)
- Sobol indices / Morris elementary effects computation — that's a downstream analysis tool
- Auto-overwriting the existing `scenario.csv` (generator writes to a path the user specifies)

The YAML schema is designed so these can be added in v2+ without breaking v1 configs.

## Architecture

```
config.yaml ──┐
              │
              ▼
     scenario_generator.py
              │
              ├─ load + validate YAML schema
              ├─ count LHS dimensions (one per `parameters` entry)
              ├─ scipy.stats.qmc.LatinHypercube(d, seed) → unit samples [n_samples × d]
              ├─ map each column to its parameter domain (date/float/int/categorical/bundle)
              ├─ expand bundles: 1 LHS column → multiple CSV columns
              ├─ apply built-in derivations (simulation_start_date, fertilizer_date)
              ├─ inject `fixed` values into every row
              ├─ assign scenario_id, look up cultivar_name / soil_name
              ▼
     scenarios.csv  (compatible with existing 17-column format)
```

## Components

### 1. YAML configuration

Top-level keys:

```yaml
n_samples: 200          # required, int > 0
seed: 42                # required, for LHS reproducibility
output: scenarios.csv   # optional, CLI --output overrides

parameters:             # things sampled by LHS (each is one LHS dimension)
  <name>: {type: ..., ...}

fixed:                  # constants applied to every row
  <name>: <value>

derivations:            # tunable knobs for built-in derived columns
  simulation_start_offset_days: 15

lookups:                # optional display-name lookups
  cultivar_id: {IB0003: "IR 36", IB0002: "CP170"}
  soil_id: {IBSG910010: "Clay_loam"}
```

### 2. Parameter types

| `type` | Example YAML | LHS dims | Mapping from `u ∈ [0,1]` |
|---|---|---|---|
| `float` | `{type: float, min: 0, max: 200}` | 1 | `min + (max-min) * u` |
| `int` | `{type: int, min: 7, max: 15}` | 1 | `floor(min + (max+1-min) * u)`, clamped to `max` |
| `date` | `{type: date, min: 2021-04-15, max: 2021-07-31}` | 1 | linear interpolation in days, rounded to nearest day |
| `categorical` | `{type: categorical, values: [a, b, c]}` | 1 | `values[floor(u * len(values))]`, clamped |
| `bundle` | `{type: bundle, values: [{name: X, k1: v1, k2: v2}, ...]}` | 1 | pick entry by index (same as categorical), then expand entry's keys to multiple output columns |

**Bundle mechanic.** A bundle counts as **one** LHS dimension but produces **multiple** output columns. This is what lets mode B (realistic) work without a separate code path. Example: `management` bundle with keys `{fertilizer, irrigation, residue_management, fertilizer_amount_n}` produces 4 output columns from 1 LHS dimension. If the user instead wanted these independent (mode A), they'd declare each as its own top-level `parameters` entry.

**Bundle key validation.** Each key inside a bundle entry (other than `name`) must match one of the 17 CSV column names. This is enforced at config load.

**Edge case — sample = 1.0.** scipy's LHS can theoretically emit 1.0; the categorical/int mappers clamp the resulting index to `n-1`/`max` to avoid out-of-range.

### 3. Derivations (v1: hardcoded)

Two computed columns, no user expressions:

- `simulation_start_date = planting_date - simulation_start_offset_days` (offset configurable via `derivations.simulation_start_offset_days`, defaults to 15)
- `fertilizer_date = planting_date if fertilizer_amount_n > 0 else ""` (matches the empty-cell convention in existing `scenario.csv`)

`planting_date` must be present (sampled, in `fixed`, or supplied by a bundle); if missing, fail validation. `fertilizer_amount_n` is looked up by name in the resolved row; if not present at all, `fertilizer_date` defaults to `planting_date`.

### 4. CSV output

17 columns, exact order matching `scenario.csv`:

```
scenario_id, cultivar_id, cultivar_name, soil_id, soil_name,
management_scenario, planting_date, plant_population, fertilizer,
irrigation, residue_management, row_spacing, fertilizer_amount_n,
fertilizer_amount_p, fertilizer_amount_k, simulation_start_date,
fertilizer_date
```

Resolution rules per column:
- Sampled by LHS → use sampled value
- Provided by a bundle → use bundle's value (bundle name fills `management_scenario`)
- In `fixed` block → use fixed value
- A derivation → compute
- Otherwise → empty cell

`scenario_id` is auto-generated as `SCENARIO_NNNN` zero-padded to width = `len(str(n_samples))`.

### 5. CLI

```bash
python scenario_generator.py config.yaml                        # generate
python scenario_generator.py config.yaml --output out.csv       # explicit output
python scenario_generator.py config.yaml --force                # overwrite existing
python scenario_generator.py config.yaml --validate             # schema check, no write
python scenario_generator.py config.yaml --preview              # print first 5 rows + total count, no write
```

### 6. Error handling

Validation errors fail loudly with the offending YAML key:
- Unknown `type` value
- `min > max` for numeric/date
- Empty `values` list for categorical/bundle
- Bundle entry keys collide with top-level `parameters` names
- `n_samples` < 1
- No `parameters` declared (LHS needs ≥ 1 dimension)
- Output file exists and `--force` not given
- `planting_date` missing but `simulation_start_date` derivation requires it

### 7. Testing

`tests/test_scenario_generator.py` (project currently has no tests; this bootstraps):

Unit tests:
- LHS reproducibility: same seed → identical CSV
- Bundle expansion: 1 LHS dim → N expected columns
- Categorical mapping uniformity: 10,000 samples hit every value at least once
- Date mapping respects month/year boundaries (e.g., min=Dec 20, max=Jan 10)
- Integer mapping respects bounds (no value < min, no value > max)
- Validation rejects each malformed config (parameterized fixtures)

Integration test:
- Generate 100 scenarios from `scenario_config.example.yaml`, assert:
  - 17 columns, 100 rows
  - `scenario_id` unique
  - `simulation_start_date` always before `planting_date`
  - `fertilizer_date` is empty whenever `fertilizer_amount_n == 0`

## File layout

```
dssat-simulation/
├── scenario_generator.py             # NEW — main entry point
├── scenario_config.example.yaml      # NEW — documented example
├── tests/                            # NEW — bootstraps testing
│   ├── __init__.py
│   └── test_scenario_generator.py
├── docs/superpowers/specs/
│   └── 2026-04-28-scenario-generator-design.md   # this file
├── scenario.csv                      # existing — generator never overwrites without --force
└── ... (existing files unchanged)
```

## Dependencies

Add to `requirements.txt` (most likely already transitively present, but pin):
- `pyyaml` — config loading
- `scipy` — `scipy.stats.qmc.LatinHypercube`

No new heavy dependencies. SALib / pyDOE3 explicitly avoided in v1.

## Example config (sensitivity mode)

```yaml
n_samples: 200
seed: 42
output: scenarios_sensitivity.csv

parameters:
  planting_date:    {type: date, min: 2021-04-15, max: 2021-07-31}
  plant_population: {type: float, min: 7, max: 20}
  row_spacing:      {type: int, min: 20, max: 75}
  cultivar_id:      {type: categorical, values: [IB0003, IB0002]}
  fertilizer_amount_n: {type: float, min: 0, max: 200}
  fertilizer_amount_p: {type: float, min: 0, max: 100}
  fertilizer_amount_k: {type: float, min: 0, max: 100}
  irrigation:       {type: categorical, values: [N, R, A]}
  residue_management: {type: categorical, values: [N, R]}
  fertilizer:       {type: categorical, values: [N, D]}

fixed:
  soil_id: IBSG910010

lookups:
  cultivar_id: {IB0003: "IR 36", IB0002: "CP170"}
  soil_id:     {IBSG910010: "Clay_loam"}
```

## Example config (realistic / training-data mode)

```yaml
n_samples: 200
seed: 42
output: scenarios_realistic.csv

parameters:
  planting_date:    {type: date, min: 2021-04-15, max: 2021-07-31}
  plant_population: {type: float, min: 7, max: 20}
  cultivar_id:      {type: categorical, values: [IB0003, IB0002]}
  management:
    type: bundle
    values:
      - {name: LowInput,    fertilizer: N, irrigation: N, residue_management: N, fertilizer_amount_n: 0,   fertilizer_amount_p: 0,  fertilizer_amount_k: 0}
      - {name: WithFert,    fertilizer: D, irrigation: N, residue_management: R, fertilizer_amount_n: 100, fertilizer_amount_p: 50, fertilizer_amount_k: 50}
      - {name: HighInput,   fertilizer: D, irrigation: R, residue_management: R, fertilizer_amount_n: 150, fertilizer_amount_p: 75, fertilizer_amount_k: 75}

fixed:
  soil_id: IBSG910010
  row_spacing: 75

lookups:
  cultivar_id: {IB0003: "IR 36", IB0002: "CP170"}
  soil_id:     {IBSG910010: "Clay_loam"}
```

The bundle's `name` field populates the `management_scenario` CSV column. Bundle keys must match valid CSV column names (validated at load).

## What this unblocks

Once shipped, the existing `scenario.csv` becomes generated-not-curated, reproducible from a YAML, and easy to extend (more samples, different ranges, different cultivars). The downstream batch runner (separate work) consumes `scenarios.csv` row-by-row regardless of whether it came from a hand-written file or this generator.
