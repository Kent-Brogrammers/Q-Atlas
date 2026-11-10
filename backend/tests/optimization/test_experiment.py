"""Typed optimization handoff, API errors, and real Max-Cut endpoint execution."""

import multiprocessing as mp
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.experiments.optimization import experiment
from app.main import app
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import (
    CompilerBenchmarkResult,
    ErrorResponse,
    OptimizationRequest,
    OptimizationResult,
    QAOAConfig,
)


@pytest.fixture
def square():
    return {
        "kind": "graph",
        "num_vertices": 4,
        "edges": [
            {"i": 0, "j": 1, "coefficient": 1},
            {"i": 1, "j": 2, "coefficient": 1},
            {"i": 2, "j": 3, "coefficient": 1},
            {"i": 0, "j": 3, "coefficient": 1},
        ],
    }


@pytest.fixture
def comparison(monkeypatch):
    """Synthetic shared-boundary record for transport tests, with no Aer execution."""
    from app.experiments.optimization.solvers import run_classical
    from app.schemas.contracts import OptimizationMetadata, OptimizationMetrics, QAOAResult

    def compare(qubo, config):
        classical = run_classical(qubo, config)
        metrics = OptimizationMetrics(
            num_qubits=qubo.num_variables,
            shots=config.shots,
            circuit_depth=1,
            optimizer_evaluations=1,
            optimality_gap=0,
        )
        return CompilerBenchmarkResult(
            problem_id="synthetic-compiler-fixture",
            backend=config.backend,
            classical=classical,
            quantum=QAOAResult(
                objective=classical.objective,
                best_bitstring=classical.best_bitstring,
                elapsed_ms=0,
                timing=classical.timing,
                metrics=metrics,
            ),
            metrics=metrics,
            metadata=OptimizationMetadata(
                seed=config.seed,
                timing_scope="end_to_end",
                simulation_method="statevector",
                qubo=qubo,
                config=config,
            ),
        )

    mock = Mock(side_effect=compare)
    monkeypatch.setattr(experiment, "benchmark_qubo", mock)
    return mock


def test_graph_and_equivalent_qubo_share_one_comparison_path(square, comparison):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    request = OptimizationRequest(problem=square, config=QAOAConfig(seed=9, shots=32))
    before = request.model_dump()
    result = experiment.run_optimization(request)
    qubo, config = comparison.call_args.args
    assert result.experiment == "optimization"
    assert result.problem_id.startswith("optimization-")
    assert result.metadata.qubo == qubo
    assert result.metadata.config == config == request.config
    assert qubo.original_sense == "maximize"
    assert result.classical.objective == result.quantum.objective == -4
    assert request.model_dump() == before
    direct = OptimizationRequest(problem={"kind": "qubo", "qubo": qubo}, config=config)
    assert experiment.run_optimization(direct).problem_id == result.problem_id
    assert comparison.call_count == 2


def test_problem_identity_is_stable_across_edge_order_and_solver_settings(square, comparison):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    first = experiment.run_optimization(OptimizationRequest(problem=square))
    square["edges"].reverse()
    other = experiment.run_optimization(
        OptimizationRequest(problem=square, config=QAOAConfig(seed=11, p=2, shots=1))
    )
    assert first.problem_id == other.problem_id
    square["edges"][0]["coefficient"] = 2
    changed = experiment.run_optimization(OptimizationRequest(problem=square))
    assert changed.problem_id != first.problem_id


def test_api_returns_the_existing_result_contract_for_graphs(client, square, comparison):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    response = client.post("/api/optimization/run", json={"problem": square})
    assert response.status_code == 200
    result = OptimizationResult.model_validate(response.json())
    assert result.status == "completed"
    assert result.classical.objective == result.quantum.objective == -4
    assert result.metadata.simulated is True
    assert result.metadata.repetitions == 1


def test_api_accepts_a_qubo_without_graph_conversion(client, qubo_payload, comparison, monkeypatch):
    convert = Mock(side_effect=AssertionError("QUBO input must not use graph conversion"))
    monkeypatch.setattr(experiment, "maxcut_to_qubo", convert)
    response = client.post(
        "/api/optimization/run", json={"problem": {"kind": "qubo", "qubo": qubo_payload}}
    )
    assert response.status_code == 200
    result = OptimizationResult.model_validate(response.json())
    assert result.metadata.qubo.model_dump() == comparison.call_args.args[0].model_dump()
    convert.assert_not_called()


