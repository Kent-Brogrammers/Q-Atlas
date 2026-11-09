"""Generated Python is inspected as AST/text only, never executed or imported."""

import ast
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.compiler.generation import generate_source
from app.schemas.contracts import QUBO, CompilerGenerateResult

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "compiler"
EXPECTED = json.loads((EXAMPLES / "expected_qubos.json").read_text())
OBJECTIVE = "@qatlas.objective(num_bits=3)\ndef cost(x):\n    return 5 - 2*x[0] + 3*x[0]*x[2]\n"
CIRCUIT = "@qatlas.circuit\ndef old_circuit():\n    raise RuntimeError('old circuit removed')\n"


@pytest.mark.parametrize("filename", EXPECTED)
def test_generated_calls_follow_shared_plan_and_independent_qubo(filename):
    result = generate_source((EXAMPLES / filename).read_text(), p=3)
    assert result.status == "supported", result.diagnostics
    assert result.qubo == QUBO.model_validate(EXPECTED[filename])
    assert result.circuit.p == 3
    artifact = result.artifact
    assert artifact.executed is False and artifact.replaced_function is None
    tree = ast.parse(artifact.source)
    factory = next(node for node in tree.body if getattr(node, "name", None) == artifact.entrypoint)
    assert not factory.decorator_list and not factory.args.args
    assert all(not node.decorator_list for node in tree.body if isinstance(node, ast.FunctionDef))
    operations = [
        node.value
        for node in factory.body
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
    ]
    assert len(operations) == len(result.circuit.gates)
    for call, gate in zip(operations, result.circuit.gates, strict=True):
        assert call.func.value.id == "_qatlas_circuit" and call.func.attr == gate.name
        indices = call.args if gate.angle is None else call.args[1:]
        assert [ast.literal_eval(index) for index in indices] == gate.qubits
        if gate.angle is not None:
            assert_angle(call.args[0], gate.angle)
    phases = [node for node in factory.body if isinstance(node, ast.AugAssign)]
    assert len(phases) == 3
    for statement, phase in zip(phases, result.circuit.global_phase, strict=True):
        assert statement.target.value.id == "_qatlas_circuit"
        assert statement.target.attr == "global_phase" and isinstance(statement.op, ast.Add)
        assert_angle(statement.value, phase)
    bindings = next(
        node.value
        for node in factory.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
    )
    assert [ast.literal_eval(key) for key in bindings.keys] == result.circuit.parameters
    assert [call.args[0].value for call in bindings.values] == result.circuit.parameters


def assert_angle(expression, angle):
    assert isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Mult)
    assert ast.literal_eval(expression.left) == angle.coefficient
    assert expression.right.value.id == "_qatlas_parameters"
    assert ast.literal_eval(expression.right.slice) == angle.parameter


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_replacement_preserves_surrounding_python_and_line_endings(newline, tmp_path):
    sentinel = tmp_path / "must-not-exist"
    before = (
        "#!/usr/bin/env python3\n# coding: utf-8\n"
        "from pathlib import Path\n"
        f"Path({str(sentinel)!r}).write_text('must not execute')\n"
        "label = 'π \u2028 and more Unicode'\n\n"
    )
    between = "\n# Ordinary helper stays exactly as written.\ndef helper():\n    return 'kept'\n\n"
    after = "\nif __name__ == '__main__':\n    print(old_circuit())\n"
    source = (before + OBJECTIVE + between + CIRCUIT + after).replace("\n", newline)
    result = generate_source(source, p=2)
    assert result.status == "supported", result.diagnostics
    output = result.artifact.source
    assert output.startswith(before.replace("\n", newline))
    assert between.replace("\n", newline) in output
    assert output.endswith(after.replace("\n", newline))
    assert "old circuit removed" not in output and "@qatlas" not in output
    assert "return 5 - 2*x[0] + 3*x[0]*x[2]" in output
    assert result.artifact.entrypoint == result.artifact.replaced_function == "old_circuit"
    assert not sentinel.exists()
    assert output.count(newline) > source.count(newline)
    if newline != "\n":
        assert "\n" not in output.replace(newline, "")


@pytest.mark.parametrize(
    "marker", ["@qatlas.objective(\n    num_bits=3,\n)", "@(\n    qatlas.objective(num_bits=3)\n)"]
)
def test_multiline_marker_and_original_diagnostic_locations_are_preserved(marker):
    source = f"# header\nimport math\n\n{marker}\ndef cost(x):\n    return run(x)\n"
    result = generate_source(source)
    assert result.status == "rejected" and result.artifact is None
    assert result.diagnostics[0].line == 8
    accepted = generate_source(source.replace("run(x)", "x[0]"))
    assert accepted.status == "supported"
    assert accepted.artifact.source.startswith("# header\nimport math\n\ndef cost(x):")


