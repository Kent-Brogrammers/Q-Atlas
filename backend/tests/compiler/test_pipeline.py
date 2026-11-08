"""Synthetic integration fixtures only: no quantum jobs or measured results."""

from unittest.mock import Mock

import pytest

from app.compiler import pipeline
from app.compiler.analysis import analyze_source
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkResult,
    QAOAConfig,
    QAOAResult,
    SolverResult,
)

SOURCE = "@qatlas.objective(num_bits=3)\ndef cost(x): return 5 - 2*x[0] + x[1]*x[2]"
LOCAL_SOURCE = (
    "@qatlas.objective(num_bits=3)\ndef cost(x):\n"
    "    weight = 2\n    benefit = weight*x[0]\n    penalty = x[1]*x[2]\n"
    "    total = 5 - benefit\n    total = total + penalty\n    return total\n"
)
LOOP_SOURCE = (
    "@qatlas.objective(num_bits=3)\ndef cost(x):\n"
    "    total = 5\n    for i in range(1):\n        total -= 2*x[i]\n"
    "    total += x[1]*x[2]\n    return total\n"
)


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
@pytest.mark.parametrize("source", [SOURCE, LOCAL_SOURCE, LOOP_SOURCE])
def test_source_to_shared_qaoa_pipeline_preserves_contract(
    client, mock_runners, algorithm, expected_gap, source
):
    mock_runners[0].return_value.algorithm = algorithm
    payload = {"source": source, "config": {"seed": 7, "shots": 32, "p": 2}}
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
    assert source not in response.text
    # A stable instance ID depends on the normalized problem, not formatting.
    again = client.post("/api/compiler/benchmark", json={**payload, "source": source + "\n"})
    assert again.json()["problem_id"] == result.problem_id


@pytest.mark.parametrize("source", [SOURCE, LOCAL_SOURCE, LOOP_SOURCE])
def test_analysis_endpoint_returns_real_qubo_without_calling_solvers(client, mock_runners, source):
    response = client.post("/api/compiler/analyze", json={"source": source})
    assert response.status_code == 200
    assert response.json()["status"] == "supported"
    assert response.json()["qubo"]["linear"] == [-2, 0, 0]
    circuit = response.json()["circuit"]
    assert circuit["kind"] == "qaoa_logical_preview"
    assert circuit["executed"] is False and circuit["depth"] is None
    assert circuit["num_qubits"] == 3 and circuit["p"] == 1
    assert circuit["gates"][0] == {"name": "h", "qubits": [0], "angle": None}
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


def test_benchmark_reports_missing_shared_runners_without_mock_data(client, mock_runners):
    mock_runners[0].side_effect = NotImplementedError("unavailable")
    response = client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == 501
    assert response.json()["error"]["code"] == "NOT_IMPLEMENTED"
    assert "Developer 3" in response.json()["error"]["message"]
    assert "quantum" not in response.json()
    mock_runners[1].assert_not_called()


def test_maximization_handoff_preserves_canonical_values_and_nonzero_gap(client, mock_runners):
    source = SOURCE.replace("num_bits=3", 'num_bits=3, sense="maximize"')
    mock_runners[0].return_value.objective = -6
    mock_runners[0].return_value.best_bitstring = "011"
    mock_runners[1].return_value.objective = -5
    mock_runners[1].return_value.best_bitstring = "001"
    response = client.post(
        "/api/compiler/benchmark", json={"source": source, "config": {"shots": 32}}
    )
    assert response.status_code == 200
    result = CompilerBenchmarkResult.model_validate(response.json())
    assert result.metadata.qubo.original_sense == "maximize"
    assert result.metadata.qubo.constant == -5
    assert result.metadata.qubo.linear == [2, 0, 0]
    assert result.metadata.qubo.quadratic[0].coefficient == -1
    assert result.classical.best_bitstring == "011"
    assert result.quantum.best_bitstring == "001"
    assert result.quantum.objective == -5
    assert result.metrics.optimality_gap == 1


