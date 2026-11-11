"""Choose two of five energy projects with two complementary project pairs."""


@qatlas.objective  # noqa: F821 - static compiler marker
def plan_projects(solar, insulation, lighting, storage, heating):
    selected = solar + insulation + lighting + storage + heating
    impact = 8 * solar + 7 * insulation + 6 * lighting + 5 * storage + 4 * heating
    synergy = 2 * solar * storage + insulation * heating
    return 30 * (selected - 2) ** 2 - impact - synergy


if __name__ == "__main__":
    score = plan_projects(1, 1, 0, 0, 0)
    print(f"Portfolio objective: {score}")
