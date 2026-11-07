# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=3)  # noqa: F821 - source marker
def cost(x):
    """Prefer one selected bit, with a benefit for later positions."""
    selected = 0
    benefit = 0
    for i in range(3):
        selected += x[i]
        benefit += (i + 1) * x[i]
    penalty = 10 * (selected - 1) ** 2
    return penalty - benefit
