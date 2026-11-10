import json
from pathlib import Path

import pytest

from app.compiler.analysis import analyze_source
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "compiler"
EXPECTED = json.loads((EXAMPLES / "expected_qubos.json").read_text())


@pytest.mark.parametrize("filename", EXPECTED)
def test_example_source_matches_independently_recorded_qubo(filename):
    # Read source as text only: examples have no runtime decorator and are never imported.
    result = analyze_source((EXAMPLES / filename).read_text())
    assert result.status == "supported", result.diagnostics
    assert result.qubo == QUBO.model_validate(EXPECTED[filename])
    assert result.circuit.executed is False


@pytest.mark.parametrize(
    ("filename", "bits", "objective"),
    [
        ("minimize_three_bits.py", "000", 5),
        ("minimize_three_bits.py", "001", 5),
        ("minimize_three_bits.py", "100", 3),
        ("minimize_three_bits.py", "101", 6),
        ("exactly_one.py", "000", 10),
        ("exactly_one.py", "001", -3),
        ("exactly_one.py", "010", -2),
        ("exactly_one.py", "011", 5),
        ("exactly_one.py", "100", -1),
        ("exactly_one.py", "101", 6),
        ("exactly_one.py", "110", 7),
        ("exactly_one.py", "111", 34),
    ],
)
def test_three_bit_examples_preserve_documented_values(filename, bits, objective):
    qubo = analyze_source((EXAMPLES / filename).read_text()).qubo
    assert evaluate_qubo(qubo, bits) == objective
