"""Expected rejection: arbitrary helper calls inside the marked objective."""


def read_weights():
    return [3, 1, 4]


@qatlas.objective(num_bits=3)  # noqa: F821 - static compiler marker
def cost(x):
    weights = read_weights()
    return weights[0] * x[0]
