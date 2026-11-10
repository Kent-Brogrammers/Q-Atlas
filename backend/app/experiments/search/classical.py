"""Classical oracle-model search with an explicit no-replacement policy."""

from dataclasses import dataclass
from time import perf_counter_ns

from app.schemas.contracts import SearchRequest


@dataclass(frozen=True)
class ClassicalSearchResult:
    """Internal measurements; API assembly remains the experiment runner's job."""

    found_state: str
    oracle_queries: int
    elapsed_ms: float
    expected_queries: float
    worst_case_queries: int


def query_bounds(num_candidates: int, num_marked: int) -> tuple[float, int]:
    """Expected/worst checks until first success, without replacement.

    Expectation assumes uniformly distributed marked positions relative to the
    checking order; it is not the observed count for a fixed supplied instance.
    """
    if (
        type(num_candidates) is not int
        or type(num_marked) is not int
        or not 1 <= num_marked <= num_candidates
    ):
        raise ValueError("require integer counts with 1 <= num_marked <= num_candidates")
    return (num_candidates + 1) / (num_marked + 1), num_candidates - num_marked + 1


def run_classical_search(request: SearchRequest) -> ClassicalSearchResult:
    """Check bitstrings in lexicographic order, stopping at the first marked one.

    Each set-membership predicate is one classical oracle query. The timer includes
    target-set preparation, enumeration, and result assembly. This tiny explicit
    predicate is not an application-scale search workload or a speedup claim.
    """
    started = perf_counter_ns()
    deadline = started + int(request.config.timeout_seconds * 1_000_000_000)
    marked = set(request.marked_states)
    count = 1 << request.num_qubits
    expected, worst = query_bounds(count, len(marked))
    for index in range(count):
        if perf_counter_ns() >= deadline:
            raise TimeoutError("Classical search exceeded config.timeout_seconds")
        candidate = format(index, f"0{request.num_qubits}b")
        if candidate in marked:
            result = ClassicalSearchResult(
                found_state=candidate,
                oracle_queries=index + 1,
                elapsed_ms=0.0,
                expected_queries=expected,
                worst_case_queries=worst,
            )
            finished = perf_counter_ns()
            if finished >= deadline:
                raise TimeoutError("Classical search exceeded config.timeout_seconds")
            return ClassicalSearchResult(
                found_state=result.found_state,
                oracle_queries=result.oracle_queries,
                elapsed_ms=(finished - started) / 1_000_000,
                expected_queries=result.expected_queries,
                worst_case_queries=result.worst_case_queries,
            )
    raise ValueError("request must contain a marked state inside the search space")
