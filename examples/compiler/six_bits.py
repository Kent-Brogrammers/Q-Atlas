# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=6)  # noqa: F821 - source marker
def cost(x):
    return (
        9
        - x[0]
        - 2 * x[1]
        - 3 * x[2]
        - 4 * x[3]
        - 5 * x[4]
        - 6 * x[5]
        + 2 * x[0] * x[5]
        + x[1] * x[4]
    )
