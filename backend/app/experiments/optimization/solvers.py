"""Classical baseline interface shared by Developers 2 and 3."""

from app.schemas.contracts import QUBO, QAOAConfig, SolverResult


def run_classical(qubo: QUBO, config: QAOAConfig) -> SolverResult:
    """Return measured baseline quality/runtime with the same budget and bit order as QAOA.

    Developer 3 selects and documents the baseline; raise TimeoutError on budget expiry.
    """
    raise NotImplementedError("Developer 3 must implement the classical baseline")
