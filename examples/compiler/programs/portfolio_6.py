"""Choose three of six energy projects. Minimize penalty minus impact and synergy."""


@qatlas.objective  # noqa: F821 - static compiler marker
def plan_projects(solar, insulation, lighting, storage, heating, monitoring):
    selected = solar + insulation + lighting + storage + heating + monitoring
    impact = 8 * solar + 7 * insulation + 6 * lighting + 5 * storage + 4 * heating + 3 * monitoring
    synergy = 2 * solar * storage + insulation * heating
    return 30 * (selected - 3) ** 2 - impact - synergy


if __name__ == "__main__":
    score = plan_projects(1, 1, 1, 0, 0, 0)
    print(f"Portfolio objective: {score}")
