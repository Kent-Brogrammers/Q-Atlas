"""Exact classical QUBO baseline shared by Developers 2 and 3."""

from time import perf_counter_ns

from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, QAOAConfig, SolverResult, TimingBreakdown


def run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult:
    """Enumerate every assignment and return the minimum canonical objective.

    The shared QUBO model bounds the search to 1–16 variables. API bitstrings put
    x[0] on the left. Enumeration is lexicographic, so equal minima keep the first
    bitstring. Inputs are read-only. Only timeout_seconds affects this deterministic
    baseline; the remaining config fields configure the future QAOA comparison.

    The end-to-end wall timer includes preparation, enumeration, best-assignment
    extraction, and result construction. Raise TimeoutError when the deadline is
    reached, including if the last evaluation or result construction overruns it.
    """
    started_ns = perf_counter_ns()
    deadline_ns = started_ns + int(config.timeout_seconds * 1_000_000_000)
    bitstring_format = f"0{qubo.num_variables}b"
    best_bitstring = ""
    best_objective = float("inf")

    for assignment in range(1 << qubo.num_variables):
        if perf_counter_ns() >= deadline_ns:
            raise TimeoutError("Classical brute-force solver exceeded timeout_seconds")
        bitstring = format(assignment, bitstring_format)
        objective = evaluate_qubo(qubo, bitstring)
        if objective < best_objective:
            best_objective = objective
            best_bitstring = bitstring

    finished_ns = perf_counter_ns()
    if finished_ns >= deadline_ns:
        raise TimeoutError("Classical brute-force solver exceeded timeout_seconds")
    result = SolverResult(
        algorithm="brute_force",
        objective=best_objective,
        best_bitstring=best_bitstring,
        elapsed_ms=(finished_ns - started_ns) / 1_000_000,
        timing=TimingBreakdown(
            includes_queue=False,
            includes_transpilation=False,
            includes_optimizer=False,
            includes_sampling=False,
        ),
    )
    finished_ns = perf_counter_ns()
    if finished_ns >= deadline_ns:
        raise TimeoutError("Classical brute-force solver exceeded timeout_seconds")
    result.elapsed_ms = (finished_ns - started_ns) / 1_000_000
    return result
