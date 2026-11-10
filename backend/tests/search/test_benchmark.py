"""Theory, real simulator results, and process-boundary timeout/error behavior."""

import multiprocessing as mp
from math import asin, sin, sqrt

import pytest

from app.experiments.search import runner
from app.experiments.search.runner import SearchDependencyError, run_search
from app.experiments.search.settings import (
    request_diagnostics,
    suggested_iterations,
    theoretical_probability,
)
from app.schemas.contracts import SearchRequest, SearchResult


@pytest.fixture
def experiment():
    pytest.importorskip("qiskit")
    pytest.importorskip("qiskit_aer")
    from app.experiments.search.experiment import run_experiment

    return run_experiment


@pytest.mark.parametrize(
    ("size", "marked", "expected"), [(8, 1, 2), (4, 1, 1), (8, 4, 0), (8, 8, 0)]
)
def test_first_peak_iteration_selection(size, marked, expected):
    assert suggested_iterations(size, marked) == expected


@pytest.mark.parametrize("iterations", range(7))
def test_probability_formula(iterations):
    assert theoretical_probability(8, 2, iterations) == pytest.approx(
        sin((2 * iterations + 1) * asin(sqrt(2 / 8))) ** 2
    )


@pytest.mark.parametrize(("size", "marked", "iterations"), [(0, 1, 1), (4, 5, 1), (4, 1, -1)])
def test_invalid_theory_inputs(size, marked, iterations):
    with pytest.raises(ValueError):
        theoretical_probability(size, marked, iterations)


@pytest.mark.parametrize(
    "changes",
    [
        {"num_qubits": 7, "marked_states": ["0000000"]},
        {"iterations": 33},
        {"config": {"shots": 10001}},
    ],
)
def test_unsupported_resources_rejected_before_spawn(monkeypatch, changes):
    def unexpected_spawn(*args):
        pytest.fail("unsupported input must not create a worker")

    monkeypatch.setattr(runner.mp, "get_context", unexpected_spawn)
    request = SearchRequest.model_validate({"num_qubits": 3, "marked_states": ["001"], **changes})
    assert request_diagnostics(request)
    with pytest.raises(ValueError):
        run_search(request)


@pytest.mark.parametrize(
    ("targets", "iterations"),
    [
        (["001"], None),
        (["001"], 0),
        (["001"], 4),
        (["001", "110"], 1),
        (["00", "01", "10", "11"], None),
        (["0"], None),
    ],
)
def test_measured_results_match_theory_and_contract(experiment, targets, iterations):
    request = SearchRequest(
        num_qubits=len(targets[0]),
        marked_states=targets,
        iterations=iterations,
        config={"shots": 4096},
    )
    before = request.model_dump()
    result = experiment(request)
    assert SearchResult.model_validate_json(result.model_dump_json()) == result
    assert request.model_dump() == before
    assert result.metrics.success_probability == pytest.approx(
        result.metrics.theoretical_success_probability, abs=0.04
    )
    assert result.metrics.quantum_oracle_queries == result.metadata.parameters.iterations
    assert (
        result.metrics.successful_shots / request.config.shots == result.metrics.success_probability
    )
    assert result.metrics.classical_observed_queries == int(min(targets), 2) + 1
    assert result.metrics.quantum_total_oracle_queries == (
        result.metrics.quantum_oracle_queries * request.config.shots
    )
    assert result.metrics.classical_expected_queries == (2**request.num_qubits + 1) / (
        len(targets) + 1
    )
    assert result.metrics.classical_worst_case_queries == 2**request.num_qubits - len(targets) + 1
    assert result.classical.best_bitstring == min(targets)
    assert result.quantum.objective is None
    assert result.classical.objective is None
    assert result.quantum.timing.includes_sampling
    assert result.quantum.timing.includes_transpilation
    assert result.quantum.elapsed_ms >= result.quantum.timing.transpilation_ms
    assert result.quantum.elapsed_ms >= result.quantum.timing.sampling_ms
    assert result.metrics.circuit_depth > 0
    assert result.metadata.simulated
    assert result.metadata.versions["qiskit"]


def test_seeded_measurements_repeat_and_target_order_does_not_change_instance(experiment):
    request = SearchRequest(num_qubits=3, marked_states=["001", "110"])
    first = experiment(request)
    second = experiment(request.model_copy(update={"marked_states": ["110", "001"]}))
    assert first.problem_id == second.problem_id
    assert first.metrics == second.metrics
    assert first.quantum.best_bitstring == second.quantum.best_bitstring


def test_unmarked_observation_is_not_relabelled_as_success(experiment):
    # Two-qubit one-target Grover returns to uniform at iteration 2. A single shot
    # can miss: find such a seed and verify that the result reports the actual miss.
    for seed in range(10):
        result = experiment(
            SearchRequest(
                num_qubits=2,
                marked_states=["00"],
                iterations=0,
                config={"shots": 1, "seed": seed},
            )
        )
        if result.metrics.success_probability == 0:
            assert result.metrics.successful_shots == 0
            assert result.quantum.best_bitstring != "00"
            break
    else:
        pytest.fail("expected an unmarked single-shot observation")


def test_spawned_runner_executes_real_comparison_and_reaps_worker(experiment):
    before = {process.pid for process in mp.active_children()}
    result = run_search(SearchRequest(num_qubits=2, marked_states=["01"]))
    assert result.metrics.success_probability == 1
    assert result.quantum.best_bitstring == "01"
    assert {process.pid for process in mp.active_children()} == before


def test_real_timeout_leaves_no_child_running():
    before = {process.pid for process in mp.active_children()}
    request = SearchRequest(
        num_qubits=3, marked_states=["001"], config={"timeout_seconds": 0.000001}
    )
    with pytest.raises(TimeoutError):
        run_search(request)
    assert {process.pid for process in mp.active_children()} == before


class FakeConnection:
    def __init__(self, message):
        self.message = message
        self.closed = False

    def poll(self, timeout):
        return True

    def recv(self):
        if isinstance(self.message, Exception):
            raise self.message
        return self.message

    def close(self):
        self.closed = True


class FakeProcess:
    pid = 123

    def __init__(self):
        self.terminated = False
        self.closed = False

    def start(self):
        pass

    def join(self, timeout):
        pass

    def is_alive(self):
        return not self.terminated

    def terminate(self):
        self.terminated = True

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (("dependency_missing", None), SearchDependencyError),
        (("error", None), RuntimeError),
        (EOFError(), RuntimeError),
    ],
)
def test_worker_failures_are_propagated_and_cleaned_up(monkeypatch, message, error):
    reader, writer = FakeConnection(message), FakeConnection(None)
    process = FakeProcess()

    class Context:
        def Pipe(self, duplex):
            return reader, writer

        def Process(self, **kwargs):
            return process

    monkeypatch.setattr(runner.mp, "get_context", lambda method: Context())
    with pytest.raises(error):
        run_search(SearchRequest(num_qubits=2, marked_states=["01"]))
    assert reader.closed and writer.closed and process.closed and process.terminated
