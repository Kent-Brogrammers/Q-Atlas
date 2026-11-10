"""Exact baseline checks with independent answers and controlled deadline clocks."""

from unittest.mock import Mock

import pytest

from app.compiler import pipeline
from app.experiments.optimization import solvers
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import (
    QUBO,
    CompilerBenchmarkResult,
    OptimizationMetrics,
    QAOAConfig,
    QAOAResult,
    SolverResult,
    TimingBreakdown,
)


def test_finds_the_known_mixed_qubo_minimum(mixed_qubo):
    qubo = QUBO.model_validate(mixed_qubo)
    result = solvers.run_classical(qubo, QAOAConfig())
    assert result.algorithm == "brute_force"
    assert result.best_bitstring == "101"
    assert result.objective == -3.75
    assert result.objective == evaluate_qubo(qubo, result.best_bitstring)
    assert SolverResult.model_validate(result.model_dump()) == result


@pytest.mark.parametrize(
    ("coefficient", "bitstring", "objective"),
    [(-2, "1", -2), (3, "0", 0), (0, "0", 0)],
)
def test_single_variable_and_zero_objectives(coefficient, bitstring, objective):
    qubo = QUBO(num_variables=1, linear=[coefficient])
    result = solvers.run_classical(qubo, QAOAConfig())
    assert (result.best_bitstring, result.objective) == (bitstring, objective)


def test_pair_terms_and_ties_use_the_first_lexicographic_minimum():
    # A single Max-Cut edge has two equal minima, 01 and 10.
    qubo = QUBO(
        num_variables=2,
        linear=[-1, -1],
        quadratic=[{"i": 0, "j": 1, "coefficient": 2}],
    )
    result = solvers.run_classical(qubo, QAOAConfig())
    assert (result.best_bitstring, result.objective) == ("01", -1)


@pytest.mark.parametrize("constant", [-7.25, 0, 9.5])
def test_constant_offsets_leading_zeros_and_original_sense(constant):
    qubo = QUBO(
        num_variables=3,
        constant=constant,
        linear=[-1, 2, -3],
        quadratic=[{"i": 0, "j": 2, "coefficient": 4}],
        original_sense="maximize",
    )
    result = solvers.run_classical(qubo, QAOAConfig())
    assert result.best_bitstring == "001"  # x[2] is 1 in the API's ordering.
    assert result.objective == constant - 3
    assert qubo.original_sense == "maximize"


def test_supports_the_full_shared_qubo_width():
    qubo = QUBO(num_variables=16, linear=[-1] * 16)
    result = solvers.run_classical(qubo, QAOAConfig())
    assert (result.best_bitstring, result.objective) == ("1" * 16, -16)


def test_preserves_inputs_and_is_independent_of_quantum_settings(mixed_qubo):
    qubo = QUBO.model_validate(mixed_qubo)
    config = QAOAConfig(seed=7, shots=64, p=2, max_iterations=1)
    before_qubo, before_config = qubo.model_dump(), config.model_dump()
    first = solvers.run_classical(qubo, config)
    second = solvers.run_classical(qubo, QAOAConfig(seed=123, shots=128, p=8))
    assert (first.best_bitstring, first.objective) == (second.best_bitstring, second.objective)
    assert qubo.model_dump() == before_qubo
    assert config.model_dump() == before_config


def test_timing_includes_evaluation_and_result_construction(monkeypatch):
    now_ns = 0

    def timed_evaluation(qubo, bitstring):
        nonlocal now_ns
        now_ns += 2_000_000
        return evaluate_qubo(qubo, bitstring)

    def timed_result(**fields):
        nonlocal now_ns
        now_ns += 3_000_000
        return SolverResult(**fields)

    monkeypatch.setattr(solvers, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(solvers, "evaluate_qubo", timed_evaluation)
    monkeypatch.setattr(solvers, "SolverResult", timed_result)
    result = solvers.run_classical(QUBO(num_variables=1, linear=[1]), QAOAConfig())
    assert result.elapsed_ms == 7  # Two evaluations plus result construction.
    assert result.timing == TimingBreakdown(
        includes_queue=False,
        includes_transpilation=False,
        includes_optimizer=False,
        includes_sampling=False,
    )


def test_timeout_before_the_first_evaluation(monkeypatch):
    times = iter([0, 1_000_000])
    evaluator = Mock(side_effect=AssertionError("deadline must be checked first"))
    monkeypatch.setattr(solvers, "perf_counter_ns", lambda: next(times))
    monkeypatch.setattr(solvers, "evaluate_qubo", evaluator)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        solvers.run_classical(QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=0.001))
    evaluator.assert_not_called()


@pytest.mark.parametrize("width", [1, 2])
def test_timeout_during_search_or_after_the_final_assignment(monkeypatch, width):
    now_ns = 0
    visited = []

    def slow_evaluation(qubo, bitstring):
        nonlocal now_ns
        visited.append(bitstring)
        now_ns += 600_000
        return evaluate_qubo(qubo, bitstring)

    monkeypatch.setattr(solvers, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(solvers, "evaluate_qubo", slow_evaluation)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        solvers.run_classical(
            QUBO(num_variables=width, linear=[1] * width), QAOAConfig(timeout_seconds=0.001)
        )
    assert len(visited) == 2


def test_timeout_during_result_construction(monkeypatch):
    now_ns = 0

    def slow_result(**fields):
        nonlocal now_ns
        now_ns = 1_000_000
        return SolverResult(**fields)

    monkeypatch.setattr(solvers, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(solvers, "SolverResult", slow_result)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        solvers.run_classical(QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=0.001))


def test_objective_overflow_aborts_the_exact_search():
    qubo = QUBO(num_variables=2, linear=[1e308, 1e308])
    with pytest.raises(ValueError, match="overflow"):
        solvers.run_classical(qubo, QAOAConfig())


def test_compiler_consumes_the_real_classical_baseline(monkeypatch):
    # Synthetic quantum boundary only. This test runs pure classical arithmetic.
    quantum = Mock(
        return_value=QAOAResult(
            elapsed_ms=0,
            objective=-1,
            best_bitstring="001",
            timing=TimingBreakdown(
                includes_queue=False,
                includes_transpilation=False,
                includes_optimizer=False,
                includes_sampling=False,
            ),
            metrics=OptimizationMetrics(num_qubits=3, shots=64),
        )
    )
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", quantum)
    source = (
        "@qatlas.objective(num_bits=3)\n"
        "def cost(x):\n"
        "    return 2 - x[0] + 2*x[1] - 3*x[2] + 4*x[0]*x[2]\n"
    )
    result = pipeline.benchmark_source(source, QAOAConfig(shots=64))
    assert result.classical.algorithm == "brute_force"
    assert (result.classical.best_bitstring, result.classical.objective) == ("001", -1)
    assert result.metrics.optimality_gap == 0
    assert result.metrics.approximation_ratio is None
    quantum.assert_called_once()


def test_compiler_returns_a_real_comparison_through_the_shared_runners(client):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    response = client.post(
        "/api/compiler/benchmark",
        json={
            "source": "@qatlas.objective(num_bits=1)\ndef cost(x): return -x[0]",
            "config": {"shots": 32, "max_iterations": 16},
        },
    )
    assert response.status_code == 200
    result = CompilerBenchmarkResult.model_validate(response.json())
    assert result.classical.objective == -1
    assert result.quantum.objective == evaluate_qubo(
        result.metadata.qubo, result.quantum.best_bitstring
    )
    assert result.metrics.num_qubits == 1
    assert result.metrics.shots == 32
    assert result.metrics.optimality_gap >= 0
    assert result.metadata.simulated is True
