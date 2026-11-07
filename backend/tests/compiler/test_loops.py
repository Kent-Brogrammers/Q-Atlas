"""Compiler-only loop/accumulation tests; no submitted code or solvers are executed."""

import itertools
from textwrap import indent

import pytest

from app.compiler import analysis, lowering
from app.quantum.qubo import evaluate_qubo


def source(body, num_bits=4, sense="minimize", parameter="x"):
    return (
        f'@qatlas.objective(num_bits={num_bits}, sense="{sense}")\n'
        f"def cost({parameter}):\n" + indent(body, "    ") + "\n"
    )


@pytest.mark.parametrize("num_bits", range(1, 7))
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_weighted_loop_and_neighbor_pairs_match_every_binary_assignment(num_bits, sense):
    body = f"total = 5\nfor i in range({num_bits}):\n    total -= (i+1)*bits[i]\n"
    if num_bits > 1:
        body += f"for i in range({num_bits - 1}):\n    total += 2*bits[i]*bits[i+1]\n"
    result = analysis.analyze_source(source(body + "return total", num_bits, sense, "bits"))
    assert result.status == "supported", result.diagnostics
    sign = -1 if sense == "maximize" else 1
    for bits in itertools.product((0, 1), repeat=num_bits):
        expected = 5 - sum((i + 1) * bit for i, bit in enumerate(bits))
        expected += 2 * sum(bits[i] * bits[i + 1] for i in range(num_bits - 1))
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == sign * expected


def test_nested_loops_and_last_index_values_follow_source_semantics():
    result = analysis.analyze_source(
        source(
            "total = 0\nfor i in range(3):\n    for j in range(3, 6):\n"
            "        total += x[i]*x[j]\nreturn total + i + j",
            num_bits=6,
        )
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.constant == 7
    for bits in itertools.product((0, 1), repeat=6):
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == 7 + sum(bits[:3]) * sum(
            bits[3:]
        )


def test_reverse_step_offsets_and_augmented_multiplication():
    result = analysis.analyze_source(
        source(
            "total = 1\nfor i in range(5, -1, -2):\n    total += x[i]*x[i-1]\n"
            "saved = total\ntotal *= 2\nreturn total + saved + i",
            num_bits=6,
        )
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.constant == 4
    assert [(t.i, t.j, t.coefficient) for t in result.qubo.quadratic] == [
        (0, 1, 3),
        (2, 3, 3),
        (4, 5, 3),
    ]


@pytest.mark.parametrize(
    "iterator",
    [
        "range(0)",
        "range(2, 2)",
        "range(3, 0)",
        "range(0, 3, 0)",
        "range(65)",
        "range(-64, 64)",
        "range(True)",
        "range(3.0)",
        "range(1+2)",
        "range(limit)",
        "range(stop=3)",
        "range(*[0, 3])",
        "other.range(3)",
        "x",
        "range(0, 1, 2, 3)",
        "range(__import__('os'))",
    ],
)
def test_invalid_or_dynamic_ranges_are_rejected(iterator):
    result = analysis.analyze_source(
        source(f"limit = 3\ntotal = 0\nfor i in {iterator}:\n    total += 1\nreturn total")
    )
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "INVALID_LOOP"
    assert result.qubo is None and result.circuit is None


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ("total = 0\nfor x in range(3):\n    total += 1\nreturn total", "INVALID_LOOP"),
        ("total = 0\ni = 1\nfor i in range(3):\n    total += 1\nreturn total", "INVALID_LOOP"),
        ("total = 0\nfor i in range(3):\n    i = 1\nreturn total", "INVALID_LOOP"),
        (
            "total = 0\nfor i in range(3):\n    for i in range(3):\n"
            "        total += 1\nreturn total",
            "INVALID_LOOP",
        ),
        ("range = 3\ntotal = 0\nfor i in range(3):\n    total += 1\nreturn total", "INVALID_LOOP"),
        ("total = 0\nfor i in range(3):\n    total += 1\nrange = 3\nreturn total", "INVALID_LOOP"),
        (
            "total = 0\nfor i in range(3):\n    total += 1\nelse:\n    total += 1\nreturn total",
            "INVALID_LOOP",
        ),
        (
            "total = 0\nfor i in range(2):\n    for j in range(2):\n"
            "        for k in range(2):\n            total += 1\nreturn total",
            "INVALID_LOOP",
        ),
        ("total = 0\nfor i in range(4):\n    total += x[i+1]\nreturn total", "INVALID_INDEX"),
        ("total = 0\nfor i in range(3):\n    total += x[i+0.5]\nreturn total", "INVALID_INDEX"),
        ("total = 0\nfor i in range(3):\n    total += sum(x)\nreturn total", "UNSUPPORTED_SYNTAX"),
        ("total = 0\nfor i in range(3):\n    break\nreturn total", "UNSUPPORTED_SYNTAX"),
        ("total = 0\nwhile total < 3:\n    total += 1\nreturn total", "UNSUPPORTED_SYNTAX"),
        ("total += x[0]\nreturn total", "UNDEFINED_NAME"),
        ("x[0] += 1\nreturn x[0]", "INVALID_ASSIGNMENT"),
        (
            "total = 0\nfor i in range(1):\n    total += x[i]*x[i+1]*x[i+2]\nreturn total",
            "HIGHER_ORDER",
        ),
    ],
)
def test_loop_scope_control_flow_and_expressions_stay_allowlisted(body, code):
    result = analysis.analyze_source(source(body))
    assert result.status == "rejected"
    assert result.diagnostics[0].code == code


def test_empty_loop_with_forbidden_body_is_rejected_instead_of_skipping_validation():
    result = analysis.analyze_source(
        source("for i in range(0):\n    unused = dangerous()\nreturn 0")
    )
    assert result.status == "rejected"


def test_malicious_loop_body_is_never_executed(tmp_path):
    target = tmp_path / "must-not-exist"
    body = (
        "for i in range(3):\n"
        f"    unused = 0*__import__('pathlib').Path({str(target)!r}).write_text('executed')\n"
        "return 0"
    )
    result = analysis.analyze_source(source(body))
    assert result.status == "rejected"
    assert not target.exists()
    assert str(target) not in result.model_dump_json()


def test_expansion_budget_and_maximum_range_size():
    accepted = analysis.analyze_source(
        source("total = 0\nfor i in range(64):\n    total += 1\nreturn total")
    )
    assert accepted.status == "supported"
    assert accepted.qubo.constant == 64
    rejected = analysis.analyze_source(
        source(
            "total = 0\nfor i in range(64):\n    for j in range(64):\n"
            "        total += 1\nreturn total"
        )
    )
    assert rejected.diagnostics[0].code == "SOURCE_LIMIT"


def test_expanded_node_budget_is_enforced(monkeypatch):
    monkeypatch.setattr(lowering, "MAX_EXPANDED_NODES", 10)
    result = analysis.analyze_source(
        source("total = 0\nfor i in range(3):\n    total += x[i]\nreturn total")
    )
    assert result.diagnostics[0].code == "SOURCE_LIMIT"


def test_independent_source_interpreter_catches_a_broken_lowering(monkeypatch):
    original = analysis.lower_body

    def broken(statements, expression, parameter):
        assignments, result = original(statements, expression, parameter)
        # Drop the final update. Verification must still interpret every source iteration.
        return assignments[:-1], result

    monkeypatch.setattr(analysis, "lower_body", broken)
    result = analysis.analyze_source(
        source("total = 0\nfor i in range(3):\n    total += x[i]\nreturn total")
    )
    assert result.status == "rejected"
    assert result.diagnostics[0].code == "VERIFICATION_FAILED"
