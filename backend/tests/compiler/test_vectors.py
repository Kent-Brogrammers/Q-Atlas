import itertools
from textwrap import indent
from unittest.mock import patch

import pytest

from app.compiler.analysis import analyze_source
from app.quantum.qubo import evaluate_qubo


def source(body):
    return "@qatlas.objective(num_bits=4)\ndef cost(x):\n" + indent(body, "    ") + "\n"


@pytest.mark.parametrize("vector", ["(1, -2, +0, 0.5)", "[1, -2, +0, 0.5]"])
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_literal_weight_vectors_match_independent_math_on_every_assignment(vector, sense):
    text = source(
        f"weights = {vector}\ntotal = 3\nfor i in range(4):\n"
        "    total += weights[i] * x[i]\nreturn total + 2*x[0]*x[3]"
    ).replace("num_bits=4", f'num_bits=4, sense="{sense}"')
    result = analyze_source(text)
    assert result.status == "supported", result.diagnostics
    sign = -1 if sense == "maximize" else 1
    for bits in itertools.product((0, 1), repeat=4):
        expected = sign * (3 + bits[0] - 2 * bits[1] + 0.5 * bits[3] + 2 * bits[0] * bits[3])
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == expected


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("weights = []\nreturn 0", "INVALID_VECTOR"),
        ("weights = [True]\nreturn 0", "INVALID_VECTOR"),
        ("weights = [run()]\nreturn 0", "INVALID_VECTOR"),
        ("weights = [[1]]\nreturn 0", "INVALID_VECTOR"),
        ("weights = [x[0]]\nreturn 0", "INVALID_VECTOR"),
        ("weights = [1e309]\nreturn 0", "NONFINITE_COEFFICIENT"),
        ("weights = [1]\nreturn weights[1]", "INVALID_INDEX"),
        ("weights = [1]\nreturn weights[-1]", "INVALID_INDEX"),
        ("weights = [1]\nreturn weights[x[0]]", "INVALID_INDEX"),
        ("weights = [1]\nreturn weights", "UNSUPPORTED_SYNTAX"),
        ("weights = [1]\nweights[0] = 2\nreturn 0", "INVALID_ASSIGNMENT"),
        ("weights = [1]\nweights += [2]\nreturn 0", "UNSUPPORTED_SYNTAX"),
    ],
)
def test_invalid_vectors_and_mutation_fail_before_generation(body, code):
    result = analyze_source(source(body))
    assert result.status == "rejected" and result.qubo is None
    assert result.diagnostics[0].code == code


def test_vector_length_bound_and_sequential_reassignment():
    vector = ",".join(["1"] * 64)
    accepted = analyze_source(source(f"weights = [{vector}]\nreturn weights[63]*x[3]"))
    assert accepted.status == "supported"
    assert accepted.qubo.linear == [0, 0, 0, 1]
    rejected = analyze_source(source(f"weights = [{vector}, 1]\nreturn 0"))
    assert rejected.diagnostics[0].code == "INVALID_VECTOR"
    reassigned = analyze_source(
        source("weights = [1]\na = weights[0]\nweights = (-2,)\nreturn a*x[0] + weights[0]*x[1]")
    )
    assert reassigned.qubo.linear == [1, -2, 0, 0]


def test_original_vector_interpreter_detects_corrupted_symbolic_values():
    with patch("app.compiler.analysis._vector_literal", return_value=(99.0,)):
        result = analyze_source(source("weights = (2,)\nreturn weights[0]*x[0]"))
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "VERIFICATION_FAILED"
