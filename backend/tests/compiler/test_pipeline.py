"""Synthetic integration fixtures only: no quantum jobs or measured results."""

import hashlib
from unittest.mock import Mock

import pytest

from app.compiler import pipeline
from app.compiler.analysis import analyze_source
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkPlan,
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
    # Opt in only while both execution boundaries are replaced by synthetic fixtures.
    monkeypatch.setenv("QATLAS_ENABLE_COMPILER_AER", "1")
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
@pytest.mark.parametrize("runner_index", [0, 1])
def test_shared_runner_errors_are_sanitized(
    client, mock_runners, failure, status, code, runner_index
):
    from fastapi.testclient import TestClient

    from app.main import app

    mock_runners[runner_index].side_effect = failure
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "private details" not in response.text
    if runner_index == 0:
        mock_runners[1].assert_not_called()


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


@pytest.mark.parametrize("runner_index", [0, 1])
def test_mutation_then_timeout_preserves_original_inputs_and_structured_failure(
    client, mock_runners, runner_index
):
    def mutate_then_timeout(qubo, config):
        qubo.linear[0] = 999
        config.seed += 1
        raise TimeoutError("private details")

    mock_runners[runner_index].side_effect = mutate_then_timeout
    qubo, config = analyze_source(SOURCE).qubo, QAOAConfig(shots=32, seed=7)
    original_qubo, original_config = qubo.model_copy(deep=True), config.model_copy(deep=True)
    with pytest.raises(TimeoutError):
        pipeline.benchmark_qubo(qubo, config)
    assert qubo == original_qubo and config == original_config
    if runner_index == 0:
        mock_runners[1].assert_not_called()
    response = client.post(
        "/api/compiler/benchmark", json={"source": SOURCE, "config": {"shots": 32}}
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "TIMEOUT"
    assert "private details" not in response.text and "quantum" not in response.json()


def test_full_script_plan_is_nonexecuting_and_matches_mocked_benchmark(
    client, mock_runners, tmp_path
):
    sentinel = tmp_path / "must-not-exist"
    source = (
        f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('not executed')\n"
        + SOURCE
        + "\n\n@qatlas.circuit\ndef build_circuit():\n    raise RuntimeError('old')\n"
    )
    payload = {"source": source, "config": {"shots": 32, "seed": 7, "p": 2}}
    response = client.post("/api/compiler/benchmark/plan", json=payload)
    assert response.status_code == 200
    plan = CompilerBenchmarkPlan.model_validate(response.json())
    assert plan.status == "planned" and plan.comparison_scope == "objective_optimization"
    assert plan.script_execution_enabled is plan.quantum_execution_enabled is False
    assert plan.source_sha256 == hashlib.sha256(source.encode()).hexdigest()
    from app.compiler.generation import generate_source

    generated = generate_source(source, p=2)
    assert (
        plan.generated_source_sha256
        == hashlib.sha256(generated.artifact.source.encode()).hexdigest()
    )
    assert plan.circuit.p == plan.config.p == 2
    assert plan.qubo == generated.qubo and plan.entrypoint == "build_circuit"
    assert "elapsed_ms" not in response.text and source not in response.text
    for runner in mock_runners:
        runner.assert_not_called()
    # Only the explicitly mocked handoff is exercised; never execute the uploaded script.
    compared = client.post("/api/compiler/benchmark", json=payload)
    assert compared.status_code == 200
    assert compared.json()["problem_id"] == plan.problem_id
    assert compared.json()["metadata"]["qubo"] == plan.qubo.model_dump(mode="json")
    assert not sentinel.exists()


def test_bad_benchmark_plans_fail_without_calling_runners(client, mock_runners):
    rejected = client.post(
        "/api/compiler/benchmark/plan", json={"source": "print('not an objective')"}
    )
    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "VALIDATION_ERROR"
    invalid = client.post(
        "/api/compiler/benchmark/plan", json={"source": SOURCE, "config": {"p": 9}}
    )
    assert invalid.status_code == 422
    for field in ("execute", "quantum_execution_enabled", "script_execution_enabled"):
        attempted = client.post(
            "/api/compiler/benchmark/plan", json={"source": SOURCE, field: True}
        )
        assert attempted.status_code == 422
    for runner in mock_runners:
        runner.assert_not_called()


def test_angle_optimizer_record_is_not_a_sampled_solver_result(mock_runners):
    from app.quantum.qaoa_optimization import AngleOptimizationResult

    mock_runners[1].return_value = AngleOptimizationResult(
        angles=(0.2, 0.3),
        expectation=3.5,
        evaluations=4,
        converged=False,
        stop_reason="evaluation_limit",
        elapsed_ms=2,
        optimizer_ms=1,
    )
    with pytest.raises(ValueError, match="angle-search record"):
        pipeline.benchmark_source(SOURCE, QAOAConfig(shots=32))


def test_shared_qaoa_evaluation_limit_is_checked(mock_runners):
    mock_runners[1].return_value.metrics.optimizer_evaluations = 5
    with pytest.raises(ValueError, match="evaluation budget"):
        pipeline.benchmark_source(SOURCE, QAOAConfig(shots=32, max_iterations=4))


@pytest.mark.parametrize("runner_index", [0, 1])
def test_shared_reported_deadline_overrun_is_not_a_completed_result(
    client, mock_runners, runner_index
):
    mock_runners[runner_index].return_value.elapsed_ms = 1001
    response = client.post(
        "/api/compiler/benchmark",
        json={"source": SOURCE, "config": {"shots": 32, "timeout_seconds": 1}},
    )
    assert response.status_code == 504
    assert response.json()["error"]["code"] == "TIMEOUT"
    if runner_index == 0:
        mock_runners[1].assert_not_called()


@pytest.mark.parametrize("runner_index", [0, 1])
def test_shared_timing_components_cannot_exceed_total(mock_runners, runner_index):
    mock_runners[runner_index].return_value.timing.optimizer_ms = 3
    with pytest.raises(ValueError, match="timing component"):
        pipeline.benchmark_source(SOURCE, QAOAConfig(shots=32))
    if runner_index == 0:
        mock_runners[1].assert_not_called()


@pytest.mark.parametrize("setting", [None, "0", "true"])
def test_compiler_api_defaults_to_no_execution(client, monkeypatch, setting):
    if setting is None:
        monkeypatch.delenv("QATLAS_ENABLE_COMPILER_AER", raising=False)
    else:
        monkeypatch.setenv("QATLAS_ENABLE_COMPILER_AER", setting)
    classical = Mock(side_effect=AssertionError("must not run"))
    quantum = Mock(side_effect=AssertionError("must not run"))
    monkeypatch.setattr(pipeline.solvers, "run_classical", classical)
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", quantum)
    response = client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == 501
    assert "disabled" in response.json()["error"]["message"]
    rejected = client.post("/api/compiler/benchmark", json={"source": "print('unsupported')"})
    assert rejected.status_code == 422
    classical.assert_not_called()
    quantum.assert_not_called()


def test_missing_optional_dependencies_are_sanitized(client, mock_runners):
    mock_runners[1].side_effect = ImportError("private installation details")
    response = client.post("/api/compiler/benchmark", json={"source": SOURCE})
    assert response.status_code == 501
    assert "quantum dependencies" in response.json()["error"]["message"]
    assert "private" not in response.text


def test_compiler_consumes_actual_shared_entrypoint_with_worker_mocked(client, monkeypatch):
    from app.quantum import qaoa

    monkeypatch.setenv("QATLAS_ENABLE_COMPILER_AER", "1")
    classical = SolverResult(
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
    sampled = QAOAResult(
        elapsed_ms=1,
        objective=3,
        best_bitstring="100",
        metrics=dict(num_qubits=3, shots=32, circuit_depth=8, optimizer_evaluations=4),
        timing=dict(
            includes_queue=False,
            includes_transpilation=True,
            includes_optimizer=True,
            includes_sampling=True,
        ),
    )
    monkeypatch.setattr(pipeline.solvers, "run_classical", Mock(return_value=classical))
    worker = Mock(return_value=(sampled, 2))
    monkeypatch.setattr(qaoa, "run_with_deadline", worker)
    clock = iter([0, 2_000_000])
    monkeypatch.setattr(qaoa, "perf_counter_ns", lambda: next(clock))
    response = client.post(
        "/api/compiler/benchmark",
        json={"source": SOURCE, "config": {"p": 2, "shots": 32, "seed": 7, "max_iterations": 4}},
    )
    assert response.status_code == 200
    result = CompilerBenchmarkResult.model_validate(response.json())
    assert result.quantum.elapsed_ms == 2 and result.quantum.best_bitstring == "100"
    assert result.metrics.optimality_gap == 0 and result.metadata.simulated
    worker.assert_called_once()
    qubo, config, compute = worker.call_args.args
    assert qubo == result.metadata.qubo and config == result.metadata.config
    assert compute is qaoa._sampled_run  # Recorded only; the worker never executes.
