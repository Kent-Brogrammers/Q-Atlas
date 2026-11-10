"""Seeded COBYLA angle search with a process boundary for native-work deadlines."""

from dataclasses import dataclass, replace
from math import isfinite
from time import perf_counter_ns
from typing import Literal

from app.quantum._execution import run_with_deadline
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


def optimize_qaoa_angles(qubo: QUBO, config: QAOAConfig) -> AngleOptimizationResult:
    """Find the best observed mean cost within a seeded, bounded local search.

    max_iterations caps expectation evaluations. timeout_seconds includes worker
    startup, optional imports, preparation, optimization, IPC, and normal cleanup.
    Timeout cleanup terminates and reaps the worker, with OS cleanup latency.
    This module's import path uses only core dependencies until the worker runs.
    """
    payload, elapsed_ms = run_with_deadline(
        qubo, config, _search_angles, task_name="QAOA angle optimization"
    )
    if not isinstance(payload, AngleOptimizationResult):
        raise RuntimeError("QAOA angle optimization failed")
    return replace(payload, elapsed_ms=elapsed_ms)
