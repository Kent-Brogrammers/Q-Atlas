"""Select high-value tasks subject to nine pairwise conflicts.

Compiler input text: load in Q-Atlas; do not run or import this file.
The graph contains two triangles and three links between them. A penalty of 11
exceeds every individual reward, so an optimal selection contains no conflict.
"""


@qatlas.objective(num_bits=6)  # noqa: F821 - static compiler marker
def select_tasks(x):
    reward = 7 * x[0] + 6 * x[1] + 5 * x[2] + 4 * x[3] + 3 * x[4] + 2 * x[5]
    conflicts = (
        x[0] * x[1]
        + x[0] * x[2]
        + x[1] * x[2]
        + x[3] * x[4]
        + x[3] * x[5]
        + x[4] * x[5]
        + x[0] * x[3]
        + x[1] * x[4]
        + x[2] * x[5]
    )
    return 11 * conflicts - reward
