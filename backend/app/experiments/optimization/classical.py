"""Classical objective evaluation for the project spec's canonical QUBO format."""

from collections.abc import Mapping, Sequence
from math import fsum
from typing import Any

from app.schemas.contracts import QUBO


def evaluate_qubo(qubo: QUBO | Mapping[str, Any], assignment: Sequence[int]) -> float:
    """Evaluate one binary assignment; this function does not find an optimum.

    Accept the shared validated QUBO model or a JSON-compatible mapping, which is
    validated and normalized through that same model. No second schema is defined.
    Entry ``assignment[i]`` is x[i], matching the API's x[0]-first bit order.
    Pass an indexed list/tuple, not a measurement string; Qiskit count conversion
    belongs at the future sampler boundary.
    """
    model = qubo if isinstance(qubo, QUBO) else QUBO.model_validate(qubo)
    if isinstance(assignment, (str, bytes)):
        raise ValueError("assignment must be an indexed sequence of binary values")
    if len(assignment) != model.num_variables:
        raise ValueError("assignment length must equal num_variables")
    if any(bit not in (0, 1) for bit in assignment):
        raise ValueError("assignment values must be binary (0 or 1)")

    terms = [model.constant]
    terms.extend(coefficient * assignment[i] for i, coefficient in enumerate(model.linear))
    terms.extend(
        term.coefficient * assignment[term.i] * assignment[term.j] for term in model.quadratic
    )
    return fsum(terms)
