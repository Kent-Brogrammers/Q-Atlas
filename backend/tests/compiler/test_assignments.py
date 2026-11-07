import itertools
from textwrap import indent

import pytest

from app.compiler.analysis import analyze_source
from app.quantum.qubo import evaluate_qubo


def source(body, num_bits=3, sense="minimize", parameter="x"):
    return (
        f'@qatlas.objective(num_bits={num_bits}, sense="{sense}")\n'
        f"def cost({parameter}):\n" + indent(body, "    ") + "\n"
    )


@pytest.mark.parametrize("num_bits", range(1, 7))
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_sequential_assignments_aliases_and_reassignment_match_all_inputs(num_bits, sense):
    body = (
        '"""A descriptive docstring."""\n'
        "weight = 2\n"
        "benefit = weight*bits[0]\n"
        "saved = benefit\n"
        f"benefit = benefit + bits[{num_bits - 1}]\n"
        "total = 5 - saved\n"
        f"total = total + benefit*bits[{num_bits - 1}]\n"
        "return total"
    )
    result = analyze_source(source(body, num_bits, sense, "bits"))
    assert result.status == "supported", result.diagnostics
    sign = -1 if sense == "maximize" else 1
    for bits in itertools.product((0, 1), repeat=num_bits):
        expected = sign * (5 - 2 * bits[0] + (2 * bits[0] + bits[-1]) * bits[-1])
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == expected
    assert result.circuit.num_qubits == num_bits


@pytest.mark.parametrize(
    ("body", "code", "line"),
    [
        ("a = b\nb = x[0]\nreturn a", "UNDEFINED_NAME", 3),
        ("a = a + 1\nreturn a", "UNDEFINED_NAME", 3),
        ("a = b\nb = a\nreturn b", "UNDEFINED_NAME", 3),
        ("x = 0\nreturn x[0]", "INVALID_ASSIGNMENT", 3),
        ("a = b = x[0]\nreturn a", "INVALID_ASSIGNMENT", 3),
        ("a, b = x[0], x[1]\nreturn a", "INVALID_ASSIGNMENT", 3),
        ("x[0] = 1\nreturn x[0]", "INVALID_ASSIGNMENT", 3),
        ("x.value = 1\nreturn x[0]", "INVALID_ASSIGNMENT", 3),
        ("a: int = 1\nreturn a", "UNSUPPORTED_SYNTAX", 3),
        ("a = 1\na /= x[0]\nreturn a", "UNSUPPORTED_SYNTAX", 4),
        ("a = 1\ndel a\nreturn 0", "UNSUPPORTED_SYNTAX", 4),
        ("return 0\na = x[0]\nreturn a", "UNSUPPORTED_SYNTAX", 3),
        ("a = 0\nif x[0]:\n    a = 1\nreturn a", "UNSUPPORTED_SYNTAX", 4),
        ("a = x\nreturn 0", "UNSUPPORTED_SYNTAX", 3),
        ("i = 0\nreturn x[i]", "INVALID_INDEX", 4),
        ("unused = 0*missing\nreturn 0", "UNDEFINED_NAME", 3),
        ("unused = sum(x)\nreturn 0", "UNSUPPORTED_SYNTAX", 3),
        ("pair = x[0]*x[1]\nunused = pair*x[2]\nreturn 0", "HIGHER_ORDER", 4),
    ],
)
def test_invalid_scope_targets_and_unused_expressions_are_rejected(body, code, line):
    result = analyze_source(source(body))
    assert result.status == "rejected"
    assert result.qubo is None and result.circuit is None
    assert result.diagnostics[0].code == code
    assert result.diagnostics[0].line == line


def test_assignment_limit_is_enforced_without_expanding_alias_trees():
    accepted = analyze_source(source("\n".join(["a = 0"] * 64 + ["return a"])))
    assert accepted.status == "supported"
    rejected = analyze_source(source("\n".join(["a = 0"] * 65 + ["return a"])))
    assert rejected.diagnostics[0].code == "SOURCE_LIMIT"


def test_unused_assignment_must_be_finite_on_every_binary_input():
    result = analyze_source(source("unused = 1e308*x[0] + 1e308*x[1]\nreturn 0"))
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "NONFINITE_COEFFICIENT"
    assert result.diagnostics[0].line == 3


def test_malicious_unused_assignment_is_never_executed(tmp_path):
    target = tmp_path / "must-not-exist"
    body = f"unused = __import__('pathlib').Path({str(target)!r}).write_text('executed')\nreturn 0"
    result = analyze_source(source(body))
    assert result.status == "rejected"
    assert not target.exists()
    assert str(target) not in result.model_dump_json()
