from pathlib import Path

import pytest

from dssat_sim.scenarios import Config, ConfigError, load_config, validate_config


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