@pytest.mark.parametrize(
    "failure,status,code",
    [
        (TimeoutError("private failure detail"), 504, "TIMEOUT"),
        (ImportError("private failure detail"), 503, "HTTP_ERROR"),
        (RuntimeError("private failure detail"), 500, "INTERNAL_ERROR"),
        (ValueError("private failure detail"), 500, "INTERNAL_ERROR"),
    ],
)
def test_solver_failures_have_sanitized_errors(monkeypatch, qubo_payload, failure, status, code):
    monkeypatch.setattr(experiment, "benchmark_qubo", Mock(side_effect=failure))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/optimization/run", json={"problem": {"kind": "qubo", "qubo": qubo_payload}}
        )
    assert response.status_code == status
    assert ErrorResponse.model_validate(response.json()).error.code == code
    assert "private failure detail" not in response.text
    assert set(response.json()) == {"status", "error"}


def test_overflow_is_rejected_before_running_solvers(client, comparison):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    response = client.post(
        "/api/optimization/run",
        json={
            "problem": {
                "kind": "graph",
                "num_vertices": 2,
                "edges": [{"i": 0, "j": 1, "coefficient": 1e308}],
            }
        },
    )
    assert response.status_code == 422
    assert ErrorResponse.model_validate(response.json()).error.code == "VALIDATION_ERROR"
    assert "Rescale" in response.json()["error"]["message"]
    comparison.assert_not_called()


def test_invalid_graph_is_rejected_before_running_solvers(client, comparison):
    response = client.post(
        "/api/optimization/run",
        json={
            "problem": {
                "kind": "graph",
                "num_vertices": 2,
                "edges": [{"i": 1, "j": 0, "coefficient": 1}],
            }
        },
    )
    assert response.status_code == 422
    comparison.assert_not_called()


def test_graph_dependency_failure_is_explicit(client, square, monkeypatch):
    monkeypatch.setattr(experiment, "maxcut_to_qubo", Mock(side_effect=ImportError("networkx")))
    response = client.post("/api/optimization/run", json={"problem": square})
    assert response.status_code == 503
    assert ErrorResponse.model_validate(response.json()).error.code == "HTTP_ERROR"


def test_real_endpoint_compares_maxcut_solvers_and_records_provenance(client, square):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    response = client.post(
        "/api/optimization/run",
        json={"problem": square, "config": {"shots": 256, "max_iterations": 60, "seed": 42}},
    )
    assert response.status_code == 200
    result = OptimizationResult.model_validate(response.json())
    assert result.classical.objective == -4
    assert result.quantum.objective == evaluate_qubo(
        result.metadata.qubo, result.quantum.best_bitstring
    )
    assert result.metrics.optimality_gap == result.quantum.objective - result.classical.objective
    assert result.metrics.approximation_ratio is None
    assert result.metrics.num_qubits == 4
    assert result.metrics.shots == 256
    assert result.metrics.circuit_depth > 0
    assert result.metadata.seed == 42
    assert result.metadata.config.max_iterations == 60
    assert result.metadata.qubo.original_sense == "maximize"
    assert result.metadata.simulated is True
    assert result.metadata.simulation_method == "statevector"
    assert result.metadata.timing_scope == "end_to_end"
    assert "qiskit" in result.metadata.versions
    assert "networkx" in result.metadata.versions
    assert result.classical.elapsed_ms > 0
    assert result.quantum.elapsed_ms > 0


def test_real_timeout_does_not_leave_a_worker(client, square):
    pytest.importorskip("networkx", reason="Install the optional quantum extra")
    before = {process.pid for process in mp.active_children()}
    response = client.post(
        "/api/optimization/run",
        json={"problem": square, "config": {"timeout_seconds": 1e-9}},
    )
    assert response.status_code == 504
    assert ErrorResponse.model_validate(response.json()).error.code == "TIMEOUT"
    assert {process.pid for process in mp.active_children()} <= before


def test_openapi_documents_operational_errors(client):
    responses = client.get("/openapi.json").json()["paths"]["/api/optimization/run"]["post"][
        "responses"
    ]
    assert {"200", "422", "503", "504"} <= responses.keys()
    for status in ("422", "503", "504"):
        assert responses[status]["content"]["application/json"]["schema"]["$ref"].endswith(
            "/ErrorResponse"
        )
