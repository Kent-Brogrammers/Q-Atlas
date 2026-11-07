"""Synthetic integration fixtures only: no quantum jobs or measured results."""

from unittest.mock import Mock

import pytest

from app.compiler import pipeline
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkResult,
    QAOAResult,
    SolverResult,
)

SOURCE = "@qatlas.objective(num_bits=3)\ndef cost(x): return 5 - 2*x[0] + x[1]*x[2]"


@pytest.fixture
def mock_runners(monkeypatch):
    # Deliberately synthetic timings; these values must never be served as live data.
    classical = Mock(
        return_value=SolverResult(
            algorithm="brute_force",
            elapsed_ms=1,
            objective=3,
            best_bitstring="100",
            timing=dict(
                includes_queue=False,
                includes_transpilation=False,
                includes_optimizer=False,
                includes_sampling=False,
            ),
        )
    )
    quantum = Mock(
        return_value=QAOAResult(
            elapsed_ms=2,
            objective=3,
            best_bitstring="100",
            metrics=dict(num_qubits=3, circuit_depth=8, shots=32, optimizer_evaluations=4),
            timing=dict(
                includes_queue=False,
                includes_transpilation=True,
                includes_optimizer=True,
                includes_sampling=True,
            ),
        )
    )
    monkeypatch.setattr(pipeline.solvers, "run_classical", classical)
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", quantum)
    return classical, quantum


@pytest.mark.parametrize(("algorithm", "expected_gap"), [("brute_force", 0), ("heuristic", None)])
def test_source_to_shared_qaoa_pipeline_preserves_contract(
    client, mock_runners, algorithm, expected_gap
):
    mock_runners[0].return_value.algorithm = algorithm
    payload = {"source": SOURCE, "config": {"seed": 7, "shots": 32, "p": 2}}
    response = client.post("/api/compiler/benchmark", json=payload)
    assert response.status_code == 200
    result = CompilerBenchmarkResult.model_validate(response.json())
    classical, quantum = mock_runners
    classical.assert_called_once()
    quantum.assert_called_once_with(*classical.call_args.args)
    qubo, config = quantum.call_args.args
    assert isinstance(qubo, QUBO)
    assert qubo.linear == [-2, 0, 0] and qubo.constant == 5
    assert config.seed == 7 and config.shots == 32 and config.p == 2
    assert result.metadata.qubo == qubo and result.metadata.config == config
    assert result.quantum.best_bitstring == "100"
    assert result.quantum.objective == result.classical.objective == 3
    assert result.metrics.optimality_gap == expected_gap
    assert result.metrics.approximation_ratio is None
    assert result.metadata.simulated and result.metadata.repetitions == 1
    assert result.metadata.versions["python"]
    assert SOURCE not in response.text
    # A stable instance ID depends on the normalized problem, not formatting.
    again = client.post("/api/compiler/benchmark", json={**payload, "source": SOURCE + "\n"})
    assert again.json()["problem_id"] == result.problem_id


def test_analysis_endpoint_returns_real_qubo_without_calling_solvers(client, mock_runners):
    response = client.post("/api/compiler/analyze", json={"source": SOURCE})
    assert response.status_code == 200
    assert response.json()["status"] == "supported"
    assert response.json()["qubo"]["linear"] == [-2, 0, 0]
    for runner in mock_runners:
        runner.assert_not_called()


def test_benchmark_revalidates_source_before_calling_solvers(client, mock_runners):
    payload = {"source": SOURCE.replace("5 - 2*x[0] + x[1]*x[2]", "__import__('os').system('id')")}
    response = client.post("/api/compiler/benchmark", json=payload)
    assert response.status_code == 422
    assert response.json()["error"]["diagnostics"][0]["code"] == "UNSUPPORTED_SYNTAX"
    for runner in mock_runners:
        runner.assert_not_called()


@pytest.mark.parametrize(
    ("failure", "status", "code"),
    [
        (NotImplementedError("private details"), 501, "NOT_IMPLEMENTED"),
        (TimeoutError("private details"), 504, "TIMEOUT"),
        (RuntimeError("private details"), 500, "INTERNAL_ERROR"),
    ],
)
def test_shared_runner_errors_are_sanitized(client, mock_runners, failure, status, code):
    from fastapi.testclient import TestClient

    from app.main import app

    mock_runners[1].side_effect = failure
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "private details" not in response.text


def test_live_benchmark_reports_missing_shared_runners_without_mock_data(client):
    response = client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"
    assert "Developer 3" in response.json()["error"]["message"]
    assert "quantum" not in response.json()
