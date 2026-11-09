"""Full-program fixtures and generated snapshots are parsed as text only."""

import ast
import json
from pathlib import Path

import pytest

from app.compiler.generation import generate_source
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO

PROGRAMS = Path(__file__).resolve().parents[3] / "examples" / "compiler" / "programs"
EXPECTED = json.loads((PROGRAMS / "expected.json").read_text())


@pytest.mark.parametrize("filename", EXPECTED)
def test_documented_program_outcomes_and_generated_snapshot(filename):
    expected = EXPECTED[filename]
    result = generate_source((PROGRAMS / filename).read_text())
    assert result.status == expected["status"], result.diagnostics
    if result.status == "rejected":
        assert result.artifact is result.qubo is None
        assert result.diagnostics[0].code == expected["diagnostic"]
        return
    assert result.qubo == QUBO.model_validate(expected["qubo"])
    optimum = expected["known_optimum"]
    assert evaluate_qubo(result.qubo, optimum["assignment"]) == optimum["canonical_objective"]
    assert result.artifact.entrypoint == expected["entrypoint"]
    snapshot = (PROGRAMS / expected["snapshot"]).read_text()
    assert ast.dump(ast.parse(snapshot)) == ast.dump(ast.parse(result.artifact.source))
    assert result.circuit.executed is result.artifact.executed is False
