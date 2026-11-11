"""Seeded search, strict evaluation budgets, and disposable-worker deadlines."""

import multiprocessing as mp
from functools import partial
from pathlib import Path
from time import perf_counter, sleep
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.quantum import _execution, qaoa_optimization
from app.schemas.contracts import QUBO, QAOAConfig


def _blocked_worker(connection, qubo_payload, config_payload, compute, *, marker):
    Path(marker).write_text("entered native call")
    sleep(30)
    connection.close()


def _packet_worker(connection, qubo_payload, config_payload, compute, *, status):
    connection.send((status, "invalid angles" if status == "invalid" else None))
    connection.close()


def _empty_worker(connection, qubo_payload, config_payload, compute):
    connection.close()


@pytest.fixture
def smooth_objective(monkeypatch):
    pytest.importorskip("numpy", reason="Install the optional quantum extra")
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    from app.quantum import qaoa_expectation

    calls = []

    class BowlObjective:
        def __init__(self, qubo, p):
            self.num_parameters = 2 * p

        def __call__(self, angles):
            calls.append(tuple(angles))
            return sum((float(angle) - 0.25) ** 2 for angle in angles)

    monkeypatch.setattr(qaoa_expectation, "QAOAExpectation", BowlObjective)
    return calls


@pytest.mark.parametrize("p,budget", [(1, 1), (1, 2), (8, 3), (8, 17)])
def test_even_small_budgets_cap_actual_evaluations(smooth_objective, p, budget):
    result = qaoa_optimization._search_angles(
        QUBO(num_variables=1, linear=[1]), QAOAConfig(p=p, max_iterations=budget)
    )
    assert len(smooth_objective) == result.evaluations == budget
    assert len(result.angles) == 2 * p
    assert result.converged is False
    assert result.stop_reason == "evaluation_limit"
    assert result.expectation == min(
        sum((float(angle) - 0.25) ** 2 for angle in values) for values in smooth_objective
    )


def test_seeded_search_converges_and_preserves_inputs(smooth_objective):
    qubo = QUBO(num_variables=1, linear=[1])
    config = QAOAConfig(seed=42, max_iterations=100)
    before = (qubo.model_dump(), config.model_dump())
    first = qaoa_optimization._search_angles(qubo, config)
    initial_score = sum((float(angle) - 0.25) ** 2 for angle in smooth_objective[0])
    second = qaoa_optimization._search_angles(qubo, config)
    assert first.expectation < initial_score
    assert first.expectation < 1e-7
    assert first.angles == pytest.approx(second.angles, abs=1e-12)
    assert first.evaluations == second.evaluations
    assert first.converged is True
    assert first.stop_reason == "converged"
    assert (qubo.model_dump(), config.model_dump()) == before


def test_keeps_best_observed_angles_and_counts_actual_calls(monkeypatch, smooth_objective):
    import scipy.optimize

    def minimize(score, initial, *, method, options):
        assert method == "COBYLA"
        score([2, 2])
        score([0.25, 0.25])
        return SimpleNamespace(success=True, x=[2, 2], fun=99, nfev=999)

    monkeypatch.setattr(scipy.optimize, "minimize", minimize)
    result = qaoa_optimization._search_angles(QUBO(num_variables=1, linear=[1]), QAOAConfig())
    assert result.angles == (0.25, 0.25)
    assert result.expectation == 0
    assert result.evaluations == 2


def test_records_preparation_and_optimizer_timing(monkeypatch, smooth_objective):
    import scipy.optimize

    from app.quantum import qaoa_expectation

    now_ns = 0

    class TimedObjective:
        num_parameters = 2

        def __init__(self, qubo, p):
            nonlocal now_ns
            now_ns += 5_000_000

        def __call__(self, angles):
            nonlocal now_ns
            now_ns += 2_000_000
            return sum(float(angle) ** 2 for angle in angles)

    def minimize(score, initial, *, method, options):
        nonlocal now_ns
        score([1, 1])
        score([0, 0])
        now_ns += 3_000_000
        return SimpleNamespace(success=True)

    monkeypatch.setattr(qaoa_expectation, "QAOAExpectation", TimedObjective)
    monkeypatch.setattr(scipy.optimize, "minimize", minimize)
    monkeypatch.setattr(qaoa_optimization, "perf_counter_ns", lambda: now_ns)
    result = qaoa_optimization._search_angles(QUBO(num_variables=1, linear=[1]), QAOAConfig())
    assert result.elapsed_ms == 12
    assert result.optimizer_ms == 7


