# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=3)  # noqa: F821 - source marker
def cost(x):
    """A small benefit/penalty objective."""
    weight = 2
    benefit = weight * x[0] + x[1]
    penalty = 3 * x[0] * x[2]
    total = 5 - benefit
    total = total + penalty
    return total
