"""Shared objective evaluation in API bit order; no classical or quantum solver."""

import math

from app.schemas.contracts import QUBO


def evaluate_qubo(qubo: QUBO, bitstring: str) -> float:
    """Evaluate C including the constant. The leftmost character is x[0]."""
    if len(bitstring) != qubo.num_variables or any(bit not in "01" for bit in bitstring):
        raise ValueError("bitstring must contain exactly num_variables binary characters")
    bits = [int(bit) for bit in bitstring]
    value = (
        qubo.constant
        + sum(a * bit for a, bit in zip(qubo.linear, bits, strict=True))
        + sum(term.coefficient * bits[term.i] * bits[term.j] for term in qubo.quadratic)
    )
    if not math.isfinite(value):
        raise ValueError("objective overflow; rescale the QUBO")
    return value
