"""Hand-calculated objective values, independent of future solver behavior."""

from copy import deepcopy

import pytest

from app.experiments.optimization.classical import evaluate_qubo


@pytest.mark.parametrize(
    ("assignment", "expected"),
    [
        ([0, 0, 0], 1.25),
        ([0, 0, 1], -1.75),
        ([0, 1, 0], 1.75),
        ([0, 1, 1], -2.75),
        ([1, 0, 0], -0.75),
        ([1, 0, 1], -3.75),
        ([1, 1, 0], 3.75),
        ([1, 1, 1], -0.75),
    ],
)
def test_mixed_coefficients_over_all_assignments(mixed_qubo, assignment, expected):
    assert evaluate_qubo(mixed_qubo, assignment) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("assignment", "expected"),
    [([0, 0, 0], 0.0), ([1, 0, 0], 10.0), ([0, 1, 0], 20.0), ([1, 1, 0], 45.0)],
)
def test_project_spec_example(assignment, expected):
    qubo = {
        "num_variables": 3,
        "constant": 0.0,
        "linear": [10.0, 20.0, 0.0],
        "quadratic": [{"i": 0, "j": 1, "coefficient": 15.0}],
        "sense": "minimize",
    }
    assert evaluate_qubo(qubo, assignment) == pytest.approx(expected)


def test_constant_objective_without_pair_terms():
    qubo = {
        "num_variables": 2,
        "constant": -2.5,
        "linear": [0.0, 0.0],
        "quadratic": [],
        "sense": "minimize",
    }
    assert evaluate_qubo(qubo, [0, 1]) == pytest.approx(-2.5)


def test_inputs_are_not_modified(mixed_qubo):
    before = deepcopy(mixed_qubo)
    assignment = [1, 0, 1]
    evaluate_qubo(mixed_qubo, assignment)
    assert mixed_qubo == before
    assert assignment == [1, 0, 1]


@pytest.mark.parametrize("assignment", [[0, 1], [0, 1, 0, 1]])
def test_rejects_assignment_length_mismatch(mixed_qubo, assignment):
    with pytest.raises(ValueError, match="length"):
        evaluate_qubo(mixed_qubo, assignment)


@pytest.mark.parametrize("assignment", [[0, 2, 1], [0, -1, 1], [0, "1", 1], "010"])
def test_rejects_nonbinary_or_string_assignment(mixed_qubo, assignment):
    with pytest.raises(ValueError, match="binary"):
        evaluate_qubo(mixed_qubo, assignment)


def test_rejects_noncanonical_objective_sense(mixed_qubo):
    mixed_qubo["sense"] = "maximize"
    with pytest.raises(ValueError, match="minimize"):
        evaluate_qubo(mixed_qubo, [0, 0, 0])
