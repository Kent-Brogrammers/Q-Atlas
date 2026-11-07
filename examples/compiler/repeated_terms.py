# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=3)  # noqa: F821 - source marker
def cost(x):
    return 2 + x[0] ** 2 + 2 * x[1] * x[0] - x[0] * x[1] - 3 * x[0]
