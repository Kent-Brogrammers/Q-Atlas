import pytest
from pydantic import ValidationError

from app.compiler.pipeline import prepare_benchmark
from app.schemas.contracts import CompilerAnalyzeResult, CompilerBenchmarkPlan, QAOAConfig


def test_supported_analysis_requires_qubo():
    with pytest.raises(ValidationError):
        CompilerAnalyzeResult(status="supported", diagnostics=[])


def test_rejected_analysis_has_structured_source_location():
    result = CompilerAnalyzeResult.model_validate(
        {
            "status": "rejected",
            "diagnostics": [
                {
                    "code": "UNSUPPORTED_SYNTAX",
                    "message": "Calls are unsupported",
                    "severity": "error",
                    "line": 3,
                    "column": 5,
                }
            ],
        }
    )
    assert result.qubo is None
    assert result.diagnostics[0].line == 3


@pytest.mark.parametrize("invalid", ["script_execution", "quantum_execution", "layers", "width"])
def test_comparison_plan_rejects_execution_or_inconsistent_circuit(invalid):
    data = prepare_benchmark(
        "@qatlas.objective(num_bits=3)\ndef cost(x): return x[0]", QAOAConfig()
    ).model_dump()
    if invalid in ("script_execution", "quantum_execution"):
        data[invalid + "_enabled"] = True
    elif invalid == "layers":
        data["config"]["p"] = 2
    else:
        data["qubo"]["num_variables"] = 4
        data["qubo"]["linear"].append(0)
    with pytest.raises(ValidationError):
        CompilerBenchmarkPlan.model_validate(data)
