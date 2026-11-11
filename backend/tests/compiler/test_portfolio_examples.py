"""Read example source as text; compare every assignment against independent arithmetic."""

from itertools import product
from pathlib import Path

import pytest

from app.compiler.generation import generate_source
from app.quantum.qubo import evaluate_qubo

PROGRAMS = Path(__file__).resolve().parents[3] / "examples/compiler/programs"


@pytest.mark.parametrize(
    "width,target,optimum", [(3, 1, -8), (4, 2, -15), (5, 2, -15), (6, 3, -22)]
)
def test_portfolio_examples_compile_and_preserve_problem_for_every_assignment(
    width, target, optimum
):
    result = generate_source((PROGRAMS / f"portfolio_{width}.py").read_text())
    assert result.status == "supported", result.diagnostics
    assert result.qubo.num_variables == width
    assert result.circuit.num_qubits == width
    assert result.artifact.executed is False
    costs = []
    for bits in product((0, 1), repeat=width):
        impact = sum(weight * bit for weight, bit in zip([8, 7, 6, 5, 4, 3], bits, strict=False))
        synergy = 2 * bits[0] * bits[3] if width >= 4 else 0
        if width >= 5:
            synergy += bits[1] * bits[4]
        expected = 30 * (sum(bits) - target) ** 2 - impact - synergy
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == expected
        costs.append(expected)
    assert min(costs) == optimum
