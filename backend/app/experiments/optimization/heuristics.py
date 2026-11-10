"""Seeded classical local search for the existing canonical minimization QUBO."""

from random import Random
from time import perf_counter_ns

from app.quantum.qubo import evaluate_qubo
from app.schemas.contracts import QUBO, QAOAConfig, SolverResult, TimingBreakdown


def run_heuristic(qubo: QUBO, config: QAOAConfig) -> SolverResult:
    """Return the best local minimum reached by eight bit-flip searches.

    Start from all zeros, then seven assignments drawn with Random(config.seed).
    Scan every one-bit neighbor and take the lowest-cost strict improvement,
    breaking equal neighbor costs by API bitstring order. Stop at a local minimum.
    Equal final costs choose the smallest reached local-minimum API string.

    Use the shared evaluator, including constant and canonical minimization sense.
    The result is a heuristic candidate with an unknown global optimum. The
    existing QUBO bounds remain 1–16 variables. Inputs and global RNG state are
    read-only. Only seed and timeout_seconds affect this classical method.

    The wall timer includes RNG setup, all starts, neighborhood evaluation,
    candidate extraction, and result construction. Raise TimeoutError on expiry.
    """
    started_ns = perf_counter_ns()
    deadline_ns = started_ns + int(config.timeout_seconds * 1_000_000_000)
    random = Random(config.seed)
    width = qubo.num_variables
    best = (float("inf"), "")

    def score(bitstring: str) -> float:
        if perf_counter_ns() >= deadline_ns:
            raise TimeoutError("Classical local search exceeded timeout_seconds")
        return evaluate_qubo(qubo, bitstring)

    for start in range(8):
        bitstring = "0" * width if start == 0 else format(random.getrandbits(width), f"0{width}b")
        objective = score(bitstring)
        while True:
            neighbor = (objective, bitstring)
            for index in range(width):
                flipped = "1" if bitstring[index] == "0" else "0"
                candidate = bitstring[:index] + flipped + bitstring[index + 1 :]
                neighbor = min(neighbor, (score(candidate), candidate))
            if neighbor[0] >= objective:
                break
            objective, bitstring = neighbor
        best = min(best, (objective, bitstring))

    finished_ns = perf_counter_ns()
    if finished_ns >= deadline_ns:
        raise TimeoutError("Classical local search exceeded timeout_seconds")
    result = SolverResult(
        algorithm="seeded_bit_flip_local_search",
        objective=best[0],
        best_bitstring=best[1],
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
        raise TimeoutError("Classical local search exceeded timeout_seconds")
    result.elapsed_ms = (finished_ns - started_ns) / 1_000_000
    return result
