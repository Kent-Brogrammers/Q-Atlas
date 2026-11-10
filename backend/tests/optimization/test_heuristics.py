"""Seeded local-search trajectories, exact references, and timing boundaries."""

from random import getstate
from unittest.mock import Mock

import pytest

from app.compiler import pipeline
from app.experiments.optimization import heuristics
from app.experiments.optimization.solvers import run_classical
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import (
    QUBO,
    OptimizationMetrics,
    QAOAConfig,
    QAOAResult,
    SolverResult,
    TimingBreakdown,
)


@pytest.fixture
def paired_qubo():
    """Eight independent pairs, with a local basin at 00 and optimum at 11."""
    return QUBO(
        num_variables=16,
        linear=[1] * 16,
        quadratic=[{"i": i, "j": i + 1, "coefficient": -3} for i in range(0, 16, 2)],
    )


@pytest.mark.parametrize("coefficient,bits,objective", [(-2, "1", -2), (3, "0", 0), (0, "0", 0)])
def test_single_variable_and_zero_objectives(coefficient, bits, objective):
    result = heuristics.run_heuristic(QUBO(num_variables=1, linear=[coefficient]), QAOAConfig())
    assert (result.best_bitstring, result.objective) == (bits, objective)
    assert result.algorithm == "seeded_bit_flip_local_search"
    assert SolverResult.model_validate_json(result.model_dump_json()) == result


def test_known_mixed_qubo_matches_the_exact_reference(mixed_qubo):
    qubo = QUBO.model_validate(mixed_qubo)
    result = heuristics.run_heuristic(qubo, QAOAConfig())
    exact = run_classical(qubo, QAOAConfig())
    assert result.objective == exact.objective == -3.75
    assert result.best_bitstring == exact.best_bitstring == "101"


@pytest.mark.parametrize("constant", [-7.25, 0, 9.5])
def test_offsets_canonical_sense_and_leading_zeros(constant):
    qubo = QUBO(
        num_variables=3,
        constant=constant,
        linear=[-1, 2, -3],
        quadratic=[{"i": 0, "j": 2, "coefficient": 4}],
        original_sense="maximize",
    )
    result = heuristics.run_heuristic(qubo, QAOAConfig())
    assert (result.best_bitstring, result.objective) == ("001", constant - 3)
    assert result.objective == evaluate_qubo(qubo, result.best_bitstring)
    assert qubo.original_sense == "maximize"


def test_strict_best_improvement_and_eight_starts_use_the_shared_evaluator(monkeypatch):
    random = Mock()
    random.getrandbits.return_value = 0
    factory = Mock(return_value=random)
    monkeypatch.setattr(heuristics, "Random", factory)
    visited = []

    def score(qubo, bits):
        visited.append(bits)
        return evaluate_qubo(qubo, bits)

    monkeypatch.setattr(heuristics, "evaluate_qubo", score)
    result = heuristics.run_heuristic(
        QUBO(num_variables=3, linear=[-3, -2, -1]), QAOAConfig(seed=7)
    )
    first_start = [
        "000",
        "100",
        "010",
        "001",
        "000",
        "110",
        "101",
        "010",
        "100",
        "111",
        "011",
        "101",
        "110",
    ]
    assert visited == first_start * 8
    assert (result.objective, result.best_bitstring) == (-6, "111")
    factory.assert_called_once_with(7)
    assert random.getrandbits.call_count == 7
    assert all(call.args == (3,) for call in random.getrandbits.call_args_list)


def test_plateaus_stop_without_cycling_and_preserve_zero_bits(monkeypatch):
    random = Mock()
    random.getrandbits.return_value = 0
    monkeypatch.setattr(heuristics, "Random", Mock(return_value=random))
    score = Mock(wraps=evaluate_qubo)
    monkeypatch.setattr(heuristics, "evaluate_qubo", score)
    result = heuristics.run_heuristic(
        QUBO(num_variables=3, constant=2.5, linear=[0, 0, 0]), QAOAConfig()
    )
    assert (result.objective, result.best_bitstring) == (2.5, "000")
    assert score.call_count == 8 * 4


def test_equal_improvements_use_api_lexicographic_order(monkeypatch):
    random = Mock()
    random.getrandbits.return_value = 0
    monkeypatch.setattr(heuristics, "Random", Mock(return_value=random))
    qubo = QUBO(num_variables=2, linear=[-1, -1], quadratic=[{"i": 0, "j": 1, "coefficient": 2}])
    result = heuristics.run_heuristic(qubo, QAOAConfig())
    assert (result.objective, result.best_bitstring) == (-1, "01")


def test_seeded_results_are_repeatable_and_preserve_inputs_and_global_rng(paired_qubo):
    config = QAOAConfig(seed=1, shots=1, p=8, max_iterations=1)
    before = paired_qubo.model_dump(), config.model_dump(), getstate()
    first = heuristics.run_heuristic(paired_qubo, config)
    second = heuristics.run_heuristic(paired_qubo, config)
    assert (first.best_bitstring, first.objective) == (second.best_bitstring, second.objective)
    assert (paired_qubo.model_dump(), config.model_dump(), getstate()) == before
    other_settings = heuristics.run_heuristic(
        paired_qubo, QAOAConfig(seed=1, shots=9999, p=1, max_iterations=1000)
    )
    assert (other_settings.best_bitstring, other_settings.objective) == (
        first.best_bitstring,
        first.objective,
    )