@pytest.mark.parametrize("invalid", ["objective", "width", "bits", "shots", "qubits", "optimum"])
def test_invalid_shared_results_never_become_completed_measurements(client, mock_runners, invalid):
    from fastapi.testclient import TestClient

    from app.main import app

    classical, quantum = (runner.return_value for runner in mock_runners)
    if invalid == "objective":
        quantum.objective = 99
    elif invalid == "width":
        quantum.best_bitstring = "1"
    elif invalid == "bits":
        quantum.best_bitstring = "001"  # Same width, wrong assignment for objective 3.
    elif invalid == "shots":
        quantum.metrics.shots = 100
    elif invalid == "qubits":
        quantum.metrics.num_qubits = 2
    else:
        classical.best_bitstring, classical.objective = "000", 5  # False exact optimum.
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post(
            "/api/compiler/benchmark", json={"source": SOURCE, "config": {"shots": 32}}
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "quantum" not in response.json()


def test_invalid_classical_result_stops_before_quantum_handoff(client, mock_runners):
    from fastapi.testclient import TestClient

    from app.main import app

    mock_runners[0].return_value.objective = None
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == 500
    mock_runners[1].assert_not_called()


def test_squared_penalty_analysis_and_mocked_comparison(client, mock_runners):
    source = (
        "@qatlas.objective(num_bits=3)\ndef cost(x):\n"
        "    selected = x[0] + x[1] + x[2]\n"
        "    benefit = x[0] + 2*x[1] + 3*x[2]\n"
        "    return 10*(selected - 1)**2 - benefit\n"
    )
    analysis = client.post("/api/compiler/analyze", json={"source": source})
    assert analysis.status_code == 200
    assert analysis.json()["qubo"]["linear"] == [-11, -12, -13]
    for runner in mock_runners:
        runner.assert_not_called()
    mock_runners[0].return_value.objective = -3
    mock_runners[0].return_value.best_bitstring = "001"
    mock_runners[1].return_value.objective = -2
    mock_runners[1].return_value.best_bitstring = "010"
    response = client.post(
        "/api/compiler/benchmark", json={"source": source, "config": {"shots": 32}}
    )
    assert response.status_code == 200
    result = CompilerBenchmarkResult.model_validate(response.json())
    assert result.metadata.qubo.constant == 10
    assert result.metrics.optimality_gap == 1
    assert result.quantum.best_bitstring == "010"
    assert result.quantum.objective == -2


@pytest.mark.parametrize("runner_index", [0, 1])
def test_large_offset_does_not_hide_an_incorrect_shared_objective(
    client, mock_runners, runner_index
):
    from fastapi.testclient import TestClient

    from app.main import app

    source = SOURCE.replace("5 - 2*x[0]", "1e12 - 2*x[0]")
    for runner in mock_runners:
        runner.return_value.objective = 1e12 - 2
    mock_runners[runner_index].return_value.objective += 1
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post(
            "/api/compiler/benchmark", json={"source": source, "config": {"shots": 32}}
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "quantum" not in response.json()
    if runner_index == 0:
        mock_runners[1].assert_not_called()


@pytest.mark.parametrize("runner_index", [0, 1])
@pytest.mark.parametrize("changed_input", ["qubo", "config"])
def test_shared_runner_mutation_is_isolated_and_rejected(
    client, mock_runners, runner_index, changed_input
):
    from fastapi.testclient import TestClient

    from app.main import app

    result = mock_runners[runner_index].return_value

    def mutate(qubo, config):
        if changed_input == "qubo":
            qubo.linear[2] = (
                1  # The chosen assignment still has cost 3; quality checks alone miss this.
            )
        else:
            config.seed += 1
        return result

    mock_runners[runner_index].side_effect = mutate
    qubo, config = analyze_source(SOURCE).qubo, QAOAConfig(shots=32, seed=7)
    original_qubo, original_config = qubo.model_copy(deep=True), config.model_copy(deep=True)
    with pytest.raises(ValueError, match="changed its input"):
        pipeline.benchmark_qubo(qubo, config)
    assert qubo == original_qubo and config == original_config
    if runner_index == 0:
        mock_runners[1].assert_not_called()

    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post(
            "/api/compiler/benchmark", json={"source": SOURCE, "config": {"shots": 32}}
        )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "quantum" not in response.json()
