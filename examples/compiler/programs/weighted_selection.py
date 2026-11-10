"""Full-file compiler input: a four-item selection report and replaceable circuit."""

from dataclasses import dataclass


@dataclass
class SelectionReport:
    assignment: str
    objective: float

    def describe(self):
        return f"Selection {self.assignment}: objective {self.objective}"


@qatlas.objective(num_bits=4)  # noqa: F821 - static compiler marker
def cost(x):
    weights = (3, 1, 4, 2)
    selected = 0
    reward = 0
    for i in range(4):
        selected += x[i]
        reward += weights[i] * x[i]
    return 6 * (selected - 2) ** 2 - reward


@qatlas.circuit  # noqa: F821 - static compiler marker
def build_circuit():
    from qiskit import QuantumCircuit

    old_circuit = QuantumCircuit(4)
    old_circuit.x(0)
    return old_circuit


def main():
    assignment = (1, 0, 1, 0)
    report = SelectionReport("1010", cost(assignment))
    print(report.describe())
    print(build_circuit())


if __name__ == "__main__":
    main()