def test_parenthesized_circuit_marker_before_objective_and_missing_final_newline():
    source = CIRCUIT.replace("@qatlas.circuit", "@(\n    qatlas.circuit\n)") + OBJECTIVE.rstrip()
    result = generate_source(source)
    assert result.status == "supported", result.diagnostics
    assert result.artifact.source.startswith("def old_circuit():")
    assert result.artifact.source.endswith("return 5 - 2*x[0] + 3*x[0]*x[2]")
    assert result.artifact.replaced_function == "old_circuit"


def test_default_builder_avoids_existing_function_variable_and_import_names():
    source = (
        "from existing_module import helper as build_qatlas_circuit\n"
        "build_qatlas_circuit_2 = 'preserved'\n"
        "def build_qatlas_circuit_3():\n    return 3\n\n" + OBJECTIVE
    )
    result = generate_source(source)
    assert result.status == "supported"
    assert result.artifact.entrypoint == "build_qatlas_circuit_4"
    assert source.split("@qatlas.objective")[0] in result.artifact.source


@pytest.mark.parametrize(
    ("source", "code"),
    [
        ("print('no objective')", "INVALID_MARKER"),
        (OBJECTIVE + OBJECTIVE, "INVALID_MARKER"),
        (OBJECTIVE + CIRCUIT + CIRCUIT, "INVALID_MARKER"),
        (
            OBJECTIVE + CIRCUIT.replace("old_circuit()", "old_circuit(gamma)"),
            "INVALID_CIRCUIT_MARKER",
        ),
        (
            OBJECTIVE + CIRCUIT.replace("@qatlas.circuit", "@qatlas.circuit()"),
            "INVALID_CIRCUIT_MARKER",
        ),
        (
            OBJECTIVE + CIRCUIT.replace("@qatlas.circuit", "@other\n@qatlas.circuit"),
            "INVALID_CIRCUIT_MARKER",
        ),
        (
            "class Wrapped:\n" + "\n".join("    " + line for line in OBJECTIVE.splitlines()),
            "INVALID_MARKER",
        ),
        (OBJECTIVE.replace("def cost", "async def cost"), "INVALID_MARKER"),
        (OBJECTIVE.replace("num_bits=3", "num_bits=(a\n@b)"), "INVALID_MARKER"),
        (OBJECTIVE.replace("x[0]", "eval('1')"), "UNSUPPORTED_SYNTAX"),
        ("#" * 20_001, "SOURCE_LIMIT"),
        ("def broken(", "SYNTAX_ERROR"),
    ],
)
def test_ambiguous_or_unsupported_input_has_no_download(source, code):
    result = generate_source(source)
    assert result.status == "rejected", result
    assert result.artifact is result.qubo is result.circuit is None
    assert result.diagnostics[0].code == code


def test_generate_http_does_not_touch_solver_boundaries(client):
    with (
        patch("app.quantum.qaoa.run_qaoa", side_effect=AssertionError("must not run")) as quantum,
        patch(
            "app.experiments.optimization.solvers.run_classical",
            side_effect=AssertionError("must not run"),
        ) as classical,
    ):
        response = client.post(
            "/api/compiler/generate", json={"source": OBJECTIVE + CIRCUIT, "p": 8}
        )
    assert response.status_code == 200
    result = CompilerGenerateResult.model_validate(response.json())
    assert result.circuit.p == 8 and result.artifact.executed is False
    quantum.assert_not_called()
    classical.assert_not_called()
    rejected = client.post("/api/compiler/generate", json={"source": "print('opaque only')"})
    assert rejected.status_code == 200 and rejected.json()["artifact"] is None


def test_generate_request_validation_and_response_invariants(client):
    for payload in [
        {"source": OBJECTIVE, "p": 0},
        {"source": OBJECTIVE, "p": 9},
        {"source": "x" * 20_001},
    ]:
        response = client.post("/api/compiler/generate", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    result = generate_source(OBJECTIVE).model_dump()
    result["artifact"] = None
    with pytest.raises(ValidationError):
        CompilerGenerateResult.model_validate(result)


def test_documented_script_example_has_expected_objective_and_replaces_old_gates():
    result = generate_source((EXAMPLES / "script_replacement.py").read_text())
    assert result.status == "supported", result.diagnostics
    assert result.qubo == QUBO.model_validate(EXPECTED["exactly_one.py"])
    assert result.artifact.entrypoint == "build_circuit"
    assert "old_circuit.x(0)" not in result.artifact.source
