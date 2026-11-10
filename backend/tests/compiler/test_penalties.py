import itertools
from textwrap import indent

import pytest

from app.compiler.analysis import analyze_source
from app.quantum.qubo import evaluate_qubo


def source(body, num_bits=3, sense="minimize"):
    return (
        f'@qatlas.objective(num_bits={num_bits}, sense="{sense}")\n'
        "def cost(x):\n" + indent(body, "    ") + "\n"
    )


@pytest.mark.parametrize("num_bits", range(1, 7))
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_weighted_named_square_matches_every_binary_assignment(num_bits, sense):
    body = (
        "weight = 2.5\nselected = 0\n"
        f"for i in range({num_bits}):\n    selected += (i+1)*x[i]\n"
        "residual = selected - 2\nreturn weight*residual**2 - x[0] + 7"
    )
    result = analyze_source(source(body, num_bits, sense))
    assert result.status == "supported", result.diagnostics
    sign = -1 if sense == "maximize" else 1
    for bits in itertools.product((0, 1), repeat=num_bits):
        expected = 2.5 * (sum((i + 1) * bit for i, bit in enumerate(bits)) - 2) ** 2 - bits[0] + 7
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == sign * expected


@pytest.mark.parametrize(
    ("expression", "constant", "linear", "pairs"),
    [
        ("(x[0] + x[1] - 1)**2", 1, [-1, -1, 0], [(0, 1, 2)]),
        ("(x[0]*x[1])**2", 0, [0, 0, 0], [(0, 1, 1)]),
        ("(x[0]**2)**2", 0, [1, 0, 0], []),
        ("(2*x[0] - x[1] + x[1])**2", 0, [4, 0, 0], []),
        ("3**2", 9, [0, 0, 0], []),
    ],
)
def test_square_expansion_preserves_binary_identities_offsets_and_cancellation(
    expression, constant, linear, pairs
):
    result = analyze_source(source("return " + expression))
    assert result.status == "supported", result.diagnostics
    assert result.qubo.constant == constant
    assert result.qubo.linear == linear
    assert [(term.i, term.j, term.coefficient) for term in result.qubo.quadratic] == pairs


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("return (x[0]*x[1] + x[2])**2", "HIGHER_ORDER"),
        ("return (x[0] + x[1])**3", "UNSUPPORTED_SYNTAX"),
        ("return x[0]**2.0", "UNSUPPORTED_SYNTAX"),
        ("return x[0]**True", "UNSUPPORTED_SYNTAX"),
        ("power = 2\nreturn x[0]**power", "UNSUPPORTED_SYNTAX"),
        ("return unknown**2", "UNDEFINED_NAME"),
        ("unused = forbidden()**2\nreturn 0", "UNSUPPORTED_SYNTAX"),
        ("return 1e200**2", "NONFINITE_COEFFICIENT"),
        # Coefficients fit individually, but the source square overflows on x=111.
        ("return (7e153*x[0] + 7e153*x[1] + 7e153*x[2])**2", "NONFINITE_COEFFICIENT"),
    ],
)
def test_unsupported_or_nonfinite_powers_are_rejected_with_locations(body, code):
    result = analyze_source(source(body))
    assert result.status == "rejected"
    assert result.qubo is None and result.circuit is None
    assert result.diagnostics[0].code == code
    assert result.diagnostics[0].line >= 3
