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
