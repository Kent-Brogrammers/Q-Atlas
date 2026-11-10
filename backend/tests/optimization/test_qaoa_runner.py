"""Observed-shot selection, measured records, complete runs, and final-phase deadlines."""

import ctypes
import multiprocessing as mp
from functools import partial
from pathlib import Path
from time import perf_counter
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.quantum import qaoa
from app.quantum.qaoa_optimization import AngleOptimizationResult
from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, QAOAConfig, QAOAResult


def _blocked_final_sampling(qubo, config, *, marker):
    import qiskit_aer

    from app.quantum import qaoa_optimization

    qaoa_optimization._search_angles = lambda qubo, config: AngleOptimizationResult(
        angles=(0.3, 0.2),
        expectation=0,
        evaluations=1,
        converged=False,
        stop_reason="evaluation_limit",
        elapsed_ms=0,
        optimizer_ms=0,
    )

    class BlockedSimulator:
        def __init__(self, **options):
            pass

        def run(self, *args, **kwargs):
            Path(marker).write_text("entered final sampling")
            ctypes.CDLL(None).sleep(30)

    qiskit_aer.AerSimulator = BlockedSimulator
    return qaoa._sampled_run(qubo, config)


@pytest.fixture
def asymmetric_qubo():
    return QUBO(
        num_variables=3,
        constant=2,
        linear=[-1, 2, -3],
        quadratic=[{"i": 0, "j": 2, "coefficient": 4}],
    )


@pytest.mark.parametrize("original_sense", ["minimize", "maximize"])
def test_chooses_lowest_observed_cost_with_offset_and_api_bit_order(
    asymmetric_qubo, original_sense
):
    asymmetric_qubo.original_sense = original_sense
    before = asymmetric_qubo.model_dump()
    counts = {"100": 1, "001": 3}
    assert qaoa._best_sample(asymmetric_qubo, counts, 4) == (-1, "001")
    assert asymmetric_qubo.model_dump() == before
    assert counts == {"100": 1, "001": 3}


def test_a_better_unobserved_assignment_is_never_substituted(asymmetric_qubo):
    assert evaluate_qubo(asymmetric_qubo, "001") == -1
    assert qaoa._best_sample(asymmetric_qubo, {"001": 4}, 4) == (1, "100")


def test_equal_sampled_costs_choose_lexicographically_first_api_string():
    qubo = QUBO(num_variables=3, linear=[0, 0, 0])
    assert qaoa._best_sample(qubo, {"010": 3, "100": 1}, 4) == (0, "001")


@pytest.mark.parametrize(
    "counts",
    [{}, {"00": 1}, {"0a0": 1}, {"000": 0}, {"000": -1}, {"000": True}, {"000": 1.5}, {1: 1}],
)
def test_invalid_counts_fail_explicitly(asymmetric_qubo, counts):
    with pytest.raises(RuntimeError, match="counts"):
        qaoa._best_sample(asymmetric_qubo, counts, 1)


def test_shot_total_must_match_the_request(asymmetric_qubo):
    with pytest.raises(RuntimeError, match="requested shots"):
        qaoa._best_sample(asymmetric_qubo, {"000": 3}, 4)


@pytest.fixture
def sampling(monkeypatch):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    import qiskit
    import qiskit_aer

    from app.quantum import qaoa_optimization

    optimized = AngleOptimizationResult(
        angles=(0.3, 0.2),
        expectation=-0.25,
        evaluations=7,
        converged=False,
        stop_reason="evaluation_limit",
        elapsed_ms=1,
        optimizer_ms=0.5,
    )
    search = Mock(return_value=optimized)
    monkeypatch.setattr(qaoa_optimization, "_search_angles", search)
    simulator = Mock()
    sampled = simulator.run.return_value.result.return_value
    sampled.success = True
    sampled.get_counts.return_value = {"100": 1, "001": 3}
    factory = Mock(return_value=simulator)
    monkeypatch.setattr(qiskit_aer, "AerSimulator", factory)
    compiled = {}
    original_transpile = qiskit.transpile

    def transpile(circuit, **options):
        compiled["input"] = circuit
        compiled["options"] = options
        compiled["circuit"] = original_transpile(circuit, **options)
        return compiled["circuit"]

    monkeypatch.setattr(qiskit, "transpile", transpile)
    return search, simulator, sampled, factory, compiled


def test_sampled_record_uses_actual_cost_depth_shots_and_seed(asymmetric_qubo, sampling):
    search, simulator, sampled, factory, compiled = sampling
    config = QAOAConfig(seed=7, shots=4, max_iterations=7)
    result = qaoa._sampled_run(asymmetric_qubo, config)
    assert (result.objective, result.best_bitstring) == (-1, "001")
    assert result.objective != search.return_value.expectation
    assert result.metrics.num_qubits == 3
    assert result.metrics.circuit_depth == compiled["circuit"].depth()
    assert result.metrics.shots == 4
    assert result.metrics.optimizer_evaluations == 7
    assert result.metrics.optimality_gap is None
    assert result.metrics.approximation_ratio is None
    assert compiled["options"] == {
        "basis_gates": ["rz", "sx", "x", "cx"],
        "optimization_level": 1,
        "seed_transpiler": 7,
    }
    circuit = compiled["input"]
    measured_pairs = [
        (circuit.find_bit(gate.qubits[0]).index, circuit.find_bit(gate.clbits[0]).index)
        for gate in circuit.data
        if gate.operation.name == "measure"
    ]
    assert measured_pairs == [(0, 0), (1, 1), (2, 2)]
    simulator.run.assert_called_once_with(compiled["circuit"], shots=4, seed_simulator=7)
    assert factory.call_args.kwargs["method"] == "statevector"
    assert factory.call_args.kwargs["max_parallel_threads"] == 1
    sampled.get_counts.assert_called_once_with(0)
    assert result.timing.includes_optimizer is True
    assert result.timing.includes_transpilation is True
    assert result.timing.includes_sampling is True
    assert result.timing.includes_queue is False
    assert result.timing.queue_ms is None
    assert QAOAResult.model_validate(result.model_dump()) == result


