# Compiler input text: read or paste this file; do not run or import it.
@qatlas.objective(num_bits=4)  # noqa: F821 - source marker
def cost(x):
    total = 5
    for i in range(4):
        total -= (i + 1) * x[i]
    for i in range(3):
        total += 2 * x[i] * x[i + 1]
    return total
