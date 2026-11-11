"""Choose one of three energy projects. One binary choice maps to one qubit."""


@qatlas.objective  # noqa: F821 - static compiler marker
def plan_projects(solar, insulation, lighting):
    selected = solar + insulation + lighting
    impact = 8 * solar + 7 * insulation + 6 * lighting
    return 30 * (selected - 1) ** 2 - impact


if __name__ == "__main__":
    score = plan_projects(1, 0, 0)
    print(f"Portfolio objective: {score}")
