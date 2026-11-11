"""Choose two of four energy projects, including a solar/storage synergy."""


@qatlas.objective  # noqa: F821 - static compiler marker
def plan_projects(solar, insulation, lighting, storage):
    selected = solar + insulation + lighting + storage
    impact = 8 * solar + 7 * insulation + 6 * lighting + 5 * storage
    synergy = 2 * solar * storage
    return 30 * (selected - 2) ** 2 - impact - synergy


if __name__ == "__main__":
    score = plan_projects(1, 1, 0, 0)
    print(f"Portfolio objective: {score}")
