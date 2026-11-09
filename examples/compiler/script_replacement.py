# A full script: only the marked circuit factory will be replaced.
# This file is compiler input text; the markers are removed in the download.


@qatlas.objective(num_bits=3)  # noqa: F821 - source marker, never executed
def cost(x):
    selected = 0
    benefit = 0
    for i in range(3):
        selected += x[i]
        benefit += (i + 1) * x[i]
    penalty = 10 * (selected - 1) ** 2
    return penalty - benefit


@qatlas.circuit  # noqa: F821 - source marker, never executed
def build_circuit():
    # Your old circuit construction goes here. This entire function is replaced.
    from qiskit import QuantumCircuit

    old_circuit = QuantumCircuit(3)
    old_circuit.x(0)
    return old_circuit


if __name__ == "__main__":
    circuit = build_circuit()
    print(circuit)
