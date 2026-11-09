"""Full-file compiler input: weighted benefits with conflicting selections."""

import json


def format_report(assignment, value):
    return json.dumps({"assignment": assignment, "original_value": value}, sort_keys=True)


def benefit(x):
    weights = [2, 7, 3]
    total = 0
    for i in range(3):
        total += weights[i] * x[i]
    return total - 4 * x[0] * x[1] - 6 * x[1] * x[2]


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
    _qatlas_circuit = _qatlas_QuantumCircuit(3)
    _qatlas_circuit.h(0)
    _qatlas_circuit.h(1)
    _qatlas_circuit.h(2)
    _qatlas_circuit.rz(2.0 * _qatlas_parameters["gamma_0"], 0)
    _qatlas_circuit.rz(7.0 * _qatlas_parameters["gamma_0"], 1)
    _qatlas_circuit.rz(3.0 * _qatlas_parameters["gamma_0"], 2)
    _qatlas_circuit.cp(-4.0 * _qatlas_parameters["gamma_0"], 0, 1)
    _qatlas_circuit.cp(-6.0 * _qatlas_parameters["gamma_0"], 1, 2)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 0)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 1)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 2)
    _qatlas_circuit.global_phase += 6.0 * _qatlas_parameters["gamma_0"]
    return _qatlas_circuit


if __name__ == "__main__":
    print(format_report("010", benefit((0, 1, 0))))
    print(build_circuit())
