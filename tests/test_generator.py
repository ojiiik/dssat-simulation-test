from datetime import date

from scenario_generator import (
    BundleParam,
    CategoricalParam,
    Config,
    DateParam,
    FloatParam,
    IntParam,
    build_params,
    resolve_rows,
    sample_rows,
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