def test_nonfinite_objective_is_an_explicit_failure(monkeypatch, smooth_objective):
    from app.quantum import qaoa_expectation

    objective = Mock(num_parameters=2, return_value=float("nan"))
    monkeypatch.setattr(qaoa_expectation, "QAOAExpectation", Mock(return_value=objective))
    with pytest.raises(ValueError, match="expectation must be finite"):
        qaoa_optimization._search_angles(QUBO(num_variables=1, linear=[1]), QAOAConfig())


def test_optimizer_return_without_scoring_is_an_explicit_failure(monkeypatch, smooth_objective):
    import scipy.optimize

    monkeypatch.setattr(
        scipy.optimize, "minimize", Mock(return_value=SimpleNamespace(success=False))
    )
    with pytest.raises(RuntimeError, match="without an objective evaluation"):
        qaoa_optimization._search_angles(QUBO(num_variables=1, linear=[1]), QAOAConfig())


def test_early_optimizer_stop_is_distinct_from_convergence(monkeypatch, smooth_objective):
    import scipy.optimize

    def minimize(score, initial, *, method, options):
        score(initial)
        return SimpleNamespace(success=False)

    monkeypatch.setattr(scipy.optimize, "minimize", minimize)
    result = qaoa_optimization._search_angles(
        QUBO(num_variables=1, linear=[1]), QAOAConfig(max_iterations=100)
    )
    assert result.evaluations == 1
    assert result.converged is False
    assert result.stop_reason == "optimizer_stopped"


def test_real_aer_search_is_reproducible_and_improves_single_edge():
    pytest.importorskip("scipy", reason="Install the optional quantum extra")
    pytest.importorskip("qiskit_aer", reason="Install the optional quantum extra")
    from app.quantum.qaoa_expectation import QAOAExpectation

    qubo = QUBO(
        num_variables=2,
        linear=[-1, -1],
        quadratic=[{"i": 0, "j": 1, "coefficient": 2}],
    )
    config = QAOAConfig(seed=42, max_iterations=100, timeout_seconds=30)
    before = (qubo.model_dump(), config.model_dump())
    first = qaoa_optimization.optimize_qaoa_angles(qubo, config)
    second = qaoa_optimization.optimize_qaoa_angles(qubo, config)
    assert first.expectation == pytest.approx(-1, abs=1e-5)
    assert first.expectation == pytest.approx(QAOAExpectation(qubo)(first.angles), abs=1e-12)
    assert first.angles == pytest.approx(second.angles, abs=1e-12)
    assert first.evaluations == second.evaluations
    assert 1 <= first.evaluations <= config.max_iterations
    assert 0 <= first.optimizer_ms <= first.elapsed_ms
    assert (qubo.model_dump(), config.model_dump()) == before


def test_deadline_stops_native_work_and_reaps_worker(monkeypatch, tmp_path):
    marker = tmp_path / "native-call-started"
    monkeypatch.setattr(_execution, "_worker", partial(_blocked_worker, marker=str(marker)))
    before = {process.pid for process in mp.active_children()}
    started = perf_counter()
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        qaoa_optimization.optimize_qaoa_angles(
            QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=2)
        )
    assert marker.is_file()
    assert perf_counter() - started < 6
    assert {process.pid for process in mp.active_children()} <= before


def test_startup_is_inside_the_deadline():
    before = {process.pid for process in mp.active_children()}
    with pytest.raises(TimeoutError, match="timeout_seconds"):
        qaoa_optimization.optimize_qaoa_angles(
            QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=1e-9)
        )
    assert {process.pid for process in mp.active_children()} <= before


@pytest.mark.parametrize(
    "status,error,message",
    [
        ("dependency_missing", ImportError, "quantum extra"),
        ("invalid", ValueError, "invalid angles"),
        ("error", RuntimeError, "optimization failed"),
    ],
)
def test_worker_failures_propagate_explicitly(monkeypatch, status, error, message):
    monkeypatch.setattr(_execution, "_worker", partial(_packet_worker, status=status))
    with pytest.raises(error, match=message):
        qaoa_optimization.optimize_qaoa_angles(
            QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=10)
        )


def test_worker_exit_without_payload_is_an_explicit_failure(monkeypatch):
    monkeypatch.setattr(_execution, "_worker", _empty_worker)
    with pytest.raises(RuntimeError, match="exited without a result"):
        qaoa_optimization.optimize_qaoa_angles(
            QUBO(num_variables=1, linear=[1]), QAOAConfig(timeout_seconds=10)
        )
