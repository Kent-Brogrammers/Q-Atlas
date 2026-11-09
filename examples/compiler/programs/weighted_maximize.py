"""Full-file compiler input: weighted benefits with conflicting selections."""

import json


def format_report(assignment, value):
    return json.dumps({"assignment": assignment, "original_value": value}, sort_keys=True)


@qatlas.objective(num_bits=3, sense="maximize")  # noqa: F821 - static compiler marker
def benefit(x):
    weights = [2, 7, 3]
    total = 0
    for i in range(3):
        total += weights[i] * x[i]
    return total - 4 * x[0] * x[1] - 6 * x[1] * x[2]


@qatlas.circuit  # noqa: F821 - static compiler marker
def build_circuit():
    from qiskit import QuantumCircuit

    return QuantumCircuit(3)


if __name__ == "__main__":
    print(format_report("010", benefit((0, 1, 0))))
    print(build_circuit())
