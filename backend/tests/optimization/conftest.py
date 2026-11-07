"""Canonical QUBO examples shared by Developer 3's tests."""

import pytest


@pytest.fixture
def mixed_qubo():
    """C(x) = 1.25 - 2*x0 + 0.5*x1 - 3*x2 + 4*x0*x1 - 1.5*x1*x2."""
    return {
        "num_variables": 3,
        "constant": 1.25,
        "linear": [-2.0, 0.5, -3.0],
        "quadratic": [
            {"i": 0, "j": 1, "coefficient": 4.0},
            {"i": 1, "j": 2, "coefficient": -1.5},
        ],
        "sense": "minimize",
    }
