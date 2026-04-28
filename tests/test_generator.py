from datetime import date

import csv

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


_PDATE = {"type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)}


def test_fixed_applied_to_every_row():
    cfg = Config(
        n_samples=5, seed=0,
        parameters={"x": {"type": "float", "min": 0, "max": 1}, "planting_date": _PDATE},
        fixed={"soil_id": "ABC", "row_spacing": 75},
    )
    rows = resolve_rows(cfg)
    for r in rows:
        assert r["soil_id"] == "ABC"
        assert r["row_spacing"] == 75


def test_lookup_populates_display_name():
    cfg = Config(
        n_samples=3, seed=0,
        parameters={
            "cultivar_id": {"type": "categorical", "values": ["IB0003"]},
            "planting_date": _PDATE,
        },
        lookups={"cultivar_id": {"IB0003": "IR 36"}},
    )
    rows = resolve_rows(cfg)
    for r in rows:
        assert r["cultivar_id"] == "IB0003"
        assert r["cultivar_name"] == "IR 36"


def test_missing_lookup_leaves_name_empty():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "cultivar_id": {"type": "categorical", "values": ["UNKNOWN"]},
            "planting_date": _PDATE,
        },
        lookups={"cultivar_id": {"IB0003": "IR 36"}},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["cultivar_id"] == "UNKNOWN"
    assert rows[0].get("cultivar_name", "") == ""


def test_simulation_start_date_default_offset():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)
        }},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["simulation_start_date"] == date(2021, 4, 16)


def test_simulation_start_date_custom_offset():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)
        }},
        derivations={"simulation_start_offset_days": 30},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["simulation_start_date"] == date(2021, 4, 1)


def test_fertilizer_date_when_n_positive():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "planting_date": {"type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)},
            "fertilizer_amount_n": {"type": "float", "min": 100, "max": 100},
        },
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == date(2021, 5, 1)


def test_fertilizer_date_empty_when_n_zero():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={
            "planting_date": {"type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)},
            "fertilizer_amount_n": {"type": "float", "min": 0, "max": 0},
        },
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == ""


def test_fertilizer_date_defaults_to_planting_when_n_absent():
    cfg = Config(
        n_samples=1, seed=0,
        parameters={"planting_date": {
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 1)
        }},
    )
    rows = resolve_rows(cfg)
    assert rows[0]["fertilizer_date"] == date(2021, 5, 1)


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
            "planting_date": {"type": "date", "min": date(2021, 5, 1), "max": date(2021, 7, 1)},
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
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 31)
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
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 31)
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
            "type": "date", "min": date(2021, 5, 1), "max": date(2021, 5, 31)
        }},
    )
    out_path = tmp_path / "out.csv"
    write_csv(cfg, out_path)
    with open(out_path) as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["cultivar_id"] == ""
    assert rows[0]["soil_id"] == ""
