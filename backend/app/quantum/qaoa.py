"""Agreed synchronous, in-process interface; implementation belongs to Developer 3."""

from app.schemas.contracts import QUBO, QAOAConfig, QAOAResult


def run_qaoa(qubo: QUBO, config: QAOAConfig) -> QAOAResult:
    """Solve a canonical minimization QUBO within config.timeout_seconds.

    Return x[0] first in best_bitstring, the canonical objective including its constant,
    and measured timings. Raise TimeoutError if the budget is exceeded; never return
    invented values. Caller maps timeouts to the shared TIMEOUT HTTP error.
    No hardware, graph conversion, source parsing, or HTTP dependencies belong here.
    """
    raise NotImplementedError("Developer 3 must implement the shared QAOA runner")
