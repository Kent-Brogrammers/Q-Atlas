"""Expected rejection: a binary input controls the loop bound."""


@qatlas.objective(num_bits=3)  # noqa: F821 - static compiler marker
def cost(x):
    total = 0
    for i in range(x[0]):
        total += x[i]
    return total
