from datetime import date

from scenario_generator import (
    BundleParam,
    CategoricalParam,
    Config,
    DateParam,
    FloatParam,
    IntParam,
    build_params,
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
