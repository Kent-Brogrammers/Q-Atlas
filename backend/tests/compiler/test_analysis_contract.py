import pytest
from pydantic import ValidationError

from app.schemas.contracts import CompilerAnalyzeResult


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
