import pytest
from scenario_generator import FloatParam, IntParam


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
