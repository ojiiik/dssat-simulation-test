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


import math


class FloatParam:
    def __init__(self, name: str, min: float, max: float):
        self.name = name
        self.min = float(min)
        self.max = float(max)

    def map(self, u: float) -> dict[str, Any]:
        return {self.name: self.min + (self.max - self.min) * u}


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
    unit = sampler.random(n=cfg.n_samples)
    rows: list[dict[str, Any]] = []
    for i in range(cfg.n_samples):
        row: dict[str, Any] = {}
        for j, p in enumerate(params):
            row.update(p.map(float(unit[i, j])))
        rows.append(row)
    return rows


LOOKUP_SUFFIX = "_name"


def _apply_lookups(row: dict[str, Any], lookups: dict[str, dict[str, str]]) -> None:
    for source_key, mapping in lookups.items():
        if source_key not in row:
            continue
        target_key = source_key.removesuffix("_id") + LOOKUP_SUFFIX
        row[target_key] = mapping.get(row[source_key], "")


def resolve_rows(cfg: Config) -> list[dict[str, Any]]:
    """Sample, apply fixed values, apply lookups. Derivations come in the next task."""
    rows = sample_rows(cfg)
    for row in rows:
        for k, v in cfg.fixed.items():
            row.setdefault(k, v)
        _apply_lookups(row, cfg.lookups)
    return rows
