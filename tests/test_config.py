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
