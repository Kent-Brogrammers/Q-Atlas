"""Classical objective evaluation for the project spec's canonical QUBO format."""

from collections.abc import Mapping, Sequence
from math import fsum
from typing import Any


def evaluate_qubo(qubo: Mapping[str, Any], assignment: Sequence[int]) -> float:
    """Evaluate one binary assignment; this function does not find an optimum.

    ``qubo`` must already follow project spec section 6.1: canonical minimization,
    finite coefficients, a linear entry for each variable, and normalized pair
    terms with valid indices and i < j. Shared schema validation/normalization
    belongs at the caller boundary; no competing schema is defined here.

    Entry ``assignment[i]`` is x[i]. Pass an indexed list/tuple, not a measurement
    string. Conversion from Qiskit counts awaits the shared bit-order agreement.
    """
    if qubo["sense"] != "minimize":
        raise ValueError("evaluate_qubo requires canonical sense='minimize'")
    if isinstance(assignment, (str, bytes)):
        raise ValueError("assignment must be an indexed sequence of binary values")
    if len(assignment) != qubo["num_variables"]:
        raise ValueError("assignment length must equal num_variables")
    if any(bit not in (0, 1) for bit in assignment):
        raise ValueError("assignment values must be binary (0 or 1)")

    terms = [qubo["constant"]]
    terms.extend(coefficient * assignment[i] for i, coefficient in enumerate(qubo["linear"]))
    terms.extend(
        term["coefficient"] * assignment[term["i"]] * assignment[term["j"]]
        for term in qubo["quadratic"]
    )
    return fsum(terms)
