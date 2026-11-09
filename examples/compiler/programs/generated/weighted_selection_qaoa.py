"""Full-file compiler input: a four-item selection report and replaceable circuit."""

from dataclasses import dataclass


@dataclass
class SelectionReport:
    assignment: str
    objective: float

    def describe(self):
        return f"Selection {self.assignment}: objective {self.objective}"


def cost(x):
    weights = (3, 1, 4, 2)
    selected = 0
    reward = 0
    for i in range(4):
        selected += x[i]
        reward += weights[i] * x[i]
    return 6 * (selected - 2) ** 2 - reward


def build_circuit():
    """Build an unbound QAOA circuit; no sampling or optimization is performed.
    Parameter order: gamma_0, beta_0.
    x[i] maps to qubit i. No measurements are included.
    """
    from qiskit import QuantumCircuit as _qatlas_QuantumCircuit
    from qiskit.circuit import Parameter as _qatlas_Parameter

    _qatlas_parameters = {
        "gamma_0": _qatlas_Parameter("gamma_0"),
        "beta_0": _qatlas_Parameter("beta_0"),
    }
    _qatlas_circuit = _qatlas_QuantumCircuit(4)
    _qatlas_circuit.h(0)
    _qatlas_circuit.h(1)
    _qatlas_circuit.h(2)
    _qatlas_circuit.h(3)
    _qatlas_circuit.rz(21.0 * _qatlas_parameters["gamma_0"], 0)
    _qatlas_circuit.rz(19.0 * _qatlas_parameters["gamma_0"], 1)
    _qatlas_circuit.rz(22.0 * _qatlas_parameters["gamma_0"], 2)
    _qatlas_circuit.rz(20.0 * _qatlas_parameters["gamma_0"], 3)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 0, 1)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 0, 2)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 0, 3)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 1, 2)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 1, 3)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 2, 3)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 0)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 1)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 2)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 3)
    _qatlas_circuit.global_phase += 17.0 * _qatlas_parameters["gamma_0"]
    return _qatlas_circuit


def main():
    assignment = (1, 0, 1, 0)
    report = SelectionReport("1010", cost(assignment))
    print(report.describe())
    print(build_circuit())


if __name__ == "__main__":
    main()
