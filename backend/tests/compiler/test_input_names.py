"""Source names are independent of the canonical index/bitstring contract."""

import itertools
from textwrap import indent
from unittest.mock import patch

import pytest

from app.compiler.analysis import analyze_source
from app.compiler.generation import generate_source
from app.compiler.pipeline import prepare_benchmark
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QAOAConfig


@pytest.mark.parametrize("name", ["assess_plan", "energy", "_收益"])
def test_objective_and_vector_parameter_names_are_arbitrary(name):
    result = analyze_source(
        f"@qatlas.objective(num_bits=3)\ndef {name}(decisions):\n"
        "    first_choice = decisions[0]\n"
        "    return 7 - 2*first_choice + 3*decisions[1]*decisions[2]\n"
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.constant == 7 and result.qubo.linear == [-2, 0, 0]
    assert result.qubo.quadratic[0].coefficient == 3
    assert "decisions[i]" in result.diagnostics[1].message


@pytest.mark.parametrize("num_bits", range(1, 7))
@pytest.mark.parametrize("sense", ["minimize", "maximize"])
def test_named_scalar_parameters_preserve_declared_order_and_all_objective_values(num_bits, sense):
    names = [f"pick_{i}" for i in range(num_bits)]
    expression = " + ".join(f"{i + 1}*{name}" for i, name in enumerate(names))
    expression = f"5 - ({expression}) + 2*{names[0]}*{names[-1]}"
    source = (
        f'@qatlas.objective(num_bits={num_bits}, sense="{sense}")\n'
        f"def assess_plan({', '.join(names)}):\n    return {expression}\n"
    )
    result = analyze_source(source)
    assert result.status == "supported", result.diagnostics
    sign = -1 if sense == "maximize" else 1
    for bits in itertools.product((0, 1), repeat=num_bits):
        expected = sign * (
            5 - sum((i + 1) * bit for i, bit in enumerate(bits)) + 2 * bits[0] * bits[-1]
        )
        assert evaluate_qubo(result.qubo, "".join(map(str, bits))) == expected
    assert "pick_0 -> bit 0" in result.diagnostics[1].message


def test_named_inputs_work_with_local_weights_and_bounded_loops():
    result = analyze_source(
        "@qatlas.objective(num_bits=3)\ndef energy(red, green, blue):\n"
        "    weights = (2, -3, 4)\n    penalty = 0\n"
        "    for index in range(2):\n        penalty += weights[index]*red*blue\n"
        "    return penalty + green**2\n"
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.linear == [0, 1, 0]
    assert result.qubo.quadratic[0].coefficient == -1


@pytest.mark.parametrize(
    ("parameters", "body", "code"),
    [
        ("a, b", "return a + b", "INVALID_SIGNATURE"),
        ("a, a, c", "return a + c", "INVALID_SIGNATURE"),
        ("a, b, c", "b = 1\nreturn a + b + c", "INVALID_ASSIGNMENT"),
        ("a, b, c", "for c in range(2):\n    value = c\nreturn a", "INVALID_LOOP"),
        ("a, b, c", "return a[0]", "INVALID_INDEX"),
        ("a, b, c", "return missing + a", "UNDEFINED_NAME"),
        ("range, b, c", "for index in range(2):\n    value = b\nreturn c", "INVALID_LOOP"),
        ("a, b, c", "return a*b*c", "HIGHER_ORDER"),
        ("a, b=1, c=0", "return a+b+c", "UNSUPPORTED_SYNTAX"),
    ],
)
def test_invalid_named_inputs_are_rejected(parameters, body, code):
    result = analyze_source(
        f"@qatlas.objective(num_bits=3)\ndef assess_plan({parameters}):\n" + indent(body, "    ")
    )
    assert result.status == "rejected"
    assert result.diagnostics[0].code == code


def test_single_bit_cannot_mix_scalar_and_vector_usage():
    result = analyze_source(
        "@qatlas.objective(num_bits=1)\ndef energy(chosen): return chosen + chosen[0]"
    )
    assert result.status == "rejected"


@pytest.mark.parametrize("marker", ["@qatlas.objective", "@qatlas.objective()"])
def test_one_marker_infers_named_inputs_without_quantum_configuration(marker):
    result = analyze_source(
        marker + "\ndef assess_plan(take_z, take_a, take_m):\n"
        "    return 7 - 2*take_z + 3*take_a*take_m\n"
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.num_variables == 3 and result.qubo.linear == [-2, 0, 0]


def test_inferred_width_uses_lowered_vector_indices_and_preserves_unused_positions():
    result = analyze_source(
        '@qatlas.objective(sense="maximize")\ndef reward(choices):\n'
        '    """An ordinary objective docstring."""\n'
        "    total = 0\n    for item in range(2, 6):\n        total += choices[item]\n"
        "    return total\n"
    )
    assert result.status == "supported", result.diagnostics
    assert result.qubo.num_variables == 6
    assert result.qubo.linear == [0, 0, -1, -1, -1, -1]


@pytest.mark.parametrize(
    "source",
    [
        "@qatlas.objective\ndef score(choices):\n    index = 0\n    return choices[index]",
        "@qatlas.objective\ndef score(choices): return choices[6]",
        "@qatlas.objective\ndef score(choices): return choices[-1]",
        "@qatlas.objective\ndef score(a,b,c,d,e,f,g): return a",
    ],
)
def test_inference_keeps_static_index_and_width_limits(source):
    assert analyze_source(source).status == "rejected"


def test_named_source_flows_through_generation_and_planning_without_execution(tmp_path):
    sentinel = tmp_path / "must-not-exist"
    source = (
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('not executed')\n"
        "@qatlas.objective(num_bits=3)\ndef score(take_z, take_a, take_m):\n"
        "    return 7 - 2*take_z + 3*take_a*take_m\n"
        "@qatlas.circuit\ndef compose_plan():\n    raise RuntimeError('removed')\n"
    )
    with (
        patch("app.quantum.qaoa.run_qaoa") as quantum,
        patch("app.experiments.optimization.solvers.run_classical") as classical,
    ):
        generated = generate_source(source)
        plan = prepare_benchmark(source, QAOAConfig())
    assert generated.status == "supported", generated.diagnostics
    assert "def score(take_z, take_a, take_m):" in generated.artifact.source
    assert "return 7 - 2*take_z + 3*take_a*take_m" in generated.artifact.source
    assert generated.artifact.entrypoint == plan.entrypoint == "compose_plan"
    assert plan.qubo.linear == [-2, 0, 0]
    quantum.assert_not_called()
    classical.assert_not_called()
    assert not sentinel.exists()
