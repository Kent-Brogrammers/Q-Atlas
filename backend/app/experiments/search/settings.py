"""Search-only resource limits and ideal Grover iteration selection."""

from math import asin, ceil, floor, isclose, pi, sin, sqrt

from app.experiments.search.classical import query_bounds
from app.schemas.contracts import Diagnostic, SearchRequest


def theoretical_probability(num_candidates: int, num_marked: int, iterations: int) -> float:
    """Ideal probability for a uniform initial state and a marked-set phase oracle."""
    query_bounds(num_candidates, num_marked)
    if type(iterations) is not int or iterations < 0:
        raise ValueError("iterations must be a nonnegative integer")
    theta = asin(sqrt(num_marked / num_candidates))
    return sin((2 * iterations + 1) * theta) ** 2


def suggested_iterations(num_candidates: int, num_marked: int) -> int:
    """Choose the better integer beside the first peak; choose fewer on ties."""
    query_bounds(num_candidates, num_marked)
    theta = asin(sqrt(num_marked / num_candidates))
    peak = pi / (4 * theta) - 0.5
    lower, upper = max(0, floor(peak)), max(0, ceil(peak))
    low_p = theoretical_probability(num_candidates, num_marked, lower)
    high_p = theoretical_probability(num_candidates, num_marked, upper)
    return upper if high_p > low_p and not isclose(low_p, high_p, abs_tol=1e-14) else lower


def request_diagnostics(request: SearchRequest) -> list[Diagnostic]:
    """Reject unsupported resource sizes without changing shared request contracts."""
    diagnostics = []
    for invalid, field, message in [
        (request.num_qubits > 6, "num_qubits", "the search runner supports 1–6 qubits"),
        (
            request.iterations is not None and request.iterations > 32,
            "iterations",
            "the search runner supports 0–32 iterations",
        ),
        (request.config.shots > 10_000, "config.shots", "search supports at most 10000 shots"),
    ]:
        if invalid:
            diagnostics.append(
                Diagnostic(code="SEARCH_PARAMETER", severity="error", message=f"{field}: {message}")
            )
    return diagnostics
