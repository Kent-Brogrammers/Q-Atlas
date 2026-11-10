# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=3)  # noqa: F821 - source marker, not a runtime decorator
def cost(x):
    return 5 - 2 * x[0] + 3 * x[0] * x[2]
