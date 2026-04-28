# Scenario Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a YAML-driven Latin Hypercube Sampling generator that produces `scenario.csv`-compatible output, supporting both independent-parameter sensitivity analysis (mode A) and bundled-parameter realistic-scenario generation (mode B) via the same tool.

**Architecture:** Single-file Python module (`scenario_generator.py`) with a small class hierarchy for parameter types (FloatParam / IntParam / DateParam / CategoricalParam / BundleParam) wrapping `scipy.stats.qmc.LatinHypercube`. Config loaded from YAML via dataclass. CLI thin shim using argparse. Tests bootstrap pytest in the project (none currently exist).

**Tech Stack:** Python 3.11+, scipy (LHS), pyyaml (config), pandas (CSV output), pytest (tests).

**Spec reference:** `docs/superpowers/specs/2026-04-28-scenario-generator-design.md`

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `scenario_generator.py` | NEW | Public API, parameter type classes, LHS sampler, CSV writer, CLI |
| `scenario_config.example.yaml` | NEW | Documented example config (sensitivity + realistic side-by-side) |
| `tests/__init__.py` | NEW | Empty, makes tests a package |
| `tests/test_param_types.py` | NEW | Unit tests for FloatParam, IntParam, DateParam, CategoricalParam, BundleParam |
| `tests/test_config.py` | NEW | Config loading + validation tests |
| `tests/test_generator.py` | NEW | LHS, derivations, CSV writing, CLI integration |
| `requirements.txt` | MODIFY | Add `pyyaml`, ensure `scipy` pinned |
| `.gitignore` | MODIFY | Add `scenarios*.csv` and `.pytest_cache/` (don't track generated outputs) |

Single-file module (not a package) follows the existing project style (`dssat_simulator.py`, `config.py` are flat). Split tests by concern so each file stays under ~150 lines.

---

## Task 1: Bootstrap testing & dependencies

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `requirements.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add dependencies to requirements.txt**

Add these lines to the existing `requirements.txt` (alphabetical order alongside existing pins):

```
PyYAML==6.0.2
scipy==1.14.1
```

- [ ] **Step 2: Update .gitignore**

Append to `.gitignore`:

```
.pytest_cache/
scenarios*.csv
!scenario.csv
```

The `!scenario.csv` keeps the existing committed CSV tracked; only generated `scenarios_*.csv` outputs are ignored.

- [ ] **Step 3: Create empty tests package**

Write `tests/__init__.py` as an empty file.

- [ ] **Step 4: Create pytest conftest**

Write `tests/conftest.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```

This puts the project root on sys.path so `import scenario_generator` works in tests.

- [ ] **Step 5: Install deps and verify pytest collects**

Run:

```bash
pip install -r requirements.txt
pytest --collect-only
```

Expected: exits 0, says "no tests ran" (no test files yet).

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore tests/__init__.py tests/conftest.py
git commit -m "chore: bootstrap pytest and add scenario generator deps"
```

---

## Task 2: Config dataclass + YAML loading

**Files:**
- Create: `scenario_generator.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_config.py`:

```python
from pathlib import Path
from scenario_generator import load_config


def test_load_minimal_config(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "n_samples: 10\n"
        "seed: 42\n"
        "parameters:\n"
        "  x: {type: float, min: 0, max: 1}\n"
    )
    cfg = load_config(cfg_file)
    assert cfg.n_samples == 10
    assert cfg.seed == 42
    assert "x" in cfg.parameters
    assert cfg.parameters["x"]["type"] == "float"
    assert cfg.fixed == {}
    assert cfg.derivations == {}
    assert cfg.lookups == {}
    assert cfg.output == "scenarios.csv"


def test_load_full_config(tmp_path: Path):
    cfg_file = tmp_path / "c.yaml"
    cfg_file.write_text(
        "n_samples: 5\n"
        "seed: 7\n"
        "output: out.csv\n"
        "parameters:\n"
        "  x: {type: int, min: 1, max: 5}\n"
        "fixed:\n"
        "  soil_id: ABC\n"
        "derivations:\n"
        "  simulation_start_offset_days: 30\n"
        "lookups:\n"
        "  soil_id: {ABC: 'Clay'}\n"
    )
    cfg = load_config(cfg_file)
    assert cfg.output == "out.csv"
    assert cfg.fixed == {"soil_id": "ABC"}
    assert cfg.derivations["simulation_start_offset_days"] == 30
    assert cfg.lookups["soil_id"]["ABC"] == "Clay"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: ImportError ("No module named 'scenario_generator'") or collection error.

- [ ] **Step 3: Write minimal implementation**

Create `scenario_generator.py`:

```python
"""LHS-based scenario generator for DSSAT simulations.

Reads a YAML config describing parameters to sample, fixed values, derivations,
and lookups, then writes a `scenario.csv`-compatible output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Config:
    n_samples: int
    seed: int
    parameters: dict[str, Any]
    fixed: dict[str, Any] = field(default_factory=dict)
    derivations: dict[str, Any] = field(default_factory=dict)
    lookups: dict[str, dict[str, str]] = field(default_factory=dict)
    output: str = "scenarios.csv"


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    return Config(
        n_samples=raw["n_samples"],
        seed=raw["seed"],
        parameters=raw.get("parameters") or {},
        fixed=raw.get("fixed") or {},
        derivations=raw.get("derivations") or {},
        lookups=raw.get("lookups") or {},
        output=raw.get("output", "scenarios.csv"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_config.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_config.py
git commit -m "feat: add Config dataclass and load_config for scenario generator"
```

---

## Task 3: Config validation

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_config.py`:

```python
import pytest
from scenario_generator import ConfigError, validate_config, Config


def _cfg(**kwargs) -> Config:
    base = dict(n_samples=10, seed=42, parameters={"x": {"type": "float", "min": 0, "max": 1}})
    base.update(kwargs)
    return Config(**base)


def test_rejects_n_samples_zero():
    with pytest.raises(ConfigError, match="n_samples"):
        validate_config(_cfg(n_samples=0))


def test_rejects_no_parameters():
    with pytest.raises(ConfigError, match="parameters"):
        validate_config(_cfg(parameters={}))


def test_rejects_unknown_type():
    with pytest.raises(ConfigError, match="unknown type"):
        validate_config(_cfg(parameters={"x": {"type": "weird"}}))


def test_rejects_min_greater_than_max():
    with pytest.raises(ConfigError, match="min .* max"):
        validate_config(_cfg(parameters={"x": {"type": "float", "min": 10, "max": 1}}))


def test_rejects_empty_categorical():
    with pytest.raises(ConfigError, match="values"):
        validate_config(_cfg(parameters={"x": {"type": "categorical", "values": []}}))


def test_rejects_bundle_without_name():
    with pytest.raises(ConfigError, match="name"):
        validate_config(_cfg(parameters={
            "m": {"type": "bundle", "values": [{"fertilizer": "N"}]}
        }))


def test_rejects_bundle_key_collision():
    with pytest.raises(ConfigError, match="collide"):
        validate_config(_cfg(parameters={
            "x": {"type": "float", "min": 0, "max": 1},
            "m": {"type": "bundle", "values": [{"name": "A", "x": 5}]},
        }))


def test_accepts_valid_bundle():
    validate_config(_cfg(parameters={
        "m": {"type": "bundle", "values": [
            {"name": "Low", "fertilizer_amount_n": 0},
            {"name": "High", "fertilizer_amount_n": 150},
        ]},
    }))
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_config.py -v
```

Expected: 8 failures (ConfigError / validate_config not defined).

- [ ] **Step 3: Add ConfigError and validate_config**

Append to `scenario_generator.py`:

```python
VALID_TYPES = {"float", "int", "date", "categorical", "bundle"}


class ConfigError(ValueError):
    """Raised when a YAML config fails validation."""


def validate_config(cfg: Config) -> None:
    if cfg.n_samples < 1:
        raise ConfigError(f"n_samples must be >= 1, got {cfg.n_samples}")
    if not cfg.parameters:
        raise ConfigError("at least one entry under `parameters` is required for LHS")

    top_level_names = set(cfg.parameters.keys())

    for name, spec in cfg.parameters.items():
        ptype = spec.get("type")
        if ptype not in VALID_TYPES:
            raise ConfigError(f"parameter `{name}`: unknown type {ptype!r}")

        if ptype in {"float", "int", "date"}:
            if "min" not in spec or "max" not in spec:
                raise ConfigError(f"parameter `{name}`: type {ptype} requires min and max")
            if spec["min"] > spec["max"]:
                raise ConfigError(f"parameter `{name}`: min ({spec['min']}) > max ({spec['max']})")

        if ptype == "categorical":
            values = spec.get("values") or []
            if not values:
                raise ConfigError(f"parameter `{name}`: categorical needs non-empty `values`")

        if ptype == "bundle":
            values = spec.get("values") or []
            if not values:
                raise ConfigError(f"parameter `{name}`: bundle needs non-empty `values`")
            for i, entry in enumerate(values):
                if "name" not in entry:
                    raise ConfigError(f"parameter `{name}`: bundle entry {i} missing `name`")
                for key in entry:
                    if key == "name":
                        continue
                    if key in top_level_names and key != name:
                        raise ConfigError(
                            f"parameter `{name}`: bundle key `{key}` "
                            f"collides with top-level parameter"
                        )
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_config.py -v
```

Expected: 10 passed (2 original + 8 new).

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_config.py
git commit -m "feat: add scenario config validation"
```

---

## Task 4: FloatParam

**Files:**
- Modify: `scenario_generator.py`
- Create: `tests/test_param_types.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_param_types.py`:

```python
import pytest
from scenario_generator import FloatParam


def test_float_at_min():
    p = FloatParam("N", min=0.0, max=200.0)
    assert p.map(0.0) == {"N": 0.0}


def test_float_at_max():
    p = FloatParam("N", min=0.0, max=200.0)
    assert p.map(1.0) == {"N": 200.0}


def test_float_midpoint():
    p = FloatParam("N", min=0.0, max=200.0)
    assert p.map(0.5) == {"N": 100.0}


def test_float_negative_range():
    p = FloatParam("delta", min=-5.0, max=5.0)
    assert p.map(0.5) == {"delta": 0.0}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_param_types.py -v
```

Expected: 4 failures (FloatParam not defined).

- [ ] **Step 3: Implement FloatParam**

Append to `scenario_generator.py`:

```python
class FloatParam:
    def __init__(self, name: str, min: float, max: float):
        self.name = name
        self.min = float(min)
        self.max = float(max)

    def map(self, u: float) -> dict[str, Any]:
        return {self.name: self.min + (self.max - self.min) * u}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_param_types.py -v
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_param_types.py
git commit -m "feat: add FloatParam for LHS continuous sampling"
```

---

## Task 5: IntParam

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_param_types.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_param_types.py`:

```python
from scenario_generator import IntParam


def test_int_at_min():
    p = IntParam("pop", min=7, max=15)
    result = p.map(0.0)
    assert result == {"pop": 7}
    assert isinstance(result["pop"], int)


def test_int_at_max_exact():
    p = IntParam("pop", min=7, max=15)
    assert p.map(1.0) == {"pop": 15}


def test_int_clamped_at_one():
    """u=1.0 must NOT produce max+1 (out of range)."""
    p = IntParam("pop", min=0, max=2)
    assert p.map(1.0) == {"pop": 2}


def test_int_uniform_buckets():
    """Each integer value should be reachable for uniform inputs."""
    p = IntParam("pop", min=1, max=4)
    seen = set()
    for u in [0.0, 0.25, 0.5, 0.75, 0.99]:
        seen.add(p.map(u)["pop"])
    assert seen == {1, 2, 3, 4}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_param_types.py -v
```

Expected: 4 new failures (IntParam not defined).

- [ ] **Step 3: Implement IntParam**

Append to `scenario_generator.py`:

```python
import math


class IntParam:
    def __init__(self, name: str, min: int, max: int):
        self.name = name
        self.min = int(min)
        self.max = int(max)

    def map(self, u: float) -> dict[str, Any]:
        n_buckets = self.max - self.min + 1
        idx = int(math.floor(u * n_buckets))
        if idx >= n_buckets:
            idx = n_buckets - 1
        return {self.name: self.min + idx}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_param_types.py -v
```

Expected: 8 passed (4 from Task 4 + 4 new).

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_param_types.py
git commit -m "feat: add IntParam with end-bucket clamping"
```

---

## Task 6: DateParam

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_param_types.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_param_types.py`:

```python
from datetime import date
from scenario_generator import DateParam


def test_date_at_min():
    p = DateParam("pdate", min=date(2021, 4, 15), max=date(2021, 7, 31))
    assert p.map(0.0) == {"pdate": date(2021, 4, 15)}


def test_date_at_max():
    p = DateParam("pdate", min=date(2021, 4, 15), max=date(2021, 7, 31))
    assert p.map(1.0) == {"pdate": date(2021, 7, 31)}


def test_date_crosses_year_boundary():
    p = DateParam("pdate", min=date(2020, 12, 20), max=date(2021, 1, 10))
    result = p.map(0.5)["pdate"]
    assert date(2020, 12, 20) <= result <= date(2021, 1, 10)


def test_date_returns_date_not_datetime():
    p = DateParam("pdate", min=date(2021, 4, 15), max=date(2021, 7, 31))
    result = p.map(0.5)["pdate"]
    assert type(result) is date
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_param_types.py -v
```

Expected: 4 new failures.

- [ ] **Step 3: Implement DateParam**

Append to `scenario_generator.py`:

```python
from datetime import date, timedelta


class DateParam:
    def __init__(self, name: str, min: date, max: date):
        self.name = name
        self.min = min
        self.max = max

    def map(self, u: float) -> dict[str, Any]:
        delta_days = (self.max - self.min).days
        offset = round(delta_days * u)
        return {self.name: self.min + timedelta(days=offset)}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_param_types.py -v
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_param_types.py
git commit -m "feat: add DateParam with day-rounded interpolation"
```

---

## Task 7: CategoricalParam

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_param_types.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_param_types.py`:

```python
from scenario_generator import CategoricalParam


def test_categorical_first():
    p = CategoricalParam("cv", values=["IB0003", "IB0002", "IB0026"])
    assert p.map(0.0) == {"cv": "IB0003"}


def test_categorical_last():
    p = CategoricalParam("cv", values=["IB0003", "IB0002", "IB0026"])
    assert p.map(1.0) == {"cv": "IB0026"}


def test_categorical_middle():
    p = CategoricalParam("cv", values=["A", "B", "C"])
    assert p.map(0.5) == {"cv": "B"}


def test_categorical_clamped_at_one():
    p = CategoricalParam("flag", values=["N", "R"])
    assert p.map(1.0) == {"flag": "R"}


def test_categorical_uniform_buckets():
    p = CategoricalParam("cv", values=["A", "B", "C"])
    seen = set()
    for u in [0.0, 0.4, 0.7, 0.99]:
        seen.add(p.map(u)["cv"])
    assert seen == {"A", "B", "C"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_param_types.py -v
```

Expected: 5 new failures.

- [ ] **Step 3: Implement CategoricalParam**

Append to `scenario_generator.py`:

```python
class CategoricalParam:
    def __init__(self, name: str, values: list):
        self.name = name
        self.values = list(values)

    def map(self, u: float) -> dict[str, Any]:
        n = len(self.values)
        idx = int(math.floor(u * n))
        if idx >= n:
            idx = n - 1
        return {self.name: self.values[idx]}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_param_types.py -v
```

Expected: 17 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_param_types.py
git commit -m "feat: add CategoricalParam with end-clamp"
```

---

## Task 8: BundleParam

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_param_types.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_param_types.py`:

```python
from scenario_generator import BundleParam


BUNDLE_VALUES = [
    {"name": "LowInput", "fertilizer": "N", "fertilizer_amount_n": 0},
    {"name": "HighInput", "fertilizer": "D", "fertilizer_amount_n": 150},
]


def test_bundle_first_entry():
    p = BundleParam(values=BUNDLE_VALUES)
    out = p.map(0.0)
    assert out["management_scenario"] == "LowInput"
    assert out["fertilizer"] == "N"
    assert out["fertilizer_amount_n"] == 0
    assert "name" not in out  # name promoted to management_scenario only


def test_bundle_last_entry():
    p = BundleParam(values=BUNDLE_VALUES)
    out = p.map(1.0)
    assert out["management_scenario"] == "HighInput"
    assert out["fertilizer_amount_n"] == 150


def test_bundle_clamped_at_one():
    p = BundleParam(values=BUNDLE_VALUES)
    assert p.map(1.0)["management_scenario"] == "HighInput"


def test_bundle_produces_multiple_columns():
    p = BundleParam(values=BUNDLE_VALUES)
    out = p.map(0.0)
    assert set(out.keys()) == {"management_scenario", "fertilizer", "fertilizer_amount_n"}
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_param_types.py -v
```

Expected: 4 new failures.

- [ ] **Step 3: Implement BundleParam**

Append to `scenario_generator.py`:

```python
class BundleParam:
    def __init__(self, values: list[dict]):
        self.values = list(values)

    def map(self, u: float) -> dict[str, Any]:
        n = len(self.values)
        idx = int(math.floor(u * n))
        if idx >= n:
            idx = n - 1
        entry = self.values[idx]
        out: dict[str, Any] = {"management_scenario": entry["name"]}
        for k, v in entry.items():
            if k != "name":
                out[k] = v
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_param_types.py -v
```

Expected: 21 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_param_types.py
git commit -m "feat: add BundleParam expanding one LHS dim to multiple columns"
```

---

## Task 9: Param factory + LHS sampling

**Files:**
- Modify: `scenario_generator.py`
- Create: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_generator.py`:

```python
from datetime import date
from scenario_generator import (
    Config,
    build_params,
    sample_rows,
    FloatParam,
    IntParam,
    DateParam,
    CategoricalParam,
    BundleParam,
)


def test_build_params_dispatches_by_type():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "a": {"type": "float", "min": 0, "max": 1},
            "b": {"type": "int", "min": 1, "max": 5},
            "c": {"type": "date", "min": date(2021, 1, 1), "max": date(2021, 12, 31)},
            "d": {"type": "categorical", "values": ["x", "y"]},
            "e": {"type": "bundle", "values": [{"name": "A", "k": 1}]},
        },
    )
    params = build_params(cfg)
    assert isinstance(params[0], FloatParam)
    assert isinstance(params[1], IntParam)
    assert isinstance(params[2], DateParam)
    assert isinstance(params[3], CategoricalParam)
    assert isinstance(params[4], BundleParam)


def test_sample_rows_count():
    cfg = Config(
        n_samples=20, seed=42,
        parameters={"x": {"type": "float", "min": 0, "max": 100}},
    )
    rows = sample_rows(cfg)
    assert len(rows) == 20


def test_sample_rows_reproducible():
    cfg = Config(
        n_samples=20, seed=42,
        parameters={"x": {"type": "float", "min": 0, "max": 100}},
    )
    rows_a = sample_rows(cfg)
    rows_b = sample_rows(cfg)
    assert rows_a == rows_b


def test_different_seeds_differ():
    cfg_a = Config(
        n_samples=20, seed=1,
        parameters={"x": {"type": "float", "min": 0, "max": 100}},
    )
    cfg_b = Config(
        n_samples=20, seed=2,
        parameters={"x": {"type": "float", "min": 0, "max": 100}},
    )
    assert sample_rows(cfg_a) != sample_rows(cfg_b)


def test_lhs_covers_range():
    """LHS guarantees one sample in each of n stratified buckets per dimension."""
    cfg = Config(
        n_samples=100, seed=0,
        parameters={"x": {"type": "float", "min": 0, "max": 1}},
    )
    rows = sample_rows(cfg)
    xs = [r["x"] for r in rows]
    assert min(xs) < 0.05
    assert max(xs) > 0.95
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v
```

Expected: 5 failures (build_params / sample_rows not defined).

- [ ] **Step 3: Implement build_params and sample_rows**

Append to `scenario_generator.py`:

```python
import numpy as np
from scipy.stats import qmc


def build_params(cfg: Config) -> list:
    """Construct parameter objects in declaration order."""
    out = []
    for name, spec in cfg.parameters.items():
        ptype = spec["type"]
        if ptype == "float":
            out.append(FloatParam(name, spec["min"], spec["max"]))
        elif ptype == "int":
            out.append(IntParam(name, spec["min"], spec["max"]))
        elif ptype == "date":
            out.append(DateParam(name, spec["min"], spec["max"]))
        elif ptype == "categorical":
            out.append(CategoricalParam(name, spec["values"]))
        elif ptype == "bundle":
            out.append(BundleParam(spec["values"]))
        else:
            raise ConfigError(f"unknown type {ptype!r} for parameter {name!r}")
    return out


def sample_rows(cfg: Config) -> list[dict[str, Any]]:
    """Run LHS and produce one dict per scenario (only sampled columns; no fixed/derived yet)."""
    params = build_params(cfg)
    sampler = qmc.LatinHypercube(d=len(params), seed=cfg.seed)
    unit = sampler.random(n=cfg.n_samples)  # shape (n_samples, n_dims)
    rows: list[dict[str, Any]] = []
    for i in range(cfg.n_samples):
        row: dict[str, Any] = {}
        for j, p in enumerate(params):
            row.update(p.map(float(unit[i, j])))
        rows.append(row)
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_generator.py
git commit -m "feat: integrate scipy LHS with parameter type dispatch"
```

---

## Task 10: Apply fixed values + lookups

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_generator.py`:

```python
from scenario_generator import resolve_rows


def test_fixed_applied_to_every_row():
    cfg = Config(
        n_samples=5, seed=0,
        parameters={"x": {"type": "float", "min": 0, "max": 1}},
        fixed={"soil_id": "ABC", "row_spacing": 75},
    )
    rows = resolve_rows(cfg)
    for r in rows:
        assert r["soil_id"] == "ABC"
        assert r["row_spacing"] == 75


def test_lookup_populates_display_name():
    cfg = Config(
        n_samples=3, seed=0,
        parameters={"cultivar_id": {"type": "categorical", "values": ["IB0003"]}},
        lookups={"cultivar_id": {"IB0003": "IR 36"}},
    )
    rows = resolve_rows(cfg)
    for r in rows:
        assert r["cultivar_id"] == "IB0003"
        assert r["cultivar_name"] == "IR 36"


def test_missing_lookup_leaves_name_empty():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"cultivar_id": {"type": "categorical", "values": ["UNKNOWN"]}},
        lookups={"cultivar_id": {"IB0003": "IR 36"}},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["cultivar_id"] == "UNKNOWN"
    assert rows[0].get("cultivar_name", "") == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v
```

Expected: 3 new failures (resolve_rows not defined).

- [ ] **Step 3: Implement resolve_rows (fixed + lookups only)**

Append to `scenario_generator.py`:

```python
LOOKUP_SUFFIX = "_name"  # cultivar_id -> cultivar_name


def _apply_lookups(row: dict[str, Any], lookups: dict[str, dict[str, str]]) -> None:
    for source_key, mapping in lookups.items():
        if source_key not in row:
            continue
        target_key = source_key.removesuffix("_id") + LOOKUP_SUFFIX
        # cultivar_id -> cultivar_name; soil_id -> soil_name
        row[target_key] = mapping.get(row[source_key], "")


def resolve_rows(cfg: Config) -> list[dict[str, Any]]:
    """Sample, apply fixed values, apply lookups. Derivations come in the next task."""
    rows = sample_rows(cfg)
    for row in rows:
        for k, v in cfg.fixed.items():
            row.setdefault(k, v)
        _apply_lookups(row, cfg.lookups)
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_generator.py
git commit -m "feat: apply fixed values and id->name lookups to resolved rows"
```

---

## Task 11: Derivations

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_generator.py`:

```python
from datetime import date as _date


def test_simulation_start_date_default_offset():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 1)
        }},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["simulation_start_date"] == _date(2021, 4, 16)  # 15 days earlier


def test_simulation_start_date_custom_offset():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 1)
        }},
        derivations={"simulation_start_offset_days": 30},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["simulation_start_date"] == _date(2021, 4, 1)


def test_fertilizer_date_when_n_positive():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "planting_date": {"type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 1)},
            "fertilizer_amount_n": {"type": "float", "min": 100, "max": 100},
        },
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == _date(2021, 5, 1)


def test_fertilizer_date_empty_when_n_zero():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "planting_date": {"type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 1)},
            "fertilizer_amount_n": {"type": "float", "min": 0, "max": 0},
        },
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == ""


def test_fertilizer_date_defaults_to_planting_when_n_absent():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 1)
        }},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == _date(2021, 5, 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v
```

Expected: 5 new failures (no derivation logic yet).

- [ ] **Step 3: Add derivation logic**

In `scenario_generator.py`, replace the `resolve_rows` function with:

```python
def _apply_derivations(row: dict[str, Any], derivations: dict[str, Any]) -> None:
    if "planting_date" not in row:
        raise ConfigError(
            "derivations require `planting_date` (sample it, fix it, or include it in a bundle)"
        )
    offset = int(derivations.get("simulation_start_offset_days", 15))
    row["simulation_start_date"] = row["planting_date"] - timedelta(days=offset)
    n_amt = row.get("fertilizer_amount_n")
    if n_amt is None:
        row["fertilizer_date"] = row["planting_date"]
    elif n_amt > 0:
        row["fertilizer_date"] = row["planting_date"]
    else:
        row["fertilizer_date"] = ""


def resolve_rows(cfg: Config) -> list[dict[str, Any]]:
    """Sample, apply fixed values, apply lookups, apply derivations."""
    rows = sample_rows(cfg)
    for row in rows:
        for k, v in cfg.fixed.items():
            row.setdefault(k, v)
        _apply_lookups(row, cfg.lookups)
        _apply_derivations(row, cfg.derivations)
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v
```

Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_generator.py
git commit -m "feat: add simulation_start_date and fertilizer_date derivations"
```

---

## Task 12: scenario_id and CSV writing

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_generator.py`:

```python
import csv
from scenario_generator import write_csv, CSV_COLUMNS


def test_csv_columns_match_existing_format():
    expected = [
        "scenario_id", "cultivar_id", "cultivar_name", "soil_id", "soil_name",
        "management_scenario", "planting_date", "plant_population", "fertilizer",
        "irrigation", "residue_management", "row_spacing",
        "fertilizer_amount_n", "fertilizer_amount_p", "fertilizer_amount_k",
        "simulation_start_date", "fertilizer_date",
    ]
    assert CSV_COLUMNS == expected
    assert len(CSV_COLUMNS) == 17


def test_write_csv_produces_correct_shape(tmp_path):
    cfg = Config(
        n_samples=10, seed=42,
        parameters={
            "planting_date": {"type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 7, 1)},
            "plant_population": {"type": "float", "min": 7, "max": 15},
        },
        fixed={"soil_id": "ABC"},
    )
    out_path = tmp_path / "out.csv"
    write_csv(cfg, out_path)

    with open(out_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    assert len(rows) == 10
    assert reader.fieldnames == CSV_COLUMNS


def test_scenario_id_zero_padded(tmp_path):
    cfg = Config(
        n_samples=15, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 31)
        }},
    )
    out_path = tmp_path / "out.csv"
    write_csv(cfg, out_path)
    with open(out_path) as f:
        ids = [r["scenario_id"] for r in csv.DictReader(f)]
    assert ids[0] == "SCENARIO_01"
    assert ids[-1] == "SCENARIO_15"


def test_scenario_id_padding_for_thousands(tmp_path):
    cfg = Config(
        n_samples=1000, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 31)
        }},
    )
    out_path = tmp_path / "out.csv"
    write_csv(cfg, out_path)
    with open(out_path) as f:
        ids = [r["scenario_id"] for r in csv.DictReader(f)]
    assert ids[0] == "SCENARIO_0001"
    assert ids[-1] == "SCENARIO_1000"


def test_missing_columns_render_as_empty(tmp_path):
    cfg = Config(
        n_samples=2, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": _date(2021, 5, 1), "max": _date(2021, 5, 31)
        }},
    )
    out_path = tmp_path / "out.csv"
    write_csv(cfg, out_path)
    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    # cultivar_id was never sampled or fixed — column exists but empty
    assert rows[0]["cultivar_id"] == ""
    assert rows[0]["soil_id"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v
```

Expected: 5 new failures.

- [ ] **Step 3: Implement write_csv**

Append to `scenario_generator.py`:

```python
import csv as _csv

CSV_COLUMNS = [
    "scenario_id", "cultivar_id", "cultivar_name", "soil_id", "soil_name",
    "management_scenario", "planting_date", "plant_population", "fertilizer",
    "irrigation", "residue_management", "row_spacing",
    "fertilizer_amount_n", "fertilizer_amount_p", "fertilizer_amount_k",
    "simulation_start_date", "fertilizer_date",
]


def _stringify(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def write_csv(cfg: Config, output_path: str | Path) -> None:
    rows = resolve_rows(cfg)
    pad_width = max(2, len(str(cfg.n_samples)))
    with open(output_path, "w", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for i, row in enumerate(rows, start=1):
            row["scenario_id"] = f"SCENARIO_{i:0{pad_width}d}"
            writer.writerow({col: _stringify(row.get(col, "")) for col in CSV_COLUMNS})
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v
```

Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add scenario_generator.py tests/test_generator.py
git commit -m "feat: add CSV writer with 17-column scenario.csv-compatible output"
```

---

## Task 13: CLI — basic generate

**Files:**
- Modify: `scenario_generator.py`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_generator.py`:

```python
import subprocess
import sys
from pathlib import Path


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
    assert result.returncode == 0, result.stderr
    assert out_path.exists()
    with open(out_path) as f:
        lines = f.readlines()
    assert len(lines) == 6  # header + 5 rows


def test_cli_invalid_config_exits_nonzero(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text("n_samples: 0\nseed: 1\nparameters: {}\n")
    out_path = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode != 0
    assert "n_samples" in result.stderr or "n_samples" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_generator.py -v -k cli
```

Expected: 2 failures (script entry point doesn't exist).

- [ ] **Step 3: Add main / CLI**

Append to `scenario_generator.py`:

```python
import argparse
import sys


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="scenario_generator",
        description="LHS-based scenario CSV generator for DSSAT simulations.",
    )
    p.add_argument("config", help="Path to YAML config")
    p.add_argument("--output", help="Override `output` from config")
    p.add_argument("--force", action="store_true", help="Overwrite existing output file")
    p.add_argument("--validate", action="store_true", help="Validate config and exit")
    p.add_argument("--preview", action="store_true",
                   help="Print first 5 rows + total count, do not write")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
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

    # preview mode
    rows = resolve_rows(cfg)
    print(f"Total: {len(rows)} scenarios. First 5:")
    for i, row in enumerate(rows[:5], start=1):
        print(f"  {i}: {row}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v -k cli
```

Expected: 2 passed.

- [ ] **Step 5: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass (~32 total).

- [ ] **Step 6: Commit**

```bash
git add scenario_generator.py tests/test_generator.py
git commit -m "feat: add CLI for scenario_generator"
```

---

## Task 14: CLI flags — validate, preview, force

**Files:**
- Modify: `tests/test_generator.py`

The CLI flags (`--validate`, `--preview`, `--force`) are already implemented in Task 13. This task adds tests covering each branch.

- [ ] **Step 1: Write failing tests**

Append to `tests/test_generator.py`:

```python
def test_cli_validate_only(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 5\nseed: 1\n"
        "parameters:\n  x: {type: float, min: 0, max: 1}\n"
    )
    out_path = tmp_path / "should_not_exist.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path), "--validate"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0
    assert not out_path.exists()
    assert "OK" in result.stdout


def test_cli_preview(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 12\nseed: 1\n"
        "parameters:\n  planting_date: {type: date, min: 2021-05-01, max: 2021-07-01}\n"
    )
    out_path = tmp_path / "should_not_exist.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path), "--preview"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0
    assert not out_path.exists()
    assert "Total: 12" in result.stdout


def test_cli_refuses_overwrite_without_force(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 3\nseed: 1\n"
        "parameters:\n  x: {type: float, min: 0, max: 1}\n"
    )
    out_path = tmp_path / "existing.csv"
    out_path.write_text("DO_NOT_OVERWRITE")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path)],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode != 0
    assert out_path.read_text() == "DO_NOT_OVERWRITE"


def test_cli_force_overwrites(tmp_path):
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text(
        "n_samples: 3\nseed: 1\n"
        "parameters:\n  x: {type: float, min: 0, max: 1}\n"
    )
    out_path = tmp_path / "existing.csv"
    out_path.write_text("OLD_CONTENT")
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path), "--force"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0
    assert "OLD_CONTENT" not in out_path.read_text()
    assert "scenario_id" in out_path.read_text()  # header is there
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
pytest tests/test_generator.py -v -k cli
```

Expected: 6 passed (the 2 from Task 13 + 4 new). All should already pass since the CLI logic was implemented in Task 13.

- [ ] **Step 3: Commit**

```bash
git add tests/test_generator.py
git commit -m "test: cover --validate, --preview, --force CLI flags"
```

---

## Task 15: Example config + integration test

**Files:**
- Create: `scenario_config.example.yaml`
- Modify: `tests/test_generator.py`

- [ ] **Step 1: Write the example config**

Create `scenario_config.example.yaml`:

```yaml
# Scenario generator example config.
# Two modes shown side-by-side: pick one and delete the other.

# ─── Mode A: Sensitivity analysis ───
# All parameters sampled independently. Use this when you want to attribute
# yield variance to individual inputs (Sobol/Morris-style downstream).

n_samples: 200
seed: 42
output: scenarios_sensitivity.csv

parameters:
  planting_date:       {type: date,        min: 2021-04-15, max: 2021-07-31}
  plant_population:    {type: float,       min: 7,          max: 20}
  row_spacing:         {type: int,         min: 20,         max: 75}
  cultivar_id:         {type: categorical, values: [IB0003, IB0002]}
  fertilizer_amount_n: {type: float,       min: 0,          max: 200}
  fertilizer_amount_p: {type: float,       min: 0,          max: 100}
  fertilizer_amount_k: {type: float,       min: 0,          max: 100}
  irrigation:          {type: categorical, values: [N, R, A]}
  residue_management:  {type: categorical, values: [N, R]}
  fertilizer:          {type: categorical, values: [N, D]}

fixed:
  soil_id: IBSG910010

derivations:
  simulation_start_offset_days: 15

lookups:
  cultivar_id: {IB0003: "IR 36", IB0002: "CP170"}
  soil_id:     {IBSG910010: "Clay_loam"}

# ─── Mode B: Realistic / training data ───
# To switch: replace the `parameters` block above with the one below. The
# `management` bundle keeps fertilizer/irrigation/residue agronomically
# coherent — N=0 won't pair with HighInput, and so on.
#
# parameters:
#   planting_date:    {type: date, min: 2021-04-15, max: 2021-07-31}
#   plant_population: {type: float, min: 7, max: 20}
#   cultivar_id:      {type: categorical, values: [IB0003, IB0002]}
#   management:
#     type: bundle
#     values:
#       - {name: LowInput,  fertilizer: N, irrigation: N, residue_management: N,
#          fertilizer_amount_n: 0,   fertilizer_amount_p: 0,  fertilizer_amount_k: 0}
#       - {name: WithFert,  fertilizer: D, irrigation: N, residue_management: R,
#          fertilizer_amount_n: 100, fertilizer_amount_p: 50, fertilizer_amount_k: 50}
#       - {name: HighInput, fertilizer: D, irrigation: R, residue_management: R,
#          fertilizer_amount_n: 150, fertilizer_amount_p: 75, fertilizer_amount_k: 75}
```

- [ ] **Step 2: Write integration test using the example**

Append to `tests/test_generator.py`:

```python
def test_example_config_generates_valid_csv(tmp_path):
    src = PROJECT_ROOT / "scenario_config.example.yaml"
    out_path = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(src), "--output", str(out_path), "--force"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stderr
    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 200
    # Sanity: scenario_ids unique
    assert len({r["scenario_id"] for r in rows}) == 200
    # Sanity: every row has soil from `fixed`
    assert all(r["soil_id"] == "IBSG910010" for r in rows)
    # Sanity: cultivar_name is populated from lookup
    assert all(r["cultivar_name"] in {"IR 36", "CP170"} for r in rows)
    # Sanity: simulation_start_date strictly before planting_date
    for r in rows:
        assert r["simulation_start_date"] < r["planting_date"]
    # Sanity: fertilizer_date empty iff fertilizer_amount_n == 0
    for r in rows:
        n_amt = float(r["fertilizer_amount_n"])
        if n_amt == 0:
            assert r["fertilizer_date"] == ""
        else:
            assert r["fertilizer_date"] == r["planting_date"]


def test_example_bundle_mode_via_yaml(tmp_path):
    """Exercise the bundle code path with an inline mode-B config."""
    cfg_path = tmp_path / "bundle.yaml"
    cfg_path.write_text("""
n_samples: 50
seed: 7
parameters:
  planting_date: {type: date, min: 2021-05-01, max: 2021-07-01}
  management:
    type: bundle
    values:
      - {name: LowInput,  fertilizer: N, fertilizer_amount_n: 0}
      - {name: HighInput, fertilizer: D, fertilizer_amount_n: 150}
fixed:
  soil_id: IBSG910010
""")
    out_path = tmp_path / "out.csv"
    result = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "scenario_generator.py"),
         str(cfg_path), "--output", str(out_path), "--force"],
        capture_output=True, text=True, cwd=PROJECT_ROOT,
    )
    assert result.returncode == 0, result.stderr
    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    # Every row has one of the two bundle names
    assert all(r["management_scenario"] in {"LowInput", "HighInput"} for r in rows)
    # Bundle correlations preserved
    for r in rows:
        if r["management_scenario"] == "LowInput":
            assert r["fertilizer"] == "N"
            assert float(r["fertilizer_amount_n"]) == 0
        else:
            assert r["fertilizer"] == "D"
            assert float(r["fertilizer_amount_n"]) == 150
```

- [ ] **Step 3: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 4: Smoke-test the CLI manually**

```bash
python scenario_generator.py scenario_config.example.yaml --output /tmp/sample.csv --force
head -3 /tmp/sample.csv
wc -l /tmp/sample.csv
```

Expected: file written, 17 columns visible, line count 201 (header + 200 rows).

- [ ] **Step 5: Commit**

```bash
git add scenario_config.example.yaml tests/test_generator.py
git commit -m "feat: add documented example YAML and end-to-end integration test"
```

---

## Self-Review Checklist (run after writing the plan; not at execution time)

**Spec coverage** — every spec section maps to a task:

| Spec section | Implementing task(s) |
|---|---|
| Goal / use cases A+B | Tasks 4-9 (parameter types) + Task 15 (bundle test exercises mode B) |
| Non-goals (v1) | Honored — no cultivar coefficients, no conditionals, no SALib |
| Architecture | Tasks 2, 9, 10, 11, 12 trace the data flow |
| YAML schema | Task 2 (load), Task 3 (validate) |
| Parameter types | Tasks 4 (float), 5 (int), 6 (date), 7 (categorical), 8 (bundle) |
| Bundle mechanic + key validation | Task 3 (collision check) + Task 8 (expansion) |
| Derivations | Task 11 |
| CSV output (17 cols) | Task 12 |
| CLI (4 flags) | Task 13 (generate) + Task 14 (--validate / --preview / --force) |
| Error handling rules | Task 3 (validation) + Task 13 (CLI exit codes) |
| Testing strategy | Tests interleaved through every task; Task 15 is the integration |
| File layout | Matches Tasks 1, 2, 15 |
| Dependencies | Task 1 |

No gaps.

**Placeholder scan** — no TBD/TODO/"add validation later"/"similar to" — all tasks contain working code.

**Type consistency** — `FloatParam`, `IntParam`, `DateParam`, `CategoricalParam`, `BundleParam` named consistently across all tasks. `Config` fields match between Task 2 and consumers in 9-15. `CSV_COLUMNS` defined once in Task 12 and referenced thereafter.

**Spec deviation note** — the spec mentioned `tests/test_scenario_generator.py` as a single test file, but the plan splits into `test_param_types.py`, `test_config.py`, and `test_generator.py`. This split is justified (each file stays small and focused) and doesn't change observable behavior.
