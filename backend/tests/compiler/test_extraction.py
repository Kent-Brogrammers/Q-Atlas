import itertools
import math

import pytest

from app.compiler.analysis import analyze_source


def source(expression, num_bits=3, sense="minimize", parameter="x"):
    return (
        f'@qatlas.objective(num_bits={num_bits}, sense="{sense}")\n'
        f"def cost({parameter}):\n    return {expression}\n"
    )


@pytest.mark.parametrize("num_bits", range(1, 7))
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_extraction_matches_independent_objective_on_every_assignment(num_bits, sense):
    expression = "7 - 3*x[0] + x[0]**2 + x[0]*x[0]"
    if num_bits > 1:
        expression += f" + 4*x[{num_bits - 1}]*x[0] - x[0]*x[{num_bits - 1}]"
    result = analyze_source(source(expression, num_bits, sense))
    assert result.status == "supported"
    qubo = result.qubo
    sign = -1 if sense == "maximize" else 1
    assert qubo.sense == "minimize"
    assert qubo.original_sense == sense
    assert qubo.constant == sign * 7
    assert qubo.linear == [-sign] + [0] * (num_bits - 1)
    for bits in itertools.product((0, 1), repeat=num_bits):
        expected = 7 - bits[0] + (3 * bits[0] * bits[-1] if num_bits > 1 else 0)
        actual = qubo.constant + sum(a * b for a, b in zip(qubo.linear, bits, strict=True))
        actual += sum(t.coefficient * bits[t.i] * bits[t.j] for t in qubo.quadratic)
        assert actual == sign * expected
    assert f"{2**num_bits} binary assignments" in result.diagnostics[0].message


def test_parentheses_fractional_coefficients_variable_order_and_cancellation():
    result = analyze_source(source("-(bits[2] - 0.5)*(bits[0] + 2) + +bits[1]", parameter="bits"))
    assert result.status == "supported"
    assert result.qubo.constant == 1
    assert result.qubo.linear == [0.5, 1, -2]
    assert [(t.i, t.j, t.coefficient) for t in result.qubo.quadratic] == [(0, 2, -1)]
    assert analyze_source(source("x[0] - x[0]")).qubo.linear == [0, 0, 0]


def test_maximization_keeps_absent_coefficients_as_canonical_positive_zeros():
    result = analyze_source(source("2*x[0]", sense="maximize"))
    assert result.status == "supported"
    assert result.qubo.linear == [-2, 0, 0]
    assert math.copysign(1, result.qubo.constant) == 1
    assert all(math.copysign(1, value) == 1 for value in result.qubo.linear[1:])


def test_large_offset_cannot_hide_floating_point_normalization_errors():
    # For x[0]=1 the inner float sum loses the bit, but symbolic extraction retains it.
    # A relative tolerance scaled by 1e12 used to accept that objective discrepancy.
    result = analyze_source(source("1e12 + (1e16 + x[0] - 1e16)"))
    assert result.status == "rejected"
    assert result.qubo is None and result.circuit is None
    assert result.diagnostics[0].code == "VERIFICATION_FAILED"


def test_consistent_large_offset_is_still_supported():
    result = analyze_source(source("1e12 + x[0]"))
    assert result.status == "supported"
    assert result.qubo.constant == 1e12
    assert result.qubo.linear == [1, 0, 0]


@pytest.mark.parametrize(
    ("expression", "code"),
    [
        ("x[0]*x[1]*x[2]", "HIGHER_ORDER"),
        ("x[-1]", "INVALID_INDEX"),
        ("x[3]", "INVALID_INDEX"),
        ("x[True]", "INVALID_INDEX"),
        ("x[1+1]", "INVALID_INDEX"),
        ("other[0]", "INVALID_INDEX"),
        ("True", "UNSUPPORTED_SYNTAX"),
        ("unknown", "UNDEFINED_NAME"),
        ("x.value", "UNSUPPORTED_SYNTAX"),
        ("sum(x)", "UNSUPPORTED_SYNTAX"),
        ("[i for i in x]", "UNSUPPORTED_SYNTAX"),
        ("x[0] / 2", "UNSUPPORTED_SYNTAX"),
        ("x[0] ** 3", "UNSUPPORTED_SYNTAX"),
        ("1e309", "NONFINITE_COEFFICIENT"),
        ("1e308 * 2", "NONFINITE_COEFFICIENT"),
    ],
)
def test_rejected_expressions_have_locations_and_no_partial_qubo(expression, code):
    result = analyze_source(source(expression))
    assert result.status == "rejected"
    assert result.qubo is None and result.circuit is None
    assert result.diagnostics[0].code == code
    assert result.diagnostics[0].line == 3
    assert result.diagnostics[0].column >= 12


@pytest.mark.parametrize(
    "text",
    [
        "import os\n" + source("x[0]"),
        source("x[0]") + "print('outside')\n",
        "def cost(x): return x[0]",
        "@other.objective(num_bits=3)\ndef cost(x): return x[0]",
        "@qatlas.objective(num_bits=True)\ndef cost(x): return x[0]",
        "@qatlas.objective(num_bits=7)\ndef cost(x): return x[0]",
        "@qatlas.objective(num_bits=3, **options)\ndef cost(x): return x[0]",
        "@qatlas.objective(num_bits=3, num_bits=2)\ndef cost(x): return x[0]",
        source("x[0]").replace("cost(x)", "cost(x=run())"),
        source("x[0]").replace("cost(x)", "cost(x: run())"),
        source("x[0]").replace("return x[0]", "for i in x:\n        return i"),
        "@qatlas.objective(num_bits=3)\nasync def cost(x): return x[0]",
        "def invalid(:",
        "\x00",
    ],
)
def test_rejects_unsupported_markers_statements_and_signatures(text):
    assert analyze_source(text).status == "rejected"


def test_malicious_source_is_never_executed(tmp_path):
    target = tmp_path / "must-not-exist"
    expression = f"__import__('pathlib').Path({str(target)!r}).write_text('executed')"
    result = analyze_source(source(expression))
    assert result.status == "rejected"
    assert not target.exists()
    assert str(target) not in result.model_dump_json()


@pytest.mark.parametrize(
    "text",
    ["x" * 20_001, source("+" * 100 + "x[0]"), source("+".join(["x[0]"] * 600))],
)
def test_source_and_ast_resource_limits(text):
    result = analyze_source(text)
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "SOURCE_LIMIT"