def test_final_sampling_failure_is_explicit(asymmetric_qubo, sampling):
    _, _, sampled, _, _ = sampling
    sampled.success = False
    with pytest.raises(RuntimeError, match="final sampling failed"):
        qaoa._sampled_run(asymmetric_qubo, QAOAConfig(shots=4))
    sampled.get_counts.assert_not_called()


def test_timings_measure_transpilation_and_final_sampling(monkeypatch, asymmetric_qubo, sampling):
    import qiskit

    search, _, sampled, _, _ = sampling
    now_ns = 0
    original_transpile = qiskit.transpile

    def timed_search(qubo, config):
        nonlocal now_ns
        now_ns += 2_000_000
        return search.return_value

    def timed_transpile(circuit, **options):
        nonlocal now_ns
        now_ns += 3_000_000
        return original_transpile(circuit, **options)

    def timed_counts(index):
        nonlocal now_ns
        now_ns += 5_000_000
        return {"100": 1, "001": 3}

    search.side_effect = timed_search
    sampled.get_counts.side_effect = timed_counts
    monkeypatch.setattr(qiskit, "transpile", timed_transpile)
    monkeypatch.setattr(qaoa, "perf_counter_ns", lambda: now_ns)
    result = qaoa._sampled_run(asymmetric_qubo, QAOAConfig(shots=4))
    assert result.elapsed_ms == 10
    assert result.timing.transpilation_ms == 3
    assert result.timing.sampling_ms == 5
    assert result.timing.optimizer_ms == 0.5  # Supplied by the synthetic optimizer fixture.


def test_complete_real_runner_is_reproducible_and_uses_shared_result():
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    qubo = QUBO(
        num_variables=2,
        linear=[-1, -1],
        quadratic=[{"i": 0, "j": 1, "coefficient": 2}],
    )
    config = QAOAConfig(seed=42, shots=256, max_iterations=100)
    before = (qubo.model_dump(), config.model_dump())
    first = qaoa.run_qaoa(qubo, config)
    second = qaoa.run_qaoa(qubo, config)
    assert (first.objective, first.best_bitstring) == (-1, "01")
    assert first.objective == evaluate_qubo(qubo, first.best_bitstring)
    assert first.metrics == second.metrics
    assert first.best_bitstring == second.best_bitstring
    assert first.objective == second.objective
    assert first.metrics.num_qubits == 2
    assert first.metrics.shots == 256
    assert 1 <= first.metrics.optimizer_evaluations <= config.max_iterations
    assert first.metrics.circuit_depth > 0
    for duration in (
        first.timing.transpilation_ms,
        first.timing.optimizer_ms,
        first.timing.sampling_ms,
    ):
        assert 0 <= duration <= first.elapsed_ms
    assert QAOAResult.model_validate_json(first.model_dump_json()) == first
    assert (qubo.model_dump(), config.model_dump()) == before


def test_full_supported_width_and_layers_produce_a_sampled_assignment():
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    qubo = QUBO(num_variables=16, constant=1.5, linear=[1] * 16)
    config = QAOAConfig(p=8, shots=1, max_iterations=1)
    result = qaoa.run_qaoa(qubo, config)
    assert len(result.best_bitstring) == 16
    assert result.objective == evaluate_qubo(qubo, result.best_bitstring)
    assert result.metrics.num_qubits == 16
    assert result.metrics.shots == 1
    assert result.metrics.optimizer_evaluations == 1


def test_deadline_covers_final_native_sampling_and_reaps_worker(monkeypatch, tmp_path):
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    marker = tmp_path / "final-sampling-started"
    monkeypatch.setattr(qaoa, "_sampled_run", partial(_blocked_final_sampling, marker=str(marker)))
    before = {process.pid for process in mp.active_children()}
    started = perf_counter()
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        qaoa.run_qaoa(QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=3))
    assert marker.is_file()
    assert perf_counter() - started < 7
    assert {process.pid for process in mp.active_children()} <= before


def test_parent_rejects_invalid_worker_payload(monkeypatch):
    monkeypatch.setattr(qaoa, "run_with_deadline", Mock(return_value=(None, 0)))
    with pytest.raises(RuntimeError, match="invalid result"):
        qaoa.run_qaoa(QUBO(num_variables=1, linear=[1]), QAOAConfig())


def test_parent_revalidates_mutable_nested_result_fields(monkeypatch, asymmetric_qubo, sampling):
    payload = qaoa._sampled_run(asymmetric_qubo, QAOAConfig(shots=4))
    payload.metrics.shots = -1
    monkeypatch.setattr(qaoa, "run_with_deadline", Mock(return_value=(payload, 0)))
    with pytest.raises(ValidationError):
        qaoa.run_qaoa(asymmetric_qubo, QAOAConfig(shots=4))