def test_local_minimum_can_be_worse_than_the_global_optimum(paired_qubo):
    result = heuristics.run_heuristic(paired_qubo, QAOAConfig(seed=1))
    exact = run_classical(paired_qubo, QAOAConfig())
    assert result.objective == -7
    assert exact.objective == -8
    assert result.algorithm != "brute_force"
    assert result.objective == evaluate_qubo(paired_qubo, result.best_bitstring)
    for index in range(paired_qubo.num_variables):
        bits = list(result.best_bitstring)
        bits[index] = "1" if bits[index] == "0" else "0"
        assert evaluate_qubo(paired_qubo, "".join(bits)) >= result.objective
    assert heuristics.run_heuristic(paired_qubo, QAOAConfig(seed=42)).objective == -8


def test_maximum_width_dense_maxcut_has_a_valid_balanced_assignment():
    qubo = QUBO(
        num_variables=16,
        linear=[-15] * 16,
        quadratic=[{"i": i, "j": j, "coefficient": 2} for i in range(16) for j in range(i + 1, 16)],
    )
    result = heuristics.run_heuristic(qubo, QAOAConfig())
    assert result.best_bitstring == "0000000011111111"
    assert result.objective == evaluate_qubo(qubo, result.best_bitstring) == -64


def test_rng_preparation_is_inside_the_deadline(monkeypatch):
    now_ns = 0

    def slow_random(seed):
        nonlocal now_ns
        now_ns = 1_000_000
        return Mock()

    score = Mock(side_effect=AssertionError("must not evaluate after expiry"))
    monkeypatch.setattr(heuristics, "Random", slow_random)
    monkeypatch.setattr(heuristics, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(heuristics, "evaluate_qubo", score)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        heuristics.run_heuristic(
            QUBO(num_variables=1, linear=[0]), QAOAConfig(timeout_seconds=0.001)
        )
    score.assert_not_called()


@pytest.mark.parametrize("expires_at", [1, 5, 16])
def test_timeout_during_search_and_after_final_evaluation(monkeypatch, expires_at):
    now_ns = 0
    evaluations = 0

    def slow_score(qubo, bits):
        nonlocal now_ns, evaluations
        evaluations += 1
        if evaluations == expires_at:
            now_ns = 1_000_000
        return evaluate_qubo(qubo, bits)

    monkeypatch.setattr(heuristics, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(heuristics, "evaluate_qubo", slow_score)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        heuristics.run_heuristic(
            QUBO(num_variables=1, linear=[0]), QAOAConfig(timeout_seconds=0.001)
        )
    assert evaluations == expires_at


def test_timer_includes_preparation_evaluations_and_result_construction(monkeypatch):
    now_ns = 0

    def timed_random(seed):
        nonlocal now_ns
        now_ns += 3_000_000
        return Mock(getrandbits=Mock(return_value=0))

    def timed_score(qubo, bits):
        nonlocal now_ns
        now_ns += 2_000_000
        return evaluate_qubo(qubo, bits)

    def timed_result(**fields):
        nonlocal now_ns
        now_ns += 5_000_000
        return SolverResult(**fields)

    monkeypatch.setattr(heuristics, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(heuristics, "Random", timed_random)
    monkeypatch.setattr(heuristics, "evaluate_qubo", timed_score)
    monkeypatch.setattr(heuristics, "SolverResult", timed_result)
    result = heuristics.run_heuristic(QUBO(num_variables=1, linear=[0]), QAOAConfig())
    assert result.elapsed_ms == 40
    assert result.timing == TimingBreakdown(
        includes_queue=False,
        includes_transpilation=False,
        includes_optimizer=False,
        includes_sampling=False,
    )


def test_timeout_during_result_construction(monkeypatch):
    now_ns = 0

    def slow_result(**fields):
        nonlocal now_ns
        now_ns = 1_000_000
        return SolverResult(**fields)

    monkeypatch.setattr(heuristics, "perf_counter_ns", lambda: now_ns)
    monkeypatch.setattr(heuristics, "SolverResult", slow_result)
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        heuristics.run_heuristic(
            QUBO(num_variables=1, linear=[0]), QAOAConfig(timeout_seconds=0.001)
        )


def test_shared_objective_overflow_is_explicit():
    with pytest.raises(ValueError, match="overflow"):
        heuristics.run_heuristic(
            QUBO(num_variables=1, constant=1e308, linear=[1e308]), QAOAConfig()
        )


def test_compiler_keeps_the_gap_unknown_for_a_heuristic_reference(monkeypatch, paired_qubo):
    # Only the quantum boundary is synthetic. The heuristic runs real classical arithmetic.
    quantum = QAOAResult(
        objective=-8,
        best_bitstring="1" * 16,
        elapsed_ms=0,
        timing=TimingBreakdown(
            includes_queue=False,
            includes_transpilation=False,
            includes_optimizer=False,
            includes_sampling=False,
        ),
        metrics=OptimizationMetrics(num_qubits=16, shots=8, optimizer_evaluations=1),
    )
    monkeypatch.setattr(pipeline.solvers, "run_classical", heuristics.run_heuristic)
    monkeypatch.setattr(pipeline.qaoa, "run_qaoa", Mock(return_value=quantum))
    result = pipeline.benchmark_qubo(paired_qubo, QAOAConfig(seed=1, shots=8))
    assert result.classical.algorithm == "seeded_bit_flip_local_search"
    assert result.classical.objective == -7
    assert result.quantum.objective == -8
    assert result.metrics.optimality_gap is None
    assert result.metrics.approximation_ratio is None
