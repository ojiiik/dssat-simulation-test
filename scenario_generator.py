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
