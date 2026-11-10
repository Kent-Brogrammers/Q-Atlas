"""Expected rejection: a cubic term needs an agreed quadratization strategy."""


@qatlas.objective(num_bits=3)  # noqa: F821 - static compiler marker
def cost(x):
    return x[0] * x[1] * x[2]
