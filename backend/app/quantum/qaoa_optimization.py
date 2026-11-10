"""Seeded COBYLA angle search with a process boundary for native-work deadlines."""

import logging
import multiprocessing as mp
from dataclasses import dataclass, replace
from math import isfinite
from multiprocessing.connection import Connection
from time import perf_counter_ns
from typing import Literal

from app.schemas.contracts import QUBO, QAOAConfig


@dataclass(frozen=True)
class AngleOptimizationResult:
    """Internal angle-search record, with mean cost and measured milliseconds."""

    angles: tuple[float, ...]
    expectation: float
    evaluations: int
    converged: bool
    stop_reason: Literal["converged", "evaluation_limit", "optimizer_stopped"]
    elapsed_ms: float
    optimizer_ms: float


class _EvaluationLimitReached(Exception):
    """Stop COBYLA before it exceeds the configured scoring budget."""


def _search_angles(qubo: QUBO, config: QAOAConfig) -> AngleOptimizationResult:
    """Worker-side computation. The parent enforces the wall-clock deadline."""
    started_ns = perf_counter_ns()
    import numpy as np
    from scipy.optimize import minimize

    from app.quantum.qaoa_expectation import QAOAExpectation

    objective = QAOAExpectation(qubo, p=config.p)
    initial = np.random.default_rng(config.seed).uniform(-np.pi, np.pi, objective.num_parameters)
    best_angles = None
    best_expectation = float("inf")
    evaluations = 0

    def score(angles):
        nonlocal best_angles, best_expectation, evaluations
        if evaluations >= config.max_iterations:
            raise _EvaluationLimitReached
        value = float(objective(angles))
        if not isfinite(value):
            raise ValueError("QAOA expectation must be finite")
        evaluations += 1
        if value < best_expectation:
            best_expectation = value
            best_angles = tuple(float(angle) for angle in angles)
        return value

    optimizer_started_ns = perf_counter_ns()
    try:
        optimized = minimize(
            score,
            initial,
            method="COBYLA",
            options={
                # PRIMA requires enough calls to form its initial model. The score
                # guard enforces smaller user budgets without silently raising them.
                "maxiter": max(config.max_iterations, objective.num_parameters + 2),
                "disp": False,
            },
        )
        converged = bool(optimized.success)
    except _EvaluationLimitReached:
        converged = False
    optimizer_finished_ns = perf_counter_ns()
    if best_angles is None:
        raise RuntimeError("COBYLA returned without an objective evaluation")
    if converged:
        stop_reason = "converged"
    elif evaluations >= config.max_iterations:
        stop_reason = "evaluation_limit"
    else:
        stop_reason = "optimizer_stopped"
    return AngleOptimizationResult(
        angles=best_angles,
        expectation=best_expectation,
        evaluations=evaluations,
        converged=converged,
        stop_reason=stop_reason,
        elapsed_ms=(perf_counter_ns() - started_ns) / 1_000_000,
        optimizer_ms=(optimizer_finished_ns - optimizer_started_ns) / 1_000_000,
    )


def _worker(connection: Connection, qubo_payload: dict, config_payload: dict) -> None:
    try:
        result = _search_angles(
            QUBO.model_validate(qubo_payload), QAOAConfig.model_validate(config_payload)
        )
        connection.send(("ok", result))
    except ImportError:
        connection.send(("dependency_missing", None))
    except ValueError as error:
        connection.send(("invalid", str(error)))
    except Exception:
        logging.getLogger(__name__).exception("QAOA angle-search worker failed")
        connection.send(("error", None))
    finally:
        connection.close()


def optimize_qaoa_angles(qubo: QUBO, config: QAOAConfig) -> AngleOptimizationResult:
    """Find the best observed mean cost within a seeded, bounded local search.

    max_iterations caps expectation evaluations. timeout_seconds includes worker
    startup, optional imports, preparation, optimization, IPC, and normal cleanup.
    Timeout cleanup terminates and reaps the worker, with OS cleanup latency.
    This module's import path uses only core dependencies until the worker runs.
    """
    started_ns = perf_counter_ns()
    deadline_ns = started_ns + int(config.timeout_seconds * 1_000_000_000)
    context = mp.get_context("spawn")
    reader, writer = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker,
        args=(writer, qubo.model_dump(mode="json"), config.model_dump(mode="json")),
        daemon=True,
    )
    received = False
    try:
        process.start()
        writer.close()
        remaining_seconds = max(0, deadline_ns - perf_counter_ns()) / 1_000_000_000
        if not reader.poll(remaining_seconds):
            raise TimeoutError("QAOA angle optimization exceeded timeout_seconds")
        try:
            status, payload = reader.recv()
        except EOFError as error:
            raise RuntimeError("QAOA optimization worker exited without a result") from error
        received = True
        if perf_counter_ns() >= deadline_ns:
            raise TimeoutError("QAOA angle optimization exceeded timeout_seconds")
    finally:
        if process.pid is not None:
            if received:
                process.join(timeout=0.05)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            process.close()
        reader.close()
        writer.close()
    finished_ns = perf_counter_ns()
    if finished_ns >= deadline_ns:
        raise TimeoutError("QAOA angle optimization exceeded timeout_seconds")
    if status == "dependency_missing":
        raise ImportError("Install the backend quantum extra to optimize QAOA angles")
    if status == "invalid":
        raise ValueError(payload)
    if status != "ok" or not isinstance(payload, AngleOptimizationResult):
        raise RuntimeError("QAOA angle optimization failed")
    return replace(payload, elapsed_ms=(finished_ns - started_ns) / 1_000_000)
