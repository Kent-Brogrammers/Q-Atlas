"""Compiler input: one marker, natural names, ordinary helpers and caller."""


def describe_score(score):
    return f"Selection score: {score}"


def evaluate_selection(include_red, include_blue, include_green):
    selected = include_red + include_blue + include_green
    benefit = 4 * include_red + 2 * include_blue + 5 * include_green
    return 6 * (selected - 1) ** 2 - benefit


if __name__ == "__main__":
    score = evaluate_selection(0, 0, 1)
    print(describe_score(score))


def build_qatlas_circuit():
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
    _qatlas_circuit.rz(10.0 * _qatlas_parameters["gamma_0"], 0)
    _qatlas_circuit.rz(8.0 * _qatlas_parameters["gamma_0"], 1)
    _qatlas_circuit.rz(11.0 * _qatlas_parameters["gamma_0"], 2)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 0, 1)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 0, 2)
    _qatlas_circuit.cp(-12.0 * _qatlas_parameters["gamma_0"], 1, 2)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 0)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 1)
    _qatlas_circuit.rx(2.0 * _qatlas_parameters["beta_0"], 2)
    _qatlas_circuit.global_phase += 8.5 * _qatlas_parameters["gamma_0"]
    return _qatlas_circuit
