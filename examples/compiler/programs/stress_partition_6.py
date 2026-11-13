"""Balance six indivisible workloads between two groups of three.

Compiler input text: load in Q-Atlas; do not run or import this file.
Squared load and count penalties couple every pair and create a large cost range.
"""


@qatlas.objective(num_bits=6)  # noqa: F821 - static compiler marker
def balance_workloads(x):
    load = 7 * x[0] + 11 * x[1] + 13 * x[2] + 17 * x[3] + 19 * x[4] + 23 * x[5]
    count = x[0] + x[1] + x[2] + x[3] + x[4] + x[5]
    return (load - 45) ** 2 + 25 * (count - 3) ** 2
