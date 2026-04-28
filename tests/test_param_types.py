from datetime import date

import pytest

from scenario_generator import (
    BundleParam,
    CategoricalParam,
    DateParam,
    FloatParam,
    IntParam,
)


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
    assert "name" not in out


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
