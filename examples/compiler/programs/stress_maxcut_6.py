"""Split six linked sites into two groups to maximize separated link weight.

Compiler input text: load in Q-Atlas; do not run or import this file.
All 15 pairs interact. Positive triangles cannot have every edge cut at once.
"""


@qatlas.objective(num_bits=6)  # noqa: F821 - static compiler marker
def dense_cut(x):
    cut = (
        2 * (x[0] + x[1] - 2 * x[0] * x[1])
        + 4 * (x[0] + x[2] - 2 * x[0] * x[2])
        + 3 * (x[0] + x[3] - 2 * x[0] * x[3])
        + 9 * (x[0] + x[4] - 2 * x[0] * x[4])
        + 5 * (x[0] + x[5] - 2 * x[0] * x[5])
        + 2 * (x[1] + x[2] - 2 * x[1] * x[2])
        + 9 * (x[1] + x[3] - 2 * x[1] * x[3])
        + 9 * (x[1] + x[4] - 2 * x[1] * x[4])
        + (x[1] + x[5] - 2 * x[1] * x[5])
        + 7 * (x[2] + x[3] - 2 * x[2] * x[3])
        + 5 * (x[2] + x[4] - 2 * x[2] * x[4])
        + 9 * (x[2] + x[5] - 2 * x[2] * x[5])
        + 5 * (x[3] + x[4] - 2 * x[3] * x[4])
        + 6 * (x[3] + x[5] - 2 * x[3] * x[5])
        + (x[4] + x[5] - 2 * x[4] * x[5])
    )
    return -cut
