# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=3, sense="maximize")  # noqa: F821 - source marker
def cost(x):
    return 5 - 2 * x[0] + x[1] * x[2]
