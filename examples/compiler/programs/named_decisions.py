"""Compiler input: one marker, natural names, ordinary helpers and caller."""


def describe_score(score):
    return f"Selection score: {score}"


@qatlas.objective  # noqa: F821 - static source marker
def evaluate_selection(include_red, include_blue, include_green):
    selected = include_red + include_blue + include_green
    benefit = 4 * include_red + 2 * include_blue + 5 * include_green
    return 6 * (selected - 1) ** 2 - benefit


if __name__ == "__main__":
    score = evaluate_selection(0, 0, 1)
    print(describe_score(score))
